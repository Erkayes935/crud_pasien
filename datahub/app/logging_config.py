import logging
import sys

def configure_logging(level: str = "INFO"):
    lvl = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        return 
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    root.setLevel(lvl)
    root.addHandler(handler)

def get_logger(name: str):
    configure_logging()
    return logging.getLogger(name)