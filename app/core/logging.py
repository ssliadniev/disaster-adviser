import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging. Call once at startup."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
