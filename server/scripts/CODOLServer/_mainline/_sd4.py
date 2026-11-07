p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()
old = "                                       a.hold_after_83,"
assert old in s
s = s.replace(old, "                                       a.hold_after_83,\n                                       a.serve_delay,", 1)
open(p,"w",encoding="utf-8").write(s)
print("wired")

p2 = r"CODOLServer\_mainline\_e57a5c_experiment.py"
s2 = open(p2, encoding="utf-8").read()
old2 = "                follow_85_wait_flag: str = \"\","
assert old2 in s2
s2 = s2.replace(old2, old2 + "\n                serve_delay: float = 0.0,", 1)
old3 = '    argv = [PY, "-X", "utf8", "-u", plain,'
new3 = '    argv = [PY, "-X", "utf8", "-u", plain,'
# add the CLI pass-through right after the base argv list is built
old4 = '''            "--echo-file", echo, "--hold-after-83", "80"]'''
assert old4 in s2
s2 = s2.replace(old4, old4 + '''
    if serve_delay > 0:
        argv += ["--serve-delay", str(serve_delay)]''', 1)
old5 = '    ap.add_argument("--patch-delay", type=float, default=0.0,'
assert old5 in s2
s2 = s2.replace(old5, '''    ap.add_argument("--serve-delay", type=float, default=0.0,
                    help="delay the plain probe's handshake by N seconds, so "
                         "the client's frame processing happens after the "
                         "observer's patches")
''' + old5, 1)
old6 = "            follow_85_wait_flag=a.follow_85_wait_flag,"
assert old6 in s2
s2 = s2.replace(old6, old6 + "\n            serve_delay=a.serve_delay,", 1)
open(p2,"w",encoding="utf-8").write(s2)
print("driver wired")
