# 229 · ★★★★★ 架构级定案：booking 应答走 **HTTPS**，不走大厅 3074

> 卷次：229（房间类 · **本轮最关键结论**）
> 方法：从 `[0x82E13FC]+0x13C` 找到 `0x632680` 的**第二个调用点** `0x7F156F` → 反汇编调用者 `0x7F1110`
> 结论：**`0x7F1110` 是 HTTPS 应答处理器**，booking 应答来自 HTTPS，不是 3074 的 `6/14`。

---

## §0 第二调用点 `0x7F1110`

```asm
; ---- 0x7F1110 入口 ----
0x7F1110  push ebp / mov ebp,esp
0x7F1113  mov ecx, [0x84ABB08]        ; ★ HTTPS 客户端全局 #1
0x7F1119  test ecx,ecx / jne 0x7F1127
0x7F111D  mov ecx, [0x84ABB14]        ; ★ HTTPS 客户端全局 #2（151/152 卷：TLS 客户端）
0x7F1123  test ecx,ecx / je  0x7F115B
0x7F1127  push esi / call 0xB9A0F0
0x7F112D  mov ecx, [eax+0x20]
0x7F1130  mov edx, [ebp+0x10]
0x7F1133  mov eax, [eax+0x24]
0x7F1137  cmp [edx+8], ecx / jne 0x7F115B     ; 校验
0x7F113C  cmp [edx+0xC], eax / jne 0x7F115B
...
; ---- 关键段 ----
0x7F153C  push 6
0x7F153E  push ebx
0x7F153F  push 0xDC6724               ; ★★★ "mmbook"
0x7F1544  call 0xC3C678               ; strcmp
0x7F154C  test eax,eax / jne 0x7F1576 ; 不等于 "mmbook" -> 跳过
0x7F1554  mov ecx, [0x82E13FC]        ; ★ dwRoomImp 单例
0x7F155A  mov eax, [ecx]
0x7F155C  mov eax, [eax + 0x13C]      ; ★★★ 取 0x632680
0x7F1562  push edx                    ; 参5
0x7F1563  push ebx                    ; 参4
0x7F1564  mov edx, edi
0x7F1566  push edx                    ; ★ 参3 = edi（HTTPS 应答解析出的字符串）
0x7F1567  mov edx, [ebp+0xC]
0x7F156A  push edx                    ; 参2 = 入参2（u64 高）
0x7F156B  mov edx, [ebp+8]
0x7F156E  push edx                    ; 参1 = 入参1（u64 低）
0x7F156F  call eax                    ; ★★★ 调用 0x632680
```

### 0.1 `edi` 是什么

```asm
0x7F11D5  lea ecx, [esp+0x14]
0x7F11DA  lea edx, [esp+0xB4]
0x7F11E1  mov ebx, 0x800
0x7F11ED  call 0xB76AF0                ; ★ 读 blob（tag 0x13）
0x7F1216  mov ecx, edi
0x7F121C  call 0xB76AF0
0x7F1230  mov byte [esp+eax+0xB0], 0   ; 补 \0
0x7F1240  lea edi, [esp+0x30]          ; ★★★ edi = 栈上解析出的字符串
```

⇒ **参3 = HTTPS 应答里解析出的字符串**。

### 0.2 `0x7F1110` 的注册点：`0xDE07C4`（处理器表）

```
0xDE07B4: 0x007F1040
0xDE07B8: 0x00B965F0
0xDE07BC: 0x007F1060   ← 139 卷「房间信道收包入口」
0xDE07C0: 0x007F10C0
0xDE07C4: 0x007F1110   ← ★ 本卷主角
0xDE07C8: 0x007F1160
0xDE07CC: 0x007F20C0
0xDE07D0: 0x007F19E0
```

★★ **`0xDE07xx` 是一张函数指针表**（条目全是 `0x7F0xxx`/`0x7F1xxx`），
且**含 139 卷的房间信道入口 `0x7F1060`** ⇒ 这是**"房间/认证层处理器表"**。

★ 而 `0x7F1110` 的**入口明确读 `[0x84ABB08]`/`[0x84ABB14]`**（HTTPS/TLS 客户端全局）
⇒ 它处理的是**与 HTTPS 客户端相关的**消息；配合 `strcmp "mmbook"` ⇒ **HTTPS 返回的 booking 应答**。

---

## §1 字符串常量

| 地址 | 内容 |
|---|---|
| **`0xDC6724`** | **`"mmbook"`**（6 字符，strcmp 用） |
| `0xDC6714` | `"EQUEST Accepted"`（附近，属另一个字符串） |
| `0xDC6734` | `" %d"` |

★★ **`0x7F1110` 处理的是"HTTPS 应答里含 `mmbook`"的场景。**

---

## §2 `[0x84ABB08]` / `[0x84ABB14]` 是什么

★★★ **151/152 卷已定名**：`[0x84ABB14]` = **HTTPS/TLS 客户端**，
目标域名 **`formal-zone-auth.codol.qq.com`**（腾讯认证服务器），证书 `cacert.pem`。

★ 而 147 卷曾把"连接建立链"的参数来源误判为游戏服 —— **151/152 卷已更正为腾讯认证服务器**。

⇒ **`0x7F1110` = 腾讯认证服务器 HTTPS 应答的处理器。**

---

## §3 ★★★ 完整开局链（最终版）

```
① 客户端 HTTPS 请求 booking
       → [0x84ABB14] TLS 客户端 → formal-zone-auth.codol.qq.com（腾讯）
② 服务端 HTTPS 应答
       → 含 u64 ID + 字符串
③ 0x7F1110 解析应答（0xB76AF0 读 blob）
       → strcmp(应答串, "mmbook") 匹配
④ call [dwRoomImp vt+0x13C] = 0x632680
       参1/参2 = u64（须 == [dwRoomImp+0x3A048/4C]）  ← 门4/5
       参3     = 应答串（须 == "mmbook accepted"）      ← 门6
⑤ 全过 → 构造 StartGame → 0x62ABF0 发送
```

### 3.1 三条关键推论

| # | 推论 |
|---|---|
| **A** | **booking 应答走 HTTPS，不走大厅 3074 的 `6/14`** ⇒ **改 `lobby_server.py` 的 `6/14 mmbook` 分支无效** |
| **B** | **216 卷的"服务端必须提供 u64"在 HTTPS 路径上成立**（门4/5 比较的是调用者入参，不是自己字段） |
| **C** | **HTTPS 对端是腾讯 `formal-zone-auth.codol.qq.com`** ⇒ **本地服务端无法提供**（除非劫持 HTTPS/DNS） |

★★★ **这解释了为什么"房间开局一直失败"：本地大厅服在 3074 上做的任何 `mmbook` 应答都到不了这条链。**

---

## §4 与 227 卷的关系

| 调用点 | 路径 | 参3 | 结果 |
|---|---|---|---|
| `0x632FC4`（FrameUpdate） | 超时检查 | `"mmbook timedout"` | 恒走超时分支 |
| **`0x7F156F`（HTTPS 应答）** | **booking 成功** | **应答串** | **可过关** |

★ **两个调用点分工明确**：一个查超时，一个处理成功应答。

⇒ 227 卷的"`0x632680` 是超时检测"**需要更正**：它是**通用的 booking 状态处理函数**，
两个调用点分别对应"超时"和"成功应答"。

---

## §5 本卷确定结论

| 项 | 状态 |
|---|---|
| `0x632680` 第二调用点 = `0x7F156F` | ✅ |
| `0x7F1110` = HTTPS 应答处理器 | ✅（入口读 `[0x84ABB08]`/`[0x84ABB14]`） |
| `0xDC6724` = `"mmbook"` | ✅ |
| 参3 = HTTPS 应答解析出的字符串 | ✅ |
| **booking 走 HTTPS，不走 3074** | ✅ **本卷定案** |
| HTTPS 对端 = 腾讯认证服务器 | ✅ 151/152 卷 |
| ⇒ 本地服务端无法提供 booking 应答 | ✅ |
| 227 卷"超时检测"定性 | ⚠️ **需更正为"通用 booking 状态处理"** |

---

## §6 对服务端修复的最终影响

★★★ **三条路线**：
1. **劫持 HTTPS**（DNS/hosts + 自签证书让客户端信任）→ 才能控制 booking 应答
2. **找另一条不走 HTTPS 的开局路径**（如 Flash 直接触发）
3. **接受"房间开局需要腾讯服务器"** —— 本地无法复现

★ **不建议**再改 3074 的服务端代码。

---

## §7 方法论

1. **★★★★★ 一个虚函数可能有多个调用点，每个调用点的参数来源不同。** 只看一个会得出片面结论（227 卷）。
2. **★★★★ 从"高频全局单例 `[0x82E13FC]` + slot"能枚举全部调用点**（228 卷的 302 处派上用场）。
3. **★★★★ 调用者的入口读哪个全局，决定了这条路径的"上游"是什么。** `0x7F1110` 读 HTTPS 全局 ⇒ 它是 HTTPS 应答处理。
4. **★★★ 「服务端必须提供 X」的结论，必须指明**哪条通道** —— 3074 和 HTTPS 是两个完全不同的服务端。**