﻿﻿﻿﻿﻿﻿﻿﻿import WebSocket from "ws";
import { BrowserWindow } from "electron";
import axios from "axios";
import { logger } from "../logger/logger";

const wsClient: WebSocket | null = null;
let communication: WSCommunication | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;

const HEARTBEAT_INTERVAL = 30000;
const HEARTBEAT_TIMEOUT = 60000;
const MAX_RECONNECT_DELAY = 60000;
const BASE_RECONNECT_DELAY = 1000;

export class WSCommunication {
  private ws: WebSocket | null = null;
  private mainWindow: BrowserWindow | null = null;
  private serverUrl: string = "";
  private token: string = "";
  private apiBase: string = "";
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private heartbeatTimeoutTimer: NodeJS.Timeout | null = null;
  private lastPongTime: number = 0;
  private reconnectAttempts: number = 0;

  constructor() {}

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
    window.on("closed", () => {
      if (this.mainWindow === window) {
        this.mainWindow = null;
      }
    });
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
        this.reconnectAttempts = 0;
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
        } catch (err) { logger.warn("[Main] operation failed:", String(err)); }
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

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  async request(method: string, url: string, data?: unknown): Promise<unknown> {
    try {
      const config: { method: string; url: string; headers: Record<string, string>; data?: unknown } = {
        method,
        url: `${this.apiBase}${url}`,
        headers: { Authorization: `Bearer ${this.token}` },
      };
      if (data) config.data = data;
      const response = await axios(config);
      return response.data;
    } catch (error) {
      return { error: true, message: (error as Error).message };
    }
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
    this.reconnectAttempts++;
    const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, this.reconnectAttempts - 1), MAX_RECONNECT_DELAY);
    const jitter = Math.random() * delay * 0.3;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      if (this.serverUrl && this.token) {
        this.connect(this.serverUrl, this.token);
      }
    }, delay + jitter);
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
