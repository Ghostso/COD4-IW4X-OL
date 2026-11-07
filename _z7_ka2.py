p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

old = "            except socket.timeout:\n                self.drain_pending(c)\n                continue"
new = ("            except socket.timeout:\n"
       "                self.drain_pending(c)\n"
       "                now = time.time()\n"
       "                if now - state.get(\"last_ka\", 0) >= 5.0:\n"
       "                    state[\"last_ka\"] = now\n"
       "                    try:\n"
       "                        c.sendall(b\"\\x00\\x00\\x00\\x00\")\n"
       "                    except OSError:\n"
       "                        pass\n"
       "                continue")
src = src.replace(old, new)

old2 = "state = {\"hello\": False, \"sent81\": False, \"sent83\": False}"
new2 = "state = {\"hello\": False, \"sent81\": False, \"sent83\": False, \"last_ka\": 0.0}"
src = src.replace(old2, new2)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
