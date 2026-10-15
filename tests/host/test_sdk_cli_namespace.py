"""Real pinned-host namespace gate, not fake PluginContext behaviour.

Run ONLY in the Python 3.14 native-host sandbox image. No live home is used.
"""
import os
import subprocess
from pathlib import Path


HOST = '/opt/hermes/.venv/bin/hermes'


def plugin(home: Path, name: str, marker: str) -> None:
    root = home/'plugins'/name
    root.mkdir(parents=True)
    (root/'plugin.yaml').write_text(f'name: {name}\nversion: 0.1.0\ndescription: Offline SDK namespace probe\n')
    (root/'__init__.py').write_text(
        'def setup(parser):\n    pass\n'
        'def handler(args):\n    print('+repr(marker)+')\n'
        'def register(ctx):\n'
        '    ctx.register_cli_command("modernise", "Offline namespace probe", setup, handler)\n'
    )


def invoke(home: Path, enabled: list[str]):
    home.mkdir(exist_ok=True)
    (home/'config.yaml').write_text('plugins:\n  enabled:\n'+''.join('    - '+name+'\n' for name in enabled))
    environment = dict(os.environ, HERMES_HOME=str(home), HOME=str(home), HERMES_BUNDLED_PLUGINS=str(home/'no-bundled'), HERMES_ENABLE_PROJECT_PLUGINS='0')
    return subprocess.run([HOST, 'modernise'], env=environment, cwd=home, capture_output=True, text=True, timeout=30)


def test_single_plugin_real_cli_route(tmp_path):
    home = tmp_path/'single'
    plugin(home, 'probe-a', 'SDK_PROBE_A')
    result = invoke(home, ['probe-a'])
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'SDK_PROBE_A' in result.stdout


def test_foreign_cli_registration_cannot_silently_replace_first(tmp_path):
    home = tmp_path/'collision'
    plugin(home, 'probe-a', 'SDK_PROBE_A')
    plugin(home, 'probe-b', 'SDK_PROBE_B')
    result = invoke(home, ['probe-a', 'probe-b'])
    # Correct refusal can preserve A, or explicitly fail admission. Arbitrary
    # import/setup errors cannot satisfy the collision gate.
    if result.returncode != 0:
        assert 'collision' in (result.stdout+result.stderr).lower(), result.stdout+result.stderr
    else:
        assert 'SDK_PROBE_A' in result.stdout, result.stdout+result.stderr
        assert 'SDK_PROBE_B' not in result.stdout, 'Foreign plugin silently replaced the modernise CLI namespace'
