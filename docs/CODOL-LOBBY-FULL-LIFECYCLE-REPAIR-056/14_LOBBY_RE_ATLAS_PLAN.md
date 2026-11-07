# 14 — 大厅全量深度逆向大纲（v0.1）

> 2026-10-29。用户判定"整个大厅功能缺损极其严重"，要求对大厅（含连接战斗服务器部分）
> 做最完整最深的逆向。本文是大纲与进度台账，实施记录追加在 `15_LOBBY_RE_FINDINGS.md`。

---

## 一、基础条件（已具备）

| 项 | 状态 |
|---|---|
| 加壳客户端 | 磁盘 EXE 仅 7.5 MB / `SizeOfImage`=230 MB，节名 `.tp3`，代码运行时才填充 ⇒ **静态逆向必须用内存镜像** |
| 解包镜像 | ✅ 已提取 `E:\codol_re\client_image_20261027.bin`（241 MB，VA−0x400000=偏移） |
| 反汇编链 | ✅ capstone 5.0.7 + pefile；已用 GateB(0x62FE80)、状态机(0x63C5E0) 复核成功 |
| RTTI | ✅ 1251 个 `.?AV` + 195 个 `.?AU` 在镜像内；已有清单 `runs/RE_FULL_20261029/rtti_full.md`（163 个 `AS_*`） |
| 运行时对象 | 5 套全内存转储在 `E:\codol_dumps\`（含 `_cover.bin` 覆盖率图） |
| 既有工具 | `CODOL_RE_NET_20261022/*.py`（find_calls/find_refs/xref_gs/state_writes/obj_fields）、`CODOLServer/_mainline/rtti_vtable_from_dump.py` |
| 服务端对照 | `REF_LOBBY_KIT/lobby_server.py`、`codol_crypto.py`、C 战斗服 `CODOL_SERVER_319_20261021/src/**` |

> ⚠ 读取覆盖：所有"未发现某对象"的结论必须附读取覆盖率（M1D 曾因覆盖率 0% 产生假阴性）。

---

## 二、六个工作流（W1–W6）

### W1 基础图谱（类/函数/引用）✅ 进行中
- W1.1 类表：类型名 → TypeDescriptor VA → COL → vftable VA（布局已定：TD=name_va−8，+4=pVFTable）
- W1.2 vtable 槽位图：每个类的 slot N → 函数 VA（**房间/大厅类优先**）
- W1.3 字符串与常量索引：VA ↔ 字符串（错误串/字段名/协议关键字）
- W1.4 交叉引用索引：谁引用某 VA（call/jmp/mov/lea/push），供反向追调用者

### W2 大厅服务层（客户端侧 Demonware 客户端）
- W2.1 54 个 (svc,task) 的客户端发送点与应答处理点
- W2.2 帧/信封编解码（0x86 任务帧、位流读写器 0xB77B10/0xB777C0/0xB774E0）
- W2.3 KDF/握手（0xBA0D20 等）与 nt10 已挂钩的关系
- W2.4 20 个 `services/*` 名字 → 客户端类与调用点

### W3 房间子系统 ★ 重点
- W3.1 `dwRoom*` 类层次与继承（RTTI + COL 链）
- W3.2 每个房间类的 vtable 槽位 → 函数语义（含 `dwRoomImp` 0x60/0x64 两道闸门）
- W3.3 房间消息分发表（0x636F3C，47 项 type）→ 逐项命名
- W3.4 `11/4` blob 结构（26 种尺寸 103–245 B）与成员列表载体
- W3.5 **UI 入口链**：`AS_CreateRoom`/`AS_JoinRoom`/`AS_LeaveRoom`/`AS_IsInRoom`/`AS_GetMemberInfoList`/`AS_QuickMatch` → 后端调用
  （055 判 BP-01"准备按钮不可达"就卡在这条链；这是本次要打通的关键）

### W4 连接状态机与人机接口 ★ 重点
- W4.1 `CA_*` 11 态（0x5C8060 映射）的**写点**与转移条件（055 未解）
- W4.2 谁在什么条件下创建指向 67 B 地址块的 UDP socket（BP-06 的真正断点）
- W4.3 房间态 / 匹配态 与 CA_* 的耦合（`roomChatChannelID`、`2486`/`3265` 等字段的来源）

### W5 战斗握手（客户端侧）
- W5.1 NAT 探针(29 B)/DTLS init(16 B)/cookie/公钥交换(219 B)/数据帧(06 02 …) 的客户端构造点
- W5.2 gamestate 消费（`CL_ParseGamestate`）与 `gamestateupdate` 回报
- W5.3 "等待玩家数据"之后客户端期待什么（快照/实体）

### W6 综合
- W6.1 大厅完整状态图（UI→服务→房间→连接）
- W6.2 未解清单 + 每条的证据与下一步实验
- W6.3 与自研服务端的差异表（我们发什么 / 客户端要什么）

---

## 三、交付物

1. 工具：`056/TOOLS/*.py`（可复跑、只读）
2. 机器可读清单：`E:\codol_re\*.json`（类表、vtable 槽位、分发表）
3. 文档：`14_*`（大纲/台账）、`15_*`（发现）、`16_*`（缺口）
4. 结论一律给：`VA 地址 + 字节/反汇编证据 + 读取覆盖率（如来自转储）`

## 四、纪律

- 只读镜像/转储；不改客户端、不改受保护基线；实机实验沿用冻结链单发规则
- 每条结论标注可信度层级（本地逆向 > IW4X > CoD4X > 其他）
- 不重复已完成的 053/055 结论，只补它们没做的层
