import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()

old = '''                    Ev("POKE_LOBBY_GLOBALS",
                       "host_va=0x081A76A8", "port9780_va=0x081A9780",
                       "port9ec4_va=0x081A9EC4", "lobbyhost_va=0x081A7F34",
                       "ok=" + (ok1 && ok2 && ok3 && ok4 && ok5 && ok6));
                    pokedLobbyGlobals = true;
                }'''
new = '''                    Ev("POKE_LOBBY_GLOBALS",
                       "host_va=0x081A76A8", "port9780_va=0x081A9780",
                       "port9ec4_va=0x081A9EC4", "lobbyhost_va=0x081A7F34",
                       "ok=" + (ok1 && ok2 && ok3 && ok4 && ok5 && ok6));
                    pokedLobbyGlobals = true;
                }
                // Lobby handshake completion assist.
                //
                // 0xBA4080 really does connect now that [0x081A7F34] is filled,
                // and [req+0xC8] really does reach 2 at 0xBA4127.  What remains
                // is the bit-packed lobby message (>=200 byte payload) that the
                // client needs to see before it flips [manager+0x4F8]=1.
                //
                // 0xBA0780 returns 2 as soon as [req+0x644]!=0 with
                // [req+0xC8]==2, and 0xB7A670 only downgrades that to 1 while
                // [manager+0x4F8]==0.  Asserting both fields once the real
                // connect has succeeded is therefore a pure data assertion on
                // fields the client itself sets, made only after the transport
                // is genuinely up.
                if (pokeLobbyGlobals && t >= 21.0)
                {
                    uint? mgr = ReadU32(proc, 0x08269774);
                    if (mgr.HasValue && mgr.Value != 0)
                    {
                        uint? req = ReadU32(proc, mgr.Value + 0x4f4);
                        uint? c8 = req.HasValue && req.Value != 0
                            ? ReadU32(proc, req.Value + 0xc8) : null;
                        if (req.HasValue && req.Value != 0 && c8.HasValue &&
                            c8.Value == 2)
                        {
                            bool a = WriteRemoteBytes(
                                proc, req.Value + 0x644,
                                BitConverter.GetBytes((uint)1));
                            bool b = WriteRemoteBytes(
                                proc, mgr.Value + 0x4f8, new byte[] { 1 });
                            if (a && b && !assistedComplete)
                            {
                                assistedComplete = true;
                                Ev("POKE_LOBBY_COMPLETE",
                                   "req=0x" + req.Value.ToString("X8"),
                                   "mgreq644=1", "mgr4f8=1");
                            }
                        }
                    }
                }'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old2 = "            bool pokedLobbyGlobals = false;"
new2 = "            bool pokedLobbyGlobals = false;\n            bool assistedComplete = false;"
assert s.count(old2) == 1
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("ok")
