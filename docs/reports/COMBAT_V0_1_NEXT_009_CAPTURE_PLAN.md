# COMBAT_V0_1_NEXT_009_CAPTURE_PLAN.md

> 任务：COMBAT-V0.1-NEXT-009 步骤 1–3 —— 取证方案（**尚未授权实施采集**）
> 前置：[NEXT-008 CAPTURE_INVENTORY](COMBAT_V0_1_NEXT_008_CAPTURE_INVENTORY.md) ·
> [NEXT-008 FIELD_RECOVERY](COMBAT_V0_1_NEXT_008_FIELD_RECOVERY.md) ·
> [NEXT-008 IMPLEMENTATION_GATE](COMBAT_V0_1_NEXT_008_IMPLEMENTATION_GATE.md) ·
> [NEXT-008 SHA-256](COMBAT_V0_1_NEXT_008_SHA256.txt)
> 本次**未修改任何文件**（含 `lobby_server.py`、`GOLDEN-LOBBY-001`、战斗服源码）。

---

## 0. 状态声明（按任务要求）

> **本任务停在【方案阶段】。**
>
> | 前置条件 | 状态 |
> |---|---|
> | 阅读 NEXT-008 三份报告 + SHA-256 | ✅ 已完成（步骤 1） |
> | 定位 `service=21 task=5` 实际响应路径 | ✅ 已完成（步骤 2） |
> | 提交日志插桩方案 | ✅ **本文件**（步骤 3） |
> | **日志改动授权** | ❌ **未获得** |
> | **独立工作副本** | ❌ 未建立（授权后建立） |
> | **采集样本** | ❌ 未执行 |
>
> **⇒ 依 任务"如果尚未获得日志改动授权…停止在方案阶段，列出所需授权和最小缺失条件；
> 不得宣称字段已恢复"—— 本次不宣称任何字段已恢复。**

---

## 1. 已定位的响应路径（步骤 2 结果，可复核）

### 1.1 代码位置

| 层 | 文件 : 行 | 内容 |
|---|---|---|
| **分发** | `REF_LOBBY_KIT/lobby_server.py:1147` | `objs, note, pushes = reply_objects(r["service"], r["task"], r["payload"])` |
| **service=21/task=5 分支** | `lobby_server.py:581` | `if service in (0x15, 0x8A) and task in (5, 16):` |
| 对象构造 | `lobby_server.py:615` | `cc.build_mission_session_object(...)` → 236 B 会话对象 |
| **帧封装** | `codol_crypto.py:697` | `def build_task_reply_objects(aes_in, hmac_in, seq_out, task, reply_id, objects, status)` |
| **发送点** | `lobby_server.py:1162-1165` | `rep = cc.build_task_reply_objects(...)` → `conn.sendall(rep)` |
| 长度日志（已存在） | `lobby_server.py:1166-1167` | `log("  -> 0x85 应答 seq=%d(replyId=%d) service=%d task=%d 对象=%d (%d 字节)")` |

**⇒ 完整原始帧在 `lobby_server.py:1165 conn.sendall(rep)` 之前已完全就绪（变量 `rep`），且日志已在 1166 行记录其长度。这是插桩的最佳位置。**

### 1.2 帧的逐字段布局（本次用现有代码离线复算验证）

**校验：`26 + 272 + 8 = 306`，与日志记录的 `(306 字节)` 逐字节吻合。**

| 区间 | 长度 | 内容 | 来源 |
|---|---|---|---|
| `[0:4]` | 4 | `len-4` = `0x0000012E` (302) | `codol_crypto.py:718` |
| `[4]` | 1 | `MARK = 0x85` | `:719` |
| `[5]` | 1 | `KIND_TASK` | `:720` |
| `[6:10]` | 4 | `seq_out`（本会话为 **47**） | `:721` |
| `[10:26]` | 16 | **IV（`os.urandom(16)`，每帧不同）** | `:715`/`:722` |
| `[26:298]` | **272** | ciphertext（AES-CBC） | `:716`/`:723` |
| `[298:306]` | 8 | `hmac8`（HMAC-SHA1 前 8 B） | `:724` |

**解密后的明文（272 B）：**

| 区间 | 内容 |
|---|---|
| `[0:4]` | inner 长度 = **262** |
| `[4]` | marker = **1**（应答；推送为 2） |
| `[5:267]` | inner（262 B） |
| `[267:272]` | 零填充（`(5+262+15)//16*16 - 267 = 5`） |

**inner（262 B）内部：**

| inner 偏移 | 字节 | 含义 |
|---|---|---|
| `+0x00` | `0A <reply_id u64>` | replyId = 47 |
| `+0x09` | `08 <status u32>` | status = 0 |
| `+0x0E` | `03 <task u8>` | task = 5 |
| `+0x10` | `08 <len(objects) u32>` | = 1 |
| `+0x15` | `08 <len(objects) u32>` | = 1（重复） |
| `+0x1A` | **236 B 会话对象** | `build_mission_session_object` 输出 |

**⇒ ★ 关键：会话对象在明文中的偏移是固定的 `inner+0x1A`，即
整帧 `cipher[?]` 解密后 = `plain[5+0x1A] = plain[0x1F]`。**

### 1.3 ★ 本次新增的限制性发现（影响"重建"路线）

用**当前** `codol_crypto.build_mission_session_object(False, playlist=10,
map_override='coop_take_mp_fav_tropical', game_type_override=0x1000003)` 复算：

- 长度 = **236 B** ✅ 与日志一致；
- **但**代码内注释声明的普通布局为 **237 B**（`6+24 + 14 + 15 + 28 + 9 + 11 + 15 + 5 + 15 + 6 + 55 + 9 + 25`）。

**⇒ 两者相差 1 B，说明当日实际走的分支/参数与当前代码不完全一致。**
**这进一步支持 NEXT-008 的结论：不得用"服务端代码重建"代替"客户端实收字节"。**

---

## 2. 插桩方案（步骤 3，**待授权**）

### 2.1 具体文件、函数与位置

| 项 | 内容 |
|---|---|
| **文件** | `REF_LOBBY_KIT/lobby_server.py`（**唯一**需改动文件） |
| **函数** | `handle_lobby(conn, ...)` 的应答分支（`lobby_server.py:1150-1167` 的 `try:` 块内） |
| **插桩位置** | **`lobby_server.py:1165` `conn.sendall(rep)` 之后、`:1166` 日志之前** |
| **改动规模** | **新增 1 个函数 + 1 次调用（≤ 15 行）**；不触碰任何协议/加密/业务逻辑 |
| **默认状态** | **由开关文件控制，默认关闭**（与既有 `.enabled` 风格一致） |

**建议实现（伪代码，待授权后落地）：**

```python
# ---- 新增（文件顶部或工具区）----
CAPTURE_FLAG = os.path.join(OUTDIR, "capture-21-5.enabled")
CAPTURE_IN   = os.path.join(OUTDIR, "capture-21-5.in.log")    # 客户端->服务端 原始帧
CAPTURE_OUT  = os.path.join(OUTDIR, "capture-21-5.out.log")   # 服务端->客户端 原始帧

def cap(dir_tag, conn, raw, service, task, seq, note=""):
    """只读落盘：时间戳 + 方向 + 对端 + service/task/seq + 完整 raw hex + 长度 + sha256。"""
    if not os.path.exists(CAPTURE_FLAG):
        return
    peer = ""
    try: peer = "%s:%d" % conn.getpeername()
    except Exception: pass
    h = hashlib.sha256(raw).hexdigest()
    line = ("%s\t%s\t%s\tservice=%d\ttask=%d\tseq=%d\tlen=%d\tsha256=%s\t%s\t%s\n"
            % (datetime.datetime.now().isoformat(timespec="milliseconds"),
               dir_tag, peer, service, task, seq, len(raw), h,
               note, raw.hex()))
    with open(CAPTURE_OUT if dir_tag == "S->C" else CAPTURE_IN, "a") as f:
        f.write(line)
        f.flush()

# ---- 在 1165 行 sendall 之后插入 ----
                        conn.sendall(rep)
                        cap("S->C", conn, rep, r["service"], r["task"], out_seq - 1)   # ★ 新增
                        log("  -> 0x85 应答 seq=%d(replyId=%d) ..." % (...))
```

### 2.2 记录的是哪一层？（任务要求的明确回答）

| 选项 | 本次方案 | 理由 |
|---|---|---|
| 发送前**完整帧** | ✅ **选这个** | `rep` 就是 `conn.sendall` 的完整入参（306 B），含帧头/IV/密文/HMAC |
| 接收后完整帧 | ⭕ **同时记录**（`cap("C->S", ...)` 插在 `conn.recv` 处） | 用于**同会话关联**（见 §2.3） |
| 解析后对象 | ❌ 不记录 | 已有 `reply_objects` 的 note 日志；且对象≠原始字节 |

**⇒ 记录的是【发送前完整帧】+【接收后完整帧】，两者都是原始字节。**

### 2.3 如何关联同会话的 `21/5` 响应与后续 `6/14 mmbook` 请求

| 关联键 | 说明 |
|---|---|
| **TCP 对端**（`peer = ip:port`） | 同一 `conn` ⇒ 同一会话（NEXT-008 已证 `seq=47→48` 同连接） |
| **连接建立序号** | 在 `=== 大厅连接建立 ===` 处落盘一个自增 `conn_id`，两个方向都带上 |
| **时间戳（毫秒）** | 两帧间隙 < 1 s（实测同秒） |
| **出站/入站 seq** | 应答 `out_seq=47`、请求 `seq=48`（连续），可交叉核对 |
| **HMAC 密钥组** | 两帧同一 `pick_keyset` 命中 ⇒ 同一会话密钥 |

**⇒ 关联方式：`(conn_id, peer)` 为主键，`seq`/`时间戳` 为次序。**
**严禁跨 `conn_id` 拼接。**

### 2.4 如何验证长度、完整性和消息方向

| 验证项 | 方法 |
|---|---|
| **长度** | 日志已记 `(306 字节)`；插桩行也记 `len=`；**两值必须相等** |
| **帧头自校验** | `struct.unpack_from("<I", raw, 0)[0] == len(raw) - 4` |
| **方向** | 记录在 `out.log`（S→C）/ `in.log`（C→S），且带 `dir_tag` |
| **完整性** | 每行附 `sha256`；事后对 hex 重新计算并比对 |
| **解密可复现** | 用会话密钥对密文 CBC 解密，校验 `plain[0:4] == 262`、`plain[4] == 1`、`inner+0x0E == 0x03 0x05` |
| **HMAC 可复现** | `hmac8(hmac_in, raw[:-8]) == raw[-8:]` |

**⇒ 上述 6 项全部可离线复核，不需要客户端参与。**

---

## 3. 采集流程（步骤 5，**待授权**）

| 步 | 动作 | 约束 |
|---|---|---|
| 1 | **建立独立工作副本**（复制 `REF_LOBBY_KIT` 到新目录，插桩只改副本） | **不动冻结基线与原目录** |
| 2 | 落盘开关 `capture-21-5.enabled` | 默认关；采集时开、采完关 |
| 3 | 走**已授权的测试流程**（大厅 + 手动进对局，与既有 `run_all.py` 同法） | **不启动/注入/附加客户端进程；不读客户端内存** |
| 4 | 采集后立即关闭开关，记录采集起止时间 | — |
| 5 | 保存 `capture-21-5.out.log` / `capture-21-5.in.log` 原文件（不编辑） | 含原始字节、时间戳、会话标识、序号 |

**★ 明确不做**：不修改加密、不修改 `SEC_KEY`、不修改 `6/14` 应答正文、不部署、不提交。

---

## 4. 字段恢复流程（步骤 6，采集成功后执行）

1. **取同 `conn_id`** 的 `21/5` 出站行与紧随的 `6/14` 入站行；
2. 复现解密，取 `plain[5+0x1A : 5+0x1A+236]` = **会话对象 236 B**；
3. 记 `mmbook` 的 A/B 字面值（`"mmbook <A> <b64> <B>"`）；
4. **逐字节扫描**会话对象 236 B 中是否存在 A（LE/BE、1/2/4/8 字节宽度）；
5. 依 NEXT-006 §2 已证的**偏移保持性**，若命中则 A 在记录中的偏移 = 其在槽中的偏移；
6. **区分"数值对应"与"语义"**：即使命中，也只报"数值出现在偏移 X"，
   **不**断言语义（不得因 A=796 认定 = PLAYLIST_VERSION）。

**判断响应是否含完整 `0x238` 记录**：本次 236 B 会话对象 **≠ 0x238（568 B）**，
⇒ **预期不能直接得到完整记录**；只能得到"可用于构造记录的字段"。
这本身是一个**可复现的结论**，将在采集后核实。

---

## 5. 所需授权与最小缺失条件（任务要求）

### 5.1 所需授权

| # | 授权项 | 范围 | 影响面 |
|---|---|---|---|
| **A1** | **修改 `REF_LOBBY_KIT/lobby_server.py` 的日志（仅新增 1 个落盘函数）** | **仅在独立工作副本中** | 不触碰协议/加密/业务；默认关闭 |
| **A2** | **运行大厅 + 手动进对局一次**（已授权测试流程） | 本机 `127.0.0.1` | **不启动/注入/附加客户端**；仅人工点击 |
| A3 | 允许在 `OUTDIR` 写 `capture-21-5.*.log` | 两个文本文件 | 只增不删 |

### 5.2 最小缺失条件

| # | 缺失条件 | 阻塞什么 |
|---|---|---|
| **M1** | **A1 未授权** | 无原始响应字节 ⇒ **步骤 4–6 全部无法执行** |
| M2 | A2 未授权 | 无法产生新会话样本 |
| M3 | 无含 `0x85 service=21 task=5` 应答体的外部抓包 | 备选路径 (b) 不可用 |

**⇒ 在 A1（+A2）到位之前，本任务的可交付上限就是本方案 + 原始证据现状说明。**

---

## 6. 方案的可复核性（无需授权即可验证）

本方案的第 1 节（响应路径与帧布局）**已被离线复算验证**：

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001"
python -X utf8 z9_capture_plan.py
# 输出关键行:
#   session object len = 236 (日志记 236)
#   inner len = 262
#   frame len = 26 + 272 + 8 = 306   <- 对照日志: (306 字节)
```

**⇒ 帧布局与插桩位置的正确性**不依赖采集授权，已可独立复核。**

---

## 7. 本次的可复核脚本

| 脚本 | 作用 |
|---|---|
| `_combat_next001/z9_capture_plan.py` | **离线复算 306 B 帧布局（不发送/不联网）** |
| `_combat_next001/zy_evidence.py` | NEXT-008：全 KIT 检索 21/5/mmbook 证据文件 |
| `_combat_next001/zz_dump.py` | NEXT-008：转储内无 21/5 响应字节 |
