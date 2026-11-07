import hashlib
import importlib.util
import os
import pathlib
import time

root = pathlib.Path.cwd()
cod = root / 'COD OL'
targets = [cod / 'codoMP_client_shipRetail.exe', cod / 'codoMP_client_shipRetailBase.dll', cod / 'TenProxy.dll']
print('MODULES')
for mod in ('pefile', 'capstone', 'lief', 'pe'):
    print(mod, bool(importlib.util.find_spec(mod)))
print('TARGETS')
for p in targets:
    print(p, 'EXISTS', p.is_file())
    if p.is_file():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        st = p.stat()
        print('  SIZE', st.st_size, 'MTIME', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)), 'SHA256', h)
print('WORKSPACE_ARTIFACTS')
patterns = ('entry', 'import', 'tls', 'base', 'dll', 'contract', 'startup', 'launch', 'cfg', 'call', 'loader')
for p in sorted(root.iterdir()):
    if p.is_file() and any(x in p.name.lower() for x in patterns):
        st = p.stat()
        print(p.name, st.st_size, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)))
print('COD_BINARIES_TOP')
items = []
for p in cod.iterdir():
    if p.is_file() and p.suffix.lower() in ('.exe', '.dll'):
        st = p.stat()
        items.append((st.st_size, p.name, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))))
for size, name, mtime in sorted(items, reverse=True)[:50]:
    print(size, name, mtime)
