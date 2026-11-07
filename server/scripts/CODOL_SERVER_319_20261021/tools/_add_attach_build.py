from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\CMakeLists.txt')
s=p.read_text(encoding='utf-8')
s=s.replace('    src/battle/weapondefs.c\n', '    src/battle/weapondefs.c\n    src/battle/weaponattach.c\n')
s=s.replace('add_executable(test_weapondefs tests/test_weapondefs.c src/battle/weapondefs.c)\n', 'add_executable(test_weapondefs tests/test_weapondefs.c src/battle/weapondefs.c src/battle/weaponattach.c)\n')
p.write_text(s,encoding='utf-8')
print('patched cmake')
