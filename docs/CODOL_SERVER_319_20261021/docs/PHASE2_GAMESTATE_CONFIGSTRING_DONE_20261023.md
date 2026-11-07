# Phase 2 收口：Gamestate / Configstring（2026-10-23）

状态：`DONE`（字节级 sample round-trip）

## 1. 已验证的 opcode 常量

来自 CODOL 2697 参考实现与 3.19 handler：

- `ServerCommandSnapshot = 0`
- `ServerCommandGameState = 3`
- `ServerCommandConfigString = 4`
- `ServerCommandEof = 5`（sample 实际尾部）

这说明外层 `0x473A50` 跳表中的 `3` 是 gamestate 路径，而不是之前推断的 serverCommand。

## 2. 3.19 gamestate 顺序

已由 `firingrange-gamestate.bin` 和 C# writer 逐字节验证：

```text
u8  = 3                         GameState
u32 = reliableSequence
cstring = mapName
cstring = gameType
u32 = field4/checksum
u8  = 4                         ConfigString block
u16 = configStringCount
... configstring records ...
... 附加 config data / trailer ...
```

样本实测：

```text
command           = 3
reliableSequence  = 0
mapName           = coop_train_mp_firingrange
gameType          = coop
field4            = 0x62F0CDCD
config command    = 4
config count      = 6
```

## 3. Configstring 记录格式

3.19 使用 14-bit 索引：

```text
index delta flag:
  1 -> previousIndex + 1
  0 -> 14-bit absolute index

value:
  raw bytes
  0x00 terminator
```

写入路径使用“双游标”：

- bit 字段写在 `Bit` 指向的位置；
- NUL 终止字符串通过 append-only raw byte 游标写入；
- 因此索引位和字符串字节会在最终缓冲区中交错，不能按普通连续位流解析。

这与样本的索引字节 `0xAF` 和后续字符串布局完全一致。

## 4. 样本解码结果

`firingrange-gamestate.bin` 的 6 条 configstring：

| Index | Value |
|---:|---|
| 0 | `\2482\2\2485\1\2490\214\2491\0\3056\2\g_gametype\coop\g_hardcore\0\mapname\coop_train_mp_firingrange\scr_game_allowkillcam\0\scr_team_fftype\0` |
| 1 | 空字符串 |
| 2 | `cod` |
| 3 | `1` |
| 11861 | `0 0 0 1` |
| 12246 | `1159` |

早期看到的内存槽位 `[5] = "1159"` 是客户端按索引映射/压缩后的槽位结果，
不是线上 configstring 的绝对索引。

## 5. 产物

- 解码/编码器：`tools/codol_gamestate_codec.py`
- 解码结果：`fixtures/firingrange-gamestate-decoded.json`

验证输出：

```text
size=259 config_start=0x2C strings=6
map=coop_train_mp_firingrange type=coop field4=0x62F0CDCD
  index=    0 len=142
  index=    1 len=  0
  index=    2 len=  3
  index=    3 len=  1
  index=11861 len=  7
  index=12246 len=  4
tail=44 bytes
byte_exact_roundtrip=True
```

## 6. 遗留边界

样本尾部 44 字节尚未拆成语义字段；当前 codec 将其作为原始 tail 保留，
因此 decode -> encode 仍然保持 259 字节完全一致。

Phase 3 将转入 snapshot codec 的精确公式和逐字节对拍。
