# E27 执行摘要

## 一句话结论

**Demonware 会话协议的服务端对端实现存在**——但它**不在冻结的 2697 服务端 `codol_dedrun.exe` 里**（E-26 已证那是 iD-Tech 栈），而在工作区内的 **Demonware 大厅模拟器项目**中：C++ 实现 `_e1_regression\ol-mod-olfinal\src\backend\Demonware\`（`Crypto.cpp` 的 `deriveSessionKeys` 使用 `"CLIENTCHAL"`/`"BDDATA"`）与 Python 实现 `REF_LOBBY_KIT\codol_crypto.py`（AES-128-CBC + HMAC-SHA1 的 `0xAB85` 帧、同样的 `expand_key`/`derive_session_keys`）。**2697 服务端生态内不存在该组件**；因此"客户端阶段 1 应答 → 2697 服务端消费"的端到端路径在本轮范围内**不可闭合**，但**该协议的独立服务端对端已确实存在**（面向 1.1.1.13 / 3.3.3.3 客户端构建）。

## 关键事实

1. **冻结样本复核**（全 MATCH）：
   - 客户端 `codoMP_client_shipRetail.exe` = `35375404…d6e1`
   - 恢复镜像 `codol2697-static-candidate.bin` = `24b4ef25…97e4`
   - 服务端 `codol_dedrun.exe` = `80816711…0ea1`

2. **2697 服务端生态盘点**（12511 文件 / 1742.0 MB）：
   - 仅 **4 个 PE 模块**：`codol_dedrun.exe`、`client_loopback_guard.exe`、`client_room2697.dll`、`client_native_loopback.dll`。
   - 其余为资源（`.iwi` 5424、无扩展名 4989、`.gsc` 1303、`.mp3` 485、`.ff` 97 等）；17 个 `.py` 全部是**本地离线启动器/资源注入**工具，不是服务端协议实现。
   - 这 4 个 PE **全部**无 `CLIENTCHAL`/`BDDATA`/`bdLobby`/`dwRoom`/HMAC 握手字符串（E-26 已证 `codol_dedrun.exe`；本轮新增其余三个）。
   - `server2697\` **无** lobby/Demonware 目录；`lobby_runtime2697.py` 是显卡/资源 trap 补丁，非协议实现。

3. **Demonware 对端确实存在于工作区**（PROVEN）：
   | 实现 | 路径 | 关键证据 |
   |---|---|---|
   | C++ | `_e1_regression\ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` | L205-212：`secret = hmacSha1(sessionKey, transcriptHash)`；`challenge = expandKey(secret,"CLIENTCHAL",16)`；`data = expandKey(secret,"BDDATA",72)`；`requestHmac=data[0:20]`、`responseHmac=data[20:40]` |
   | C++ | 同目录 `LobbyProtocol.cpp`（18.7 KB）、`Auth3Protocol.cpp`、`ServiceRegistry.cpp` | 大厅服务分发 |
   | Python | `REF_LOBBY_KIT\codol_crypto.py`（961 行） | `derive_session_keys()`：`challenge=expand_key(secret,b"CLIENTCHAL",16)`、`data=expand_key(secret,b"BDDATA",72)`；帧结构 `u32 len｜0xAB｜0x85｜u32 seq｜iv16｜cipher｜hmac8` |
   | Python | `REF_LOBBY_KIT\codol_crypto.py` 的 `build_handshake_reply`/`build_stage2`/`decrypt_task_frame`/`ticket_from_client_auth`/`session_key_from_ticket` | 完整握手往返 |

4. **协议族判定**：Demonware 帧 = `u32 len｜0xAB｜0x85｜u32 seq｜iv[16]｜AES-128-CBC(cipher)｜HMAC-SHA1[:8]`；明文 = `u32 payload_len｜u8 marker｜payload`。2697 客户端含 `bdLobby`(2)、`dwLobby`(1)、`dwRoom`(38)、`CLIENTCHAL`(1)、`BDDATA`(1)、`0x00AB`(18) —— **是 Demonware 客户端**，但其 Demonware 服务端**不在 2697 服务端包内**。

5. **版本归属冲突**（本轮核心负结论）：
   - 上述 Demonware 对端**面向 `1.1.1.13`（`C1.exe`）/ `3.3.3.3`**，其 IDA 库与 `dw_wire.py` 引用的客户端地址（如 `0x9CE310 bdLobbyConnection::getMessageToDispatch`）**在我们的 2697 恢复镜像中不成立**（`RVA 0x5CE310` 处是数据，不是 `bdLobbyConnection` 代码）。
   - 反之，E-26 在 `codol_dedrun.exe` 里证的 `recvfrom → _SV_ReadPackets → _SV_PacketEvent → _SV_ExecuteClientMessage`（3 位 opcode 0..4）是 **iD-Tech 对局服务端**，与 Demonware 控制面**分层共存**：Demonware = 大厅/认证控制面（TCP，`0xAB85` 帧）；iD-Tech = 对局服务（UDP，17733）。

## 判定表（任务书 §九问）

| 问题 | 回答 | 等级 |
|---|---|---|
| Demonware 协议处理链是否找到？ | **是**，但在 `ol-mod-olfinal`（C++）与 `REF_LOBBY_KIT`（Python）中，**非** 2697 服务端包 | PROVEN |
| 客户端阶段 1 应答是否找到服务端消费者？ | **是（存在），但在另一构建的 Demonware 对端**；**2697 服务端生态内未找到** | 存在性 PROVEN / 2697 内缺失 PROVEN（范围内） |
| 2697 服务端生态是否有 Demonware 组件？ | **无**（4 个 PE + 12511 文件全覆盖扫描，0 命中） | PROVEN（范围内） |
| 首个可证实冲突点？ | 客户端构建不匹配：对端 IDA/地址基于 `1.1.1.13 C1.exe`，2697 恢复镜像在同址无可匹配代码 | PROVEN |

## 被证伪/更正的假设

- **「2697 服务端生态包含 Demonware 会话服务」→ REFUTED**（4 个 PE + 全部 12511 文件 0 命中）。
- **「E-26 的『Demonware 服务端对端不存在』」→ 更正**：**存在**，只是不在 2697 服务端包内；E-26 的措辞应理解为"在 `codol_dedrun.exe` 内不存在"。
- **「`ol-mod`/`REF_LOBBY_KIT` 的 Demonware 实现可直接用于 2697 客户端」→ REFUTED（当前）**：其客户端地址引用（`0x9CE310` 等）在 2697 恢复镜像中不成立。

## 剩余阻塞

1. **2697 的 Demonware 服务端**：未在任何已枚举模块中找到；最小缺失证据 = 含 `bdLobby`/`CLIENTCHAL`/`BDDATA` 的 2697 服务端二进制。
2. **`ol-mod`/`REF_LOBBY_KIT` 的 2697 适配度**：需对其引用的客户端地址在 2697 客户端重新定位后，才能判断协议是否同构。
3. 2697 客户端的 Demonware 帧魔数位置（`0x686210 mov [ecx],0xDEADBEEF`）是**写入**而非比较；2697 是否采用 `0xDEADBEEF` 或其它魔数未闭合。

## 下一步唯一建议

**将 `ol-mod-olfinal` / `REF_LOBBY_KIT` 的 Demonware 握手实现与其客户端地址引用，在 2697 恢复镜像上重新定位并逐项比对**（端口、帧魔数、`0x85` opcode、`CLIENTCHAL`/`BDDATA` 派生——这些字符串在 2697 客户端已确认存在）。若派生物一致，则 2697 客户端可复用该对端实现；若不一致，则把"2697 需要独立的 Demonware 服务端实现"记录为首个架构级阻塞。
