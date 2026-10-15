"""Phase 0 native SDK facade. Execution remains explicitly unavailable."""
import json
import shlex


MISSING = (
    'complete external executor and native caller authority coverage',
    'full isolation acceptance and provenance conformance',
    'migration jobs, comparison, reports and release gates',
)


def status():
    return {'schema_version': 1, 'implementation_status': 'PHASE_0_ONLY',
            'execution_available': False, 'missing_evidence': list(MISSING)}


def slash(raw_args):
    try:
        words = shlex.split(raw_args or '')
    except ValueError:
        return json.dumps({'error': 'INVALID_ARGUMENTS'})
    if not words or words == ['status']:
        return json.dumps(status())
    return json.dumps({'error': 'EXECUTION_UNAVAILABLE', 'message': 'Only status is implemented. Execution requires the separately approved external executor; caller text cannot approve it.'})


def setup(parser):
    parser.add_argument('operation', choices=['status', 'run'], nargs='?', default='status')
    parser.add_argument('--job')


def cli(arguments):
    if arguments.operation != 'status':
        print(json.dumps({'error': 'EXECUTION_UNAVAILABLE', 'missing_evidence': list(MISSING)}))
        raise SystemExit(2)
    print(json.dumps(status()))


def tool(arguments, **kwargs):
    if arguments:
        return json.dumps({'error': 'INVALID_ARGUMENTS', 'message': 'Status takes no arguments'})
    return json.dumps(status())


def register(ctx):
    handles = []
    try:
        registrations = (
            lambda: ctx.register_cli_command('modernise', 'Migration evidence engine status', setup, cli),
            lambda: ctx.register_command('modernise', slash, description='Migration engine status; execution disabled', args_hint='status', argument_mode='text'),
            lambda: ctx.register_tool('modernise_status', 'modernisation-engine',
                              {'name': 'modernise_status', 'description': 'Read implementation availability; does not run code or models.',
                               'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}, tool),
        )
        for registration in registrations:
            handle = registration()
            if handle is None:
                raise RuntimeError('Modernisation namespace collision; registration refused')
            handles.append(handle)
    except BaseException:
        for handle in reversed(handles):
            handle.dispose()
        raise
