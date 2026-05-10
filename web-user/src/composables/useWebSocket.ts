import { ref, onUnmounted } from "vue";
import { useAuthStore } from "../stores/auth";

interface WSMessage {
  type: string;
  data?: any;
  ts?: string;
}

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const lastMessage = ref<WSMessage | null>(null);
  const listeners: Map<string, Set<(data: any) => void>> = new Map();

  function connect() {
    const auth = useAuthStore();
    const token = auth.token || localStorage.getItem("access_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws?token=${token}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      connected.value = true;
      ws.value = socket;
    };

    socket.onclose = () => {
      connected.value = false;
      ws.value = null;
      setTimeout(() => {
        if (auth.isLoggedIn) connect();
      }, 5000);
    };

    socket.onerror = () => {
      connected.value = false;
    };

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
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
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    connected.value = false;
  }

  onUnmounted(() => {
    disconnect();
  });

  return { connected, lastMessage, connect, disconnect, on, off, send };
}
