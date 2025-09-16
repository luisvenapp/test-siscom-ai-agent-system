import inspect
import logging
import sys

from loguru import logger

from conf import settings


def setup_intercept_handler() -> None:
    """
    Configure standard logging to intercept and route to Loguru.

    This replaces the root logger handlers with a custom
    InterceptHandler that forwards records to Loguru.
    """

    class InterceptHandler(logging.Handler):
        """
        Logging handler that intercepts standard logging records
        and routes them through Loguru.
        """

        def emit(self, record: logging.LogRecord) -> None:
            """
            Emit a log record to Loguru, preserving level and stack depth.
            """
            # Determine the Loguru level name if it exists, else use record level
            level_name = record.levelname
            if level_name in logger._core.levels:
                level = logger.level(level_name).name
            else:
                level = record.levelno

            # Find the first frame outside the logging module
            frame = inspect.currentframe()
            depth = 0
            while frame and (
                depth == 0 or frame.f_code.co_filename == logging.__file__
            ):
                frame = frame.f_back
                depth += 1

            # Forward the message to Loguru
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Configure the basic logging to use our intercept handler
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.DEBUG,
        format=(
            "%(asctime)s - %(levelname)s - %(message)s "
            "(%(module)s:%(filename)s:%(lineno)d)"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    # Replace existing handlers on the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.DEFAULT_LOG_LEVEL)

    # Clear handlers for all existing loggers and enable propagation
    for name in logging.root.manager.loggerDict.keys():
        logger_obj = logging.getLogger(name)
        logger_obj.handlers = []
        logger_obj.propagate = True


def configure_loguru_logger() -> None:
    """
    Set up Loguru logger with console and optional file sinks.
    """
    # Remove default Loguru handlers
    logger.remove()

    # Add console output with configured format and level
    logger.add(
        sys.stdout,
        format=settings.LOG_FORMAT,
        level=settings.DEFAULT_LOG_LEVEL,
    )

    # Optionally add a rotating file sink
    if settings.USE_FILE_LOG:
        log_file = f"/tmp/{settings.PROJECT_NAME}.log"
        logger.add(
            log_file,
            rotation="10 MB",
            format=settings.LOG_FORMAT,
            level=settings.DEFAULT_LOG_LEVEL,
        )


def setup_logging() -> None:
    """
    Main entry point to configure both standard logging and Loguru.
    """
    setup_intercept_handler()
    configure_loguru_logger()


def get_logger(name: str) -> logger.__class__:
    """
    Get a named Loguru logger instance, ensuring setup is run.

    Args:
        name: Identifier to bind to the logger.

    Returns:
        A Loguru logger bound to the given name.
    """
    setup_logging()
    return logger.bind(name=name)
