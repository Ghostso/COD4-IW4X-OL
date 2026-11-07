# CODOL 固化记录：启动链恢复（`enable_iips` 闸门）

日期：2026-09-27
工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`
状态：**启动链已恢复，三次独立复现，标准固化链已跑通。**

本文件取代 `HANDOFF_20260927_DYNAMIC_CAPTURE.md` 中的诊断结论。
后者的"阻塞点是 WeGame/TCLS 上下文"与"iips.dll 需恢复为 E2367C48"两条均已证伪，见第 2 节。

---

## 0. 一句话结论

启动链的闸门是 **`iips.ini` 的 `enable_iips`**：

```text
enable_iips=1  ->  IIPSHostApp.exe 启动
               ->  iips.dll 载入
               ->  ifs2.dll 载入
               ->  在线模式（CoD Splash: "使命召唤online Multiplayer"）
               ->  真实 POST /auth/

enable_iips=0  ->  不启动 IIPSHostApp
               ->  不载入 iips.dll / ifs2.dll
               ->  无任何网络层；多数运行静默跑到超时，个别运行 t=11.4s 崩溃（0xc0000005）
```

`enable_iips` 不是"只读回显"。`SUBAGENT_2_IIPS_VERDICT.md` 的 A.2 结论
（"`enable_iips` 一个开关都不控制"）已被单变量对照推翻：那份结论是在
`iips.ini` 恒为 `0` 的条件下得出的，从未做过 `0/1` 对照。

---

## 1. 决定性对照实验（单变量）

克隆沙箱 `run_codol_001\sandbox_ifs1_ctl_iips1_20260927`，与母沙箱
`run_codol_001\sandbox_ifs1_20260923` **只差 `iips.ini` 一个字节**
（`enable_iips=1` 的 `31` vs `=0` 的 `30`）。

其余变量全部受控相同：同一个 `iips.dll`（`E2367C48`）、同版本 exe/Base、
同 `cacert.pem`、同 `dwauth.ini`、同固化链、同提权令牌。

| 运行 | `iips.ini` | `IIPSHostApp` | `iips.dll` | `ifs2.dll` | `/auth/` | 结果 |
|---|---|---|---|---|---|---|
| `IFS1_ELEVATED_20260927_152054` | `=0` `3C143A9E` | 无 | 无 | 无 | 无 | t=11.4s 崩溃 `0xc0000005` |
| `IFS1_ELEVATED_20260927_152647` | `=0` `3C143A9E` | 无 | 无 | 无 | 无 | 跑满 90s，无网络 |
| `IFS1_ELEVATED_20260927_154526` | `=1` `14DEFEE9` | **有** | **有** | **有** | **有** | t=28.0s 退出码 0 |
| `IFS1_ELEVATED_20260927_155155` | `=1` `14DEFEE9` | **有** | **有** | **有** | **有** | t=24.1s 退出码 0 |
| `IFS1_ELEVATED_20260927_155355` | `=1` `14DEFEE9` | **有** | **有** | **有** | **有** | 跑满 90s |

`155355` 用的是**标准固化链** `capture_elevated_network.ps1`（不带 `-Sandbox`，
走默认沙箱 `sandbox_ifs1_20260923`），即固化后的默认路径本身已可用。

### 1.1 附带的强证据

`/auth/` 请求里的 `identity` **三次完全相同**（`356c4bc3`），而 `iv_seed`
与 `X-TransactionID` 每次都不同。`identity` 直接来自 `iips.dll`
（见 `restore_iips_contract_001\t01_iipsinit_identity.py`），
这解释了为什么**必须过 IIPS 才会有 `/auth/`**：缺的不是端口转发、证书或
`dwauth.ini`，而是 `identity` 的产出方。

---

## 2. 修正上一份交接文档的两条错误结论

### 2.1 WeGame / TCLS 上下文不是阻塞点

`tcls_core.exe` / `wegame.exe` 是否存在，与 IIPS 是否载入**无关**：

| 运行 | `enable_iips` | 进程表中 `tcls_core` | IIPS 载入 |
|---|---|---|---|
| `152054` | 0 | 有 | 否 |
| `154526` | 1 | 有 | **是** |
| `155155` | 1 | 无 | **是** |
| `155355` | 1 | 无 | **是** |

三次成功复现里有两次**完全没有** TCLS，仍然完整走到 `/auth/`。

上一份交接文档写的"当前系统检查未发现 wegame.exe / tcls_core.exe"
是可见性造成的误判：非提权进程读 `ExecutablePath` 会返回空（所以才看到
`Path` 空白），而提权 observer 能正常读到
`…\WeGame\TCLS\tcls_core.exe`。它们当时确实在运行（15:06 启动）。

### 2.2 `iips.dll` 的"历史成功版本"认错了，方向是反的

| 版本 | SHA256 | 时间戳 | 身份 |
|---|---|---|---|
| **原始版** | `72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348` | 2026-09-10 | 出厂原件 |
| 09-21 副本 | `E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770` | 2026-09-21 | 本项目自己的 PE 手术产物 |

原始版 `72DD…` 在三处一致：`工具\EX035_DIR\IIPS\iips.dll`、
`工具\EX053_BASELINE\IIPS\iips.dll`、`COD OL\IIPS\iips.dll`。
`E2367C48…` 只存在于沙箱与 `iips.dll.s2backup`，就是
`SUBAGENT_2_IIPS_VERDICT.md` 描述的"抹掉 MSVC RTTI/异常元数据 + 塞入
`0x12345678` 调试桩"的那份。

`CODOLServer\_mainline\_ifs_compare_20260927.json` 把
`SuccessHash` / `NowHash` **写反了**：它把自制的 09-21 副本当成"成功版本"。
上一份交接文档据此把 `72DD` → `E2367C48` 的替换称为"恢复"，方向刚好颠倒。

**当前可用的组合用的是 `E2367C48`，保持不动。** 未验证 `72DD` + `=1`
是否同样可用（见第 5 节）。

---

## 3. 已固化的配置（已验证可用）

沙箱：`run_codol_001\sandbox_ifs1_20260923`

| 文件 | SHA256 |
|---|---|
| `iips.ini` | `14DEFEE97155DCF2E23281DEFFD43C533C0A8E25BB9FCB0A4A8724C16A4C68AB` |
| `IIPS\iips.dll` | `E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770` |
| `IIPS\IFS2.dll` | `5B0324E0B2BA3545A6C02626287D4FBC6A3116594744F4647333982D85508421` |
| `codoMP_client_shipRetail.exe` | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| `codoMP_client_shipRetailBase.dll` | `EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20` |
| `cacert.pem` | `93196D95448DE1755715F5AA8ED972335B1DB64D883E9A02A64758ACB5DEA046` |
| `dwauth.ini` | `7FC20C0868FD15D4CBF4098511EF40425C54D2C3F15250693A92AE0DE4CA8601` |

`iips.ini` 内容（46 字节，LF 行尾，来源 `工具\EX035_DIR\iips.ini`）：

```ini
enable_iips=1
iips_url="http://10.231.2.181/"
```

`dwauth.ini` 内容：

```text
127.0.0.1
0
127.0.0.1
443
0
0
0
```

克隆沙箱 `sandbox_ifs1_ctl_iips1_20260927` 已验证等价（375/375 文件一致，
13 个 junction 指向 `COD OL`），作为回滚快照保留。

---

## 4. 真实 `/auth/` 样本（三次）

服务端：`CODOLServer\lobby_server\lobby_probe_server.py`，
日志 `CODOLServer\logs\lobby_probe.20260927_152039.jsonl`。
每次 TLS 均为 `TLSv1 / AES256-SHA`，HTTP 为
`POST /auth/ HTTP/1.1` + `Expect: 100-continue`。

| 运行 | `iv_seed`（请求=响应） | `X-TransactionID` | `identity` | 结果 |
|---|---|---|---|---|
| `154526` | `3618551541` (`0xD7AEB6F5`) | `4025100734834283898` | `356c4bc3` | `auth_task 10 -> 11`, `code 700`, `lsg_server_ticket_size 128` |
| `155155` | `58073780` | `12324723781211138905` | `356c4bc3` | 同上 |
| `155355` | `2276458792` | （见日志） | `356c4bc3` | 同上 |

请求体模板（三次同构）：

```json
{"auth_task":"10","iv_seed":"<随机>","title_id":"0","identity":"356c4bc3",
 "extra_data":"{\"version\":\"0\",\"user_id\":\"10995207597479878709\",\"extended_data\":true}"}
```

**当前探针在此阶段回显请求的 `iv_seed`。**

---

## 5. 未决项

```text
1. iv_seed 悬案：客户端反汇编记录 response.iv_seed 必须为 0
   （SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md, 0xB984E7 cmp [ebp-0xE4],0），
   但当前探针把请求值回显到响应。此前从未在真实 /auth/ 上验证过，
   因为从来没有真实 /auth/。现在首次具备条件。
2. 握手只推进到 auth_task 10 -> 11。stage 12/24/26/32 尚未触达。
3. 未验证：原始 iips.dll（72DD…）+ enable_iips=1 是否同样可用。
   当前固化沿用 E2367C48 是"经验上可用"，不是"原始正确"。
4. 母沙箱 iips.ini 已由 =0 改为 =1；旧值备份在
   sandbox_ifs1_20260923\iips.ini.bak_enable0_20260927。
```

---

## 6. 当前环境状态

```text
提权代理        pid=3284   port=60220   debug_privilege=true
lobby_probe    127.0.0.1:8443  pid=16100
lobby_socket   127.0.0.2:8444  pid=13296
portproxy      127.0.0.1:443 -> 127.0.0.1:8443
               127.0.0.2:443 -> 127.0.0.2:8444
WeGame/tcls    当前未运行（与 IIPS 载入无关，见 2.1）
```

observer 入口：

```text
标准固化链   CODOLServer\_mainline → python agent_client.py run powershell -NoProfile
             -ExecutionPolicy Bypass -File "…\run_codol_001\capture_elevated_network.ps1"
             -DurationSeconds 90
单沙箱       …\run_codol_001\elevated_ifs1_observer.ps1 -DurationSeconds 90 -Sandbox "<目录>"
```

`elevated_ifs1_observer.ps1` 本轮新增了可选的 `-Sandbox` 参数（默认仍是
`sandbox_ifs1_20260923`）。

---

## 7. 不要再做的（更新版）

```text
不要试图复现 WeGame/TCLS 上下文        已证伪，与 IIPS 载入无关
不要把 iips.dll 换成 72DD 当作"基线"   72DD 是原件，不是当前可用组合
不要把 iips.dll 换成 E2367C48 当作"恢复"  方向本来就反了；当前可用组合已在位
不要从 dwauth.ini / portproxy 入手     三次成功运行都不需要改它们
不要把 enable_iips 当"只读回显"        已被 0/1 单变量对照推翻
不要按进程名批量杀 python.exe          会杀掉提权代理 pid=3284
不要把 enable_iips 改回 0              会直接失去启动链
```

---

## 8. 建议的下一步

按 `AUTH_IV_SEED_CONFLICT_20260927.md` 第 5 节做那个单变量实验
（现在首次可执行）：**只把响应 `iv_seed` 改成 0**，其余全部保持不变
（启动链 / TLS / 证书 / `auth_task` 映射 / ticket / HTTP 200 / 收尾逻辑）。

验收：

```text
last_err=741 消失，或 sub_state 7 -> 9   -> iv_seed 假设成立
变成 735                                  -> 进入 ticket/tag 路径，查 vtable 0xD5A1F8
仍为 741                                  -> 查 HTTP response code 保存与收尾路径
```

================================================================================
固化完成：标准固化链已可稳定载入 IIPS 并产生真实 /auth/。下一步是 iv_seed 单变量。
================================================================================
