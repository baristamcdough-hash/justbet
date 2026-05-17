"""
WebSocket server for real-time odds streaming.
Subscribes to Redis Pub/Sub and broadcasts odds updates to connected clients.
"""
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from app.config import get_settings
from app.redis_client import get_redis

settings = get_settings()

app = FastAPI(title="JustBet WebSocket Server")

# Connection manager
class ConnectionManager:
    def __init__(self):
        # match_id -> set of WebSocket connections
        self.subscriptions: dict[str, set[WebSocket]] = {}
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)
        # Remove from all subscriptions
        for match_id in list(self.subscriptions.keys()):
            self.subscriptions[match_id].discard(websocket)
            if not self.subscriptions[match_id]:
                del self.subscriptions[match_id]

    def subscribe(self, websocket: WebSocket, match_ids: list[str]):
        for match_id in match_ids:
            if match_id not in self.subscriptions:
                self.subscriptions[match_id] = set()
            self.subscriptions[match_id].add(websocket)

    def unsubscribe(self, websocket: WebSocket, match_ids: list[str]):
        for match_id in match_ids:
            if match_id in self.subscriptions:
                self.subscriptions[match_id].discard(websocket)

    async def broadcast_to_match(self, match_id: str, message: str):
        if match_id in self.subscriptions:
            dead_connections = set()
            for ws in self.subscriptions[match_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead_connections.add(ws)
            # Clean up dead connections
            for ws in dead_connections:
                self.disconnect(ws)


manager = ConnectionManager()


def validate_token(token: str) -> dict | None:
    """Validate JWT token from WebSocket query parameter."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


@app.websocket("/ws/odds")
async def websocket_odds(websocket: WebSocket, token: str = Query(default="")):
    """WebSocket endpoint for real-time odds streaming."""
    # Validate token
    if token:
        payload = validate_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
    
    await manager.connect(websocket)

    try:
        while True:
            # Receive subscription messages from client
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                match_ids = msg.get("match_ids", [])

                if action == "subscribe":
                    manager.subscribe(websocket, match_ids)
                    # Send current cached odds for subscribed matches
                    redis = get_redis()
                    for mid in match_ids:
                        cached = await redis.get(f"odds:current:{mid}")
                        if cached:
                            await websocket.send_text(json.dumps({
                                "type": "odds_snapshot",
                                "match_id": mid,
                                "odds": json.loads(cached),
                            }))

                elif action == "unsubscribe":
                    manager.unsubscribe(websocket, match_ids)

                elif action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def redis_listener():
    """Background task that listens to Redis pub/sub and broadcasts to WebSocket clients."""
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.psubscribe("odds:*")

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]

                # Extract match_id from channel "odds:{match_id}"
                if isinstance(channel, bytes):
                    channel = channel.decode()
                if isinstance(data, bytes):
                    data = data.decode()

                match_id = channel.replace("odds:", "")
                await manager.broadcast_to_match(match_id, data)
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe()


@app.on_event("startup")
async def startup():
    """Start Redis listener on server startup."""
    asyncio.create_task(redis_listener())


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "websocket", "credits": "Built by P.o.Riot"}
