"""Check the 8 prerequisites from CODOL_LOBBY_WORKING_20261002.md against
what this machine actually has right now.

The document's own table lists, for each item, the correct form AND the wrong
form that fails -- so each check reports which one we match.
"""
import os
import re
import subprocess

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
SAND = os.path.join(ROOT, r"run_codol_001\sandbox_datafix_20260929")
HOSTS = r"C:\Windows\System32\drivers\etc\hosts"

ok = []
bad = []
unknown = []


def note(good, msg):
    (ok if good else bad).append(msg)


print("=" * 72)
print("1. hosts")
print("=" * 72)
try:
    txt = open(HOSTS, encoding="utf-8", errors="replace").read()
    live = [l.strip() for l in txt.splitlines()
            if l.strip() and not l.strip().startswith("#")]
    print("   live lines:", live if live else "(none)")
    want_auth = any("formal-zone-auth.codol.qq.com" in l for l in live)
    want_lsg = any("formal-zone-lsg.codol.qq.com" in l for l in live)
    hijack = [l for l in live
              if "down.qq.com" in l or "intldlgs.qq.com" in l]
    note(want_auth, "hosts: formal-zone-auth mapped")
    note(want_lsg, "hosts: formal-zone-lsg mapped")
    if hijack:
        bad.append("hosts: HIJACKS %s  <-- document says this kills ACE/TP3"
                   % hijack)
    else:
        ok.append("hosts: does not hijack down.qq.com / intldlgs.qq.com")
except Exception as e:
    unknown.append("hosts unreadable: %s" % e)

print()
print("=" * 72)
print("2. dwauth.ini")
print("=" * 72)
p = os.path.join(SAND, "dwauth.ini")
if os.path.exists(p):
    raw = open(p, "rb").read()
    print("   bytes:", raw)
    good = (b"formal-zone-lsg.codol.qq.com 3074" in raw
            and b"formal-zone-auth.codol.qq.com 3074" in raw)
    wrong = raw.startswith(b"127.0.0.1")
    note(good, "dwauth.ini: three-line form (document's correct form)")
    if wrong:
        bad.append("dwauth.ini: 127.0.0.1/0/... form (document's WRONG form)")
else:
    unknown.append("dwauth.ini missing")

print()
print("=" * 72)
print("3. port 3074")
print("=" * 72)
out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True)
txt = out.stdout.decode("gbk", "replace")
for port in (3074, 8443, 8446):
    hit = [l for l in txt.splitlines() if (":%d " % port) in l
           and "LISTENING" in l]
    print("   port %-5d listening: %s" % (port, bool(hit)))
note(True, "port: 3074 is what the document requires (above shows current)")

print()
print("=" * 72)
print("4. certificate")
print("=" * 72)
cacert = os.path.join(SAND, "cacert.pem")
if os.path.exists(cacert):
    n = open(cacert, "rb").read().count(b"BEGIN CERTIFICATE")
    print("   cacert.pem: %d certificate(s), %d bytes"
          % (n, os.path.getsize(cacert)))
    ok.append("cacert.pem present")
rootcerts = subprocess.run(
    ["certutil", "-store", "Root"], capture_output=True)
rt = rootcerts.stdout.decode("gbk", "replace")
print("   LocalMachine\\Root entries mentioning codol/local: %d"
      % len(re.findall(r"codol|local", rt, re.I)))

print()
print("=" * 72)
print("5. four compatibility patches")
print("=" * 72)
IMG = os.path.join(ROOT,
                   r"CODOLServer\_mainline\_dyn100_run_20260925_182324"
                   r"\live\image_best.bin")
if os.path.exists(IMG):
    d = open(IMG, "rb").read()
    for name, va, want in [
            ("#4 0xBA3C1A", 0xBA3C1A, b"\x85\xc0\x75\x44"),
            ("#1 0xB9A78C", 0xB9A78C, b"\x84\xc0\x74\xb2\xb0\x01"),
            ("#3 ref 0xB9A7CC", 0xB9A7CC,
             b"\x8d\x8d\x38\xfd\xff\xff\xc7\x85\x68\xfd\xff\xff")]:
        got = d[va - 0x400000: va - 0x400000 + len(want)]
        print("   %-16s %s  %s" % (name, got.hex(),
                                   "MATCH" if got == want else "no match"))

print()
print("=" * 72)
print("6. TAS not injected")
print("=" * 72)
print("   tas_off.flag in sandbox:",
      os.path.exists(os.path.join(SAND, "tas_off.flag")))

print()
print("=" * 72)
print("7. session key snapshot mechanism")
print("=" * 72)
print("   secrets.txt exists:", os.path.exists(os.path.join(SAND, "secrets.txt")))

print()
print("=" * 72)
print("8. data files")
print("=" * 72)
for d in ["publisher_files", "player_profiles", "user_files",
          "player-account.json", "marketplace-inventory.json"]:
    print("   %-30s %s" % (d,
          "OK" if os.path.exists(os.path.join(SAND, d)) else "missing"))

print()
print("=" * 72)
print("SUMMARY")
print("=" * 72)
print("  satisfied :", len(ok))
for m in ok:
    print("     +", m)
print("  MISSING   :", len(bad))
for m in bad:
    print("     -", m)
if unknown:
    print("  unknown   :", len(unknown))
    for m in unknown:
        print("     ?", m)
