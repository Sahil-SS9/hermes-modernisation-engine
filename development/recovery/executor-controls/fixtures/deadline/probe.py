import subprocess,sys,time
subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
print('spawned descendant',flush=True)
time.sleep(60)
