import hashlib, subprocess, pathlib
F = r'F:\桌面\ol\ol-mod-olfinal'
for rel in ('tools/runtime/CodolGame.py', 'tools/runtime/CodolGameTests.py'):
    blob = subprocess.run(['git','-C',F,'show','HEAD:'+rel], capture_output=True, check=True).stdout
    print('HEAD   sha256=' + hashlib.sha256(blob).hexdigest().upper() + '  bytes=' + str(len(blob)) + '  ' + rel)
    now = pathlib.Path(F, rel).read_bytes()
    print('WORK   sha256=' + hashlib.sha256(now).hexdigest().upper() + '  bytes=' + str(len(now)) + '  ' + rel)