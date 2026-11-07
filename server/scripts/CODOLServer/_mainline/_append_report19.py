"""Append section 19 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 19. 实跑：3 条候选假设全部证伪（2026-09-29）

用修好的绝对路径重跑，一次干净命中（attempt 8，
`IFS1_ELEVATED_20260929_121706`），首次在**不移除任何状态**的条件
下打到 `5E8=3`。

### 19.1 本轮实跑事实

```text
37.334  CODEC_TRANSITION  c8=1 s9c=0 5e8=0
37.366  POKE_LOBBY_COMPLETE  mgreq644=1 mgr4f8=1
37.368  c8=2 s9c=1 5e8=1       644 由客户端自己写 = 1
37.369  LOBBY_READY_ONLY      （观察器未强制 5E8）
37.369  LOBBY_5E8_READY       <- 探针发 0x81
37.446  c8=2 5e8=2 638=0x55667788 63c=0x11223344 640=0xD2
37.447  LOBBY_ECHO_READY      5fc8=4570bf477ce4e913
37.477  c8=2 s9c=4 5e8=3 5ec=1 5f0=1      <- 0x83 校验通过
37.478  POST83_SAMPLE  s9c=4 5e8=3 644=1   <- 644 保持 1（本轮未覆盖）
37.509  c8=4 s9c=0 5e8=0 644=0             <- 复位
84.485  「致命错误 / 与大厅服务失去连接」
```

探针侧（`lobby_plain_probe.py`）：

```text
sent_81  (204 B)
recv     153 B  客户端 0x82
sent_83  (204 B, echo8=4570bf477ce4e913)
hold_after_83 25 s
hold_peer_closed   46 ms 后对端关闭
```

### 19.2 假设一：`644=0` 覆盖是复位主因 —— 证伪

```text
本轮完全未写 [req+0x644]：
  c8=1 -> 644=0（构造初值）
  c8=2 -> 644=1（0xBA4080 自己写）
  5e8=3 时 644 仍 =1
  -> 仍然在 32 ms 后复位
```

复位与 `644` 取值无关。此前「`644=0` 才满足 dispatcher」的判断作废。

### 19.3 假设二：客户端在 `5E8=3` 后会主动发 `0x86` —— 证伪

```text
0x83 之后探针持续 recv 25 s（hold_after_83 已实现并生效）
收到的字节数：0
46 ms 后收到对端关闭（RST）
```

客户端在握手成功后**没有向本探针发送任何字节**。§18 里从
`0xBA3E20 -> 0xBA2A60(op=0x86)`、`0xBA3370 -> 0xBA2A60(op=0x86)` 推出的
「客户端会发 0x86」在**本路径上没有发生**。

### 19.4 假设三：复位是「服务端把 socket 关掉」造成 —— 证伪（决定性）

复现窗口内直接读客户端读入器游标（`req+0xB0` = reader）：

```text
reader +0x1C  buffer base = 0x39CAEEA8
reader +0x10  read  cursor = 0x39CAEEC7   (= base + 0x1F)
reader +0x14  write cursor = 0x39CAEEC7   (= base + 0x1F)
```

**读游标 == 写游标**：`0x83` 帧被完整消费后，缓冲区已**排空**，
没有任何「未消费的剩余字节数」去满足 0x83 里携带的长度字段。

→ 3 字节内容不构成 `.text` 修改。**是客户端在收到完整、合法、校验通过的
0x83 后主动关闭连接**，与探针是否关闭无关（探针当时正阻塞在 recv）。

### 19.5 因此第 ④ 步的真实形态

```text
0x83 校验通过 -> 5E8=3（已确证）
下一个动作必然要求一次「客户端发起」的客户端->服务端消息
  （0xBA2A60 在 644==0 分支只回头（ack）入站对象；
   只有 644==3 分支才是客户端自发的 0x86 发送）
而该客户端发起动作在本环境下从未发生 -> 32 ms 后关闭
```

注意：`0x83` handler（`0xBA3BA0`）只写 `5E8` 与 `5EC`/`5F0`，**不写 `644`**。
现有静态推断里没有任何一条能把 `0x83` 校验成功直接推到「发送 `0x86`」，
说明这条边落在尚未找到的第三处代码上。

### 19.6 第一档状态（本轮终态）

```text
① 0x81                已闭合
② 0x82                已闭合（153 B 回帧，稳定）
③ 0x83 校验           已闭合（5E8=3, 5EC=1, 5F0=1）
④ 0x83 -> 下一阶段    未闭合：已证伪 644 取值、客户端自发 0x86、
                       服务端关闭 三条候选；复位由客户端主动发起
⑤ 保活/持续           未闭合
UI 资源缺失           已修复（LoadImage 127 -> 0）
```

### 19.7 顺带修掉的工具问题

```text
1. lobby_plain_probe.py 的 --hold-after-83 解析了但未接线，已补齐
   （签名 + 0x83 后保持连接循环 + 调用点），本轮已是生效版本。
2. auto_lobby_loop 的「SUCCESS: DW_LOBBY_CONNECTED」是**假成功**：
   本轮 attempt 1/2 在探针 sent81=false 的情况下也报成功。
   该判据只反映 DW 状态机到 uA50=5，不反映握手，勿再据此收工。
3. 观察器的 --handshake-ready-file / --handshake-echo-file
   必须传**绝对路径**（提权进程工作目录不同），否则
   LOBBY_5E8_READY_ERROR: DirectoryNotFoundException。
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
