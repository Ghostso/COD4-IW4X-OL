from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md')
s=p.read_text(encoding='utf-8')
s += '''\n## 关键发现：type43 payload 是“编码后的字段流”，不是 12B tuple\n\n3.19 中：\n\n- `0xAF0790` = `%c%c%c%c` / `%c%c%c=` / `%c%c==` base64 encoder\n- `0xAF0920` = encoder wrapper\n- `0x49CC70` 通过 `0xE5CA30[type]` 取 type 固定大小，然后拷贝资产\n- `0xE5CA30[43] = 0x4834D0`，返回 `0x0C`\n- `0xE5CA30[45] = 0x4834E0`，返回 `0x30EC`\n\n因此：\n\n- 目录中的 type 43 资产的 12B header 是 `{name_ref,count,entries_ref}`\n- 名字后不是 1.1.1.13 的 12B tuple 数组，而是 3.19 自有的变长字段流\n- 可变字段流最终被编码/序列化为附件数据；当前观察到 `07 08/06/03 ...`、`00 04 ...`、`0A 03 ...`、`0E 03 ...` 等稳定 opcode\n\n这解释了不同附件 `count` 与尾部长度不成 12 倍关系。\n\n## 下一步\n\n以 `0xAF0790` / `0xAF0920` 及 `0xAF0920` 上游解析器为入口，恢复：\n\n1. 字段流 opcode 表\n2. 每个 opcode 的 payload 长度\n3. 与 WeaponDef 的 offset 映射\n4. 多个附件叠加顺序\n'''
p.write_text(s,encoding='utf-8')
print('updated')
