"""
Logging configuration for VerificAI Backend
"""

import logging
import logging.config
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry["ip_address"] = record.ip_address

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        formatted = super().format(record)
        return f"{color}{formatted}{self.RESET}"


def setup_logging() -> None:
    """Setup logging configuration"""

    # Create logs directory if it doesn't exist

    # Configure logging
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "app.core.logging.JSONFormatter"
            },
            "colored": {
                "()": "app.core.logging.ColoredFormatter",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "colored" if settings.LOG_FORMAT == "colored" else "standard",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": "WARNING" if not settings.DEBUG else "INFO",
                "propagate": False
            },
            "redis": {
                "handlers": ["console"],
                "level": "WARNING" if not settings.DEBUG else "INFO",
                "propagate": False
            }
        }
    }
    
        #check environment variable to disable file logging in production
    if settings.ENVIRONMENT == "development":
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_config["loggers"][""]["handlers"].append("file")
        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "json" if settings.LOG_FORMAT == "json" else "standard",
            "filename": log_dir / "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        }
    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


class RequestLogger:
    """Logger for HTTP requests"""

    def __init__(self, logger_name: str = "http.requests"):
        self.logger = get_logger(logger_name)

    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """Log HTTP request information"""
        self.logger.info(
            f"HTTP {method} {url} - {status_code} - {response_time:.3f}s",
            extra={
                "method": method,
                "url": url,
                "status_code": status_code,
                "response_time": response_time,
                "user_id": user_id,
                "ip_address": ip_address,
                "request_id": request_id
            }
        )


class SecurityLogger:
    """Logger for security events"""

    def __init__(self, logger_name: str = "security.events"):
        self.logger = get_logger(logger_name)

    def log_authentication_event(
        self,
        event_type: str,
        username: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log authentication events"""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"Auth {event_type}: {username} - {'Success' if success else 'Failed'}",
            extra={
                "event_type": event_type,
                "username": username,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )

    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "INFO",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Log security events"""
        level = getattr(logging, severity.upper(), logging.INFO)
        self.logger.log(
            level,
            f"Security Event: {event_type} - {description}",
            extra={
                "event_type": event_type,
                "description": description,
                "user_id": user_id,
                "ip_address": ip_address
            }
        )


# Initialize logging - moved to main.py to avoid circular import
# setup_logging()

# Create logger instances
app_logger = get_logger("verificai")
request_logger = RequestLogger()
security_logger = SecurityLogger()