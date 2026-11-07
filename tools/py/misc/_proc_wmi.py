import csv
import io
import subprocess

raw = subprocess.check_output(['wmic','process','get','ProcessId,ParentProcessId,Name,CreationDate,ExecutablePath,CommandLine','/format:csv'], text=True, errors='replace')
rows = list(csv.DictReader(io.StringIO(raw)))
keep = {'client.exe','launcher.exe','tcls_core.exe','tgp_daemon.exe','taslogin.exe','wegame_env.exe','wegame.exe','browser.exe','codomp_client_shipretail.exe'}
sel = [r for r in rows if (r.get('Name') or '').lower() in keep]
for r in sorted(sel, key=lambda x: x.get('CreationDate') or ''):
    print('PID', r.get('ProcessId'), 'PPID', r.get('ParentProcessId'), 'NAME', r.get('Name'), 'CREATED', r.get('CreationDate'))
    print(' PATH', r.get('ExecutablePath'))
    print(' CMD', r.get('CommandLine'))