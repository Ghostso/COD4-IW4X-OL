import subprocess, pathlib, shutil, sys, os, tempfile
F = pathlib.Path(r'F:\桌面\ol\ol-mod-olfinal')
EV = pathlib.Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_acceptance_evidence')
tmp = pathlib.Path(tempfile.mkdtemp(prefix='t2_accept_head_'))
for rel in ('tools/runtime/CodolGame.py', 'tools/runtime/CodolGameTests.py', 'tools/runtime/CodolClientAccount.py'):
    blob = subprocess.run(['git','-C',str(F),'show','HEAD:'+rel], capture_output=True, check=True).stdout
    (tmp / pathlib.Path(rel).name).write_bytes(blob)
print('control dir:', tmp)
result = subprocess.run([sys.executable, 'CodolGameTests.py', '-v'], cwd=tmp, capture_output=True, text=True, encoding='utf-8', errors='replace')
out = result.stdout + result.stderr
(EV / 'acceptance_caller_tests_head_both.log').write_text(out, encoding='utf-8')
print('exit =', result.returncode)
for line in out.splitlines():
    if line.startswith(('FAIL','ERROR','Ran ','OK','FAILED')):
        print(' ', line)