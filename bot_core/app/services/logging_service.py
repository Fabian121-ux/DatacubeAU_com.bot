import logging
import json
from typing import Any

from app.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event}
    payload.update({key: value for key, value in fields.items() if value is not None})
    logger.log(level, json.dumps(payload, default=str, sort_keys=True, ensure_ascii=True))
