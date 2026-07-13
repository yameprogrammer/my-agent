// WebSocket Manager for Real-time workflow streaming
import { getToken } from '../utils/auth.js';
import { showToast } from '../components/toast.js';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
    this.projectId = null;
    this.episodeId = null;
    this.status = 'disconnected'; // disconnected, connecting, connected
  }

  connect(projectId, episodeId) {
    this.projectId = projectId;
    this.episodeId = episodeId;
    this.status = 'connecting';
    this.trigger('status-change', 'connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    // Proxied URL via Vite config
    const wsUrl = `${protocol}//${host}/ws/projects/${projectId}/episodes/${episodeId}/write`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    try {
      this.ws = new WebSocket(wsUrl);
    } catch (e) {
      console.error('WebSocket connection failed to initiate:', e);
      this.handleClose();
      return;
    }

    this.ws.onopen = () => {
      console.log('WebSocket connection opened');
      this.status = 'connected';
      this.reconnectAttempts = 0;
      this.trigger('status-change', 'connected');
      
      // Auto authenticate
      const token = getToken();
      if (token) {
        this.send('auth', { token });
      } else {
        showToast('인증 토큰이 유효하지 않습니다.', 'error');
        this.disconnect();
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WS Received:', data);
        
        const eventName = data.event || data.type;
        if (eventName === 'error' || data.event === 'error' || data.type === 'error') {
          showToast(data.message || '오류가 발생했습니다.', 'error');
        }
        
        if (eventName) {
          this.trigger(eventName, data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err, event.data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
      this.trigger('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
      this.handleClose();
    };
  }

  handleClose() {
    this.status = 'disconnected';
    this.trigger('status-change', 'disconnected');
    this.ws = null;

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectAttempts * 2000;
      console.log(`Reconnecting in ${delay}ms... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      showToast(`연결이 끊어졌습니다. 재연결을 시도합니다... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'info');
      setTimeout(() => {
        if (this.status === 'disconnected' && this.projectId && this.episodeId) {
          this.connect(this.projectId, this.episodeId);
        }
      }, delay);
    } else {
      showToast('서버 연결에 실패했습니다. 다시 시도해주세요.', 'error');
    }
  }

  send(action, payload = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send, WebSocket is not open');
      return false;
    }
    const message = { action, ...payload };
    console.log('WS Sending:', message);
    this.ws.send(JSON.stringify(message));
    return true;
  }

  disconnect() {
    this.projectId = null;
    this.episodeId = null;
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto reconnect
    if (this.ws) {
      this.ws.close();
    }
  }

  // Event handler registration
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
  }

  trigger(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => {
        try {
          cb(data);
        } catch (e) {
          console.error(`Error in WebSocket event listener for ${event}:`, e);
        }
      });
    }
  }
}

export const wsManager = new WebSocketManager();
