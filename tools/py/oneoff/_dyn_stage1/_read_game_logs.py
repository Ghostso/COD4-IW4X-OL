from pathlib import Path
import os, datetime, re, sys
files=[
 r'COD OL\BugTrace.log',
 r'COD OL\Cross\Logs\codomp_client_shipretail.tlg',
 r'COD OL\Cross\Logs\CrossProxy.tlg',
]
for f in files:
    p=Path(f)
    print('===',f,'size',p.stat().st_size,'mtime',datetime.datetime.fromtimestamp(p.stat().st_mtime))
    b=p.read_bytes()
    print('head',repr(b[:128]))
    for enc in ('utf-8','gb18030','utf-16le'):
        try:
            t=b.decode(enc,errors='replace')
            if enc!='utf-8' or '\ufffd' in t:
                pass
            print('DECODE',enc,'replacement',t.count('\ufffd'))
            print('\n'.join(t.splitlines()[-80:]))
            break
        except Exception as e: print('ERR',enc,e)
