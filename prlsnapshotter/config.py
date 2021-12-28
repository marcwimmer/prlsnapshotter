import atexit
import click
import logging
from pathlib import Path
import sys

class Config(object):
    def __init__(self, template_name=None, machine_prefix=None):
        super().__init__()
        self.template_name = template_name
        self.machine_prefix = machine_prefix

        def cleanup():
            pass

        atexit.register(cleanup)

    def setup_logging(self):
        FORMAT = '[%(levelname)s] %(asctime)s %(message)s'
        formatter = logging.Formatter(FORMAT)
        logging.basicConfig(format=FORMAT)
        self.logger = logging.getLogger('')  # root handler
        self.logger.setLevel(self.log_level)

        stdout_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stdout_handler)
        stdout_handler.setFormatter(formatter)


pass_config = click.make_pass_decorator(Config, ensure=True)
