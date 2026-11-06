import os
import socket
import threading
import configparser
from typing import Optional, Dict, Any

from common.protocol import send_message, receive_message, Request, Response


class ServerConnection:
    """
    Thread-safe client TCP connection manager to communicate with QuizServer.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._is_connected = False

        if not self.host or not self.port:
            self._load_config()

    def _load_config(self):
        """Reads host and port from config.ini if not specified."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            try:
                config.read(config_path, encoding="utf-8")
                if not self.host:
                    self.host = config.get("client", "server_host", fallback="127.0.0.1")
                if not self.port:
                    self.port = config.getint("client", "server_port", fallback=9999)
            except Exception as e:
                print(f"[Network] Error reading config.ini: {e}")

        # Fallbacks if still not set
        if not self.host:
            self.host = "127.0.0.1"
        if not self.port:
            self.port = 9999

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self.sock is not None

    def connect(self) -> bool:
        """
        Connects to the TCP server.
        Returns True if successful, False otherwise.
        """
        with self._lock:
            if self.is_connected:
                return True

            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10.0)  # 10s connect/read timeout
                self.sock.connect((self.host, int(self.port)))
                self._is_connected = True
                print(f"[Network] Connected to server at {self.host}:{self.port}")
                return True
            except (socket.error, OSError) as e:
                print(f"[Network] Failed to connect to {self.host}:{self.port}: {e}")
                self._is_connected = False
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                    self.sock = None
                return False

    def disconnect(self):
        """Disconnects cleanly from the server."""
        with self._lock:
            self._is_connected = False
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
                print("[Network] Disconnected from server.")

    def send_request(
        self,
        command: str,
        data: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Thread-safe method to send a request and await the response.
        Returns response dictionary: {"status": "SUCCESS"/"ERROR", "message": "...", "data": ...}
        """
        with self._lock:
            if not self.is_connected:
                # Try auto-reconnect
                try:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.settimeout(10.0)
                    self.sock.connect((self.host, int(self.port)))
                    self._is_connected = True
                except Exception as e:
                    return {
                        "status": "ERROR",
                        "message": f"Không thể kết nối tới máy chủ ({e})",
                        "data": None
                    }

            req = Request(command=command, token=token, data=data or {})

            try:
                success = send_message(self.sock, req)
                if not success:
                    self._is_connected = False
                    return {
                        "status": "ERROR",
                        "message": "Không thể gửi dữ liệu tới máy chủ",
                        "data": None
                    }

                response_dict = receive_message(self.sock)
                if response_dict is None:
                    self._is_connected = False
                    return {
                        "status": "ERROR",
                        "message": "Mất kết nối hoặc máy chủ đóng kết nối",
                        "data": None
                    }

                return response_dict

            except (socket.timeout, socket.error, OSError) as e:
                self._is_connected = False
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                    self.sock = None
                return {
                    "status": "ERROR",
                    "message": f"Lỗi giao tiếp máy chủ: {e}",
                    "data": None
                }
