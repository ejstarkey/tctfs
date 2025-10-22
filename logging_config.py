"""
Structured logging configuration for TCTFS.
Provides JSON-formatted logs with correlation IDs.
"""
import logging
import sys
import json
from datetime import datetime
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    # Fallback if python-json-logger not installed
    jsonlogger = None


class CustomJsonFormatter(jsonlogger.JsonFormatter if jsonlogger else logging.Formatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record, record, message_dict):
        if jsonlogger:
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id


def setup_logging(app):
    """
    Configure application logging.
    
    Args:
        app: Flask application instance
    """
    log_level = logging.DEBUG if app.debug else logging.INFO
    
    # Remove default handlers
    app.logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if jsonlogger:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Fallback to standard formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add handler to app logger
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    
    app.logger.info("Logging configured", extra={
        'log_level': logging.getLevelName(log_level),
        'environment': app.config.get('FLASK_ENV', 'unknown')
    })


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records from Flask request context."""
    
    def filter(self, record):
        try:
            from flask import has_request_context, g
            
            if has_request_context():
                record.correlation_id = getattr(g, 'correlation_id', 'no-correlation-id')
            else:
                record.correlation_id = 'background-task'
        except ImportError:
            record.correlation_id = 'no-flask-context'
        
        return True
