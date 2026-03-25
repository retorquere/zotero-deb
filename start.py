#!/usr/bin/env python3

import subprocess, signal, time, sys, os
from xvfbwrapper import Xvfb

exe = sys.argv[1]
log = f'{exe}.log'
if os.path.exists(log):
  os.remove(log)

start = time.time()
with Xvfb(), open(log, 'wb') as f:
  print('starting', exe)
  p = subprocess.Popen(
    [f'/usr/lib/{exe}/zotero', '-P', 'BBTTEST', '-jsconsole', '-purgecaches', '-ZoteroDebugText'],
    stdout=f, stderr=subprocess.STDOUT, start_new_session=True
  )
  print('started', exe)
  
  time.sleep(20)
  print('stopping', exe)
  os.killpg(os.getpgid(p.pid), signal.SIGTERM)

  time.sleep(5)
  if p.poll() is None:
    print('killing', exe)
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)

  p.wait()

if 'Asynchronously opening database' not in open(log).read():
  print(f'Failed after {time.time() - start:.2f} seconds')
  sys.exit(1)
