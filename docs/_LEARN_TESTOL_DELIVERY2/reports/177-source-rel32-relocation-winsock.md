# 177 · rel32 重定位、四段安装的顺序、WinSock 收发

## 一、范围

本报告学习 **2 处实现**：

- `DisconnectWitness.cpp` 399–518 行
- `win32/win_net.cpp` 120–199 行（**该文件完整读完**）

## 二、`E8 rel32` 的重定位：本组最精确的一段

```cpp
const auto originalDelta = *(const std::int32_t*)(comError + 1);
auto *const destination = comError + ComErrorStolen + originalDelta;
tramp[0] = 0xE8;
*(std::int32_t*)(tramp + 1) = (std::int32_t)(destination - (tramp + 5));
tramp[ComErrorStolen] = 0xE9;
*(std::int32_t*)(tramp + ComErrorStolen + 1) =
    (std::int32_t)((comError + ComErrorStolen) - (tramp + ComErrorStolen + 5));
```

注释：

> **重定位这条 call。**它的操作数是从**指令末尾**算起的 delta，所以同样的字节放在新地址会调用完全不同的地方。**解析原始目的地，然后从 trampoline 重新编码 delta。**

### 2.1 三步

```text
1. destination = (comError + 5) + originalDelta        ← 解出绝对目的地
2. tramp 内的 call：delta = destination - (tramp + 5)   ← 重新编码
3. tramp 尾部的 jmp：delta = (comError + 5) - (tramp + 5 + 5)
```

**注意第 3 步的目标是 `comError + ComErrorStolen`**（= `comError + 5`），即**跳过整个被偷的 call**，从它的下一条指令继续。

### 2.2 与"位置无关指令"的对照

同一个文件里，`cls.state` 的 10 字节 `mov [imm32], imm32` **可以直接复制**（`std::copy_n(target, StolenSize, trampoline)`），因为它是**绝对地址**、位置无关。

而 `E8 rel32` **必须重算**。这两条并排出现在同一个安装函数里，是最好的教学对照。

## 三、五字节跳 + NOP 填充的两种写法

### 3.1 `cls.state`：`std::fill`

```cpp
std::fill(target + HookSize, target + StolenSize, std::uint8_t{0x90});
```

注释：

> **把跳转没有覆盖的五个字节 NOP 掉**，这样如果执行曾经落到跳转之后，**不会留下半条解码的指令**。

`HookSize = 5`、`StolenSize = 10`，所以填 `target[5..9]`。

### 3.2 validator：单个 `validator[5] = 0x90`

`ValidatorStolen = 6`、`HookSize = 5`，所以只需填一个字节。

**两种写法本质相同，只是填充长度不同**——用 `std::fill` 更通用。

## 四、四段安装的顺序与"失败可见"

### 4.1 顺序

```text
1. cls.state 写入钩子          ← 硬要求（失败即返回 UnsupportedHost / UnexpectedBytes）
2. Com_Error 钩子              ← 字节不符则【只记日志，继续】
3. configstring validator      ← 同上
4. 硬件写断点                  ← 最后，注释说明理由
```

### 4.2 第 4 步为什么最后

```cpp
// The watchpoint last: it is the one that cannot be evaded, and it is armed
// after the software hooks so their own writes cannot trip it.
```

> **写断点放最后：它是那个无法被规避的，而它在软件钩子【之后】武装，这样钩子自己的写不会触发它。**

即：**安装动作本身会写内存**，如果断点先装好，可能被安装过程触发的写污染。

### 4.3 每一段都有成功与失败的日志

```text
"Com_Error witness armed too"                                      成功
"Com_Error witness NOT armed -- sub_4F8350 is not the expected call"     失败
"configstring validator witness armed"                             成功
"configstring validator NOT armed -- sub_514540 prologue differs"   失败
```

**失败消息直接说明"哪个函数的什么不符"**，而不是笼统的 "failed"。对比 `animtree` 的多站点安装是**静默跳过**——这里的做法更好。

## 五、`NET_GetPacket` 的错误分级

```cpp
if (received == SOCKET_ERROR) {
    lastError_ = WSAGetLastError();
    if (diagnostic < 8 && lastError_ != WSAEWOULDBLOCK) {
        ++socketDiagnostics[socket_];
        log("udp recv error socket= port= error=");
    }
    if (lastError_ == WSAEWOULDBLOCK || lastError_ == WSAECONNRESET) {
        lastError_ = 0;
        return NetPacketResult::Empty;      // 正常：没有包
    }
    return NetPacketResult::Error;          // 真错误
}
```

### 5.1 两个"不是错误"的错误码

- `WSAEWOULDBLOCK`：非阻塞套接字暂时没有数据 —— **正常**；
- `WSAECONNRESET`：UDP 上收到 ICMP port unreachable —— **正常**（对端没监听）。

两者都归零并返回 `Empty`。

### 5.2 日志封顶 8 条，且排除 `WSAEWOULDBLOCK`

```cpp
if (diagnostic < 8 && lastError_ != WSAEWOULDBLOCK)
```

**非阻塞空轮询不记日志**——否则每秒几十条。这是"热路径里不能有日志"的一条变体：**日志本身要有节流条件**。

`socketDiagnostics` 是文件级的 `unordered_map<uintptr_t, uint32_t>`，按 socket 句柄计数。

### 5.3 地址转换

```cpp
peer = { .ipv4 = ntohl(source.sin_addr.s_addr), .port = ntohs(source.sin_port) };
```

**两处都转主机序**，所以 `PeerAddress::ipv4` 是主机序的 32 位值。这解释了为什么 `(ipv4<<16)|port` 这种键能直接用。

## 六、`NET_SendPacket` 的部分发送检查

```cpp
const auto sent = sendto(...);
if (sent == SOCKET_ERROR) { lastError_ = WSAGetLastError(); return false; }
lastError_ = 0;
return (std::size_t)sent == packet.size();
```

**UDP 的 `sendto` 要么全发要么报错**，所以 `sent != size` 理论上不会发生——但**返回值检查仍在**，这是防御性但不冗余的（Windows 上 `sendto` 对超大数据报 `WSAEMSGSIZE` 而非部分发送）。

`destination.sin_addr.s_addr = htonl(peer.ipv4)` —— 与读取时的 `ntohl` 对称。

## 七、`open()` 是 const 的

```cpp
bool open() const { return socket_ != InvalidSocket; }
```

而 `NET_IPSocket` 与 `close` 是非 const 的。这意味着**三个查询方法（`open`/`port`/`lastError`）都可在 const 上下文调用**。

`InvalidSocket = (uintptr_t)INVALID_SOCKET` —— 因为 `INVALID_SOCKET` 是 `SOCKET`（即 `UINT_PTR`）类型，用 `uintptr_t` 存储而不是 `SOCKET`，让头文件不必包含 Winsock 头。

## 八、关键结论

1. **`E8 rel32` 必须重算 delta，绝对 `mov [imm32]` 可以直接复制** —— 判定标准是"位置相关"。
2. **跳转后的剩余字节要 NOP**，否则执行落到那里会解码半条指令。
3. **无法被规避的手段（硬件断点）要最后装**，避免被安装过程自身的写触发。
4. **每一段安装都要有具名的成功与失败日志**，而不是静默跳过。
5. **`WSAEWOULDBLOCK` 与 `WSAECONNRESET` 不是错误**，且前者不该进日志。
6. **`sockaddr` 双向都做字节序转换**，让 `PeerAddress` 的语义明确。

## 九、未闭合点

- `cls.state` 10 → 0 的成因仍未点名。
- 518 行之后的断点武装尾段与结果日志未读取。
