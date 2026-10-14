from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from hermes_modernisation.sandbox import SandboxSpec, docker_argv

IMAGE = 'python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258'


class SandboxPolicyTests(unittest.TestCase):
    def spec(self, root: Path, **changes):
        original = SandboxSpec(image=IMAGE, source=root, argv=('python', '-B', '-c', 'print(1)'), name='modernise-test-123')
        return replace(original, **changes)

    def test_accepted_command_is_contained(self):
        with tempfile.TemporaryDirectory() as root:
            command = docker_argv(self.spec(Path(root)))
        for item in ('--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=64', '--memory=512m', '--memory-swap=512m', '--cpus=1', '--user=65534:65534', '--pull=never'):
            self.assertIn(item, command)
        self.assertIn('type=bind,src='+root+',dst=/source,readonly,bind-recursive=disabled', command)
        self.assertNotIn('--privileged', command)
        self.assertEqual(command[-4:], ['python', '-B', '-c', 'print(1)'])

    def test_image_must_be_immutable(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                docker_argv(self.spec(Path(root), image='python:latest'))

    def test_source_cannot_be_host_home_or_root(self):
        for root in (Path('/'), Path('/home'), Path('/home/kensei')):
            with self.assertRaises(ValueError):
                docker_argv(self.spec(root))

    def test_system_directories_rejected(self):
        for root in (Path('/etc/ssl'), Path('/usr/local')):
            with self.subTest(root=str(root)):
                with self.assertRaises(ValueError):
                    docker_argv(self.spec(root))

    def test_source_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'alias'
            path.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                docker_argv(self.spec(path))

    def test_unsafe_bind_characters_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'bad,name'
            path.mkdir()
            with self.assertRaises(ValueError):
                docker_argv(self.spec(path))

    def test_empty_command_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                docker_argv(self.spec(Path(root), argv=()))

    def test_name_injection_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                docker_argv(self.spec(Path(root), name='--privileged'))


if __name__ == '__main__':
    unittest.main()
