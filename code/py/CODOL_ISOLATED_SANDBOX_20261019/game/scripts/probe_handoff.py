"""One-shot probe: launch the game through the recovered hand-off and check whether it
consumed our shared memory (marker scan) -- control: scan for a string in its own module."""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codol_launch as CL  # noqa: E402
import procmem as PM       # noqa: E402

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
exe = CL.find_game(root)
key = CL.filetime_key(exe)
cmdline = '"%s" -q 0 -i 0 -s 0 -g 0 -u 0 -n  -m --1' % exe

si = CL.STARTUPINFOW()
si.cb = ctypes.sizeof(si)
pi = CL.PROCESS_INFORMATION()
buf = ctypes.create_unicode_buffer(cmdline)
assert CL.k32.CreateProcessW(exe, buf, None, None, True, CL.CREATE_SUSPENDED,
                             None, root, ctypes.byref(si), ctypes.byref(pi))
pid = pi.dwProcessId
hs = []
hs.append(CL.create_mapping(CL.TAS_NAME_FMT % pid,
                            CL.build_tas_payload(key, block1=b'CODOLBLOCK1-MARKER',
                                                 text_utf8=b'CODOL-TEXT-MARKER')))
hs.append(CL.create_mapping(CL.SHELL_NAME_FMT % pid, CL.build_shell_payload()))
print('launched pid=%d with TAS+SHELL mappings (markers set)' % pid)
CL.k32.ResumeThread(pi.hThread)

PATTERNS = (('ascii', 'codoMP_client'), ('ascii', 'CODOLBLOCK1-MARKER'),
            ('ascii', 'CODOL-TEXT-MARKER'), ('ascii', 'TCLS_TASMEMORY_'),
            ('utf16', 'TCLS_TASMEMORY_'), ('ascii', 'TCLS_SHELLMEMORY_'))

for wait in (6, 12):
    time.sleep(wait if wait == 6 else 6)
    print('--- t+%ds ---' % wait)
    try:
        res = PM.cmd_scan_multi(pid, PATTERNS, 3)
        for kind, text in PATTERNS:
            hits = res.get(text, [])
            print('  %-6s %-20s %d hit(s) %s' %
                  (kind, text, len(hits), ' '.join('0x%08X' % h for h in hits)))
    except SystemExit as e:
        print('  scan FAILED %s' % e)
    sys.stdout.flush()

for h in hs:
    CL.k32.CloseHandle(h)
