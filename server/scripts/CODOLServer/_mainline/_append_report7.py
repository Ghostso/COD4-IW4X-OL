import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 26. 停止 Frida 路线：注入客户端会触发 ACE 告警

### 26.1 结论

**在本游戏进程上使用 Frida 会触发 ACE 告警。该路线已弃用。**

### 26.2 经过（如实记录）

目标是读出 `0x00BA20A0` 收帧解析后的字段真值，以替代纯猜字节。为此
写了 `frida_lobby_codec.py`，挂钩 6 个位置：

```text
0xBA20A0  收帧解析
0xBA21E4  回帧重建
0xBA4080  连接/发送启动
0xBA4127  唯一写 [req+0xC8]=2 处
0xBA0FF0  负载消费
0x7F3800  大厅阶段入口
```

结果分两步：

```text
1) spawn 后挂 6 个 Interceptor，script.load() 时
   frida.TransportError: the connection is closed
   —— 进程被 ACE 回收
2) 改为「先 resume 再 load」后仍然一样；
   只挂系统 DLL(ws2_32 recv/send) + 纯内存轮询的「安全模式」能加载，
   但用户随后观察到游戏弹出告警码
```

即：**只要对平台进程注入，就会被检测**。这与此前
`--patch-lobby-result` 改写 `.text` 触发 `3/1023/61022` 是同一类
反应（见安全边界）。

### 26.3 已执行的处置

```text
1. 立即停止全部 Frida 进程：frida-helper-x86 / x86_64 共 3 个
2. 结束游戏进程 codoMP_client_shipRetail 与 TQMCenter
3. 停止全部本地探针(8443/8444/8446 已无监听)
4. 隔离脚本：frida_lobby_codec.py -> frida_lobby_codec.DO_NOT_RUN.py
5. 删除临时脚本 _frida_safe.py
6. 复核无残留 frida 进程、无残留监听端口
```

### 26.4 安全边界（更新）

```text
不再绕过 ACE、不改安全组件                       —— 原有
不再改客户端 .text 代码                          —— 原有
不再对游戏/平台进程做 Frida 注入                  —— 新增
```

### 26.5 对后续路线的影响

Frida 这条「读运行期字段真值」的捷径已关闭。还原大厅帧 5 位字段语义
只能走**纯静态分析**：

```text
0x00BA0FF0   负载消费入口
0x00BA12E0   用位读取器构造结果对象
0x00BA0EB0   构造发送用位写入器
0x00BA1720   写入发送队列
0x00B78350   位写入原语(dst, bitOff, src, bitCount)
0x00B9BEB0   位读取器构造
```

注意：观察器 `AboProbe.cs` 走的是 `ReadProcessMemory` + EnumWindows，
属于读内存与枚举窗口，**不注入代码**，此前多轮运行未触发告警，仍可继续
使用。所有已确认结论（`DW_LOBBY_CONNECTED`、`DWLOBBY_PUMP_SUCCESS`）
均由该观察器取得，不受本次事件影响。
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
