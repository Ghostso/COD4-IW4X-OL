from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\CMakeLists.txt')
s=p.read_text(encoding='utf-8')
s=s.replace('    src/battle/equipment.c\n', '    src/battle/equipment.c\n    src/battle/weapondefs.c\n')
s=s.replace('add_executable(test_collision tests/test_collision.c src/world/collision.c)\n', 'add_executable(test_weapondefs tests/test_weapondefs.c src/battle/weapondefs.c)\ntarget_include_directories(test_weapondefs PRIVATE ${CMAKE_SOURCE_DIR}/include)\nadd_test(NAME weapondefs COMMAND test_weapondefs)\n\nadd_executable(test_collision tests/test_collision.c src/world/collision.c)\n')
p.write_text(s,encoding='utf-8')
print('patched CMakeLists')
