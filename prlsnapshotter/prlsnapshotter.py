#!/usr/bin/env python3
import os
import sys
import time
import arrow
import shutil
from pathlib import Path
import json
import inquirer
import click
import subprocess
from . import cli
from .config import pass_config


def _stop_machine(machine):
    machine = _get_machine(machine)
    if not machine:
        return
    if machine['status'] == 'running':
        subprocess.check_call(["prlctl", "stop", machine['name']])

def _stop_all_other_machines(keep):
    for machine in _get_all_machines():
        if machine['status'] in ['running']:
            subprocess.check_output(["prlctl", "stop", machine['name']])

def _get_all_machines():
    return json.loads(subprocess.check_output(["prlctl", "list", "-a", "-f", "-j"]))

def _get_machine(name):
    data = [x for x in _get_all_machines() if x['name'] == name]
    if data:
        return data[0]
    return data

def _make_sure_machine_exists(config, name):
    all_machines = _get_all_machines()
    exists = [x for x in all_machines if x['name'] == name]
    if not exists:
        _clone_machine(config, name)

def _clone_machine(config, name):
    subprocess.check_call(['prlctl', 'clone', config.template_name, '--name', name])

# def install_new_parallels_machine():
#     machine_name = machine_prefix + "template"
#     subprocess.check_call(['prlctl', 'exec', machine_name, 'apt update'])
#     subprocess.check_call(['prlctl', 'exec', machine_name, 'apt install -y postgresql'])
#     pass

@cli.command(help="Starts a parallels machine")
@click.argument('machine')
@click.option('-s', '--single', is_flag=True)
@pass_config
def start(config, machine, single):
    machine = config.machine_prefix + machine
    _make_sure_machine_exists(config, machine)
    data = _get_machine(machine)
    click.secho(f"Machine is listening on {data['ip_configured']}")
    if single:
        _stop_all_other_machines(machine)
    if data['status'] == 'running':
        return
    subprocess.check_call(["prlctl", "start", machine])

@cli.command(help="Takes a snapshot in a machine", no_args_is_help=True)
@click.argument('machine', required=True)
@click.argument('name', required=True)
@pass_config
def save_snapshot(config, machine, name):
    machine = config.machine_prefix + machine
    subprocess.check_call([
        "prlctl", "snapshot", machine,
        '-n', name
        ])

def _select_snapshot(machine):
    snaps = _get_all_snapshots(machine)
    snaps = list(filter(lambda x: x['machine'] == machine, snaps))

    snaps_display = [(f"{x['name']} of {x['date']}", x['id']) for x in snaps]
    questions = [
        inquirer.List('snapshot', message="Please choose a snapshot", choices=snaps_display),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        return
    return answers['snapshot']

@cli.command(help="Takes a snapshot in a machine", no_args_is_help=True)
@click.argument("machine", required=True)
@pass_config
def restore_snapshot(config, machine):
    machine = config.machine_prefix + machine
    snapshot = _select_snapshot(machine)

    subprocess.check_call([
        "prlctl", "snapshot-switch", machine,
        '--id', snapshot
        ])

@cli.command(help="Deletes a snapshot in a machine", no_args_is_help=True)
@click.argument("machine", required=True)
@pass_config
def delete_snapshot(config, machine):
    machine = config.machine_prefix + machine
    snapshot = _select_snapshot(machine)

    subprocess.check_call([
        "prlctl", "snapshot-delete", machine,
        '--id', snapshot
        ])

@cli.command(help="Deletes a snapshot in a machine", no_args_is_help=True)
@click.argument("machine", required=True)
@pass_config
def clear_all_snapshots(config, machine):
    machine = config.machine_prefix + machine

    for snapshot in _get_all_snapshots(machine):
        subprocess.check_call([
            "prlctl", "snapshot-delete", machine,
            '--id', snapshot['id']
            ])

def _get_all_snapshots(machine):
    snaps = []
    output = subprocess.check_output([
        "prlctl", "snapshot-list", machine,
        '-j'
    ])
    if not output:
        return []
    for snapid, snap in json.loads(output).items():
        snaps.append({
            'id': snapid,
            'machine': machine,
            'date': snap['date'],
            'name': snap['name']
        })
    return snaps

@cli.command(no_args_is_help=True)
@click.argument("machine")
@pass_config
def list_snapshots(config, machine):
    machine = config.machine_prefix + machine
    for snap in _get_all_snapshots(machine):
        if snap['machine'] != machine:
            continue
        click.secho(f"{snap['name']} from {snap['date']} [{snap['id']}]")

@cli.command()
@pass_config
def list_machines(config):
    for machine in _get_all_machines():
        if not machine['name'].startswith(config.machine_prefix):
            continue
        if machine['name'] == config.machine_prefix + "template":
            continue
        click.secho(f"{machine['name']} - {machine['status']}")

@cli.command(no_args_is_help=True)
@click.argument("machine")
@pass_config
def destroy(config, machine):
    if machine == 'template':
        click.secho("Cannot delete template machine.")
        sys.exit(-1)

    machine = config.machine_prefix + machine
    data = _get_machine(machine)
    if not data:
        click.secho(f"Machine not found {machine}")
        return

    _stop_machine(machine)
    output = subprocess.check_call([
        "prlctl", "unregister", machine
    ])

    path = Path(os.path.expanduser("~/Parallels")) / (machine + '.pvm')
    started = arrow.get()
    while (arrow.get() - started).total_seconds() < 20:
        try:
            if path.exists():
                shutil.rmtree(path)
                click.secho(f"Successfully deleted {path}")
        except:
            pass
        else:
            break
        time.sleep(1)

@cli.command(help="Makes a quick call prefix")
@click.argument("path")
@pass_config
def shortcut(config, path):
    path = Path(path)
    if path.exists():
        if 'prl-snap' not in path.read_text():
            click.secho("File is not a prl snap file and cannot be overwritten.", fg='red')
            sys.exit(1)

        questions = [
            inquirer.Confirm('continue', default=True, message=f"{path} will be deleted. Continue?"),
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            return
        if not answers['continue']:
            return

    path.write_text("""#!/bin/bash
if [[ -z "$@" ]]; then
    set -- "--help"
fi
prl-snap -t {template_name} -p {machine_prefix} "$@"
    """.format(
        exe=sys.executable,
        template_name=config.template_name,
        machine_prefix=config.machine_prefix,
    ))
    os.chmod(path, 0o775)
