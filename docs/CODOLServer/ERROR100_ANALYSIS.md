# 错误 100 深度分析报告

## 结论
错误 100 **不是** 连接失败，而是 **dwLobby 状态机卡死在 DNS 阶段**。

---

## 三个必须分清的事实
1. **面板文本来源**  
   - 字符串 `@SF_UI_DW_LIVE_CONNECTING_FAILED`（EXE VA `0x00DE0640`）  
   - 中文 “无法连接大厅服务!” 在 `localization.txt` 偏移 `0x94F`（GBK 编码）  
   - 由 GFx/Scaleform 绘制的蓝框面板，**非** `MessageBox`（实拍图 `_pop_trace\shots\desktop_game.png` 可见官网按钮）

2. **触发点固定在三处**  
   - `0x007EF210` `cmp esi,4` → 只有“对外可见状态 == 4”才进入该分支  
   - `0x007F25B0` 负责把内部 `[0x84ABA50]` 映射成那个 4  
   - `0x007EF253` `push 0x00DE0640 / call 0x00771240` 投递面板

3. **根因在 `0x007F26C0` 状态 1**  
   - `call 0x007F3600`（DNS 检查）返回值 `[0x84ABA78]` 恒为 0  
   - `0x007F26EE` `push 0x00DE08D8 = DW_DNS_ERROR`  
   - 动态轨迹里 `dwLobby_state` 从 1 走到 2，随后停在 10，状态名全局 `[0xE4EA3C]` 在 *t≈18.54s* 指向 `0x00DE08D8`

---

## 十项核心问答对应
| # | 内容 | 关键结论 |
|---|------|----------|
| 4 | **错误 100 属于哪一类** | 非 socket 连接失败，非握手失败。原始环境 AFD ETW 18 次 `connect` 全部成功，**但目标里没有任何大厅地址** —— 客户端连“往哪连”都没拿到。归属：**DNS/名字解析阶段的本地失败 + 状态机固化为未映射终态**，再以状态 4 的 UI 面板呈现。 |
| 5 | **Lobby / AUTH / LSG 关键函数** | **Lobby**: `0x7F25B0` `0x7F26C0`(跳转表 `0x7F2850`) `0x7F28F0` `0x7F2B90` `0x7F3600` `0x7F34E0`  <br> **AUTH**: `0xB991A0`(校验 HTTP 200 + `auth_task==1` + `code==0x2BC`) `0xB983F0` `0xBA9BC0`  <br> **LSG**: 仅键名 `lsg_server_ticket` / `lsg_server_ticket_size` 与模板 `%s://%s:%d/%s/title/%d/queue/%d`，语义 **UNKNOWN** |
| 6 | **地址来源** | `dwauth.ini`，在 `WinMain 0x77EE40` `fopen` 后按 **7 行** `sscanf`：<br> 字段 3 → `0x81A76A8` (HOST) <br> 字段 4 → `0x81A9EC4` (PORT) <br> 字段 1 → `0x81A7F34` (第二个待解析主机) <br> 当前 `COD OL\` 根目录**没有** `dwauth.ini`，仅存实验产物 `dwauth.ini.mine_created`；全盘仅两个沙箱里有（均为实验写入）。 |
| 7 | **关键词命中统计** | `3074` 在 EXE 与 `Base.dll` 均 **0 命中**（CODOL 不用该经典端口）。<br> DemonWare 明文端点 `stun.us.demonware.net` 等。<br> `dwauth` 仅在 `0xDDBD9C` 一处。<br> `Lobby` 在 exe **52 处**（含主机侧 lobby / leavelobbywarning），`Base.dll` 0 处。 |
| 8 | **网络 API 导入表** | 主 exe 仅导入 `codoMP_client_shipRetailBase.dll` 序号 #1。<br> `Base.dll` 仅 2 项（`LoadLibraryA/GetProcAddress` + `libcef` 一项）。<br> 所有 socket/TLS/HTTP **静态链接**：`WSASocketA` 7 处、`getaddrinfo` 7 处、`SSL_connect` 2 处、`X509_verify_cert` 2 处。<br> OpenSSL 版本字符串同时存在 `0.9.8zg` (34 处) 与 `1.1.0k` (1 处)，实际握手用哪套 = **UNKNOWN**。 |
| 9 | **错误前最后一个成功网络操作** | *t≈20.330/20.342* 两次 UDP `connect` 返回 0 到 `116.130.224.66:8000`，之后为 SSDP 与 QoS 心跳。**这不是大厅**，而是 `ied-tqos.qq.com` 的 IIPS/TQoS 地址发现（载荷 `"ur"` 魔数 `75 72`，且有 6×73B 正常回程）。需纠正前序报告的错误归因。 |
| 10 | **抓包情况** | 四个 pcap 命中该地址，**仅 UDP**，`ied-tqos.qq.com` DNS 解析结果即为该 IP。**全部抓包无大厅 TCP/UDP 会话**，故“大厅用 TCP 还是 UDP” = **UNKNOWN**。 |

---

## 两个方法论关键点（防止下游踩坑）
- **磁盘 EXE 的 `.tp3` 是加密的**。`0x7EF210` 磁盘字节 `0c56578b...`，运行期才是 `83fe040f...`（即 `cmp esi,4`）。**任何对磁盘代码段的反汇编都不成立**，必须用运行期解密镜像：  
  `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` (SHA‑256 `17CEF6E0...FD045`)。
- **`[100]` 这个数字本身来源未定**。它不在 `localization.txt`，也不在 `BD_*` 枚举表，代码路径只压入字符串 key。最可能是 UI 面板编号/参数，但产生点没找到 = **UNKNOWN**，**不要**拿它当协议错误码反推服务端。

---

## 明确标 **UNKNOWN** 的（别当结论用）
- `dwauth.ini` 原始取值
- 字段 2/5/6/7 业务含义
- 大厅实际协议与端口
- `/auth/` 真实 TLS 库
- ticket / LSG 内容语义
- 所有网络调用的调用栈（AFD ETW 不带栈，注入取栈被安全软件挡住）

---

## 建议的下一步（按性价比排序）
1. **E1**：在原始 `COD OL\` 根目录临时放一个 `dwauth.ini` 指向本机，**只读观察** `[0x84ABA78]` 是否变 2、状态名是否变 `DW_DNS_COMPLETE`。这一步能一次锁定“地址缺失 = 唯一第一因”。
2. **E2**：在 `0x007EF253` 下断点读 `[0x84ABA50]` / `[0xE4EA3C]`，补齐第三方可复核的调用栈。
3. **E3**：跟踪 UI 上下文 (`esi+8 / +0x3c / +0x40`) 与 popup 注册表 `0x00DE68CC / 0x00DE68FC`，定位 `100` 的产生点。
4. **E4**：分别置空 `0x81A76A8` 与 `0x81A7F34`，验证两个名字是否都必须解析成功。

---

> **后续动作**  
> - [ ] 将本报告落盘为 `ERROR100_ANALYSIS.md`（已完成）  
> - [ ] 执行 **E1**：在 `COD OL\` 写入最小可用 `dwauth.ini` 并观察状态变化  
> - [ ] 根据 E1 结果决定是否继续 E2–E4