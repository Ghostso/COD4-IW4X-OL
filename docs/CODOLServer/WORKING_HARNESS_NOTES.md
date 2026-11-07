# CODOL 本地服务器 Harness —— 可复现操作手册

最后更新：2026-09-25（无人值守会话）

## 0. 前提

- 提权代理在跑：`CODOLServer\logs\elevated_agent.json`
- 所有提权命令通过 `agent_client.py` 发送，无需再点 UAC
- 不修改任何系统网络配置（无 netsh / 路由 / DNS / 防火墙 / 网卡）

## 1. 已确认可行的核心技术

### 1.1 绕过 ACE 读内存

```text
SeDebugPrivilege 必须在提权进程内显式启用（High 完整性不算够）
挂起创建时先 OpenProcess(PROCESS_VM_READ / ALL_ACCESS)，句柄在 ACE 武装后仍有效
已运行十余秒再 OpenProcess 会被 ACE 以 err=5 拒绝
```

### 1.2 绕过 ACE 改内存（不注入）

Frida 注入会被 ACE 抓到（`警告码(3, 1032, 179002)`）。
正确做法：挂起期 + 运行期持续原地改写字符串。

```text
C:\...\run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe

python -X utf8 CODOLServer\_mainline\suspend_host_redirect.py ^
  --exe <game.exe> --cwd <sandbox> --out <run_dir> ^
  --seconds 55 --reply-variant 0
```

## 2. 已打通的主机名改写清单

```text
挂起期即可命中：
  ied-tqos.qq.com            @ 0x00DD98A0
  cod4master.activision.com  @ 0x00DBD558
  stun.us.demonware.net      @ 0x00DC6610
  stun.eu/jp/au.demonware.net @ 0x00D5A9FC / 0x00D5A9E4 / 0x00D5A9CC

运行期才出现（后加载模块）：
  tqos.gamesafe.qq.com       @ 0x67990A20, 0x68917438, 0x63061504 ...
  dump.gamesafe.qq.com       @ 0x11D22B78 ...
  exp.tcls.qq.com            @ 0x146C5080 ...
  intldlgs.qq.com            @ 0x0ECAFD48 ...（十余处）
  down.safe.wegamex.com(.hk) @ 0x146BDE08
  stun1-tub.codol.qq.com     @ 0x081A9C50, 0x12392FE8
```

## 3. TQoS 协议（已实测确认）

### 请求（客户端 → 服务器，UDP 8000）

```text
0..1    'ur'
2..3    ruHeadLen = 0x0010 (16)
4..5    BodyLen   = 0x0008 (8)
6..7    Cmd       = 0x0003
8..9    ProtoVer  = 0x0000
10..11  reserved  = 0x000B
12..15  Seq (u32) 每次重传 +1
16..19  BusinessID = 100
20..21  0x0018 (24)
22..23  0x0000
```

全部**大端**。`16 + 8 = 24` = 包长。

### 最小应答（已实测被客户端接受）

```text
'ur' + u16(16) + u16(8) + u16(4) + u16(0) + u16(0) + u32(seq) + u32(100) + u32(0)
```

效果：客户端**停止重传**，交互闭合。

## 4. 当前未解决

```text
1. QOS_GET_RES 完整字段位宽（GameSvrIPList / ConndIPPortList 24 项的结构）
2. 大厅/认证的真实 host:port —— 二进制里零命中，只能运行时下发
3. 启动竞态：约一半概率客户端停在 TQoS 之前（需自动重试）
4. TCP 80 端口被系统保留，无法绑定（UDP 80 可绑）
```

## 5. 已知的坑

```text
- 必须先用 taskkill 清掉 codoMP_client_shipRetail / TQMCenter / IIPSHostApp，
  否则 8000/8081 被上次的监听占用，本轮监听会 bind 失败。
- 组合脚本(run_fake_stack.py)的多进程模式会破坏时序，务必用
  suspend_host_redirect.py 的单进程模式做协议实验。
- Frida 一律不要挂在游戏进程上。
```
