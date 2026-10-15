"""Public validator regression; run in native sandbox, not the live host."""
import json
import subprocess


def test_public_validator_accepts_real_registration_handles():
    result = subprocess.run(['hermes', 'plugins', 'validate', '/source', '--json'], capture_output=True, text=True, timeout=30)
    report = json.loads(result.stdout)
    assert result.returncode == 0, result.stdout+result.stderr
    assert report['ok'] is True
    assert any(check['name']=='capability probe' and check['ok'] for check in report['checks'])


def test_recording_handles_track_disposal_without_core_import(tmp_path):
    from hermes_cli.plugin_validate import _run_capability_probe
    root = tmp_path/'handles'
    root.mkdir()
    (root/'__init__.py').write_text('''def register(ctx):
    for call in (
        lambda: ctx.register_cli_command('same', 'one', lambda parser: None),
        lambda: ctx.register_command('same', lambda text: text),
        lambda: ctx.register_tool('same', 'example', {}, lambda args: '{}'),
    ):
        handle=call()
        assert handle is not None and handle.active
        handle.dispose()
        assert not handle.active
        handle.dispose()
    kept=ctx.register_cli_command('kept', 'keep', lambda parser: None)
    assert kept.active
    old=ctx.register_command('duplicate', lambda text: text)
    current=ctx.register_command('duplicate', lambda text: text)
    old.dispose()
    assert current.active
    import sys
    assert 'hermes_cli.plugins' not in sys.modules
''')
    recorded, error = _run_capability_probe(root, {})
    assert not error, error
    assert recorded is not None
    assert recorded['commands'] == ['kept', 'duplicate']
    assert recorded['tools'] == []
