import { useEffect, useRef } from 'react';
import { wsService } from '../services/ws';
import { OddsUpdate } from '../types';

export function useWebSocket(
  matchIds: string[],
  onUpdate: (data: OddsUpdate) => void
) {
  const handlerRef = useRef(onUpdate);
  handlerRef.current = onUpdate;

  useEffect(() => {
    wsService.connect();

    const unsubscribe = wsService.onMessage((data) => {
      handlerRef.current(data);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (matchIds.length > 0) {
      wsService.subscribe(matchIds);
    }
    return () => {
      if (matchIds.length > 0) {
        wsService.unsubscribe(matchIds);
      }
    };
  }, [matchIds]);
}
