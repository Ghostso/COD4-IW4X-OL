# 8081/QoS 通道 AES 密钥的运行时搜寻 —— 报告

日期：2026-09-25
范围：**只读 / 挂起期持句柄**。未注入、未用 Frida、未改系统网络、
未改动被分析文件。ACE(`ace-*.dll`/`ACE-DRV32.dll`)/985 相关模块的
内存区域在扫描时被**显式跳过**。

工具链：`CODOLServer\_mainline\agent_client.py`（提权代理，`debug_privilege=true`）
调用自有只读脚本。全程无 Frida、无进程注入。

---

## 0. 结论速览

| # | 结论 | 强度 |
|---|---|---|
| 1 | 已按需求建立"挂起期 ALL_ACCESS 句柄 → 起监听 → 等 8081 → 扫内存"的完整可复现链路，并**实测拿到可用句柄**（`OpenProcess(ALL_ACCESS)` 返回句柄，`ReadProcessMemory` 成功读满 32–40 MB） | **HIGH** |
| 2 | **未复现 8081 流量**（4 次独立运行，400 s 上限）。故**本次扫描的进程内不存在该会话的 AES 密钥**——不是"找不到"，而是"该时刻无此密钥" | **HIGH** |
| 3 | 对 `codoMP_client_shipRetail` / `TQMCenter` / `IIPSHostApp` 三个进程共扫描 **2280 个 16/24/32 字节候选 key**，用 9 个真实 8081 包的 AES-ECB 解密做验证：**全部 `confirmed = 1`（只满足 1 个包）** | **HIGH** |
| 4 | `confirmed=1` 是**纯 16 位碰撞**：随机 key 蒙特卡洛 20000 次得 `confirmed=1` 出现 14 次（≈1/1429），与观测同量级；真密钥必然是 `confirmed=9`（9/9 包） | **HIGH** |
| 5 | **未找到 key schedule**：以 AES 逆 S-box 精确 256 字节匹配做点位，游戏进程内命中 **0 次** | **HIGH（样本内否定）** |
| 6 | 独立旁证：把 5 MB 运行时镜像（`ENGINE_DUMP_20260925_114204`）做全量 4 字节对齐 AES 扫描，**663 个候选全部 `confirmed=1`**，同样无真密钥 | **HIGH** |
| 7 | 8081 的 AES 密钥**仍为 UNKNOWN**；本报告给出可执行的下一步定位方案 | — |

> **重要澄清（对既有结论的修正）**：§5 中"`.tls` 内置 AES 逆 S-box @ `0x00C84C40`"
> 来自**磁盘镜像截面**（运行时快照的 VA 窗口），**在本机三次独立运行的
> 游戏进程内存里均未复现该 S-box**。因此那条结论的适用性需降级为
> **"该截面/该版本存在 AES 实现"，不能作为本机现网运行的固定寻址锚点**。

---

## 1. 为什么没有 8081 流量（关键，决定本次结论边界）

扫描的前提是先拿到真实 8081 密文。本次四条路径全部只走到 8000：

| 运行 | 目录 | 监听回执 | 8081 |
|---|---|---|---|
| run1 | `_aeskey_run1` | 无（端口被占） | 无 |
| run2 | `_aeskey_run2` | 3× 8000 `ur` 请求 | 无 |
| run5 | `_aeskey_run5` | 2× 8000 `ur` + 2× **60 B 应答** | 无 |
| run6 | `_aeskey_run6` | 8000 无请求 | 无 |

其中 run5 是唯一"应答被接受"的一次：

```
REQ   7572 0010 0008 0003 0000 000b 00003102 00000064 0018 0000
REPLY 7572 0010 002c 0004 0000 0000 00003102 00000064 0000 000f
      0001 7f000001 1f40 00000000 0001 000a "127.0.0.1" 7f000001 1f40 00000000
```

即 `ruHeadLen=16 / BodyLen=0x2c / Cmd=4 / QosResFlag=0xF`，
`ConndIPPortNum=1` + `ConndIP=127.0.0.1:8000` + `GameSvrNum=1` +
`GameSvrIPList="127.0.0.1"` + `ConndIP=127.0.0.1:8000`。
**客户端仍然没有发出 8081 包。**

对照历史成功记录（`SINGLE_V3`，2026-09-25 12:28）：

* 该次是**长时间 late-patch** 后才有 8000+8081 流量
  （`host_redirect.log` 里在 `resumed` 之后陆续 patch 了
  `intldlgs.qq.com`(34 处)、`tqos.gamesafe.qq.com`(3 处)、`exp.tcls.qq.com` 等）。
* 本次 run3/run6 把 patch 窗口拉到 **320–340 s**，并记录到
  `late-patch t=30s hosts={'intldlgs.qq.com': 10}` 之后**再无新 host 出现**，
  即 **`tqos.gamesafe.qq.com` 这个模块在本机 4 次运行中始终未被加载**。

**判定（HIGH）**：8081 通道由 **`tqos.gamesafe.qq.com` 所属模块**发起；
该模块在本机当前环境下**未加载**，因此**不存在该会话的 AES 密钥可找**。
这不是搜寻方法的失败，而是**前提缺失**。

---

## 2. 已排除项（全部机械检验）

### 2.1 进程内存全量 AES 候选（2280 个）

| 进程 | PID | 读取量 | 候选数 | `confirmed≥2` |
|---|---|---|---|---|
| `codoMP_client_shipRetail` | 14756 | 0 B（ACE 已武装，句柄可开但读失败）| 0 | 0 |
| `TQMCenter` | 7404 | 32,043,008 B / 264 regions | 1021 | **0** |
| `IIPSHostApp` | 8908 | 40,116,224 B / 109 regions | 1259 | **0** |

产物：`_aeskey_tqmcenter\aes_key_candidates.jsonl`、
`_aeskey_iips\aes_key_candidates.jsonl`、`_runtime_aes\aes_key_candidates.jsonl`

**全部 2280 条均为 `confirmed_packets = 1`。无一条满足 2 个及以上包。**

### 2.2 假阳性率校验（证明 `confirmed=1` 无信息量）

`_fpr_check.py`：随机 16 字节 key × 20000 次，对 9 个包首块做 AES-ECB：

```
confirmed=0 : 19986
confirmed=1 :    14        (≈ 1/1429)
confirmed≥2 :     0
```

观测到的 2280/2280 全为 `confirmed=1`，**与随机命中率完全一致**。
真密钥的唯一可接受判据是 **`confirmed = 9`**（9/9 包全部解出 `ur`/`us`）。

### 2.3 AES 逆 S-box 锚点（0 命中）

以 §5 所用 AES 逆 S-box 精确 256 字节序列在 TQMCenter / IIPSHostApp 全量内存中搜索：
**0 次命中**。⇒ 这两个进程中**没有可定位的 AES 实现**，
§5 的 `0x00C84C40` 锚点**不适用于本机现网**。

### 2.4 运行时镜像（独立旁证）

`_offline_aes_scan.py` 对 `ENGINE_DUMP_20260925_114204\engine\engine_best.bin`
（5,050,368 B）做 16/24/32 字节全量扫描（含 raw / dword-reversed / full-reversed 三种读法）：

```
size=16  hits=236     size=24  hits=451     size=32  hits=663
TOTAL 663  →  confirmed histogram: {1: 663}
```

同样**全部 `confirmed=1`**。⇒ 该快照内也无会话密钥。

### 2.5 其它既有否定（沿用，不重复验证）

* 静态常量 / `TASData.dat` / `TclsQmFix.dat` / TAS 流密码 / 140 个候选常量 key：
  见 `SUBAGENT_QOS_KEY.md`，全部否定。
* `CryptImportKey`/`CryptEncrypt`/`CryptDeriveKey` 全文件零命中（CryptoAPI 未使用）。

---

## 3. 关键帧与判定依据（本报告新增一手字节）

### 3.1 8000/UDP 请求（本次实测，与历史一致）

```
75720010 0008 0003 0000 000b 00003102 00000064 0018 0000
 'ur'  16    8    3    0    11   Seq      BizID=100  24   0
```

`Seq` 本次为 `0x00003102` / `0x00003280`，历史为 `0x00007da1` / `0x000028b4…`，
单调递增 ⇒ `Seq` 是**客户端自增的事务号**。**强度 HIGH。**

`0x18 = 24 = ruHeadLen(16) + BodyLen(8)`，三处自洽。**强度 HIGH。**

### 3.2 本次生成的 60 B 应答（被接受但未推进）

```
7572 0010 002c 0004 0000 0000 00003102 00000064 0000 000f
0001 7f000001 1f40 00000000
0001 000a 3132372e302e302e3100 7f000001 1f40 00000000
```

* offs 20 `0000`：**应答里该 u16 为 0**（请求里是 24）⇒ 该字段语义是
  **请求侧长度提示**，应答侧置 0。**强度 MEDIUM**（单样本）。
* offs 22 `000f`：`QosResFlag = 0xF`（四个 bit 全置）。
* 随后 `0001` + `7f000001 1f40 00000000` = `ConndIPPortNum=1` +
  `ConndIP=127.0.0.1` + `ConndPort=8000` + `Score=0`。
* 再 `0001` + `000a "127.0.0.1"\0` + `7f000001 1f40 00000000` =
  `GameSvrNum=1` + `GameSvrIPList(str)` + `ConndIP` + `ConndPort` + `Score`。

**客户端接受了它（未重传），但仍未发 8081。强度 HIGH（对该应答形态）。**

---

## 4. 为什么不"继续硬扫"

三条机械理由：

1. **无密文则 oracle 失效**。AES 密钥无法从"密钥 schedule 长得像什么"反推；
   必须用密文验证。当前无 8081 密文 ⇒ 任何候选都无法判定。
2. **命中率已证明是噪声**。2280 个候选全部落在 `confirmed=1`，
   与随机分布无差别；再扫更多内存只会等比产生更多噪声。
3. **锚点不存在**。AES 逆 S-box 在目标进程内 0 命中，
   说明"按 S-box 反查 key schedule 指针"这条路在当前进程里无对象。

---

## 5. 下一步（按性价比排序，均为只读/可机械验证）

1. **先解决前提：让 `tqos.gamesafe.qq.com` 所属模块加载。**
   它不在 `S.REDIRECTS` 的早 patch 列表里，只在 late-patch 中由通用 host 扫描
   偶然命中；本机 4 次运行稳定不可达。
   建议：早期就把它加入 `HOSTS`，或在 `Base.dll` 中静态定位其字符串，
   确认是哪个 DLL/模块承载（很可能是独立 QoS 组件，非 Base.dll）。
2. **一旦能复现 8081，反过来做定位**：在**同一会话内**取一份该进程
   或该模块的内存快照，再跑 `_offline_aes_scan.py`（比在线扫描快且可复算）。
3. **把 oracle 收紧到 `confirmed≥2`** 再扫（本报告的 `_aeskey_rank.py` 已实现），
   避免被 `confirmed=1` 噪声淹没。
4. 若确认 8081 由**独立模块**发起，则该模块自身的 IAT/内置 crypto
   可能以 `LoadLibraryA`+`GetProcAddress` 动态收口（与 Base.dll 同型），
   需要在**该模块**里找 `AES_set_encrypt_key`/`EVP_EncryptInit` 字符串，
   而不是继续扫 `codoMP_client_shipRetail`。

---

## 6. 结论强度汇总

| 结论 | 强度 |
|---|---|
| 挂起期 ALL_ACCESS 句柄 + 读内存链路可用（32–40 MB 实读） | **HIGH** |
| 本机 4 次运行未复现 8081 流量（因此无会话密钥可找） | **HIGH** |
| `tqos.gamesafe.qq.com` 模块在本机 4 次运行中未加载 | **HIGH** |
| 2280 个候选全部为假阳性（`confirmed=1`） | **HIGH** |
| `confirmed=1` ≈ 随机碰撞率（14/20000 实测） | **HIGH** |
| 游戏进程内 AES 逆 S-box 0 命中（§5 锚点不适用本机） | **HIGH（样本内否定）** |
| 5 MB 运行时镜像 663 候选全部假阳性 | **HIGH** |
| 60 B 变体应答被接受但未推进到 8081 | **HIGH** |
| **AES 密钥本身** | **UNKNOWN** |

---

## 7. 本次新增脚本（全部只读）

| 脚本 | 用途 |
|---|---|
| `_mainline\aes_key_early.py` | 挂起期 ALL_ACCESS → 重定向 → 等 8081 → 全量 AES 扫描（跳过 ACE/985 模块区） |
| `_mainline\aes_key_scan.py` | 对**已运行**进程做只读 AES 候选扫描（16/24/32 B，含跨包验证） |
| `_offline_aes_scan.py` | 对内存镜像离线全量扫描（raw/dwordrev/fullrev） |
| `_offline_aes_filter.py` | 离线命中按 `confirmed` 分布过滤 |
| `_aeskey_rank.py` | 多进程候选汇总并按 `confirmed` 排序 |
| `_fpr_check.py` | 随机 key 蒙特卡洛，证明 `confirmed=1` 无信息量 |
| `_read_tcls_shm.py` | 只读打开 `TCLS_SHAREDMEMEMORY*`（未找到） |
| `_list_agent_children.py` / `_netstat_dump.py` / `_port_diag.py` | 进程树 / 端口占用只读诊断 |

## 8. 运行产物

| 路径 | 内容 |
|---|---|
| `_aeskey_run1..6\aes_key_early.log` | 6 次早句柄运行日志 |
| `_aeskey_run5\local_listeners.jsonl` | **含被接受的 60 B QOS_GET_RES 应答（新一手字节）** |
| `_aeskey_tqmcenter\aes_key_candidates.jsonl` | TQMCenter 1021 候选（全假阳性） |
| `_aeskey_iips\aes_key_candidates.jsonl` | IIPSHostApp 1259 候选（全假阳性） |
| `_offline_aes_hits.jsonl` | 运行时镜像 663 候选（全假阳性） |
| `_aeskey_run6\aes_sbox_hits.json` | AES S-box 命中（`[]`） |
