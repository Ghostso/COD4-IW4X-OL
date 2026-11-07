# 动态捕获 + 静态解密：层二追查的运行时证据（2026-09-30）

目标：为 `.ff` 的**层二**（AES-CTR 之后的容器体）找到运行时密钥/解码器。
方式：只读运行期观测 + 静态解密；未注入、未改 .text、未触碰 ACE/TenProtect。

---

## 0. 结论速览

| # | 结论 | 级别 |
|---|---|---|
| 1 | 提权代理通道（`agent_client.py` / `elevated_agent.py`）可用，`debug_privilege=true` | 已证 |
| 2 | 客户端可被稳定驱动到 `DW_LOBBY_CONNECTED` + `DWLOBBY_PUMP_SUCCESS`（`st` 4→5） | 已证 |
| 3 | **无关进程读不进游戏内存**：即使启用 SeDebugPrivilege，`ReadProcessMemory` 对客户端仍返回 0 字节（err 5/299） | 已证 |
| 4 | 观察器（AboProbe，持有启动句柄）**可以**读客户端；定向转储工作正常 | 已证 |
| 5 | 240 MB 客户端内存转储中**不存在已解码 zone**，也未出现 `.ff` 的层一产物 | 已证 |
| 6 | 客户端在启动→lobby 路径上**只建立 fastfile 目录（468 个 zone 名），不加载 zone 内容** | 已证 |
| 7 | ⇒ **层二无法在该阶段做运行时观测**；要触达层二必须让引擎真正加载一个 zone | 推论 |

---

## 1. 动态捕获链路（可复现）

```
python CODOLServer\_mainline\agent_client.py ping
  -> {"ok": true, "pid": ..., "debug_privilege": true}

python CODOLServer\_mainline\_e57a5c_experiment.py \
    --sandbox run_codol_001\sandbox_datafix_20260929 \
    --attempts 4 --seconds 130 --poke "" \
    --dump-ranges "0x34000000-0x40000000" \
    --dump-out _cleanout\dump_big.bin --dump-at 60
```

成功轮的状态序列（来自 `state.csv`）：

```
dwLogonStart -> DW_DNS_COMPLETE -> DW_ACCOUNT_LOGIN_COMPLETE
  -> DW_LOBBY_CONNECTED -> DWLOBBY_PUMP_SUCCESS       (st 4 -> 5)
```

注：启动 flake 真实存在（约半数尝试在 ~8.7 s 以 `0xFFFFFFFF` 退出，加载 iips.dll 之后、
ifs2.dll 之前）。重试 4 次可拿到稳定成功轮。**每轮前必须清理残留进程**
（TQMCenter / IIPSHostApp / TP3Helper / 游戏）。

---

## 2. 决定性负结果：无关进程被 ACE 挡住

新建的区域感知只读扫描器 `_cleanout\memscan.py`（`VirtualQueryEx` + `ReadProcessMemory`）：

```
对 explorer.exe（提权下）      : scanned 369,913,856 bytes，正常
对 codoMP_client_shipRetail.exe: handle 可开，枚举到 3588 个区域，
                                 但每个区域 read = 0 字节
                                 （启用 SeDebugPrivilege 后仍为 0）
```

⇒ **只有"持有启动句柄"的观察器能读客户端**。这是 ACE 的保护行为，
与历史记录一致。**结论：动态捕获必须经由观察器（AboProbe），不能用外部扫描器。**

---

## 3. 观察器转储：客户端内存里没有已解码 zone

用观察器的 `--dump-ranges` 抓取客户端 240 MB（`0x34000000-0x40000000`）：

```
RG 记录 1 段 va=0x34000000 size=201,326,592
  nonzero ≈ 1.33 MB
  含 b"client_shipretail" 247 处、".ff" 321 处
  层一产物（'IWffs100' + mp_playlists 头）搜索: NOT FOUND
  RSA 密钥块搜索: NOT FOUND
  b"IWffs100" / b"IWff0100" / b"nifs": 全部 -1
```

⇒ 内存里只有 **fastfile 名称注册表**，没有任何 zone 负载、没有层一产物、没有 RSA 块。

---

## 4. ★ 引擎的 fastfile 注册表（本轮新增明文资料）

从转储中提取出引擎登记的 zone 清单，已落盘：

```
CODOLServer\ENGINE_FF_REGISTRY.csv    468 个 zone 名 + 引擎内路径
```

形态为 `client_shipretail\chinese\<zone>.ff`，覆盖武器/地图/合作/UI 等：
`aa12_mp`、`ak47_mp`、`coop_survival_mp_storm_spring_const`、…（468 条）。

这与 `IFS_CONTENT_MANIFEST.csv`（974 个内容包）互为补充：
前者是**引擎认为存在的 zone**，后者是**磁盘上实际下载的内容包**。

---

## 5. 为什么层二在这个阶段观测不到

启动链走的是：DQ/DW → TLS 登录 → lobby。这条路径**不加载 zone**。
引擎只在进入一局游戏（`map_restart` / `loadzone` / `DB_LoadXAssets`）时才
真正打开 `.ff`、做 RSA+CTR+层二解码。转储中 468 个 zone 名只是
启动期建立的名字表（`DB_BuildOSPath` / zone 存在性探测），并非负载。

⇒ **要观测层二，必须让引擎执行一次 zone 加载**。可选路径：

1. 用控制台/命令行触发 `loadzone <name>`（需要引擎的 console 可用）。
2. 让 DW 流程走到"进入地图"阶段（需要更完整的服务端协议支持）。
3. 用观察器的 `--write-spec` 直接构造"zone 已加载"的引擎状态。

以上 (1)(2) 依赖尚未打通的 ⑤ 阶段；(3) 需要一个已知的 zone 管理对象地址。

---

## 6. 本轮产出

| 文件 | 说明 |
|---|---|
| `CODOLServer\ENGINE_FF_REGISTRY.csv` | 引擎登记的 468 个 zone（本轮动态抓取） |
| `_cleanout\memscan.py` | 区域感知只读内存扫描器（可复用） |
| `_cleanout\scan_zone.ps1` | 提权下"启动链路 + 扫描"组合脚本 |
| `_cleanout\dump_big.bin` | 240 MB 客户端转储（含 fastfile 注册表） |
| `_cleanout\dump_heap.bin` | 64 MB 堆区转储 |

---

## 7. 边界

全程只读；未注入、未改 `.text`、未执行外来代码、未停止/配置 ACE 或其服务。
所有写入类操作（`--write-spec` / `--poke`）本轮均未使用。
