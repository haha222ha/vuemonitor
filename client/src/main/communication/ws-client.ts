import WebSocket from "ws";
import { BrowserWindow } from "electron";
import axios from "axios";

let wsClient: WebSocket | null = null;
let communication: WSCommunication | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;

const HEARTBEAT_INTERVAL = 30000;
const HEARTBEAT_TIMEOUT = 60000;

export class WSCommunication {
  private ws: WebSocket | null = null;
  private mainWindow: BrowserWindow | null = null;
  private serverUrl: string = "";
  private token: string = "";
  private apiBase: string = "";
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private heartbeatTimeoutTimer: NodeJS.Timeout | null = null;
  private lastPongTime: number = 0;

  constructor() {}

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  connect(serverUrl: string, token: string): boolean {
    this.serverUrl = serverUrl;
    this.token = token;
    this.apiBase = serverUrl.replace(/\/$/, "");

    const wsUrl = `${serverUrl.replace(/^http/, "ws")}/ws`;

    try {
      this.ws = new WebSocket(wsUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      this.ws.on("open", () => {
        this.sendToRenderer("ws:connected", {});
        this.startHeartbeat();
      });

      this.ws.on("message", (data: WebSocket.Data) => {
        try {
          const msg = JSON.parse(data.toString());

          if (msg.type === "pong") {
            this.lastPongTime = Date.now();
            this.resetHeartbeatTimeout();
            return;
          }

          this.sendToRenderer(`ws:message`, msg);

          if (msg.type === "monitor:triggered" || msg.type === "notification:new") {
            this.sendToRenderer("notification", msg);
          }
        } catch {}
      });

      this.ws.on("close", () => {
        this.sendToRenderer("ws:disconnected", {});
        this.stopHeartbeat();
        this.scheduleReconnect();
      });

      this.ws.on("error", () => {
        this.stopHeartbeat();
        this.scheduleReconnect();
      });

      return true;
    } catch {
      return false;
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(type: string, data: unknown): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.ws.send(JSON.stringify({ type, data }));
    return true;
  }

  async pushToCloud(data: unknown): Promise<unknown> {
    try {
      const response = await axios.post(`${this.apiBase}/api/v1/sync/push`, data, {
        headers: { Authorization: `Bearer ${this.token}` },
      });
      return response.data;
    } catch (error) {
      return { error: true, message: (error as Error).message };
    }
  }

  private startHeartbeat(): void {
    this.lastPongTime = Date.now();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
        this.heartbeatTimeoutTimer = setTimeout(() => {
          if (Date.now() - this.lastPongTime > HEARTBEAT_TIMEOUT) {
            this.ws?.terminate();
          }
        }, 10000);
      }
    }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.resetHeartbeatTimeout();
  }

  private resetHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      if (this.serverUrl && this.token) {
        this.connect(this.serverUrl, this.token);
      }
    }, 5000);
  }

  private sendToRenderer(channel: string, data: unknown): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }
}

export function getCommunication(): WSCommunication {
  if (!communication) {
    communication = new WSCommunication();
  }
  return communication;
}
