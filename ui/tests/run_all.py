"""Run all backend, MCP HTTP, UI, and adapter checks against a clean local demo.

Preconditions: both UI/MCP processes run via ui/run.py. Restart the backend
first so the simulated plug starts ON; test_mcp.py verifies its ON -> OFF path.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def main():
    env = os.environ.copy()
    cert_bundle = Path('/etc/ssl/cert.pem')
    if sys.platform == 'darwin' and cert_bundle.is_file():
        env.setdefault('SSL_CERT_FILE', str(cert_bundle))
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js is required for the UI test suite.')
    commands = [
        [sys.executable, 'test_mcp.py'],
        [sys.executable, 'ui/tests/live_http.py'],
        [sys.executable, 'test_protocol.py'],
        [sys.executable, 'test_lifecycle.py'],
        [sys.executable, 'test_workflow.py'],
        [sys.executable, 'check.py'],
        [sys.executable, '-m', 'unittest', 'ui.tests.test_bridge', 'ui.aws.test_bedrock_explanation'],
        [node, '--test', 'ui/tests/*.test.js'],
    ]
    for command in commands:
        rendered = ' '.join(command)
        print(f'\n$ {rendered}', flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    print('\nALL BACKEND, UI, AND MCP HTTP TESTS PASSED', flush=True)

if __name__ == '__main__': main()
