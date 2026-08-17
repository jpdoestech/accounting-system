"""
Logging configuration.

Structured (JSON-ish key=value) logging to stdout so a production
deployment can ship logs to any log aggregator without a custom
parser -- deliberately not writing to local files, since a container/
process-managed deployment shouldn't assume a persistent local disk.
"""
import logging
import sys

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = logging.INFO if settings.is_production else logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt='level=%(levelname)s logger=%(name)s msg="%(message)s"',
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Quiet down noisy third-party loggers unless something's actually wrong.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
