import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "archive_confirmed_20260928.py"
s = open(p, encoding="utf-8", errors="replace").read()

s = s.replace('STAMP = "20260928_1730"', 'STAMP = "20260928_1900"', 1)

old_runs = '''    "IFS1_ELEVATED_20260928_172524",  # lobby port global [0x81A9780] == 0
]'''
new_runs = '''    "IFS1_ELEVATED_20260928_172524",  # lobby port global [0x81A9780] == 0
    # ---- 20260928 late session: lobby channel protocol cracked ----
    "IFS1_ELEVATED_20260928_174644",  # reqC8 1->4; CSV header/order bug proved
    "IFS1_ELEVATED_20260928_175045",  # tplB garbage IP; [0x81A7F34] empty
    "IFS1_ELEVATED_20260928_175619",  # tplA=127.0.0.1 tplB=236.3.0.0 raw dump
    "IFS1_ELEVATED_20260928_180039",  # reqC8 reaches 2 -> connect made -> tls_fail
    "IFS1_ELEVATED_20260928_180944",  # plain 28-byte probe accepted (sub-state 3)
    "IFS1_ELEVATED_20260928_181236",  # 200-byte padded frame accepted
    "IFS1_ELEVATED_20260928_181603",  # 24-byte frame rejected (len gate)
    "IFS1_ELEVATED_20260928_181937",  # 204-byte frame accepted
]'''
assert s.count(old_runs) == 1
s = s.replace(old_runs, new_runs, 1)

old_logs = '''    "AUTO_LOBBY_20260928_172517_r1",
]'''
new_logs = '''    "AUTO_LOBBY_20260928_172517_r1",
    "AUTO_LOBBY_20260928_180032_r1",  # lobby connect lands on HTTPS probe as plain TCP
    "AUTO_LOBBY_20260928_180920_r1",
    "AUTO_LOBBY_20260928_181236_r2",
    "AUTO_LOBBY_20260928_181603_r3",
    "AUTO_LOBBY_20260928_181937_r4",
]'''
assert s.count(old_logs) == 1
s = s.replace(old_logs, new_logs, 1)

old_files = '''    "CODOLServer/_subagents/_tenproxy_shm_fixed.bin",
]'''
new_files = '''    "CODOLServer/_subagents/_tenproxy_shm_fixed.bin",
    # ---- 20260928 late session ----
    "CODOLServer/lobby_server/lobby_plain_probe.py",
    "restore_iips_contract_001/observer2/AboProbe.csproj",
    "CODOLServer/_mainline/_dis_va.py",
    "CODOLServer/_mainline/archive_confirmed_20260928.py",
]'''
assert s.count(old_files) == 1
s = s.replace(old_files, new_files, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
