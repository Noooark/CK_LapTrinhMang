import os
import socket
import ssl
import threading
import configparser
from typing import Optional, Dict, Any

from common.snapshots import SNAPSHOT_COMMANDS
from common.protocol import send_message, receive_message, Request


class ServerConnection:
    """
    Thread-safe client TCP connection manager to communicate with QuizServer.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, tls_ca=None):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._is_connected = False
        self.tls_ca = tls_ca if tls_ca is not None else os.getenv("QUIZ_TLS_CA")

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
            try:
                self._connect_locked()
                return True
            except (OSError, ValueError):
                return False

    def _connect_locked(self):
        if not self.is_connected:
            context = ssl.create_default_context(cafile=self.tls_ca) if self.tls_ca else None
            sock = socket.create_connection((self.host, int(self.port)), timeout=10.0)
            try:
                self.sock = context.wrap_socket(sock, server_hostname=self.host) if context else sock
            except (OSError, ValueError):
                sock.close()
                raise
            self._is_connected = True

    def _disconnect_locked(self):
        self._is_connected = False
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def disconnect(self):
        """Close the socket after any active request completes."""
        with self._lock:
            self._disconnect_locked()

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
            try:
                self._connect_locked()
                if command in SNAPSHOT_COMMANDS and not isinstance(self.sock, ssl.SSLSocket):
                    return {"status": "ERROR", "message": "Ảnh bằng chứng yêu cầu TLS.", "data": None}
                request = Request(command=command, token=token, data=data or {})
                if send_message(self.sock, request):
                    response = receive_message(self.sock)
                    if isinstance(response, dict):
                        return response
            except (OSError, ValueError):
                pass

            # A timeout can leave part of a frame unread. Reconnect on the next request.
            self._disconnect_locked()
            return {
                "status": "ERROR",
                "message": "Không thể liên lạc với máy chủ. Vui lòng thử lại.",
                "data": None,
                "transport_error": True,
            }
