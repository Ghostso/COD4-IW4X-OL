from pathlib import Path
p = Path('_tcls_dynamic_probe_fixed.py')
s = p.read_text(encoding='utf-8-sig')
s = s.replace("ROOT = r'D:\\BaiduNetdiskDownload\\浣垮懡鍙敜OL\\COD OL'", "ROOT = r'D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL'")
s = s.replace("r'D:\\BaiduNetdiskDownload\\浣垮懡鍙敜OL\\WeGame\\tcls'", "r'D:\\BaiduNetdiskDownload\\使命召唤OL\\WeGame\\tcls'")
s = s.replace("if alive:\n    print('INTENTIONAL_STOP', iso(), 'ROOTS', root)\n    stopped = stop_tree(root, final_procs)\n    print('STOPPED_PIDS', ','.join(str(x) for x in stopped))\nelse:\n    print('NO_STOP_NEEDED', iso())", "if alive:\n    print('ALIVE_AT_END_NO_STOP', iso(), 'ROOTS', root)\nelse:\n    print('NO_STOP_NEEDED', iso())")
p.write_text(s, encoding='utf-8')
