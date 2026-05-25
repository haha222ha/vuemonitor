import { ref, onUnmounted } from "vue";
import { useAuthStore } from "../stores/auth";

interface WSMessage {
  type: string;
  channel?: string;
  data?: any;
  ts?: string;
}

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const lastMessage = ref<WSMessage | null>(null);
  const reconnectAttempts = ref(0);
  const maxReconnectAttempts = 10;
  const messageQueue: WSMessage[] = [];
  const listeners: Map<string, Set<(data: any) => void>> = new Map();

  function connect() {
    const auth = useAuthStore();
    const token = auth.token || localStorage.getItem("access_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: "auth", token }));
    };

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);

        if (msg.type === "auth" && msg.status === "ok") {
          connected.value = true;
          ws.value = socket;
          reconnectAttempts.value = 0;
          while (messageQueue.length > 0) {
            const queuedMsg = messageQueue.shift();
            if (queuedMsg) socket.send(JSON.stringify(queuedMsg));
          }
          return;
        }

        lastMessage.value = msg;

        if (msg.type === "ping") {
          socket.send(JSON.stringify({ type: "pong" }));
          return;
        }

        const handlers = listeners.get(msg.type);
        if (handlers) {
          handlers.forEach((fn) => fn(msg.data));
        }

        const wildcardHandlers = listeners.get("*");
        if (wildcardHandlers) {
          wildcardHandlers.forEach((fn) => fn(msg));
        }
      } catch {}
    };

    socket.onclose = () => {
      connected.value = false;
      ws.value = null;
      if (auth.isLoggedIn && reconnectAttempts.value < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.value, 30000);
        reconnectAttempts.value++;
        setTimeout(() => {
          connect();
        }, delay);
      }
    };

    socket.onerror = () => {
      connected.value = false;
    };
  }

  function on(type: string, handler: (data: any) => void) {
    if (!listeners.has(type)) {
      listeners.set(type, new Set());
    }
    listeners.get(type)!.add(handler);
  }

  function off(type: string, handler: (data: any) => void) {
    const handlers = listeners.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  function send(msg: WSMessage) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(msg));
    } else {
      // Queue message when disconnected
      messageQueue.push(msg);
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    connected.value = false;
    reconnectAttempts.value = 0; // Reset on manual disconnect
    messageQueue.length = 0; // Clear queue
  }

  function subscribe(channel: string) {
    send({ type: "subscribe", channel });
  }

  onUnmounted(() => {
    disconnect();
  });

  return { 
    connected, 
    lastMessage, 
    connect, 
    disconnect, 
    on, 
    off, 
    send,
    reconnectAttempts,
    subscribe
  };
}