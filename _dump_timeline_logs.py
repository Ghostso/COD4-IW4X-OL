import os
root = r'D:\BaiduNetdiskDownload\使命召唤OL'
paths = [
 r'WeGame\log\tcls\log\TCLSHost_2026-9-14-1789316941.log',
 r'WeGame\cmd_start_for.ini',
 r'WeGame\log\wegame.20260914-002859-619.log',
 r'WeGame\log\client_proxy\wegame.client_proxy.20260914-002902-188.log',
 r'WeGame\log\app.web_log.20260914-002901-691.log',
 r'WeGame\log\app.wegame_env.20260914-002901-090.log',
 r'WeGame\log\comm_auth_log\comm_auth.tgp_daemon.20260914-002901-457271.log',
 r'WeGame\log\tinyget\tinyget.20260914-002900-494.log',
]
for rel in paths:
    p = os.path.join(root, rel)
    print('\n===== ', p, ' =====')
    try:
        raw = open(p,'rb').read()
        for enc in ('utf-8-sig','gbk','utf-16le'):
            try:
                txt = raw.decode(enc)
                if enc == 'utf-16le' or '\x00' not in txt:
                    break
            except UnicodeDecodeError:
                continue
        print(txt)
    except Exception as e:
        print('ERROR', type(e).__name__, e)