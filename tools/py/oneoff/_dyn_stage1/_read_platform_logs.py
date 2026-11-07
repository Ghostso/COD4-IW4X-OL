from pathlib import Path
import datetime, re
paths = [
    Path(r'WeGame/log/comm_auth_log/comm_auth.tgp_daemon.20260913-184948-885895.log'),
    Path(r'WeGame/log/tcls/log/TCLSHost_2026-9-13-1789296589.log'),
    Path(r'WeGame/log/app.wegame_env.20260913-184948-552.log'),
    Path(r'WeGame/apps/Cross/Log/tgp_daemon.20260913-185015-311.log'),
    Path(r'WeGame/crash_log.rs'),
]
for p in paths:
    print('='*20, p, '='*20)
    b = p.read_bytes()
    print('size', len(b), 'mtime', datetime.datetime.fromtimestamp(p.stat().st_mtime))
    for enc in ('utf-8-sig','utf-16le','gb18030'):
        try:
            s = b.decode(enc)
            bad = s.count('\ufffd')
            print('encoding', enc, 'bad', bad, 'preview', repr(s[:220]))
        except Exception as e:
            print('encoding', enc, 'error', e)
