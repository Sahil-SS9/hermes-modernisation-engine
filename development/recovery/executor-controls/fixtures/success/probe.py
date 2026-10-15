import json,os,socket,sys
from pathlib import Path
assert sys.argv[1:] == ['--rm']
assert Path('empty').is_dir()
assert not Path('/home/kensei').exists()
assert not Path('/var/run/docker.sock').exists()
assert not any(k in os.environ for k in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','AWS_SECRET_ACCESS_KEY','HERMES_HOME'))
try: Path('/source/forbidden').write_text('no')
except OSError: pass
else: raise AssertionError('Source mount writable')
try: socket.create_connection(('1.1.1.1',443),timeout=0.2)
except OSError: pass
else: raise AssertionError('Network escaped')
print(json.dumps({'value':4,'protected_boundary':True}))
