import logging


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="[%(created).3f] [%(levelname)s] [%(name)s] %(message)s",
        force=True,
    )
    for logger_name in ("uvicorn", "uvicorn.error"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers.clear()
        framework_logger.propagate = True
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
