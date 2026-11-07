# Phase 5 收口：Usercmd / 可靠命令 / 输入闭环（2026-10-23）

状态：`DONE`

## 1. Usercmd 向量验收

生成向量：

```text
test_usercmd: 600 cases, 0 mismatch
```

真实客户端 body：

```text
test_usercmd: 15 cases, 0 mismatch
```

## 2. 已确认的 usercmd 格式

- 首部 3-bit opcode
- `opcode == 2` 为可靠文本命令段
- 命令数量为 1 字节
- time 支持绝对值和 delta 两种形式
- buttons、pitch、yaw、roll、move、weapon 等字段按 delta 编码
- move 为 4-bit 位域
- 输入尾部 terminator 校验通过

按钮位定义：

```text
ATTACK   = 1 << 0
SPRINT   = 1 << 1
MELEE    = 1 << 2
ACTIVATE = 1 << 3
RELOAD   = 1 << 4
ADS      = 1 << 11
```

## 3. 可靠命令格式

```text
3-bit opcode = 2
u32 sequence
NUL-terminated ASCII command
```

支持背包命令：

```text
mr 1 1 custom1
mr 1 1 custom2
```

## 4. 动作验收

`test_backpack_reliable`：

```text
ok   custom2    slots=3 current=1157
ok   custom1    slots=1 current=1156
ok   malformed  ignored, slots=1 current=1156
ALL PASSED (0)
```

说明：

- `custom2` 切换到 3 槽，当前武器 1157
- `custom1` 回到单槽，当前武器 1156
- 非法可靠命令不会修改装备状态

## 5. 产物

- C 解析器：`src/world/usercmd.c`
- 背包状态机：`src/battle/equipment.c`
- 测试：`tests/test_usercmd.c`、`tests/test_backpack_reliable.c`
- 向量：`tools/cases.txt`、`tools/real_cases.txt`

## 6. 边界

行为层输入闭环已经完成。官方 3.19 客户端 usercmd 函数的符号级地址绑定
仍可作为后续逆向加固项，但不再阻塞可靠命令和输入处理。
