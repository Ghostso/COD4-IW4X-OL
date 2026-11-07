# 未受保护基线副本 · Frozen Launch Chain (Unprotected Copy)

> 本目录是**固化启动链的可读写副本**，用于阅读、试验与重建。

## 1. 它和受保护基线的关系

| | 受保护基线 | 本目录 |
|---|---|---|
| 位置 | 本机 `CODOL_VERIFIED_GOLDEN_20261019\` 与 `REF_LOBBY_KIT\` | 仓库 `baseline/unprotected-kit/` |
| 性质 | **固定范本**，只读；一旦被直接拿去跑或改动，就会失效 | 可读写副本，随便改、随便跑 |
| 是否入库 | **不入库**（一个字节都没有上传） | 入库存档 |

来源：本机 `CHAIN_UNIFIED_20261103\REF_LOBBY_KIT\`（统一链，2026-11-03）。

**为什么要分开**：受保护基线是"参照系"——它必须保持逐字节不变，才能用来判定
"这次改动到底改了行为还是改了环境"。任何直接拿它去跑、去改的实验都会污染参照系。
所以正确做法永远是：**复制一份到别处改，参照系只读校验**。

## 2. 文件职责

| 文件 | 职责 |
|---|---|
| `run_all.py` | 一键集成启动器：清理旧占用 → 修 hosts / dwauth.ini / 证书 → 起两个本地服务 → 驱动注入与观测 |
| `nt10.py` | 注入与观测驱动（API 挂钩、内存映射追踪、网络调用追踪） |
| `lobby_server.py` | 大厅 lsg 服务（明文，监听 127.0.0.2:3074） |
| `fake_auth_tls.py` | 鉴权服务（TLS `/auth/`，监听 127.0.0.1:3074） |
| `battle_server.py` | 战斗服（UDP 28960：NAT → DTLS → ECDH → 快照） |
| `codol_crypto.py` | 协议与密码学实现（ECDH-P224、AES 流、HMAC-SHA1、会话描述符） |
| `marketplace_store.py` | 商城 / 商店目录数据 |
| `write_dwauth.py` | 生成 `dwauth.ini` |
| `make_local_ca.ps1` | 生成本地 CA 与 SAN 证书 |
| `_golden_hashes.json` | 固化清单：每个文件的 SHA-256 与字节数 |

## 3. 固化启动链怎么用

### 3.1 前置

- Windows + Python 3.11
- 证书：`make_local_ca.ps1` 生成，SAN 必须同时包含
  `localhost` + `formal-zone-auth.codol.qq.com` + `formal-zone-lsg.codol.qq.com`
- 私钥与证书**不在本仓库**（已剔除），必须本地重新生成 —— 见 §5

### 3.2 校验清单（动手前必做）

```powershell
python run_frozen_chain_once.py --verify-only --kit <kit 目录>
```

逐文件比对 SHA-256 与字节数；任何一项不符就停下，说明基线被动过，本次结果无效。

### 3.3 单发启动（推荐）

```powershell
python run_frozen_chain_once.py --seconds 90 --out chain.txt
```

| 参数 | 含义 |
|---|---|
| `--kit` | 基线目录（默认指向受保护基线；实验请显式指向本副本） |
| `--game-root` | 客户端根目录 |
| `--seconds` | 观测时长 |
| `--out` | 观测输出文件 |
| `--verify-only` | 只校验清单，不启动 |
| `--write-manifest` | 为当前 kit 生成新清单（**不要对受保护基线用**） |
| `--authorize-next-launch` | 显式授权下一次启动 |

### 3.4 直接跑集成链

```powershell
python run_all.py --secs 150 --out n10run.txt
```

常用开关：`--restore-hosts`（只恢复 hosts，不跑游戏）、`--no-hosts`（不改 hosts）、
`--trace`、`--ps-probe`、`--clients 1`、`--no-kill`、`--force`。

### 3.5 端口与域名约定（写错就静默失败）

| 域名 | 地址 | 协议 | 进程 |
|---|---|---|---|
| `formal-zone-auth.codol.qq.com` | 127.0.0.1:3074 | TLS `/auth/` | `fake_auth_tls.py` |
| `formal-zone-lsg.codol.qq.com` | 127.0.0.2:3074 | 明文大厅 lsg | `lobby_server.py` |
| 战斗服 | UDP 28960 | 二进制 | `battle_server.py` |

`dwauth.ini` 的正确内容是三行：

```
formal-zone-lsg.codol.qq.com 3074
formal-zone-auth.codol.qq.com 3074
0x03EA
```

### 3.6 铁律

1. **单发**：一次调用只起一个客户端；早退不自动重启，重试必须换新的 run 目录。
2. **产物隔离**：日志、快照、标志、证书、生成配置全部落在 `runs/<run-id>/`，不写回 kit。
3. **不动受保护基线**：不复制、不改写、不往里写运行时状态。
4. **收尾**：`--restore-hosts` 恢复 hosts，避免残留劫持。

## 4. 内存转储：什么时候做

转储的价值取决于**时机**，晚 10 秒现场就已经变了。按下面这张表判断：

| 现象 | 转储时机 | 目的 |
|---|---|---|
| 握手无响应 | 客户端发起连接后 3–5 秒仍无 `RX #1` | 看 socket 是否建立、密钥是否派生 |
| 大厅停住 | 登录界面停留 >15 秒、状态不变 | 看 lsg 解析到哪一步 |
| 战斗服收不到包 | 服务端 `收包=0` 且客户端已进房 | 看 battle endpoint / securityKey 是否一致 |
| 崩溃 / 闪退 | 崩溃后 **30 秒内** | 保留异常现场与调用栈 |
| 正确的状态 | 已进入目标界面且稳定 5 秒 | 作为"应有的样子"对照样本 |

执行要点：

- 转储前先记录：**PID、进程启动时间、run-id、时间戳**，四者缺一不可，否则事后对不上日志
- 一个 run **只转储一次**（与单发规则一致），需要第二次就换新 run 目录
- 只转需要的内存区（例如仅相关模块的线性区），不要把整个进程倒一遍
- 转储后立刻与同一 run 的 RX/TX 日志按时间对齐，先定位"最后一次正确交互"在哪一帧

## 5. 安全说明

- 本目录**不含**任何私钥或证书：`_rsa.txt`、`_leaf2.key`、`_ca.pem`、`_leaf2_chain.pem`
  等已全部剔除。需要时用 `make_local_ca.ps1` 在本机重新生成。
- 不含游戏本体文件、不含任何压缩包。
- 清单 `_golden_hashes.json` 只包含哈希与字节数，不含数据本身。
