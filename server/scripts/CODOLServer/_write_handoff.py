import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\HANDOFF_20260928_LOBBY_PROTOCOL.md"
doc = r"""# CODOL 大厅协议攻坚 · 交接手册

会话日期：2026-09-28  报告：`CONFIRMED_RESULTS_20260928.md`（33 节）

**当前状态：第一档未完成，第二档未开始。**

---

## 0. 一句话

`[100] 无法连接大厅服务` 已消除；DW 状态机可走到终态 `uA50=5`。
但握手第一步从未执行过（`[req+0x5E8]` 在所有实跑里都停在 1），
因此约 50 秒后必弹 `致命错误 / 与大厅服务失去连接`。

---

## 1. 环境与入口

```
根目录        D:\BaiduNetdiskDownload\使命召唤OL
提权代理      pid 12916（agent_client.py ping 验证）
              python -X utf8 CODOLServer\_mainline\agent_client.py ping
启动链闸门    run_codol_001\sandbox_ifs1_20260923\iips.ini  →  enable_iips=1
iips.dll      须为历史成功版本
              SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
客户端 exe    COD OL\codoMP_client_shipRetail.exe
              SHA256 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537（已验证）
```

磁盘：D 盘 2026-09-28 曾满盘（0 字节可用），导致 AFD ETW 启动失败
（`AFD ETW start failed with exit code -2147024784`）。**跑测试前先确认有空间。**

---

## 2. 复现命令

```text
# 1) 明文大厅探针（必须持续持有连接，超时后不能 break）
python -X utf8 CODOLServer\lobby_server\lobby_plain_probe.py ^
  --bind 127.0.0.1 --port 8446 --log CODOLServer\logs\PLAIN\x.jsonl ^
  --reply-hex <hex>

# 2) 提权链
python -X utf8 CODOLServer\_mainline\auto_lobby_loop.py --rounds 2 ^
  --seconds 100 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 ^
  --poke-lobby-globals

成功判据   SUCCESS: client reported DW_LOBBY_CONNECTED
```

`--poke-lobby-globals` 做两件事：

```text
t>=20s   写 0x081A76A8 / 0x081A7F34 / 0x081A9784 = "127.0.0.1"
         写 0x081A9EC4 = 8443   0x081A9780 = 8446   0x081A9EC0 = 8446
持续     当 [0x08269774+0x4F4+0xC8] == 2 时
         写 [req+0x644] = 1     写 [[0x08269774]+0x4F8] = 1
```

---

## 3. 已确证的契约（可直接实现，无需再验证）

### 3.1 启动链

`iips.ini` 的 `enable_iips=1` 是唯一闸门。此前「必须复现 WeGame/TCLS 上下文」
的结论**已证伪**。

### 3.2 HTTP `/auth/`（TLS）— 完整

```text
响应  200 / application/json / Connection: close
字段  code=700（数字）
      auth_task = 请求 task 映射（请求 32 → 应答 57）
      iv_seed = 0
      server_ticket / lsg_server_ticket: Base64，解码后 128 字节，
        前 4 字节必须 == de ad bd ef
      client_ticket: Base64，长度须与请求一致
      member_position / estimated_wait_time / next_poll_after = 0
      lsg_server_ticket_size = 128
      extra_data: JSON 字符串（749 字节模板见 lobby_response.json）
必须支持  Expect: 100-continue
收尾    TLS close-notify
```

### 3.3 HTTP 队列 PUT — 完整

```text
请求  PUT /v1.0/title/<id>/queue/0/member/<id>
      DW-Server-Ticket / DW-Server-Ticket-Size:128
      DW-Client-Ticket / DW-Client-Ticket-Size:129
      DW-Ticket-Seed: 0
响应  709 字节压缩版（含 client_ticket + server_ticket）
      1220 字节完整版会超 1024 缓冲 → 失败
      263 字节极简版缺票据 → 失败
判据  lob1400=8900  lob240=2
```

### 3.4 大厅通道 — 明文 TCP，非 TLS

指到 HTTPS 端口会报 `WRONG_VERSION_NUMBER`。
根因：大厅主机全局 `0x081A7F34` 从未被填充，导致 DNS 对象 B 解析出
`236.3.0.0`。填入 `127.0.0.1` 后连接才真正建立。

### 3.5 帧布局 — 有原始内存对位为证

```text
u32  frame_len        （含自身 4 字节）
u8   type             （1 或 2 → 帧头 9 字节；其它 → 1 字节；1/2 实测必失败）
u8[] body
```

客户端读入器缓冲区实际内容：

```text
索引  0..24 : 25 字节残留（写入区起点，非我们可控）
索引 25..28 : u32 frame_len
索引 29     : 客户端重建的 type 字节
索引 30..   : body[1..]        ← 分发器从这里取
```

**结论：`body[0]` = type，`body[1]` = opcode，`body[2..5]` = 魔数 u32 ∈ [0xD2,0xDC]**

写点 / 读点相差 `4 + 帧头长度` 字节，来源是 `0xBA217F` 与 `0xBA21E5`
两次调用 `0xB9BB90` 把 `[reader+0x24]` 从 6 改成 1。

### 3.6 分发器操作码表（`0x00BA4440`）

```text
[req+0x5E8]==1 : 0x81 -> 0xBA3C70      0x04 -> 失败
[req+0x5E8]==2 : 0x83 -> 0xBA3BA0
[req+0x5E8]==3 : 0x85 -> 0xBA3710      0x84 -> 0xBA0E20
其余           -> 失败
```

### 3.7 三个处理器

```text
0x81 (0xBA3C70)
   读 u32 → 必须 ∈ [0xD2,0xDC]
   读 u64 → this+0x638 / this+0x63C
   读 8 字节
   调 0xBA1850 写回帧 → 0xBA2F20 入队列 → [req+0x5E8] = 2

0x83 (0xBA3BA0)   ★ 纯回显校验
   读 8 字节，与 this+0x5FC 做 memcmp
   相等 → [req+0x5E8]=3，[req+0x5EC]=[req+0x5F0]=1
   ★ 服务端只需把客户端给的 8 字节原样回发，无需生成密钥

0x85 (0xBA3710)
   读 u32，读 16 字节
```

### 3.8 回帧构造（`0xBA1850` 另一分支）

```text
序列化器  0xB779A0
写原语    0xB777C0
位宽声明  0xB77B10
回帧类型  0x82（客户端对 0x81 的应答）
内含      0xFF 起始字节 + [this+0x538] + [this+0x53C] + 0x400 payload
```

### 3.9 常量表

```text
0xAB   握手确认字节（0xBA1850 无条件写）
0x90   仅 [req+0x644]==3 时写
0xFF   回帧起始字节
0xD2   魔数下界（0xBA1BFA 写死）
0x400  payload 上限
0x418  回帧缓冲
0x44A  回帧缓冲总长（= 0x400 + 0x4A）
```

### 3.10 读入器内存布局（`[req+0xB0]`）

```text
+0x08  size（构造时给定）      +0x0C  游标起点 = 基址 + 0x1F
+0x10  读游标                  +0x14  写游标
+0x1C  缓冲区基址              +0x20  分配量 = size + 0x37
+0x24  由 0xB9BB90 设 = min(n, 0x1F)
0xB9BBB0 = 基址 - [+0x24] + 0x1F     ← 返回指针，不是长度
```

---

## 4. 未完成步骤（按依赖顺序）

### ① 让 `0x81` 处理器真正执行 —— 硬骨头

```text
现状   帧已送进 0xBA3C70，opcode 与魔数均命中，但内部失败
       [req+0x5E8] 不变 2，c8 回落到 4
已缩到 0xBA1850 或其前置条件（[this+0x6DC] / [this+0x644] 的取值要求）
性质   必须实跑验证，不能纯静态推断
```

**建议的绕过方案（性价比最高）**：不做 `0x81` 的内部细节，直接用
`WriteProcessMemory` 把 `[req+0x5E8]` 从 1 置成 2，然后验证 ③④。
这样能跳过这个硬骨头，立刻推进后面的握手步骤。

### ② 收下客户端 `0x82` 回帧

```text
反汇编已完成（0xB779A0 / 0xB777C0 / 0xB77B10）
待确认  服务端收到 0x82 后是否必须应答、应答什么
性质    偏静态
```

### ③ 发 `0x83` 帧（8 字节回显）

```text
契约清楚：把客户端给的 8 字节原样发回 → [req+0x5E8]=3
这是第一档里最容易的一步
性质    需实跑验证
```

### ④ 发 `0x85` 帧（u32 + 16B）

```text
字段语义未确认；0xBA3710 尾部尚未读完
性质    静态 + 实跑
```

### ⑤ 保活节奏

```text
那约 50 秒超时对应服务端应周期发什么 —— 完全未开始
已知   周期重发同一帧会破坏握手（实测），必须按正确节奏发正确内容
性质    需实跑验证
```

### 第二档（未开始）

```text
入口线索  0x7F9350（0xBA4567 附近出现），疑为大厅 UI 与网络层桥
          尚未查证
规模      同类项目数十个处理函数
前置      必须先闭合第一档，否则功能层不会被触发，无从观察
```

---

## 5. 当前唯一的阻塞点：观测手段

```text
需要看到   0xBA20A0 收帧过程中 [req+0xB0] 的逐字段变化
窗口       约 30ms（建立 → 失败）
现有手段   20ms CSV 采样 —— 扫遍全部历史运行，一次都没落进 C8==2 窗口
Frida      能抓，但对游戏进程注入会触发 ACE 告警 —— 已封，不可再用
剩余路径   在 0xBA20A0 的 0xBA20C8（入口）与 0xBA227F（出口）成对采样
```

**已做的改进**：观察器 `AboProbe.cs` 已加入 `CODEC_TRANSITION` 事件，
在 `c8 / s9c / a8 / 5e8` 任一跳变时立即记录完整 reader 缓冲（不走 CSV 行对齐）。
这条通道在本轮已成功抓到写入 `[reader+0xB0]` 的原始字节，
**证明有效，应继续用它**。

---

## 6. 安全边界（不可逾越）

```text
不绕过 ACE、不改安全组件                     —— 原有
不再改客户端 .text 代码                      —— 原有
不再对游戏/平台进程做 Frida 注入              —— 2026-09-28 新增
```

观察器走 `ReadProcessMemory` / `WriteProcessMemory` / `EnumWindows`，
**不注入代码**，多轮运行未触发告警，可继续使用。

---

## 7. 已踩过的坑（避免重走）

### 7.1 方法层面

```text
错误做法  用构造期的静态值推运行期的偏移
后果      同一函数上四次推断被采样推翻（报告 28.5 / 31 / 32 / 33 节）
正确做法  记录原始内存变化（CODEC_TRANSITION），不做推断
```

### 7.2 具体误判

```text
1) CSV 表头与取值顺序错位 → 误判「大厅端口为 0」
   实际 [0x81A9780] 一直是 8443
2) 「[req+0xC8] 从 1 直接跳 4」→ 采样漏帧，实际走完 1→2→4
3) 「大厅通道是 TLS」→ 实际是明文 TCP
4) 「0xB9BBB0 返回可用长度」→ 实际返回缓冲区指针
5) 「缺魔数」被误判为「偏移假设被推翻」（喷洒式实验）
6) 「必须复现 WeGame/TCLS」→ 实际唯一闸门是 iips.ini
```

### 7.3 已知会导致失败的操作

```text
type ∈ {1,2}                        立即 RST
一次性多发多帧                       握手第 3 阶段失败
周期重发同一帧（--repeat-every）      握手第 3 阶段失败
探针 recv 超时后关闭连接              客户端崩溃 0xFFFFFFFF
```

### 7.4 启动 flake

约 20–40% 的启动会无状态直接退出（只载入 iips.dll、无 ifs2.dll）。
`auto_lobby_loop.py` 已内置重试（判定条件：无状态且无 auth task）。
**不要把 flake 当成协议结果** —— 本轮曾因此误判过一次偏移。

---

## 8. 关键文件

```text
报告        CODOLServer\CONFIRMED_RESULTS_20260928.md（33 节）
本手册      CODOLServer\HANDOFF_20260928_LOBBY_PROTOCOL.md
明文探针    CODOLServer\lobby_server\lobby_plain_probe.py
观察器      restore_iips_contract_001\observer2\AboProbe.cs
轮次驱动    CODOLServer\_mainline\auto_lobby_loop.py
提权代理    CODOLServer\_mainline\elevated_agent.py + agent_client.py
反汇编工具  CODOLServer\_mainline\_dis_va.py（镜像 image_best.bin，基址 0x400000）
归档        CODOLServer\archive\CONFIRMED_20260928_2359（470 文件，SHA256 全通过）
```

镜像说明：`_dis_va.py` 读的是
`_mainline\_dyn100_run_20260925_182324\live\image_best.bin`，
加载基址 `0x400000`，覆盖到 `0xE65000`。

---

## 9. 建议的第一步

```text
1. 用 WriteProcessMemory 把 [req+0x5E8] 从 1 置成 2，绕过 ① 的硬骨头
2. 按 3.7 的 0x83 契约，构造 8 字节回显帧，验证 [req+0x5E8] 能否到 3
3. 若成功 → 第一档立即推进一大步；再解决 0x85 与保活
4. 若失败 → 用 CODEC_TRANSITION 抓 0x83 处理时的原始缓冲，按数据判断
```

不要再用「报一个偏移 + 实跑验证」的循环 —— 已在同一处失败六次。
"""
open(p, "w", encoding="utf-8", newline="\n").write(doc)
print("wrote", len(doc), "chars")
