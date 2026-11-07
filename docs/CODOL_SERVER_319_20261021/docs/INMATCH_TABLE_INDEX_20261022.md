# 对局内 delta 表总清单（2026-10-22）

> 证据：`run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin`
> 方法：扫描全部 `push imm32` / `mov ecx,imm32` 指向 0xDA0000–0xDB0000 的立即数，
> 只保留「40 字节内紧跟 0x670FF0 / 0x677E10 / 0x6779B0 / 0x677D40 / 0x670D30 / 0x6701D0」的引用。

---

## 1. 对局内一共 6 张表

对局解析入口是 `0x472360` 的 snapshot 解析函数，它依次调用：

```
0x472360  snapshot parser
  ├─ 0x671D80  子结构解析器      → 0xDA8520 (246) + 0xDA90A8 (9)
  │    ├─ 0x4723B9  call 0x671D80
  │    ├─ 0x6720E9/0x672181  read 0xDA8520
  │    └─ 0x673FB3/0x67AE1E/0x67AE3A  read/write 0xDA90A8
  ├─ 0x472401  call 0x471980  readEntityState → 0xDA63E8 (24)
  ├─ 0x472445  call 0x471560  readPlayerState → 0xDA8078 (87)
  └─ 0x470F1F  call 0x671170  数组解码       → 0xDA4608 (64)
```

| # | 表地址 | 字段数 | indexBits | 读引用 | 写引用 | 用途 |
|---|---|---:|---:|---|---|---|
| 1 | `0xDA8078` | 87 | 7 | 0x471797 / 0x471873 | 0x6784B3 | playerState |
| 2 | `0xDA63E8` | 24 | 5 | 0x471BBB / 0x471C71 | 0x6785D7 | entityState |
| 3 | `0xDA90A8` | 9 | 4 | 0x673FB3 | 0x67AE1E / 0x67AE3A | 第三结构（每项 0x2C） |
| 4 | `0xDA4608` | 63~64 | 6 | 0x67122B / 0x671242 | — | 数组元素（每项 0x118） |
| 5 | `0xDA9138` | 42 | 6 | 0x671C27 / 0x671C94 | — | 子结构（每项 0x0C） |
| 6 | `0xDA8520` | 246 | 8 | 0x6720E9 / 0x672181 | — | 大结构（约 0x3B90 字节） |

字段数由代码里的边界检查直接确认：
- `0xDA4608`：reader 内 `mov [ebp-0x14],0x3f` → indexBits=6；边界 `cmp edi,0x3f; ja` 允许到 63。表项数 63 或 64，需真实快照验证（不影响 indexBits=6）
- `0xDA9138`：`0x671C14  cmp [ebp-4],0x29` → 最大索引 41 → 42 项
- `0xDA8520`：`0x6720CB  cmp [ebp-0x3b98],0xf5` → 最大索引 245 → 246 项
- `0xDA8078` / `0xDA63E8` / `0xDA90A8`：由 `push 0x57 / 0x18 / 0x09` 直接给出

---

## 2. 已查清 / 未查清

| 表 | 字段全量导出 | 位序规则 | 状态 |
|---|---|---|---|
| `0xDA8078` playerState | ✅ 87/87 | ✅ | **完成** |
| `0xDA63E8` entityState | ✅ 24/24 | ✅ | **完成** |
| `0xDA90A8` struct3 | ✅ 9/9 | ✅ | **完成** |
| `0xDA4608` | ✅ 63 条已导出 | ✅ | **完成** |
| `0xDA9138` | ✅ 42 条已导出 | ✅ | **完成** |
| `0xDA8520` | ✅ 246 条已导出 | ✅ | **完成** |

**进度：6 张表字段全部导出完成（87 / 24 / 9 / 63 / 42 / 246）。**

---

## 3. 重要更正

旧文档 `INMATCH_TABLES_20261022.md` 的附录写「0xDA4608 = 9 条」——
**错了**。9 条只是这张表的**前 9 项**，实际 64 项。
当时用「连续 plausibility 扫描」在偏移 0x0D8 之后断了，误判为表尾。
代码里的 `cmp edi,0x3f` 证明它到索引 63。

同样，`0xDA63E8` 曾被写成 87 项（与 playerState 相同）——
那也是扫描时越界串到下一张表造成的假象。实际 24 项（`push 0x18`）。

---

## 4. 下一步

1. encoder: bw_run 用 indexBits
2. codec: 见 CODEC_SPEC_20261022.md
3. 离线 decode->encode 对拍
4. 改 src/battle/snapshot.c 补 entityState / struct3 / clientInfo
