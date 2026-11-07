# -*- coding: utf-8 -*-
"""把 install_allocator.py 的调用插入 run_all.py 的 patch 之后。"""
import io
import os

N = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_LOCAL_CHAIN_V2"
f = os.path.join(N, "run_all.py")
t = open(f, encoding="utf-8").read()

anchor = 'print("      [patch] " + (_rc.stdout or _rc.stderr).strip().replace("\\n", " | "))\n'
idx = t.find(anchor)
if idx < 0:
    print("anchor not found")
    raise SystemExit(1)

if "install_allocator.py" in t:
    print("already integrated")
    raise SystemExit(0)

insert_at = idx + len(anchor)
# 保持与 anchor 相同的缩进（20 空格）
indent = " " * 20
block = (
    indent + '_alloc = os.path.join(ROOT, "install_allocator.py")\n'
    + indent + "if os.path.exists(_alloc):\n"
    + indent + '    _ra = subprocess.run([sys.executable, _alloc, "--pid", str(max(_ps))],\n'
    + indent + '                         capture_output=True, text=True, errors="replace")\n'
    + indent + '    print("      [alloc] " + (_ra.stdout or _ra.stderr).strip().replace("\\n", " | "))\n'
)

t2 = t[:insert_at] + block + t[insert_at:]
open(f, "w", encoding="utf-8", newline="\n").write(t2)
print("integrated OK")
print("--- 插入位置上下文 ---")
s = t2.find('print("      [alloc]')
print(t2[max(0, s - 400):s + 300])
