from pathlib import Path
p = Path('_tcls_dynamic_probe_fixed.py')
s = p.read_text(encoding='utf-8-sig')
s = s.replace("ROOT = r'D:\\BaiduNetdiskDownload\\娌℃湁鎵惧埌浣嶇疆\\COD OL'", "ROOT = r'D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL'")
s = s.replace("ROOT = r'D:\\BaiduNetdiskDownload\\娴ｅ灝鎳￠崣顒€鏁淥L\\COD OL'", "ROOT = r'D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL'")
s = s.replace("r'D:\\BaiduNetdiskDownload\\娌℃湁鎵惧埌浣嶇疆\\WeGame\\tcls'", "r'D:\\BaiduNetdiskDownload\\使命召唤OL\\WeGame\\tcls'")
s = s.replace("r'D:\\BaiduNetdiskDownload\\娴ｅ灝鎳￠崣顒€鏁淥L\\WeGame\\tcls'", "r'D:\\BaiduNetdiskDownload\\使命召唤OL\\WeGame\\tcls'")
p.write_text(s, encoding='utf-8')
