import { io } from 'socket.io-client';

export class SocketService {
  private socket;

  constructor() {
    this.socket = io(import.meta.env.VITE_FLASK_SOCKET_URL || 'http://localhost:5000');
  }

  on(event: string, callback: Function) {
    this.socket.on(event, (data) => callback(data));
  }

  emit(event: string, data: any) {
    this.socket.emit(event, data);
  }

  disconnect() {
    this.socket.disconnect();
  }
}
