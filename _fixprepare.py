from pathlib import Path
p = Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\DYNAMIC_CLOSURE_RETRY_20261023_2309\prepare.py')
s = p.read_text(encoding='utf-8')
s = s.replace('s, n = re.subn(r"^GAME_ROOT\\s*=.*$", "GAME_ROOT = r\\"D:\\\\BaiduNetdiskDownload\\\\使命召唤OL\\\\run_codol_001\\\\sandbox_ifs1_20260923\\"", s, count=1, flags=re.M)', 's, n = re.subn(r"^GAME_ROOT\\s*=.*$", lambda m: "GAME_ROOT = r\\\"D:\\\\BaiduNetdiskDownload\\\\使命召唤OL\\\\run_codol_001\\\\sandbox_ifs1_20260923\\\"", s, count=1, flags=re.M)', 1)
p.write_text(s, encoding='utf-8')
print('patched replacement')
