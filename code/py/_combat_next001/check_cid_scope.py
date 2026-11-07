# -*- coding: utf-8 -*-
"""Reproduce the suspected NameError: _cap_cid is a MODULE global but assigned
as a LOCAL of handle_lobby; the OTHER decrypt function (around line 426) would
reference the module global which may be undefined at first use."""
import ast, io, sys
COPY = sys.argv[1]
P = COPY + "/lobby_server.py"
src = io.open(P, encoding="utf-8").read()
tree = ast.parse(src)
# find every module-level assignment to _cap_cid and every function that assigns it
assigned_global = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "_cap_cid":
                assigned_global.append(node.lineno)
print("module-level `_cap_cid` assignments:", assigned_global)
def walk(fn, depth=0):
    found = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "_cap_cid":
                    found.append(n.lineno)
    return found
print()
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        f = walk(node)
        if f:
            print("  def %-22s assigns `_cap_cid` (LOCAL) at lines %s" % (node.name, f))
print()
# locate the hook call sites
lines = src.splitlines()
print("hook call sites:")
for i, l in enumerate(lines, 1):
    if "_cap_frame(" in l and "def " not in l:
        print("   line %d: %s" % (i, l.strip()[:110]))
