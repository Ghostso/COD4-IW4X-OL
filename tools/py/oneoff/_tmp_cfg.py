import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for p in (r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\players\config_mp.cfg',
          r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923\players\config_mp.cfg'):
    d = open(p,'rb').read()
    print('===', p.split('使命召唤OL\\\\')[-1], len(d), 'bytes')
    print('  头部:', d[:16].hex(' '))
    # 试着当文本找 dvar 名
    for t in (b'dw_autoStartGame', b'dw_matchmaking_intermission', b'dw_startGameCountingDown'):
        i = d.find(t)
        print('   ', t.decode(), '->', ('0x%X'%i) if i>=0 else '未见')
    # 打印全部可打印串里含 dw_ 的
    found = set()
    for m in re.finditer(rb'dw_[A-Za-z_]{3,40}', d):
        found.add(m.group(0).decode('latin1'))
    print('   dw_ 串:', sorted(found)[:20] if found else '(无)')
