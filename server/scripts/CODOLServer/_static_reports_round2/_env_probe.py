import sys, importlib.util as u
print(sys.version)
for m in ("capstone", "pefile", "lief", "rich", "construct"):
    print(m, bool(u.find_spec(m)))
