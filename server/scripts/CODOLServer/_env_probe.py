import importlib.util as u

for name in ("pefile", "capstone", "lief", "r2pipe", "scapy"):
    print(f"{name}: {bool(u.find_spec(name))}")
