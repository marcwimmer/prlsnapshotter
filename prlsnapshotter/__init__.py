import click
from pathlib import Path
from .config import pass_config

global_data = {
    'config': None
}

@click.group(invoke_without_command=True)
@click.option("-t", "--template-machine", required=True)
@click.option("-p", "--machine-prefix", required=True)
@pass_config
def cli(config, template_machine, machine_prefix):
    config.template_machine = template_machine
    config.machine_prefix = machine_prefix
    global_data['config'] = config


from . import prlsnapshotter