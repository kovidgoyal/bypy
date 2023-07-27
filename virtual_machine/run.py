#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

import atexit
import json
import os
import shlex
import socket
import subprocess
import sys
import threading
from functools import wraps
from time import monotonic, sleep

is_running_remotely = False
monitor_template = '{}/monitor.socket'
machine_spec_template = '{}/machine-spec'
BUILD_VM_USER = 'kovid'
ssh_masters = set()
disable_known_hosts = ['-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no', '-o', 'LogLevel=ERROR']

try:
    import pwd
except ModuleNotFoundError:
    USER = os.environ.get('USER', 'kovid')
else:
    USER = pwd.getpwuid(os.geteuid()).pw_name


def os_from_machine_spec(raw):
    if 'isa-applesmc' in raw:
        return 'macos'
    if '-rtc base=localtime,clock=host' in raw:
        return 'windows'
    return 'linux'


def metadata_from_vm_dir(vm_dir):
    with open(machine_spec_template.format(vm_dir)) as f:
        raw = f.read()
    return {'os': os_from_machine_spec(raw), 'is_accelerated': 'accel=kvm' in raw}


def shutdown_cmd_for_os(os):
    if os == 'linux':
        return ['sudo', 'poweroff']
    if os == 'windows':
        return 'shutdown.exe -s -f -t 0'.split()
    return ['osascript', '-e', """'tell app "System Events" to shut down'"""]


with_gui = False


def cmdline_for_machine_spec(lines, monitor_path):
    ans = []
    prefix = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            ans.extend(shlex.split(line))
            if line.startswith('-machine '):
                spec = line.split(' ', 1)[-1]
                if 'q35' in spec:
                    prefix.append('qemu-system-x86_64')
                elif 'virt' in spec:
                    prefix.append('qemu-system-aarch64')
                else:
                    raise ValueError(f'Unknown machine type: {spec}')
                if 'accel=kvm' in spec:
                    prefix.append('-enable-kvm')
    if not prefix:
        raise ValueError('No -machine specification found')
    ans.extend(['-k', 'en-us'])
    ans.extend(['-monitor', f'unix:{monitor_path},server,nowait'])
    if not with_gui:
        ans.append('-nographic')
    return prefix + ans


def run_monitor_command(monitor_path, cmd='info usernet', data_is_complete=lambda x: False, get_output=True, timeout=0.5):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(monitor_path)
    with s:
        s.sendall(cmd.encode('utf-8') + b'\n')
        if not get_output:
            return ''
        data = b''
        begin = monotonic()
        s.setblocking(False)
        while True:
            if data and monotonic() - begin > timeout:
                break
            try:
                q = s.recv(4096)
            except BlockingIOError:
                sleep(0.001)
                continue
            if q:
                data += q
                q = data.decode('utf-8', 'replace')
                if data_is_complete(q):
                    return q
                begin = monotonic()
            else:
                sleep(0.01)
        return data.decode('utf-8', 'replace')


def get_ssh_port(monitor_path):

    def data_is_complete(raw):
        for line in raw.splitlines():
            parts = line.strip().split()
            if parts and parts[0] == 'TCP[HOST_FORWARD]' and len(parts) > 3:
                return parts[3]
        return False
    data = run_monitor_command(monitor_path, 'info usernet', data_is_complete)
    return int(data_is_complete(data))


def startup(vm_dir, timeout=30):
    start = monotonic()
    monitor_path = monitor_template.format(vm_dir)
    with open(machine_spec_template.format(vm_dir)) as f:
        cmdline = cmdline_for_machine_spec(f, monitor_path)
    session_name = vm_dir.strip('/').replace('/', '-').replace(' ', '_')
    cmdline = ['screen', '-U', '-d', '-m', '-S', session_name] + cmdline
    # print(shlex.join(cmdline), file=sys.stderr)
    p = subprocess.Popen(cmdline, cwd=vm_dir)
    user = USER
    print(f'VM started, attach to its console with: sudo -u {user} screen -r {session_name}', file=sys.stderr)
    print('Waiting for monitor socket creation', monitor_path, '...', file=sys.stderr)
    rc = p.wait()
    if rc != 0:
        raise SystemExit(rc)
    while not os.path.exists(monitor_path):
        sleep(0.01)
        if monotonic() - start > timeout:
            raise SystemExit(f'VM failed to create monitor socket in {timeout} seconds')
    return monitor_path


def ssh_port_for_vm_dir(vm_dir, start_if_not_running=True):
    monitor_path = monitor_template.format(vm_dir)
    just_started = False
    if not os.path.exists(monitor_path):
        if not start_if_not_running:
            return -1
        startup(vm_dir)
        just_started = True
    ans = get_ssh_port(monitor_path)
    if just_started:
        print('Waiting for SSH server to come up...', file=sys.stderr)
        start = monotonic()
        timeout = 10 # minutes
        while True:
            try:
                cp = subprocess.run(ssh_command_to(port=ans, use_master=False) + ['date'], capture_output=True, timeout=10)
            except TimeoutError:
                pass
            else:
                if cp.returncode == 0:
                    break
                if cp.stderr and b'Connection reset by peer' in cp.stderr:
                    sleep(1)
            if monotonic() - start > (timeout * 60):
                raise TimeoutError(f'SSH server failed to come up in {timeout} seconds')
        print('SSH server came up in', int(monotonic() - start), 'seconds', file=sys.stderr)
    return ans


def end_ssh_master(address, socket, process):
    server, port = address
    subprocess.run(['ssh', '-O', 'exit', '-S', socket, '-p', port, server], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if process.poll() is None:
        process.terminate()
    if process.poll() is None:
        sleep(0.1)
        process.kill()
    ssh_masters.discard(address)


def ssh_command_to(*args, user=BUILD_VM_USER, server='localhost', port=22, allocate_tty=False, timeout=30, use_master=True):
    server = f'{user}@{server}'
    socket = os.path.expanduser(
        f'~/.ssh/controlmasters/bypy-{server}-{port}-{os.getpid()}')
    os.makedirs(os.path.dirname(socket), exist_ok=True)
    port = str(port)
    address = server, port
    ssh = ['ssh', '-p', port, '-o', f'ConnectTimeout={timeout}'] + disable_known_hosts
    if use_master:
        ssh += ['-S', socket]
        if address not in ssh_masters:
            ssh_masters.add(address)
            atexit.register(
                end_ssh_master, address, socket,
                subprocess.Popen(ssh + ['-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=3', '-M', '-N', server]))
    if allocate_tty:
        ssh.append('-t')
    return ssh + [server] + list(args)


actions = {}


def is_local(parsed_spec):
    server = parsed_spec.hostname or 'localhost'
    return server in ('localhost', '127.0.0.1', '::1')


def parse_ssh_spec(spec, port=22):
    from urllib.parse import urlparse
    p = urlparse(spec)
    if p.scheme not in ('', 'ssh'):
        raise ValueError(f'Not a valid SSH URL: {spec}')
    path = p.path
    if not path:
        raise ValueError(f'No path specified in SSH URL: {spec}')
    if is_local(p):
        return path, []
    server = p.hostname or 'localhost'
    if p.username:
        user = p.username
    else:
        user = USER
    port = p.port or port
    return path, ssh_command_to(port=port, server=server, user=user)


def remote_or_local(name, stdout_converter=None):

    def wrapper(func):
        @wraps(func)
        def f(spec):
            path, cmd = parse_ssh_spec(spec)
            if not cmd:
                return func(path)
            rcmd = ['python', '-', '--running-remotely', f'{name}', path]
            with open(__file__) as f:
                script = f.read()
            start = monotonic()
            limit = 120
            while monotonic() - start < limit:
                try:
                    cp = subprocess.run(cmd + rcmd, input=script, text=True, timeout=limit/10, stdout=subprocess.PIPE)
                except subprocess.TimeoutExpired:
                    continue
                if cp.returncode != 0:
                    raise SystemExit(cp.returncode)
                if stdout_converter is None:
                    return None
                return stdout_converter(cp.stdout.strip())
            raise SystemExit(f'Failed to run {name} on {path} remotely after {limit} seconds')
        actions[name] = f
        return f
    return wrapper


@remote_or_local('ssh_port', int)
def ssh_port(spec):
    return ssh_port_for_vm_dir(spec)


@remote_or_local('shutdown_data', str)
def shutdown_data(spec):
    m = metadata_from_vm_dir(spec)
    system = m['os']
    cmd = shutdown_cmd_for_os(system)
    return json.dumps({'metadata': m, 'cmd': cmd, 'port': ssh_port_for_vm_dir(spec, start_if_not_running=False)})


def server_from_spec(spec):
    from urllib.parse import urlparse
    p = urlparse(spec)
    return p.hostname or 'localhost'


def wait_for_ssh(spec, timeout=180):
    port = ssh_port(spec)
    server = server_from_spec(spec)
    cmd = ssh_command_to('date', server=server, port=port, timeout=timeout)
    start = monotonic()
    print(f'Waiting for master connection to SSH server at {server}:{port}...', file=sys.stderr)
    while monotonic() - start < timeout:
        try:
            cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except KeyboardInterrupt:
            raise SystemExit('Interrupted by user')
        if cp.returncode == 0:
            time = monotonic() - start
            print(f'Connected in {time:.1f} seconds', file=sys.stderr)
            return int(port)
    print(cp.stdout.decode('utf-8', 'replace'), file=sys.stderr)
    raise SystemExit(cp.returncode)


def start_shell(spec, port):
    cmd = ssh_command_to(server=server_from_spec(spec), port=port)
    return subprocess.run(cmd).returncode


def shell(spec, timeout=60):
    port = wait_for_ssh(spec, timeout=timeout)
    raise SystemExit(start_shell(spec, port))


def shutdown_vm_dir(vm_dir):
    timeout = 20
    start = monotonic()
    monitor_path = monitor_template.format(vm_dir)
    if not os.path.exists(monitor_path):
        print('VM already shutdown', file=sys.stderr)
        return
    m = metadata_from_vm_dir(vm_dir)
    system = m['os']
    print('Shutting down', system, file=sys.stderr)
    run_monitor_command(monitor_path, 'system_powerdown')
    if not m['is_accelerated']:
        timeout *= 2
    while os.path.exists(monitor_path) and monotonic() - start < timeout:
        sleep(0.1)
    if os.path.exists(monitor_path):
        if start >= 0:
            print(vm_dir, 'failed to shutdown in', timeout, 'seconds. Halting', file=sys.stderr)
        run_monitor_command(monitor_path, 'quit')


@remote_or_local('ensure_halted')
def ensure_halted(vm_dir):
    timeout = 20
    start = monotonic()
    monitor_path = monitor_template.format(vm_dir)
    while os.path.exists(monitor_path) and monotonic() - start < timeout:
        sleep(0.1)
    if os.path.exists(monitor_path):
        if start >= 0:
            print(vm_dir, 'failed to shutdown in', timeout, 'seconds. Halting', file=sys.stderr)
        run_monitor_command(monitor_path, 'quit')


def shutdown(spec):
    from urllib.parse import urlparse
    p = urlparse(spec)
    if is_local(p):
        shutdown_vm_dir(spec)
        return
    data = json.loads(shutdown_data(spec))
    if data['port'] > 0:
        cmd = ssh_command_to(server=p.hostname, port=data['port'])
        cmd += data['cmd']
        print(shlex.join(cmd))
        for i in range(5):
            if subprocess.run(cmd).returncode == 0:
                break
        ensure_halted(spec)
    else:
        print('Server not running')


@remote_or_local('shutdown_all')
def shutdown_all(spec):
    running = []
    for x in os.listdir(spec):
        x = os.path.join(spec, x)
        if os.path.exists(monitor_template.format(x)):
            running.append(x)
    workers = [threading.Thread(target=shutdown_vm_dir, args=(x,)) for x in running]
    for w in workers:
        w.start()
    for w in workers:
        w.join()


actions['wait_for_ssh'] = actions['run'] = wait_for_ssh
actions['shell'] = shell
actions['shutdown'] = shutdown


def real_main(action, vm_spec):
    ret = actions[action](vm_spec)
    if ret is not None:
        print(ret)


def main(args):
    global is_running_remotely, with_gui
    is_running_remotely = args.running_remotely
    with_gui = args.with_gui
    loc = args.location
    if not loc.startswith('ssh:') and not os.path.isabs(loc):
        loc = os.path.join('/vms', loc)
    try:
        real_main(args.action, loc)
    except KeyboardInterrupt:
        raise SystemExit('Exiting because of Ctrl-C')


def setup_parser(parser):
    parser.add_argument(
        'action',
        choices=list(actions),
        help='The action to take. One of: ' + ', '.join(actions))
    parser.add_argument(
        'location', help='The VM location either an ssh:// URL of the form'
        ' ssh://user@host/path/to/vm/dir or just /path/to/vm/dir for local virtual machines.'
    )
    parser.add_argument('--running-remotely', action='store_true', help='For internal use')
    parser.add_argument('--with-gui', action='store_true', help='For internal use')
    parser.set_defaults(func=main)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        prog='run.py' if sys.argv[0] == '-' else sys.argv[0],
        description='Control the execution of Virtual Machines')
    setup_parser(parser)
    args = parser.parse_args()
    args.func(args)
