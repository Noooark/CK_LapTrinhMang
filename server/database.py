"""
Database connection manager using PyMySQL.
Reads configuration from config.ini.
"""

import pymysql
import configparser
import os
import logging

logger = logging.getLogger(__name__)

# Tìm file config.ini ở thư mục gốc dự án
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.ini')


def _load_config() -> dict:
    """Load database config from config.ini."""
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')
    return {
        'host': config.get('database', 'host', fallback='localhost'),
        'port': config.getint('database', 'port', fallback=3306),
        'user': config.get('database', 'user', fallback='root'),
        'password': config.get('database', 'password', fallback=''),
        'db_name': config.get('database', 'db_name', fallback='quiz_app'),
    }


class DatabaseConnection:
    """Simple MySQL connection manager with context manager support."""

    _config = None

    @classmethod
    def _get_config(cls):
        if cls._config is None:
            cls._config = _load_config()
        return cls._config

    @classmethod
    def get_connection(cls) -> pymysql.Connection:
        """Create and return a new database connection."""
        cfg = cls._get_config()
        try:
            conn = pymysql.connect(
                host=cfg['host'],
                port=cfg['port'],
                user=cfg['user'],
                password=cfg['password'],
                database=cfg['db_name'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            return conn
        except pymysql.Error as e:
            logger.error(f"Lỗi kết nối database: {e}")
            raise

    def __init__(self):
        self.conn = None

    def __enter__(self) -> pymysql.Connection:
        self.conn = self.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()
        return False
