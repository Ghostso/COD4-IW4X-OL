from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md')
s=p.read_text(encoding='utf-8')
s += '''\n## 纠正：payload 不是 base64 文本\n\n`0xAF0790` 的字符表确实是 base64，但这只是 C1 某条编码路径，不是 type43 payload 的编码。type43 payload 实测为二进制且以 `07 08 21 75 ...` 等字段流开头；尝试按 4 字符一组反转时 284/285 条在第一组就失败。\n\n因此撤回“payload 是编码文本流”的假设，保留已证实的资产 header 和真实 payload 字节。\n\n已确认：\n\n```text\nasset = [12B header][NUL name][payload bytes]\nheader = {name_ref=0xFFFFFFFF, count, entries_ref}\n```\n\n285/285 条 type43 都能按这个真实基点解析，0 条短资产。\n\n下一步应直接依据 payload 的 opcode 边界（`07 08 ...`、`00 04 ...`、`0A 03 ...`、`0E 03 ...`）恢复字段流语法。\n'''
p.write_text(s,encoding='utf-8')
print('updated')
