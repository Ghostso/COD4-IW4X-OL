import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()

add = """

---

## 22. 「致命错误」正文已捕获：与大厅服务失去连接

### 22.1 弹窗正文（此前从未拿到）

观察器 `AboProbe.cs` 原先只记录窗口标题，所以只能看到
`#32770 text=致命错误`。本轮给 `ScanWindows` 增加了子控件枚举
（`DLG_CHILD` 事件），一次运行即拿到正文：

```text
t=89.151  WINDOW_NEW hwnd=0x7103D6 class=#32770 text=致命错误
t=89.153  DLG_CHILD idx=0 class=Button text=确定
t=89.153  DLG_CHILD idx=1 class=Static text=
t=89.153  DLG_CHILD idx=2 class=Static text=与大厅服务失去连接
```

**弹窗正文是「与大厅服务失去连接」。** 即该弹窗是大厅通道被判定断开的
*后果*，不是大厅连接阶段失败。

### 22.2 精确时序（run `IFS1_ELEVATED_20260928_190708`）

```text
t=37.065  探针 accept，收到 28 字节首帧，已回 204 字节
t=84.076  uA50=5  DWLOBBY_PUMP_SUCCESS      <- 大厅状态机已成功
t=89.151  弹窗「与大厅服务失去连接」
```

探针侧日志：

```text
t=send     回帧 204 字节
t=+20.09   recv_timeout holding=true        ; 其后不再收到任何字节
t=+40.09   recv_timeout holding=true
t=+60.10   recv_timeout holding=true
t=+80.12   recv_timeout holding=true
t=+93.12   conn_error WinError 10054        ; 客户端发 FIN，探针才发现
```

探针在 t≈93 才读到 FIN，而弹窗出现在 t=89.15 —— 说明**客户端是先发
FIN、再弹窗**，探针只是迟了一个 20 秒超时窗口才察觉。断开是客户端
主动发起的，不是探针关连接导致的。

### 22.3 断开的直接原因：服务端从未发出可解的业务帧

收帧契约（`0xBA20A0` + `0xB9BB90`/`0xB9BBB0`）：

```asm
00BA20D3  call 0xC73A00        ; 裸 recv(1) 到 [req+0xa8]（帧类型字节）
00BA20E9  mov al, byte [edi]   ; al = 从连接读到的类型字节
00BA20F0  cmp al, 1
00BA20F4  cmp al, 2
00BA20F8  mov ebx, 9           ; 类型 1/2 -> 帧头 9 字节
                              ; 其它     -> 帧头 1 字节(ebx 保持 1)

00B9BB90  cmp eax, 0x1f        ; [obj+0x24] = max(n, 31)
00B9BBB0  mov eax, [ecx+0x1c]  ; 已缓冲字节
          sub eax, [ecx+0x24]
          add eax, 0x1f        ; 可用长度 = 0x1c - 0x24 + 31
```

客户端只收到 28 字节时：

```text
0x1C = 28, 0x24 = 31  ->  可用长度 = 28 - 31 + 31 = 28
```

`0xBA20A0` 的取帧返回 `edi <= 0`，**没有任何业务帧被解出**。客户端在
「连接已建立、但服务端始终没有帧」的状态下撑了约 50 秒（37 -> 87），
然后判定与大厅服务失去连接。

### 22.4 已确定的完整帧格式

```text
u32  长度前缀（little-endian，含自身 4 字节）
u8   类型
        类型 1 或 2  ->  帧头 9 字节
        其它        ->  帧头 1 字节
     ---------- 位打包负载 ----------
     每字段 5 位编码（头部 / 长度 / 元数据），载荷 ≥ 200 字节
```

对照实验（`lobby_plain_probe.py --reply-hex`）：

| 回送 | 结果 |
|---|---|
| 不回 | 卡在 `req9c=1`，最终断连 |
| 28B 回声 | 进入 `sub-state 3`，弹窗推迟到 t≈84 |
| 24B（`18 00 00 00`+20B） | 立即 RST |
| 200B / 204B | 被接受，状态推到 `uA50=5`，约 50 秒后仍断连 |

### 22.5 已排除：周期性重发并不能保活

给探针加 `--repeat-every 2`（每 2 秒重发同一帧）后，结果**反而变差**：

```text
DW_ACCOUNT_LOGIN_COMPLETE uA50=3 -> DW_LOBBY_ERROR  uA50=3
```

大厅握手在第 3 阶段即失败。说明客户端对帧的**到达时点/顺序有要求**，
盲发会打断握手。因此保活必须是「按正确节奏发正确内容的帧」，而不是
简单心跳。

### 22.6 结论与下一步

```text
大厅连接                 ✓
[100]无法连接大厅服务     ✓ 已消除
DWLOBBY_PUMP_SUCCESS     ✓ 已达成
与大厅服务失去连接        ✗ 仍会发生：服务端没有可解的业务帧
```

唯一剩余缺口：**构造一条客户端的合法首帧并按时序送达**。已知输入：

```text
客户端首帧 28B: c8 00 00 00 | c8 00 00 00 d2 00 00 00 dc 00 00 00
                00 00 08 00 | <rand32> <rand32>
长度字段 = 200；负载需 ≥ 200 字节
类型字节待定（1/2 -> 9 字节帧头）
```

下一步应定位**构造/解析该首帧的服务端侧对应函数**（客户端在
`0xBA20A0` 之后由 `0xBA0FF0` 等消费），据此推导服务端应答的类型字节
与 5 位字段语义。

### 22.7 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2115 + 本轮 190708/191742 两次运行
观察器新增 DLG_CHILD 子控件文本采集
探针新增 --repeat-every（实验用，默认关闭）
```
"""

s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add), "chars")
