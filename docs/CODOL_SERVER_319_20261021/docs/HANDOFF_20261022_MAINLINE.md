# CODOL 3.19 战斗服 —— 交接文档 / 下一步主线

> 生成：2026-10-22 晚（接手断点）
> 证据基座：`run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin`
> 规则：只写本机已复核的事实；推断标 [推断]，未完成标 [未完成]。

---

## 0. 一句话现状

对局内三张 delta 表的地址/字段数/偏移/位宽已全部拿到。
当前卡点不是“找不到表”，而是**还没把客户端的 delta 位序完整还原**。

**下一步唯一主线：还原客户端自带的 listen server 写快照路径
（0x6784E0 → 0x677E10 → 0x677D40 → 0x6779B0 → 0x676E00），
据此重写 `src/battle/snapshot.c`；离线用客户端自己的读路径
（0x670FF0 → 0x670CB0 → 0x670D30 → 0x6701D0）做逐字节对拍，通过后才实机。**

---

## 1. 接手起点

### 1.1 证据文件

| 项 | 值 |
|---|---|
| 内存转储 | `run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin` |
| 大小 | 241,537,024 B |
| ImageBase | 0x400000 |
| 偏移换算 | `file_offset = VA - 0x400000` |
| 反汇编 | Python + capstone 5.0.7（本机已装） |

### 1.2 四张表（已导出）

| 表 | 地址 | 字段数 | 索引位宽 | 用途 |
|---|---|---|---|---|
| playerState | `0xDA8078` | 87 (0x57) | 7 bit | 玩家状态 |
| entityState | `0xDA63E8` | 24 (0x18) | 5 bit | 场景实体 |
| struct3 | `0xDA90A8` | 9 (0x09) | 4 bit | 第三类结构 |
| 全 codec 表 | `0xDA4608` | 9 | 4 bit | [推断] clientState / archivedEntity |

`netField_t` = 12 B：`{ uint32 offset; int32 bits; uint32 pad; }`
`bits>0` 位宽；`bits<0` codec；`bits==0` 不发送。
字段明细：`docs/INMATCH_TABLES_20261022.md`、`docs/NETFIELD_TABLE_20261022.md`。

索引位宽 = `floor(log2(numFields)) + 1`（0x670FF0 内 `bsr` / `xor 0x1F` / `0x20-eax`）。

### 1.3 代码现状

- `src/battle/snapshot.c`：只拼了一条 playerState 风格位流。
- **entityState 段从未生成；struct3 段从未生成。**
- `clientInfo` 段在第 250 行附近被 `#if 0` 关闭，注释原因是索引写成 1 bit（应为 7 bit）。
- 构建产物 `build\Debug\codol_battle_server.exe`（本轮未重编译）。

---

## 2. 本轮关键发现：客户端里同时存在“读快照”和“写快照”两条完整路径

这一点纠正了上一版交接里的说法（上一版把 0x670FF0 链误标成“写链”）。
判定依据是底层函数语义：

| 底层函数 | 语义 | 依据 |
|---|---|---|
| `0x66E7F0` | 写 1 bit | `or byte ptr [esi], bl` |
| `0x66E840` | 写 n bit（LSB-first） | `and ebx,mask` + 移位写入 |
| `0x66EC30` | 读 n bit | 从 `[esi+0x0c]` 数据指针取字节 |
| `0x447190` | 读 1 bit | 读 `[edx+0x20]` 位位置并 `and eax,1` |

### 2.1 读路径（客户端解包）—— 这是“协议规范”

```
0x670FF0  MSG_ReadDeltaStruct
  ├─ 0x670CB0  读“最后变化字段索引”（变长/逃逸编码）
  ├─ 0x670D30  MSG_ReadDeltaField（按 netField_t 分派 codec）
  └─ 0x6701D0  单字段读入并与基线异或：to = read ^ from
```

调用点（客户端解析快照）：

| 调用点 | 表 | 字段数 |
|---|---|---|
| `0x4717A4` / `0x471886` | 0xDA8078 | 0x57 |
| `0x471BC8` / `0x471C84` | 0xDA63E8 | 0x18 |
| `0x673FC6` | 0xDA90A8 | 0x09（0x2C 步进 × 0x20） |

### 2.2 写路径（客户端自带的 listen server 发快照）—— 这是“官方实现”

```
0x5AD94A / 0x5ADD76  SV_SendClientSnapshot 区
  ├─ 0x6784E0 / 0x6783B0  写 clientInfo / playerState 外层
  │    └─ 0x677E10  MSG_WriteDeltaStruct
  │         ├─ 0x677D40  从尾向头扫“最后一个变化字段”，返回变化字段数
  │         ├─ 0x66E7F0  写 1 bit（has-delta）
  │         ├─ 0x676030  写变化字段数（11 bit 时有 delta 优化）
  │         └─ 0x6779B0  字段循环
  │              └─ 0x676E00  MSG_WriteDeltaField（判等 + 写出）
  │                   ├─ 0x675A70  浮点/值比较
  │                   └─ 0x6769A0  角度压缩（+0x1000、13 bit、XOR）
  └─ 0x67AE4E / 0x67AE2D  struct3 段
```

**意义**：这就是用户要的“与官方服务器一致”的权威来源——不是猜，
是客户端里真实存在的服务器写码。把它还原即可原样复刻。

### 2.3 已确认的基础写函数细节

| 地址 | 语义 |
|---|---|
| `0x66E7F0` | 写 1 bit（字节对齐时先补零字节） |
| `0x66E840` | 写 n bit，LSB-first，字节对齐补零 |
| `0x676030` | 写 n bit；**n==11 且与上次值差 <0x200 时写 9 bit 差值**，否则写 11 bit 全值 |
| `0x6769A0` | 角度：`(deg*182.04+0x1000)` 取整、5+8 bit、XOR 编码 |

`0x6701D0`（读）已见 codec 分支：-64/-63/-62、-101、-102、-94（8B memcpy）、
-88（32 位）、-61/-60/-59（与全局掩码异或）、-99、0（非发送字段）。

---

## 3. 下一步主线（按顺序，不可跳）

### 步骤 1 —— 位序表（离线，先做）

完整反汇编并伪代码化：`0x677E10 / 0x677D40 / 0x6779B0 / 0x676E00`。
产出位序表，必须写清：

1. has-delta 位的位置
2. “最后变化字段索引”的编码（0x676030 的 11-bit 逃逸规则）
3. 逐字段 change-bit
4. 每个 codec 的负载位宽与字节对齐时机
5. 尾部未变化字段的处理

**验收**：Python writer 输出与客户端写路径逐字节一致；
用客户端读路径语义实现 decoder，decode(encode(x)) == x。

### 步骤 2 —— 补 entityState / struct3 段

按同一套位序实现 entityState（24 字段）与 struct3（9 字段），
接在 playerState 段之后。先各发 1 个实体。

**验收**：离线闭环一致；帧长与客户端真实快照同量级。

### 步骤 3 —— clientInfo 段

索引改 7 bit，解除 `#if 0`。

**验收**：离线解码出 clientNum=0、字段 0 = ET6 实体号。

### 步骤 4 —— 单轮实机（遵守单发规则）

新 run 目录、单客户端、只启动一次。按顺序记录：
出生点是否在地面 → 主武器是否出现 → W+Shift 是否奔跑 → 开火是否掉弹且生效 → 小地图是否有内容。

---

## 4. 明确不做

- 位序表完成前不再实机、不再改 `snapshot.c` 常量。
- 不动 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019`（受保护资产）。
- 不把大厅链路混进对局主线（大厅已单独存档）。
- 不重建整棵游戏树；不改游戏二进制/证书/hosts 作为附带修复。

---

## 5. 复核命令（PowerShell）

```powershell
# 反汇编任意 VA（示例：写路径入口 0x677E10）
python -X utf8 -c "from capstone import *; p=r'D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin'; f=open(p,'rb'); f.seek(0x677E10-0x400000); b=f.read(0x160); md=Cs(CS_ARCH_X86,CS_MODE_32); [print('%08X  %-18s %s'%(i.address,i.bytes.hex(),i.mnemonic+' '+i.op_str)) for i in md.disasm(b,0x677E10)]"

# 导出 playerState 表
python -X utf8 -c "import struct; p=r'D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin'; d=open(p,'rb').read(); o=0xDA8078-0x400000; [print(i, hex(struct.unpack_from('<I',d,o+i*12)[0]), struct.unpack_from('<i',d,o+i*12+4)[0]) for i in range(87)]"
```

---

## 6. 地址速查

| 地址 | 作用 |
|---|---|
| `0x670FF0` | MSG_ReadDeltaStruct（读，协议规范） |
| `0x670CB0` | 读最后变化字段索引 |
| `0x670D30` | MSG_ReadDeltaField |
| `0x6701D0` | 单字段读 + 基线异或 |
| `0x6784E0` / `0x6783B0` | listen server 写 clientInfo / playerState |
| `0x677E10` | MSG_WriteDeltaStruct（写，官方实现） |
| `0x677D40` | 差异扫描（尾→头） |
| `0x6779B0` | 字段循环 |
| `0x676E00` | MSG_WriteDeltaField |
| `0x6769A0` | 角度压缩 |
| `0x676030` | 写 n bit（11-bit delta 优化） |
| `0x66E7F0` | 写 1 bit |
| `0x66E840` | 写 n bit |
| `0x66EC30` | 读 n bit |
| `0x447190` | 读 1 bit |
| `0x5AD350` | SV_SendClientSnapshot 函数起点 |

---

## 7. 运行纪律（AGENTS.md）

- 每个实验独立目录：`run_codol_001\runs\<RUN_ID>\`
- 一次调用只创建一个客户端；早退不自动重启。
- 运行前后对受保护文件哈希并记录；哈希变化则该轮无效。
- 不改 IIPS / hosts / 证书 / 注册表 / 游戏二进制作为附带修复。
- 成功判定必须有时间戳证据：IIPS、Auth、Lobby、同一 client PID。
