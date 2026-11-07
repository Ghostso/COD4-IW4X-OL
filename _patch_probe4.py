from pathlib import Path
p = Path('_tcls_dynamic_probe_fixed.py')
s = p.read_text(encoding='utf-8-sig')
lines = s.splitlines()
for i, line in enumerate(lines):
    if "ROOT = r'" in line:
        lines[i] = "ROOT = r'D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL'"
    if "WeGame\\tcls'" in line and 'r\'' in line:
        lines[i] = "    r'D:\\BaiduNetdiskDownload\\使命召唤OL\\WeGame\\tcls',"
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
