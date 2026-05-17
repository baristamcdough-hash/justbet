import { OddsUpdate } from '../types';

type MessageHandler = (data: OddsUpdate) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private subscribedMatches: string[] = [];

  connect() {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';
    const token = localStorage.getItem('access_token') || '';
    
    this.ws = new WebSocket(`${wsUrl}/ws/odds?token=${token}`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      // Re-subscribe to any previously subscribed matches
      if (this.subscribedMatches.length > 0) {
        this.subscribe(this.subscribedMatches);
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data: OddsUpdate = JSON.parse(event.data);
        this.handlers.forEach((handler) => handler(data));
      } catch {
        // Ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.reconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private reconnect() {
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;
    setTimeout(() => this.connect(), delay);
  }

  subscribe(matchIds: string[]) {
    this.subscribedMatches = [...new Set([...this.subscribedMatches, ...matchIds])];
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'subscribe', match_ids: matchIds }));
    }
  }

  unsubscribe(matchIds: string[]) {
    this.subscribedMatches = this.subscribedMatches.filter(
      (id) => !matchIds.includes(id)
    );
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'unsubscribe', match_ids: matchIds }));
    }
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

export const wsService = new WebSocketService();
