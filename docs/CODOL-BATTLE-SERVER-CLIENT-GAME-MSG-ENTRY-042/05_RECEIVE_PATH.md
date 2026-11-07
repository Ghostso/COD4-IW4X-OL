# 05_RECEIVE_PATH — 接收路径(socket → recv → message buffer)与 BLOCKED 边界

**镜像:** `image_best.bin`(sha `17ce…f045`),覆盖 `.text 0x1000..0x8a8000` 与 `.rdata/.data 0x8a8000..0xa65000`。

---

## 1. 已确认的读取原语(接收侧下游)

| 步骤 | RVA | 指令/证据 | 等级 |
|---|---|---|---|
| read 调用 | `0x85E71A` | `call 0x87BA50`(thunk → `0x87BE00`) | CONFIRMED_DIRECT |
| read 返回长度 | `0x85E71F..0x85E724` | `add esp,0x10; test eax; jg`(正字节数) | CONFIRMED_DIRECT |
| 消息类型读 | `0x85E75A` | `movzx eax, word [esp+6]` | CONFIRMED_DIRECT |
| 类型分派 | `0x85E75F..0x85E767` | `sub eax,2; je …; sub eax,2; jne …` | CONFIRMED_DIRECT |
| 处理 #1 | `0x85E7B0` | `push ebx; lea edx,[esp+4]; call 0x85E4F0` | CONFIRMED_DIRECT |
| 处理 #2 | `0x85E769` | `push edi; push esi; call 0x85E5C0` | CONFIRMED_DIRECT |

> **归属:** 该分派器与其对象(`0x85D2E0` 构造,字段 `QOSCSPkg*`/`QOSSSPkg*`,`udp://%s:%d`,`tqos_*`)
> 属 **TQOS = Tencent QoS 平台层**,**不是**游戏 netchan。此处**仍证明**:客户端在 `.text` 内确有
> "读包 → 取消息类型字 → 分派 → 处理"的完整形状。

---

## 2. 读包原语 `0x87BE00`

```
0087be00  sub  esp, 0x110
...
0087be76  push ecx
0087be77  push 0
0087be79  push 0
0087be7b  lea  eax, [esp+0x20]         ; timeout/overlapped 输出
0087be7f  push eax
0087be80  lea  ecx, [esi+1]            ; socket/handle + 1
0087be83  push ecx
0087be84  call dword ptr [0xCA84E8]    ; 读 API(槽名未在镜像内)
0087be8a  test eax, eax
0087be8c  jns  0xC7BEB5
...
0087bec3  call dword ptr [0xCA84E4]    ; 另一路径
```

**限制:** `0xCA84E8`/`0xCA84E4`/`0xCA853C` 是 IAT 槽,**其值位于镜像未提供的高地址节区** →
无法解析为具体 API 名 → 本边的"recv/socket"具体身份 **BLOCKED**(见 07)。

---

## 3. BLOCKED 边界(精确)

| 项 | 缺失 | 后果 |
|---|---|---|
| `.tp3 #3` `VA 0x00A16000`(VSize `0x0DBB1CC0`) | 镜像仅前 `0x62000` 字节 | 运行期全局(`0x76xxxxxx`/`0xE4xxxxxx`)不可解析 |
| `.tp3 #4/#5` `VA 0x0E5C8000/0x0E5C9000` | 镜像仅部分 | IAT(recv/WSARecv)槽值不可解析 |
| socket/recv 代码 | 可能位于上述节区 | "recv → netchan 缓冲"边未闭环 |

**结论:** 接收点(recv/WSARecv)**本轮 BLOCKED**;不得以 TQOS 读包原语冒充游戏业务接收点。

---

## 4. 解除条件(最小充分)

1. 覆盖 `VA 0x0E5C9000`+ 与 `0x76xxxxxx` 的**完整运行期内存镜像**(只读),用于:
   - 解析 `0xCA84E8/0xCA84E4/0xCA853C` 的 API 名;
   - 定位调用 `0x87C110/0x87D5A0` 的**非 TQOS** 调用者;
   - 沿 `net_start/net_end` 回追缓冲分配点。
2. 或:在单独授权下做**只读**运行时 API 追踪(不注入/hook)。
