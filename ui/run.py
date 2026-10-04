"""Start the unchanged backend and isolated UI together. Ctrl-C stops both."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent

def main():
    env = os.environ.copy()
    if sys.platform == 'darwin' and Path('/etc/ssl/cert.pem').is_file():
        env.setdefault('SSL_CERT_FILE', '/etc/ssl/cert.pem')
    for port in (8000, 3000):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                sys.exit(f'Port {port} is already in use. Stop the existing demo server before starting another.')
    children = []
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for path in ('server.py', 'ui/bridge.py'):
            children.append(subprocess.Popen([sys.executable, path], cwd=ROOT, env=env, start_new_session=True))
        print('\nOpen http://127.0.0.1:3000 — Ctrl-C stops both servers.\n', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.3)
        raise RuntimeError('A demo server exited; inspect the error above.')
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()

if __name__ == '__main__': main()
