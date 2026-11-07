"""Does the restored 09-28 observer accept every flag today's launch script
passes?  If not, the observer exits immediately and the round fails -- which
would look like "the restore did not work" when it is really an arg mismatch.
"""
import re
import os
import sys

CS = sys.argv[1] if len(sys.argv) > 1 else \
     r"restore_iips_contract_001\observer2\AboProbe.cs"
PS = r"run_codol_001\elevated_ifs1_observer.ps1"

cs = open(CS, encoding="utf-8-sig", errors="replace").read()
ps = open(PS, encoding="utf-8", errors="replace").read()

print("=== %s (%d bytes) ===" % (os.path.basename(CS), len(cs)))
for k in ["compat4", "RecheckJmpTarget", "VSD_PROBE", "handshake-ready-file",
          "POKE_LOBBY_644", "TraceEips", "LOBBY_READY_ONLY", "HandshakeEchoFile"]:
    print("   %-22s %s" % (k, "yes" if k in cs else "-"))
print()

have = set(re.findall(r'"(--[a-z0-9\-]+)"', cs))
print("observer (restored 09-28) knows %d flags" % len(have))

wants = set(re.findall(r"' (--[a-z0-9\-]+)", ps))
wants |= set(re.findall(r"\+= ' (--[a-z0-9\-]+)", ps))
print("launch script passes %d flags" % len(wants))

miss = sorted(wants - have)
print()
print("=== flags the launch script sends that the old observer does NOT know ===")
if miss:
    for a in miss:
        print("   *** %s" % a)
else:
    print("   (none -- the old observer accepts everything)")

print()
print("=== flags the old observer knows but the script no longer sends ===")
extra = sorted(have - wants)
for a in extra:
    print("   %s" % a)
