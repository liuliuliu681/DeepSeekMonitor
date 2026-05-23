import logging
import os

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.log")


class UILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S"
            )
        )

    def emit(self, record):
        msg = self.format(record)
        if self.callback:
            self.callback(msg, record.levelno)


def setup_logger(ui_callback=None):
    logger = logging.getLogger("deepseek-monitor")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
    )
    logger.addHandler(fh)

    if ui_callback:
        ui = UILogHandler(ui_callback)
        logger.addHandler(ui)

    return logger
