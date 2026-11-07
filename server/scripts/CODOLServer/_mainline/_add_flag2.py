p = r"CODOLServer\_mainline\_e57a5c_experiment.py"
s = open(p, encoding="utf-8").read()

old = "                follow_85_delay: float = 0.0,"
new = old + "\n                follow_85_wait_flag: str = \"\","
assert old in s
s = s.replace(old, new, 1)

old2 = '''            if follow_85_delay > 0:
                argv += ["--follow-85-delay", str(follow_85_delay)]'''
new2 = old2 + '''
            if follow_85_wait_flag:
                argv += ["--follow-85-wait-flag", follow_85_wait_flag]'''
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = '''    ap.add_argument("--follow-85-delay", type=float, default=0.0,'''
new3 = '''    ap.add_argument("--follow-85-wait-flag", default="",
                    help="with --follow-85: wait for this file (observer's "
                         "obj+0xAC 0->382 edge) before sending")
    ap.add_argument("--follow-85-delay", type=float, default=0.0,'''
assert old3 in s
s = s.replace(old3, new3, 1)

old4 = "            follow_85_delay=a.follow_85_delay,"
new4 = old4 + "\n            follow_85_wait_flag=a.follow_85_wait_flag,"
assert old4 in s
s = s.replace(old4, new4, 1)

# also pass the flag file to the observer as -AcReadyFlag
old5 = '        argv += ["-HandshakeP608KeyFile", p608_key_file]'
new5 = '''    if p608_key_file:
        argv += ["-AcReadyFlag", (p608_key_file.replace(".txt", "") +
                                  "_ac_ready.flag")]
''' + old5
assert old5 in s
s = s.replace(old5, new5, 1)

open(p, "w", encoding="utf-8").write(s)
print("driver patched")
