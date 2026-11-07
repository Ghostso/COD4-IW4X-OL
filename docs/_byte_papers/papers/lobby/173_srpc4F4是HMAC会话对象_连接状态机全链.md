# 173 · `srpc+0x4F4` 定案：不是"闸门标志"，是 **HMAC 会话对象指针**；连接状态机全链闭合

> 卷次：173（房间类 · 172 卷结论的更正与上溯）
> 方法：对 172 卷的"闸门"逐条反解写入值，不满足于"有这个 mov"
> 结论：**172 卷「`srpc+0x4F4` 是状态标志」是错的。它是对象指针，指向 `bdHmacSession`。**

---

## §0 结论

1. **`srpc+0x4F4` 是对象指针，不是布尔标志。** 7 个写点里 6 个写 0（构造/析构），唯一的非零写点是 `0xB81FFD`：`mov [++0x4F4], esi`，而 `esi = call 0xBA2800(...)` 的返回值。`0xBA2800` 的 vtable = `0xD5A4F4`，其相邻字符串是 **`CLIENTCHAL` / `HMAC` / `Hmac mismatch` / `Hmac calculation`** ⇒ 这是 **HMAC 会话对象**。

2. **所以 `0xB7A670` 的语义是"已建立 HMAC 会话？"**，不是"某个状态位开着"。
   ```asm
   0xB7A670  mov ecx,[esi+0x4F4]      ; ecx = HMAC 会话对象
   0xB7A679  test ecx,ecx / jne ok
   0xB7A67D  xor eax,eax / ret        ; 没建会话 → 返回 0
   ok:       call 0xBA0780            ; 查 [ecx+0x644] / [ecx+0xc8]
   0xB7A686  cmp byte [esi+0x4F8],0   ; 0x4F8 = 强制标志
   0xB7A68F  cmp eax,2                ; sub 状态==2（已认证）
   0xB7A694  mov eax,1
   ```

3. **因此房间消息发不出去 = 客户端还没完成 srpc 的 HMAC 会话建立**，不是"服务端缺分支"，也不是"某个 flag 没置"。

---

## §1 逐条反解 7 个写点（这是 172 卷缺的那一步）

对每条 `mov [X+0x4F4], reg`，在同函数内向前找该 reg 的最近赋值：

| 地址 | 所在函数 | 写入值 | 性质 |
|---|---|---|---|
| `0x847155` | `0x847100` | `ebx`=0（`xor ebx,ebx`） | 清理 |
| `0x8B3F89` | `0x8B3ED0` | `edx`=0（`xor edx,edx`） | ctor 初始化 |
| `0xB81EA3` | `0xB815E0` | `ebx`=0 | 析构 |
| **`0xB81FFD`** | **`0xB81EF0`** | **`esi` = `call 0xBA2800` 的返回值** | ★ 唯一的非零写点 |
| `0xB82404` | `0xB82130` | `ebx`=0（`xor ebx,ebx`） | srpc ctor |
| `0xBA92C6` | `0xBA9210` | `edi`=0（`0xBA923C xor edi,edi`） | ctor |
| `0xBA9339` | `0xBA9310` | `eax`=0（`0xBA9312 xor eax,eax`） | ctor |

★ **172 卷说「16 个候选写点，无一可静态归属」是错的。** 实际只有 7 个写点，其中 6 个是清零，1 个是对象赋值。

### 1.1 `0xB81EF0` 的完整语义（152 字节参数的"建立会话"函数）

```asm
0xB81F18  mov eax,[ebp+0x94]          ; 参数
0xB81F26  mov ecx,[ebp+0x98]
0xB81F35  mov esi,[ebp+0x90]          ; ★ 输入数据指针
0xB81F42  test esi,esi / jne          ; 空 → call 0x8435D0（空桩）→ 失败
0xB81F52  mov ecx,[ebx+0x4F4]         ; 已有旧会话？
0xB81F58  test / je                   ; 有 → call 0xBA41B0 + 0xB815E0（释放旧的）
0xB81F6B  mov [ebx+0x5B0], al         ; 存标志
0xB81F71  lea edi,[ebx+0x500]
0xB81F77  mov ecx,0x2C
0xB81F81  rep movsd                   ; ★ 拷贝 0x2C*4 = 176 字节参数到 +0x500
0xB81F7C  push 0xAE8 / call 0xB74220  ; alloc(0xAE8) = 2792 字节
0xB81F88  mov esi,eax
0xB81FBD  call 0xB75340               ; 构造临时
0xB81FC4  mov ecx,esi / call 0xBA2800 ; ★★★ 构造 HMAC 会话对象
0xB81FC9  mov esi,eax
0xB81FDD..0xB81FFB                    ; 若旧会话在，Release
0xB81FFD  mov [ebx+0x4F4], esi        ; ★★★ 存进 srpc+0x4F4
0xB8201E  mov byte [ebx+0x4F8], 0     ; ★ 强制标志清零
0xB82025  call 0xBA4080               ; 用 +0x500 的 176 字节参数初始化会话
0xB8202F  call 0xB7F7F0               ; 后续
0xB82041  call 0xBA0DE0
```

★★ **这就是"登录/建立会话"函数**：拷 176 字节参数 → 分配 2792 字节 → 构造 HMAC 会话 → 存进 `srpc+0x4F4` → 用参数初始化。

---

## §2 `srpc+0x4F4` 指向的类是 HMAC 会话

`0xBA2800` 的 vtable `0xD5A4F4`，紧邻的 `.rdata` 内容是：

```
0xD5A4E4: 0x00004154   "TA\0\0"
0xD5A4E8: 0x45494C43   "CLIE"
0xD5A4EC: 0x4843544E   "NTCH"
0xD5A4F0: 0x00004C41   "AL\0\0"     -> "CLIENTCHAL"
0xD5A4F4: 0x00BA2A30   vtable[0]
0xD5A4F8: 0x00BA3370   vtable[1]
0xD5A4FC: 0x43414D48   "HMAC"
0xD5A500: 0x73696D20   " mis"
0xD5A504: 0x6374616D   "matc"
0xD5A508: 0x00000068   "h\0"
0xD5A50C: 0x43414D48   "HMAC"
0xD5A510: 0x6C616320   " cal"
0xD5A514: 0x616C7563   "cula"
0xD5A518: 0x6E6F6974   "tion"
```

★★★ **`CLIENTCHAL`（= 163 卷记的客户端 KDF 标签！）+ `HMAC` + `Hmac mismatch` + `Hmac calculation`。**
⇒ `srpc+0x4F4` = **绑定 `CLIENTCHAL` 的 HMAC 会话对象**。

这与 163 卷「客户端用 `KDF(shared,"CLIENTCHAL")`→16B」是**同一个东西的两端**：会话对象持有 KDF 标签与密钥。

---

## §3 完整上游链：从大厅状态机到会话建立

```
0x7F26C0  ★ 大厅状态机（[0x84ABA50]==5 分支）
   0x7F276A  call 0x7F3800
      ├─ [0x84ABA7C]==0 → 0x7F386B → call 0x7F3890
      │    0x7F38A4  call 0x803830          ; 取 srpc 单例（惰性构造）
      │    0x7F38CB/E1/E7                   ; 读 [0x84ABB08] / [0x84ABB0C] / [0x84ABB14]
      │                                        （151 卷：HTTPS 客户端族）
      │    0x7F3912  call 0xB82070
      │        0xB820C5  mov byte [esi+0x4E8],1     ; 置"登录中"
      │        0xB820D3  call 0xB81EF0             ; ★ 建立会话
      │    0x7F391E  mov [0x84ABA7C], 1             ; ★ 状态 -> 1
      └─ [0x84ABA7C]==1 → 0x7F380E  call 0x803830
                      0x7F3819  lock 0x81A5570
                      0x7F3826  call 0xB838A0   ; 139 卷的投递链入口
                      0x7F3830  unlock
                      0x7F3838  call 0xB7A670   ; ★ 查会话状态
                      0x7F383D  cmp eax,4 / ja
                      0x7F3842  jmp [eax*4 + 0x7F3878]   ; ★ 5 槽跳表
                        case 0: [0x84ABA7C] = 0   ; 失败 → 重来
                        case 1: [0x84ABA7C] = 2   ; ★ 成功 → 2
```

★★ **`0x7F26C0` 与记忆条目 `codol-lobby-boot-chain-12-layers` 完全吻合**：
`[0xe59d20]`→`[0x8269774]`→`+0x4F8`→`0xb7a670()==2`→`[0x84aba50]==5`。
本卷把这链里的 `0xb7a670()==2` 落到了具体对象：**HMAC 会话已认证**。

---

## §4 对 172 卷的更正汇总

| 172 卷说法 | 本卷正确说法 |
|---|---|
| 「`srpc+0x4F4` 是状态闸门/标志」 | **是 HMAC 会话对象指针** |
| 「`0xB7A670` 返回 1 当 `+0x4F4 != 0`」 | 对，但 `!= 0` 的含义是**会话对象存在**；`sub()==2` 是**已认证** |
| 「`[obj+0x21]` 16 个候选写点无一可归属」 | **只有 7 个写点：6 个清零 + 1 个对象赋值** |
| 「闸门推断未经实测」 | 逻辑链已闭合到对象级；剩"实际运行时是否走到"仍属实测 |

★ **`[obj+0x21]` 仍未解** —— 那是**位流写器**（vtable `0xD59838`）的字段，与 `srpc+0x4F4` 无关。
`0xD59838` 的 ctor 是 `0xB77B30`，其中 `mov [esi],0xD59838`，但**未初始化 `+0x21`**；`0xBC18B0` 基类 ctor 只写 vtable `0xD5B094`。
⇒ `+0x21` 由谁初始化**仍未定位**（16 个候选写点全部不在 `0xB77B30`/`0xBC18B0` 的调用链上）。

---

## §5 本卷新增的确定事实

| 项 | 值 |
|---|---|
| `0xBA2800` | HMAC 会话 ctor（vtable `0xD5A4F4`，2792 字节对象） |
| `srpc+0x4F4` | 该对象指针（唯一非零写点 `0xB81FFD`） |
| `srpc+0x4F8` | 强制放行标志（`0xB81FFD` 后清零；`0xB7A670` 判它） |
| `0xBA0780` | 会话子状态查询（`[+0x644]` / `[+0xC8]`，返回 2 = 已认证） |
| `0xB81EF0` | 建立会话（拷 176B 参数 → alloc 2792B → ctor → 初始化） |
| `0xB82070` | 登录包装（置 `srpc+0x4E8`=1 → `0xB81EF0`） |
| `0x7F3890` | 会话建立入口（取单例 + 读 HTTPS 客户端三个全局） |
| `0x7F3800` | 连接状态机（`[0x84ABA7C]` 0→1→2，5 槽跳表 `0x7F3878`） |
| `0x7F26C0` | 大厅状态机（`[0x84ABA50]` 分支，5 槽跳表 `0x7F2850`） |

---

## §6 诚实边界

1. **`[obj+0x21]`（位流写器的零位填充开关）仍未解。** 16 个候选写点没有一个落在 `0xD59838` 类的构造链上。这是**唯一还开的位流层项**。
2. **`0xBA0780` 的 `[+0x644]` / `[+0xC8]` 语义未展开**（只知返回 2 = 已认证）。
3. **`0x84ABB08/0C/14` 三个全局**：151 卷定过一个（`0x84ABB14` = HTTPS 客户端）。另两个在本卷只看到被读，未定名。
4. **"实机是否真的走完 0→1→2"未实测。**

---

## §7 方法论

1. **★★ 「有这个 mov」≠「这个 mov 写的是非零」。** 必须反解写入值。7 个写点全被 172 卷当成"未知"，实际 6 个是清零。
2. **★★★ 对象指针 vs 布尔标志的判据：看唯一非零写点的来源。** 若来自 `call <ctor>`，就是对象。
3. **★★ 类的身份靠 vtable 邻近字符串。** `0xD5A4F4` 的邻居直接给出 `CLIENTCHAL` + `HMAC`，比追 RTTI 快。
4. **★★ 状态机跳表 `jmp [eax*4 + 表]` 的 case 赋值就是状态迁移全图。** `0x7F3878` 五个 case 一眼看完。
