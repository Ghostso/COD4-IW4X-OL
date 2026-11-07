p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()

old = '''                    if follow_85_delay > 0:'''
new = '''                    if follow_85_wait_flag:
                        # Wait for the observer to publish the AC edge
                        # ([obj+0xAC] 0 -> 382).  The 0x85 reader at 0xBA3A91
                        # uses that length; sending outside the window makes it
                        # read with length 0 and the dispatch byte is never 0x87.
                        log(path, {"event": "follow_85_wait_flag_start",
                                   "peer": list(peer),
                                   "flag": follow_85_wait_flag})
                        deadline_f = time.time() + 120.0
                        while time.time() < deadline_f:
                            if read_key_file(follow_85_wait_flag, 0.0):
                                break
                            time.sleep(0.01)
                        log(path, {"event": "follow_85_wait_flag_done",
                                   "peer": list(peer),
                                   "found": bool(read_key_file(
                                       follow_85_wait_flag, 0.0))})
                    if follow_85_delay > 0:'''
assert old in s
s = s.replace(old, new, 1)

old2 = "                    follow_85_delay: float = 0.0,"
new2 = old2 + "\n                    follow_85_wait_flag: str = \"\","
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = '''    ap.add_argument("--follow-85-delay", type=float, default=0.0,'''
new3 = '''    ap.add_argument("--follow-85-wait-flag", default="",
                    help="with --follow-85: wait until this file exists before "
                         "sending (the observer writes it on the [obj+0xAC] "
                         "0->382 edge)")
    ap.add_argument("--follow-85-delay", type=float, default=0.0,'''
assert old3 in s
s = s.replace(old3, new3, 1)

old4 = "                                       a.follow_85_delay,"
new4 = old4 + "\n                                       a.follow_85_wait_flag,"
assert old4 in s
s = s.replace(old4, new4, 1)

open(p, "w", encoding="utf-8").write(s)
print("probe patched")
