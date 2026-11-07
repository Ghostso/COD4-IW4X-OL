import os, glob, datetime
root = r'D:\BaiduNetdiskDownload\使命召唤OL\WeGame'
logs = []
for p in glob.glob(os.path.join(root, '**', '*.log'), recursive=True):
    try:
        st = os.stat(p)
        logs.append((st.st_mtime, st.st_size, p))
    except OSError:
        pass
logs.sort(reverse=True)
print('LATEST_LOGS')
for mt, sz, p in logs[:40]:
    print(datetime.datetime.fromtimestamp(mt).isoformat(timespec='seconds'), sz, p)
print('TARGET_TEXTS')
keys = ['StartGame','LaunchGame','RunGame','codoMP','client_shipRetail','TCLS_SHAREDMEMEMORY','TCLSHOST','gameID: 29']
for p in [x[2] for x in logs[:120]]:
    try:
        raw = open(p,'rb').read(2*1024*1024)
    except OSError:
        continue
    for key in keys:
        if key.encode('ascii').lower() in raw.lower() or key.encode('utf-16le').lower() in raw.lower():
            print('HIT', key, p)
for p in glob.glob(os.path.join(root, '**', 'cmd_start_for.ini'), recursive=True):
    print('INI', p)
    print(open(p,'rb').read().decode('utf-8-sig','replace'))