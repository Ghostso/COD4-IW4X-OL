# dwRoomMessage 协议逆向成果 — 2026-10-27

参照：本地内存转储（最高可信度）+ IW4X `IclipMap_t.cpp` 的 RTTI 方法论

## 突破：RTTI 链其实没断，是我算错了偏移

前一版判断"RTTI 被剥离"是**错的**。正确布局（实测 `0x00E6F754`）：

```
+0   pVFTable = 0x00D77818     ← TypeDescriptor 的 vftable
+4   spare    = 0
+8   name[]   = ".?AVdwRoomMessageStartGame@@"
```

关键：内存里搜到的 `?AV...` 地址 `name_va` **指向 `?` 而不是 `.`**，
所以 `TypeDescriptor = name_va - 9`（不是 -8，也不是 -4）。

修正后 **49/49 个 `dwRoom*` 类型全部解析成功**。

## 完整的 RTTI → vtable 链（以 StartGame 为例）

```
名字    ".?AVdwRoomMessageStartGame@@"  @ 0x00E6F75C
TypeDescriptor                          @ 0x00E6F754  { pVFTable=0x00D77818, spare=0 }
CompleteObjectLocator                   @ 0x00DF93B0  { sig=0, off=0, cd=0,
                                                        pTD=0x00E6F754,
                                                        pCD=0x00DF93C4 }
vtable                                  @ 0x00DC7518  (COL 指针在此)
  vtable[0] = 0x00625BE0   serialize   (写方向)
  vtable[1] = 0x00625CE0   deserialize (读方向)
```

49 个 vtable 地址全部唯一，交叉验证通过。
完整清单见 `fixtures/dwroommsg_vtables_20261027.json`。

## ★ 找到 Demonware 位流读写器

从 `StartGame` 的虚函数反汇编里提取出的 API：

| 地址 | 名称 | 行为 |
|---|---|---|
| `0xB77B10` | `writeBits(v)` | 写 v 位，内部 `call 0xB77A70(value, 0, 0x1f, 0)` |
| `0xB777C0` | `writeData(ptr, nbits)` | 写 nbits 位的数据（`shr edi,3` = 按字节算） |
| `0xB774E0` | `readBits()` | 读方向，结构对称 |
| `0xB77A70` | `writeBitsCore(value, start, width, pad)` | 真正的位写入核心 |

## ★ dwRoomMessageStartGame 的线格式（serialize @ 0x00625BE0）

```asm
00625BF0  mov al, byte [esi+4]         ; 1 字节字段
00625BF3  push 3
00625BFA  call writeBits               → writeBits(3)          ; 类型 ID?
00625BFF  push 8 / lea [ebp+8] / push
00625C07  call writeData               → writeData(&byte, 8)   ; 1 字节

00625C0C  mov eax, [esi+8]             ; 某个对象指针
00625C0F  mov edx, [eax+0x118]         ; 取 4 字节值
00625C17  add eax, 0x18                ; 取数据块指针
00625C1A  push 0x13
00625C24  call writeBits               → writeBits(0x13)       ; 19
00625C29  push 8
00625C2D  call writeBits               → writeBits(8)          ; 8
00625C35  push 0x20 / lea [ebp-4]
00625C40  call writeData               → writeData(&val, 0x20) ; 4 字节
00625C4B  lea eax, [edx*8]
00625C56  call writeData               → writeData(&[eax+0x18], edx*8)  ; 变长块

00625C63  push 0x13
00625C6A  call writeBits               → writeBits(0x13)       ; 19
00625C6F  push 8
00625C73  call writeBits               → writeBits(8)          ; 8
00625C78  push 0x20 / [ebp+8]=8
00625C87  call writeData               → writeData(&8, 0x20)   ; 4 字节 = 8
00625C8F  push 0x40 / push eax
00625C94  call writeData               → writeData(&[+0x10], 0x40)  ; 8 字节
```

**`0x13`(=19) + `8` 这一对反复出现 → TLV 风格的 tag/length 前缀。**

## 工具（全部可复跑）

```
CODOLServer\_mainline\
  dump_early.py                    早期抢句柄 + 内存转储（★ 必须先于游戏启动）
  memdump_core.py                  转储内核
  resolve_all_dwroom_vtables.py    49 个 dwRoom* RTTI → vtable（★ 核心成果）
  disasm_dwroom_vfuncs.py          虚函数反汇编
  decode_startgame_msg.py          StartGame 序列化格式解析
```

## 下一步

1. 继续反汇编 `serialize` 剩余部分，解出全部字段
2. 找 `StartGame` 在哪条 service/task 上传输（找父类 `dwRoom` 的分发表）
3. 用它替换大厅 11/4 的 `GAME_START_PAYLOAD`

相关：[[pve-startgame-blocker-who-owns-start]]、[[codol-memdump-and-rtti-limits]]
