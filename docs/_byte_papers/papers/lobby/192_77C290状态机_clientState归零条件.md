# 192 · `0x77C290` 状态机定案：`clientState` 归零逻辑 = **离开 lobby 时的清理**

> 卷次：192（房间类 · P4 完成）
> 结论：`0x77C290` 是**离开大厅/断连**的清理函数，`clientState` 归零只是其中一步。

---

## §0 完整逻辑

```asm
0x77C290  mov eax, [0x7644694]           ; 某索引
0x77C29D  mov dword [0x849B5B0], 1       ; 置标志
0x77C2A7  test eax,eax / je
0x77C2AB  imul eax, eax, 0x114           ; ★ 步进 0x114 的数组
0x77C2B1  mov eax, [eax + 0x7659F88]     ; 取元素
0x77C2B7  mov edx, [eax]
0x77C2BB  mov eax, [edx + 0x24]          ; vtable[0x24]
0x77C2BE  call eax                        ; 虚调用

0x77C2C0  mov ecx, [0x8269774]           ; ★ srpc 单例
0x77C2C6  test ecx,ecx / je
0x77C2CA  push 0 / call 0xB7A400          ; srpc 重置

0x77C2D1  call 0x7FA4C0                   ; 另一处清理

0x77C2D6  mov edi, [ebp+0xC]              ; 参数2
0x77C2D9  mov esi, [ebp+8]                ; 参数1
0x77C2E5  call 0x774980                   ; 格式化
0x77C2F5  call 0x5BF300                   ; 日志/上报

0x77C2FA  mov eax, [0x76446B0]            ; ★★ clientState
0x77C302  cmp dword [0x331C0C8], 0        ; ★ 全局开关
0x77C309  jne 0x77C313                    ; 非 0 → 跳过范围检查
0x77C30B  lea ecx, [eax - 3]
0x77C30E  cmp ecx, 3
0x77C311  ja  0x77C34D                    ; ★ clientState ∉ [3,6] → 不归零！
0x77C313  cmp eax, 5
0x77C316  jne 0x77C343                    ; ≠5 → 归零
0x77C318  call 0x7F9090                   ; ==5 → 特殊处理
...
0x77C343  mov dword [0x76446B0], 0        ; ★★★ 归零
0x77C34D  ...
```

---

## §1 语义表

| `[0x331C0C8]` | `clientState` | 结果 |
|---|---|---|
| ≠ 0 | 任意 | 走 `0x77C313`：`==5` 特殊处理，否则**归零** |
| == 0 | ∉ [3,6] | **不归零**（`ja 0x77C34D` 跳过） |
| == 0 | ∈ [3,6] 且 ≠5 | **归零** |
| == 0 | ==5 | 特殊处理（`0x7F9090` → 写 `[eax+0x1112C]=1` / `[eax+0x20]=edx`），**不归零** |

★★ **关键：`clientState ∈ [3,6]` 时才归零；`<3` 或 `>6` 都不动。**

### 1.1 这与 138 卷「开局闸门 <3 拒绝」吻合

`clientState < 3` ⇒ 未进入房间 ⇒ `0x77C290` 不归零（因为本来就没进）。
`clientState >= 3` ⇒ 在房间里 ⇒ 清理时归零。

---

## §2 `0x77C290` 的身份

调用链证据：
```asm
0x77C2C0  mov ecx, [0x8269774]     ; srpc 单例
0x77C2CA  push 0 / call 0xB7A400    ; srpc::reset(0)
0x77C2D1  call 0x7FA4C0             ; 清理
0x77C2F5  call 0x5BF300             ; 日志
```

⇒ **这是"退出/重连"清理函数**：重置 srpc、清标志、上报、把 clientState 归零。

★ 与 173 卷的 `srpc+0x4F4`（HMAC 会话）呼应：`0xB7A400` 很可能是会话清理。

---

## §3 对房间类黑箱的意义

### 3.1 三道门现在全部有实体

| 门 | 位置 | 值 |
|---|---|---|
| HMAC 会话 | `srpc+0x4F4` | 非空且 `0xBA0780()==2` |
| **clientState** | `[0x76446B0]` | **≥3 才进房间；[3,6] 才会被清理归零** |
| 强制标志 | `srpc+0x4F8` | 非 0 时绕过 `==2` 检查 |

★★ **服务端能做的只有"回正确的字节"，这三道门全在客户端。**

### 3.2 `StartGame` vs `StartGameFailed` 的正确理解（修正 190 卷）

190 卷说 `clientState==0` → 构造 StartGame（解析后丢弃）。现在看：

`0x634AE0 cmp [0x76446B0],0 / jne 0x634C29`
- `==0` → 构造 `StartGame`（`0xDC751C`）→ **解析（可能只是消费位流）**
- `!=0` → 构造 `StartGameFailed`（`0xDC7528`）

★★★ **修正理解**：`clientState==0` 表示"还没进过大厅"，
此时收到 StartGame 就**解析进临时对象**（不保留）；
`clientState!=0` 表示"在大厅里"，收到 StartGame 但**条件不满足** → 回 Failed。

★ 但 `0x634C29` 前面还有别的条件（`0x634AC2 cmp byte[0xE36DDA0],0 / jne`、`0x634AD1 call [eax+0x60]`），
所以 `!=0` 分支未必一律 Failed。

---

## §4 本卷确定结论

| 项 | 状态 |
|---|---|
| `0x77C290` = 退出/重连清理 | ✅ |
| `clientState` 归零条件 = `[0x331C0C8]!=0` 或 `∈[3,6]` 且 ≠5 | ✅ |
| `clientState == 5` 走特殊分支（不归零） | ✅ |
| `srpc` 在清理里被 reset | ✅ `0xB7A400` |
| `0x7644694` 步进 `0x114` 的数组 | ⬜ 未定名 |

---

## §5 下一步

1. **`0x331C0C8`** 是什么开关（决定"是否做范围检查"）
2. **`0x7F9090` 的返回值**（`clientState==5` 时的特殊对象）
3. 回到 **P1**：`+0x18` 的真实归属

---

## §6 方法论

1. **★★★ 全局状态变量的"归零点"必须连带看它的前置条件。** `cmp [0x331C0C8],0` + `lea ecx,[eax-3]/cmp ecx,3/ja` 两道门决定了"什么情况下才归零"。
2. **★★ `lea ecx,[eax-3] / cmp ecx,3 / ja` 是"区间 [3,6] 检查"的典型写法。** 等价于 `eax < 3 || eax > 6`。
3. **★★ 清理函数里出现 `srpc reset` ⇒ 它是"断连/退出"路径。**
4. **★★★ 190 卷的"StartGame vs Failed"理解需要修正**：`clientState==0` 不是"未连接"，是"还没进过大堂"。
