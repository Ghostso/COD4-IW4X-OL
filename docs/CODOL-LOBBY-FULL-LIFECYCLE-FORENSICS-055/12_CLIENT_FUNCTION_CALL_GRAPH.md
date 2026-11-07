# 12 — 客户端函数调用图（大厅相关）

> **地址纪律**：本文件所有地址均标注 `(模块, VA, RVA)`，ImageBase `0x00400000`，无 ASLR。
> 历史上有两处地址错误（`0x7765A0`→`0xB765A0`、`0x7A44F6`→`0xBA44F6`），本文件已按实测校正。

---

## 1. 大厅链路总图

```
[UI 进程内 Flash]
   │  ✗ 不可达（ui_mp.ff 加密，熵 7.95–8.00）
   ▼
[Scaleform ExternalInterface]
   │  ✗ AS_* 类名存在（163 个），TD→COL 引用 0 处 ⇒ 注册方式 UNKNOWN
   ▼
[dwLobbyEventHandler]        vtable 0x00DE07A4
   ├─ 槽4 0x7F1040 (ret 0xc)  3 参数
   ├─ 槽6 0x7F1060 (ret 0x20) 8 参数 → 0x7E7C90 路由
   ├─ 槽7 0x7F10C0 (ret 0xc)  3 参数 → 0x7E79C0
   └─ 槽8 0x7F1110 (ret 0x14) 5 参数 → "是不是我自己"
   ▼
[0x7E7C90 路由]   按 (p1,p2) 遍历表 0xE376C08..0xE37B7A8（stride 0x25D0）
   │  命中条件：p1==[esi-0x25A8] && p2==[esi-0x25A4]
   ▼
[handler 0x6371F0]  房间信道处理器（建房后注册）
   ▼
[0x637000]  构造位流： push nbits(=[ebp+0x24]*8); push buf(=[ebp+0x20]); call 0xB779A0
   ▼
[0xB774E0 readBits(3)] → [0xB772E0 readData(8)] → type
   ▼
[0x636f3c 分发表]  47 项（type 0..0x2E），41 个有效 handler
   ├─ 0x02 → 0x63495A → 0x625940 → vtable 0x00DC7504 (dwRoomMessageText)
   └─ 0x0F → 0x635968 → 0x627ee0 (RoomInfo::deserialize)
```

---

## 2. 房间对象相关

| 符号 | 模块 | VA | RVA | 说明 |
|---|---|---|---|---|
| `dwRoomImp` vtable | EXE | `0x00DC7274` | `0x9C7274` | 单例 `[0x082E13FC]` |
| `dwRoomMatchUber` vtable | EXE | `0x00DC795C` | `0x9C795C` | 单例 `[0x082E1518]` |
| `MyEventHandler` vtable | EXE | `0x00DC78F0` | `0x9C78F0` | `dwRoomMatch::Init` 的局部类 |
| 自动开局状态机 | EXE | `0x0063C5E0` | `0x23C5E0` | `dwRoomMatchUber` 的 vtable+0x68 |
| 建房回调 | EXE | `0x0063B500` | `0x23B500` | `MyEventHandler` 的 slot[1] |
| 创建 dwRoomMatchUber | EXE | `0x0063E510` | `0x23E510` | `0x63E5D6` 有无条件写 `[0x82E1514]` |
| 状态机跳表 | EXE | — | — | 1→0x63C7F8, 2→0x63C85F, 3→0x63C89B, 4→0x63C8B8, 5→0x63C970 |

**实测字段（memberCount=1 时的 `dwRoomMatchUber`）**
```
+0x020 = 1            状态（停在 1）
+0x024 = 0x7852B855
+0x028 = 0x38
+0x02C = 0x80
+0x030..0x038 = 0
+0x108 = 0x3B03DBF8
+0x120 = 0            timer
+0x138 / +0x140 = 0   计时器字段（从未启动）
```

---

## 3. 位流原语

| 符号 | VA | RVA | 行为 |
|---|---|---|---|
| `writeBits(v)` | `0xB77B10` | `0x777B10` | 内部 `call 0xB77A70(value,0,0x1f,0)` |
| `writeData(ptr,nbits)` | `0xB777C0` | — | — |
| `readBits` | `0xB774E0` | `0x7774E0` | — |
| `readData` | `0xB772E0` | — | — |
| 位流构造 | `0xB779A0` | — | 34 B 对象，参数 `(buf, nbits)` |
| 剩余比特 | `0xB9BBB0` | — | `[+0x1C] − [+0x24] + 0x1F` |

---

## 4. 接收分发（战斗服侧，供对照）

| 符号 | VA | 说明 |
|---|---|---|
| 接收分发 | `0xBA4430` | 成员函数，`cmp [esi+0xC8],2` 状态门 |
| 类型码比较 | `0xBA44F6` / `0xBA4557` / `0xBA45F0` | 0x81 / 0x83 / 0x84 |
| 1 字节读取器 | `0xB765A0` | 包装 `0xB783C0` |

> ⚠️ 历史文档写的 `0x7765A0` / `0x7A44F6` **不在此表中**，因为经反汇编验证**不是函数**。

---

## 5. 连接状态机（供交接边界参考）

`0x005C8060` 是"状态值→状态名"映射：

| 值 | 名称 |
|---|---|
| 0 | CA_DISCONNECTED |
| 3 | CA_CONNECTING |
| 4 | CA_CHALLENGING |
| 5 | CA_LOADING |
| 6 | CA_CONNECTED |
| 7 | CA_SENDINGSTATS |
| 8 | CA_GAMESTATE |
| 9 | CA_PRIMED |
| 10 | CA_ACTIVE |

`call 0x5C8060` 搜不到（通过 vtable/间接调用）。
**服务端能观测到的对应信号**：

| 客户端状态 | 服务端可见 |
|---|---|
| 3 CA_CONNECTING | `RX_OOB cmd='connect …'` |
| 7 CA_SENDINGSTATS | `RX_OOB cmd='stats'` |
| 8 CA_GAMESTATE | `RX_OOB cmd='gamestateupdate N'` |
| 9 CA_PRIMED | **无信号** |
| 10 CA_ACTIVE | `RX_CLIENT_GAME_HEADER` 带 usercmd |

---

## 6. 未定位的环节

| 环节 | 状态 |
|---|---|
| Flash 按钮 → Scaleform 回调 | **不可达**（加密资源） |
| `AS_*` 类的注册点 | **未知** |
| `dwRoomMatch::Init` 的调用点 | **未知**（函数体在加密节 `.tp3`，VSize 219 MB） |
| 各 `dwRoomMessage*` 的 type 常量 | 41 个 handler 里只有 2 个语义确定 |
| 信封里 roomId 的字节位置 | **未知** |
| "客户端决定不建 UDP socket"的判定点 | **未知**（这是 BP-06） |
