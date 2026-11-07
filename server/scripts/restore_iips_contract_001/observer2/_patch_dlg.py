import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "AboProbe.cs"
s = open(p, encoding="utf-8", errors="replace").read()

old = '''                    if (wins.Add((uint)(long)h))
                    {
                        var txt = new StringBuilder(1024);
                        IntPtr r;
                        SendMessageTimeoutW(h, 0x000D, (IntPtr)1024, txt, 0x0002, 200, out r);
                        Ev("WINDOW_NEW", "hwnd=0x" + ((ulong)(long)h).ToString("X"),
                           "class=" + c, "text=" + San(txt.ToString()), "");
                    }'''
new = '''                    if (wins.Add((uint)(long)h))
                    {
                        var txt = new StringBuilder(1024);
                        IntPtr r;
                        SendMessageTimeoutW(h, 0x000D, (IntPtr)1024, txt, 0x0002, 200, out r);
                        Ev("WINDOW_NEW", "hwnd=0x" + ((ulong)(long)h).ToString("X"),
                           "class=" + c, "text=" + San(txt.ToString()), "");
                        // The game raises a generic engine dialog (localization
                        // key WIN_ERROR -> "致命错误") some seconds after the
                        // lobby succeeds.  The top-level title carries no
                        // reason, so dump every child control's text as well.
                        if (c == "#32770")
                        {
                            int idx = 0;
                            EnumChildWindows(h, (ch, cl) =>
                            {
                                var ccls = new StringBuilder(256);
                                GetClassNameW(ch, ccls, ccls.Capacity);
                                var ctxt = new StringBuilder(2048);
                                IntPtr cr;
                                SendMessageTimeoutW(ch, 0x000D, (IntPtr)2048,
                                                    ctxt, 0x0002, 200, out cr);
                                Ev("DLG_CHILD", "parent=0x" +
                                   ((ulong)(long)h).ToString("X"),
                                   "idx=" + idx, "class=" + ccls.ToString(),
                                   "text=" + San(ctxt.ToString()));
                                idx++;
                                return true;
                            }, IntPtr.Zero);
                        }
                    }'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
