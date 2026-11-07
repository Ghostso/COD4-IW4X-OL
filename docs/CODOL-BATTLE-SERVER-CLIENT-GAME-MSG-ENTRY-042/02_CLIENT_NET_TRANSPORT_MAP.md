# 02_CLIENT_NET_TRANSPORT_MAP — 客户端网络传输层次图

**证据等级:** `[D]`=CONFIRMED_DIRECT `[F]`=CONFIRMED_DATAFLOW `[X]`=CONFIRMED_CROSSREF `[?]`=UNKNOWN `[B]`=BLOCKED

---

## 1. 层次与模块归属

```
  层                 归属模块                       证据/入口                     本任务状态
 -------------------------------------------------------------------------------------------------
 L0 socket/recv     引擎 EXE(镜像未覆盖节区)       0x76xxxxxx / 0x84xxxxxx        [B] BLOCKED
 L1 netchan/编解码  引擎 EXE .text(镜像已覆盖)      0x87C110 / 0x87D5A0            [D] 已定位
     消息缓冲读取   net-buffer 诊断串              0x99EE98..0x99F428             [D] 已定位
 L2 平台 QoS 分派   引擎 EXE .text(镜像已覆盖)      0x85E6F0(TQOS)                 [D] 平台层
 L3 连接期 OOB      引擎 EXE .text                  0x1C05F0 命令族                 [D] 连接期
 L4 HTTP/代理       libcurl(同镜像内, 单独族)      "Could not resolve"/"proxy"     [D] 独立
 L5 ICMP ping       codoMP_...Base.dll 0x235F7E     041 已判                       [D] 独立
 L6 反作弊/平台通道  .rdata "SendPacket/Kernel*"     ACE/TenGuard 驱动通信           [X] 非游戏netchan
```

---

## 2. 与 040/041 的边界

- 040/041 分析的是 **DLL `codoMP_client_shipRetailBase.dll`**;其唯一独立 socket 簇 = ICMP ping。
- 本轮分析的是 **客户端引擎 EXE 的恢复镜像 `image_best.bin`**;`.text` 内存在 CoD 风格 **netchan/netbuffer 解码器**。
- 两者是**不同模块**,不得互相替代:041 的"无 netchan"结论只适用于该 DLL 的 `.text` 可达范围。

---

## 3. ICMP / libcurl / 平台代理 / 游戏业务 分离(摘要)

| 类别 | 识别证据 | 结论 |
|---|---|---|
| ICMP ping | `WSASocketW(AF_INET,SOCK_RAW,1)` + ICMP type/seq/checksum(DLL `0x235F7E`) | 诊断,与业务无关(041) |
| libcurl / HTTP 代理 | `Could not resolve %s:%s` / `proxy` / `SOCKS5` / `CONNECT %s HTTP` | 平台下载/HTTP,独立簇 |
| 平台 QoS(TQOS) 代理 | 对象字段 `QOSCSPkg*`/`QOSSSPkg*`,`udp://%s:%d`,`tqos_*`,分派器 `0x85E6F0` | 平台 QoS,非业务 netchan |
| 游戏业务 netchan | net-buffer 读取器 `0x87C110/0x87D5A0` + `net_start/net_end/sizeinfo` | **业务消息解析,已定位** |
| 反作弊/内核通道 | `[KernelBind]`/`SendPacket Failed`/ACE-DRV32.dll | 平台/反作弊,非业务 |
