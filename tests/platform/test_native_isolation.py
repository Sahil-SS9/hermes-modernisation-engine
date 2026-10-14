"""Native negative controls. Run ONLY in the approved rootless Docker sandbox."""
from __future__ import annotations

import os
import socket
import subprocess
import unittest
from pathlib import Path


class NativeIsolationTests(unittest.TestCase):
    def test_readonly_source_and_root(self):
        for path in (Path('/source/.escape-canary'), Path('/root/.escape-canary')):
            with self.assertRaises(OSError):
                path.write_text('escape')

    def test_host_paths_and_docker_socket_absent(self):
        for path in ('/home/kensei', '/run/user/1001/docker.sock', '/var/run/docker.sock', '/run/severian/embed.sock'):
            self.assertFalse(Path(path).exists(), path)

    def test_credentials_not_inherited(self):
        for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN', 'AWS_ACCESS_KEY_ID', 'HERMES_HOME'):
            self.assertNotIn(name, os.environ)

    def test_network_refused(self):
        with socket.socket() as sock:
            sock.settimeout(1)
            with self.assertRaises(OSError):
                sock.connect(('1.1.1.1', 443))
        interfaces = {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:]}
        self.assertEqual(interfaces, {'lo'})

    def test_kernel_enforcement(self):
        status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
        self.assertEqual(status['NoNewPrivs'].strip(), '1')
        self.assertEqual(int(status['CapEff'].strip(), 16), 0)
        self.assertEqual(status['Seccomp'].strip(), '2')
        self.assertEqual(os.geteuid(), 65534)
        self.assertEqual(Path('/sys/fs/cgroup/pids.max').read_text().strip(), '64')
        self.assertEqual(Path('/sys/fs/cgroup/memory.max').read_text().strip(), '536870912')

    def test_child_inherits_isolation(self):
        code = "import pathlib; assert not pathlib.Path('/home/kensei').exists(); pathlib.Path('/source/.child-escape').write_text('x')"
        result = subprocess.run(['python', '-B', '-c', code], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Read-only file system', result.stderr)

    def test_symlink_and_hardlink_write_escape_refused(self):
        link = Path('/tmp/escape-link')
        link.symlink_to('/source/src/hermes_modernisation/sandbox.py')
        with self.assertRaises(OSError):
            link.write_text('overwrite source')
        with self.assertRaises(OSError):
            os.link('/source/src/hermes_modernisation/sandbox.py', '/tmp/escape-hardlink')
        self.assertNotEqual(Path('/source/src/hermes_modernisation/sandbox.py').read_text(), 'overwrite source')

    def test_cpu_limit_enforced(self):
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
        self.assertNotEqual(quota, 'max')
        self.assertEqual(int(quota), int(period))

    def test_writable_tmp_is_disposable(self):
        path = Path('/tmp/modernise-isolation-canary')
        path.write_text('container-only')
        self.assertEqual(path.read_text(), 'container-only')


if __name__ == '__main__':
    unittest.main()
