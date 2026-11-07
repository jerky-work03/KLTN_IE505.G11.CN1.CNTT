#!/bin/sh
set -eu
timeout 420 cloud-init status --wait
python3 - <<'PY'
import json
import pathlib
import subprocess

def command(*args):
    return subprocess.check_output(args, text=True).strip()

result = {
    'cloudInit': 'done',
    'python': command('python3', '--version'),
    'venvPython': command('/home/azureuser/kltn/.venv/bin/python', '--version'),
    'git': command('git', '--version'),
    'docker': command('docker', '--version'),
    'dockerService': command('systemctl', 'is-active', 'docker'),
    'workingDirectoryExists': pathlib.Path('/home/azureuser/kltn').is_dir(),
    'sshHostPublicKey': pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip(),
    'sshHostFingerprint': command('ssh-keygen', '-lf', '/etc/ssh/ssh_host_ed25519_key.pub'),
}
print(json.dumps(result, indent=2))
PY
