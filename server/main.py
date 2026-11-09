"""
Quiz Server - Main TCP server entry point.
Multi-threaded server that handles multiple client connections.
"""

import socket
import ssl
import threading
import signal
import sys
import configparser
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('QuizServer')

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.client_handler import ClientHandler
from pymysql import MySQLError
from server.service.snapshot_service import SnapshotService
from server.service.auth_service import AuthService
from server.service.proctoring_service import ProctoringService


class QuizServer:
    """Multi-threaded TCP Quiz Server."""

    def __init__(self, host: str = '0.0.0.0', port: int = 9999, max_connections: int = 50,
                 tls_context=None, snapshots=None):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.server_socket = None
        self.running = False
        self.clients: list[ClientHandler] = []
        self.lock = threading.Lock()

        # Shared auth service (session store)
        self.auth_service = AuthService()
        self.monitor_stop = threading.Event()
        self.tls_context = tls_context
        self.snapshots = snapshots

    def start(self):
        """Start the server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_connections)
            self.server_socket.settimeout(1.0)  # Allow periodic check for shutdown
            self.running = True
            self.monitor_stop.clear()
            threading.Thread(target=self._monitor_heartbeats, daemon=True).start()
            if self.snapshots is not None:
                threading.Thread(target=self._cleanup_snapshots, daemon=True).start()

            logger.info("=" * 55)
            logger.info("  📝 QUIZ SERVER - Ứng dụng Trắc nghiệm Trực tuyến")
            logger.info("=" * 55)
            logger.info(f"  🌐 Server đang chạy tại: {self.host}:{self.port}")
            logger.info(f"  📊 Số kết nối tối đa: {self.max_connections}")
            logger.info(f"  ⏹  Nhấn Ctrl+C để dừng server")
            logger.info("=" * 55)

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    handler = ClientHandler(client_socket, address, self.auth_service,
                                            self.tls_context, self.snapshots)
                    with self.lock:
                        self.clients.append(handler)
                    handler.start()
                    self._cleanup_dead_clients()
                    logger.info(f"📌 Đang phục vụ {self._active_count()} client(s)")
                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break

        except KeyboardInterrupt:
            logger.info("\n⚠ Nhận tín hiệu dừng...")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop()

    def _cleanup_snapshots(self):
        while not self.monitor_stop.is_set():
            try:
                self.snapshots.cleanup()
            except (MySQLError, OSError):
                logger.exception("Snapshot retention cleanup failed")
            self.monitor_stop.wait(300)

    def _monitor_heartbeats(self):
        while not self.monitor_stop.wait(2):
            try:
                ProctoringService.sweep_timeouts()
            except MySQLError:
                logger.exception("Heartbeat sweep failed")

    def stop(self):
        """Stop the server and clean up."""
        self.running = False
        self.monitor_stop.set()
        logger.info("🛑 Đang dừng server...")

        # Stop all client handlers
        with self.lock:
            for client in self.clients:
                client.stop()
            self.clients.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        logger.info("✅ Server đã dừng thành công")

    def _cleanup_dead_clients(self):
        """Remove finished client handler threads."""
        with self.lock:
            self.clients = [c for c in self.clients if c.is_alive()]

    def _active_count(self) -> int:
        """Count active client connections."""
        with self.lock:
            return sum(1 for c in self.clients if c.is_alive())


def load_config() -> dict:
    """Load server configuration from config.ini."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config.ini'
    )
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    return {
        'host': config.get('server', 'host', fallback='0.0.0.0'),
        'port': config.getint('server', 'port', fallback=9999),
        'max_connections': config.getint('server', 'max_connections', fallback=50),
    }


def tls_context_from_env():
    cert, key = os.getenv("QUIZ_TLS_CERT"), os.getenv("QUIZ_TLS_KEY")
    if not cert and not key:
        return None
    if not cert or not key:
        raise ValueError("Set both QUIZ_TLS_CERT and QUIZ_TLS_KEY")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    return context


if __name__ == '__main__':
    cfg = load_config()
    server = QuizServer(
        host=cfg['host'],
        port=cfg['port'],
        max_connections=cfg['max_connections'],
        tls_context=tls_context_from_env(), snapshots=SnapshotService.from_env()
    )

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    server.start()
