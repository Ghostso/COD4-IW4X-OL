# CODOL 连接/握手链逆向报告（逆向子代理 C2）

日期：2026-09-26
镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`（10,899,456 B）
加载基址：`0x400000`，`file_offset = VA - 0x400000`

约束遵守：全程只读静态反汇编。**未运行游戏**，未改内存/注册表/文件，未使用 `netsh`/路由/DNS/防火墙/网卡命令，
未使用 `sc` 命令，未删除文件，未下载安装，未执行 `taskkill /IM python.exe`。
**关键前提**：磁盘 exe 的 `.tp3` 段是密文，本报告**全部代码证据来自运行期解密镜像**。

证据分级：`[反汇编]` = 本轮从镜像直接反汇编；`[实测]` = 本轮只读命令输出；`[既有]` = 仓库旧产物（未由本轮复核）；`[推断]` = 外推。

---

## 0. 结论速览（先看这一段）

**这条链其实不是自定义二进制帧，而是 `libcurl` 的 HTTPS 请求。**

`0xB88CC0` 只是"配置暂存 + 建流对象"，真正的网络动作全部在 `0xB9A9E0`：
它把一个 JSON 请求体 `POST` 到

```
https://<host>:<port>/auth/
```

其中 `<host>` 来自全局 `0x81A76A8`，`<port>` 来自全局 `0x81A9EC4`（16 位）。
模板字符串就在镜像里：`0xD5A2CC = "https://%s:%d/auth/"`。

**成功判据（[反汇编]，VA 级）**：HTTP 状态码必须落在 `200..299`。
证据在 `0xC752E3`：

```asm
00C752E3  81 fa c8 00 00 00    cmp edx, 0xC8          ; 200
00C752E9  7c 35                jl  0xC75320            ; <200 -> 失败状态 6
00C752EB  81 fa 2c 01 00 00    cmp edx, 0x12C         ; 300
00C752F1  7d 2d                jge 0xC75320           ; >=300 -> 失败状态 6
00C752F3  ...                  ; 2xx -> 状态 5（成功）
```

也就是说：**服务端收到 `POST /auth/` 后，返回任意 `2xx` 且响应完整，这条链就能走通。**
响应体在这一环里**没有被解析**（见 §5）。

---

## 1. 前置事实核对（部分修正任务书）

| 任务书描述 | 本轮核对结果 | 证据 |
|---|---|---|
| `0xB88CC0` 是 `thiscall + ret 0x28`，10 个栈参数 | **成立** | `0xB88CDF…0xB88F5E`，末尾 `c2 28 00` |
| 配置块 `+0x98` 不是端口 | **成立**，是 `+0x18` 缓冲的长度字 | `0x7F2CC8 movzx edx,word [0x331c658]` |
| 真端口在 `0x81A9EC4` | **成立**（但**不经过** `0xB88CC0`，而是进 `0xB88B80`） | `0x7F2BAF movzx edi,word [0x81a9ec4]` → `0x7F2BDC push edi` |
| 失败点在 `0xB9A9E0` | **成立**，且已定位到具体分支 | 见 §4 |

新增事实（本轮首证）：

1. `0xB9A9E0` 构造的是 **HTTPS POST /auth/**，URL 模板 `0xD5A2CC`。
2. HTTP 客户端对象在 `0xB9A1A0` 构造时创建于 `objA+0x160`；它的 vtable 是 `0xD95600`。
3. HTTP 客户端槽位：`0xD95600 +0x04 = 0xC75F80` 设置 URL/方法、`+0x08 = 0xC76870` 加头部、`+0x0C = 0xC758A0` 加格式化头部、`+0x14 = 0xC76210` 设置 POST body/上传回调、`+0x1C = 0xC764C0` 设置接收缓冲、`+0x28 = 0xC75A50` 执行 cURL、`+0x2C = 0xBC1190` 读状态。
4. 状态判定 `[objA+0x160]` 的 `vtable+0x2C` 必须等于 **3**，而状态 3 只在 HTTP `2xx` 时写入（`0xC752F3`）。
5. 证书链是**强校验**的：`CURLOPT_SSL_VERIFYPEER=1`、`CURLOPT_SSL_VERIFYHOST=2`、`CURLOPT_CAINFO="cacert.pem"`。

---

## 2. 完整反汇编 `0xB88CC0`（连接构造，到 `ret 0x28`）

调用点（全镜像唯一调用者）：

```asm
007F2D1A  8b 0d 08 bb 4a 08        mov  ecx, dword ptr [0x84ABB08]   ; this = objA
007F2D20  68 d8 c5 31 03           push 0x331C5D8                    ; arg2  (+0x18)
007F2D25  68 5c c6 31 03           push 0x331C65C                    ; arg1  (+0x9C)
007F2D2A  e8 91 5f 39 00           call 0xB88CC0
007F2D2F  80 7d b3 00              cmp  byte ptr [ebp-0x4D], 0
007F2D33  8a d8                    mov  bl, al
007F2D35  74 45                    je   0x7F2D7C
007F2D37  84 db                    test bl, bl
007F2D39  74 45                    je   0x7F2D80                       ; al==0 -> 失败
007F2D80  bf 06 00 00 00           mov  edi, 6
007F2D8E  c7 05 60 ba 4a 08 00 00 00 00  mov dword ptr [0x84ABA60], 0   ; sub_state = 0
```

（`0x7F2D7A` 处 `mov bl, al` 是降级路径汇合；真实 objA 路径下 `[ebp-0x4D]` 即 `0xE3EC97C` 的缓存值。）

### 2.1 10 个栈参数（右到左压栈，`[ebp+8]` 起）

| 参数 | VA | 来源 | 用途（[反汇编]） |
|---|---|---|---|
| arg1 | `[ebp+8]` | `0x331C65C` (+0x9C) | 复制 16 字节 → `objA+0x3190/0x3194/0x3198/0x319C`（`0xB88D0E–0xB88D42`） |
| arg2 | `[ebp+0xC]` | `0x331C5D8` (+0x18) | 写入流对象的缓冲区（`0xB88F06–0xB88F14`） |
| arg3 | `[ebp+0x10]` | `0x331C658` (+0x98) | **长度字**，供 `0x4AA4A0` 与 `0xB75E00` 使用（`0xB88EA6`、`0xB88F0F`） |
| arg4 | `[ebp+0x14]` | `0x331C5C4` (+0x04) | 复制 16 字节 → `objA+0x35FC`（`0xB88D50–0xB88D69`） |
| arg5 | `[ebp+0x18]` | `0x331CAF8` (+0x538) | 存 `objA+0x364C`（`0xB88D47`） |
| arg6 | `[ebp+0x1C]` | `ebp-0x4C` 或 `0` | ASCII 校验；截断 0x3F → `objA+0x360C`（`0xB88CF1–0xB88DA5`） |
| arg7 | `[ebp+0x20]` | `0` | 存 `objA+0x3654`（`0xB88DDF–0xB88DE5`） |
| arg8 | `[ebp+0x24]` | `0x331C670` (+0xB0) | 截断 0x3FF → `objA+0x3658`（`0xB88DDF–0xB88E37`） |
| arg9 | `[ebp+0x28]` | `0` 或 `0xE3EC578` | 截断 0x3FF → `objA+0x3A58`（`0xB88E3F–0xB88E88`） |
| arg10 | `[ebp+0x2C]` | `0`/`0x80`（由 `0x849B501` 决定） | 单字节模式 → `objA+0x3650`（`0xB88E90`） |

### 2.2 主体流程

```asm
00B88CE5  8b f1                    mov  esi, ecx
00B88CE7  83 7e 20 00              cmp  dword ptr [esi+0x20], 0      ; ★ 出口 A
00B88CEB  0f 85 31 02 00 00        jne  0xB88F22
00B88CF1  8b 5d 1c                 mov  ebx, [ebp+0x1C]             ; arg6
00B88CF4  85 db                    test ebx, ebx
00B88CF6  74 16                    je   0xB88D0E
00B88D00  0f 88 a1 00 00 00        js   0xB88DA7                    ; ★ 非 ASCII -> 0x73
00B88D0E  8b 45 08                 mov  eax, [ebp+8]                ; arg1 -> +0x3190..+0x319C
00B88D33  8d be fc 35 00 00        lea  edi, [esi+0x35FC]
00B88D3C  e8 99 a0 0b 00           call 0xC42DE0                   ; memset(+0x35FC,0,0x85C)
00B88D47  8b 45 18                 mov  eax, [ebp+0x18]             ; arg5 -> +0x364C
00B88D50  8b 45 14                 mov  eax, [ebp+0x14]             ; arg4 -> +0x35FC (16B)
00B88E93  6a 1c                    push 0x1C
00B88E9B  e8 80 b3 fe ff           call 0xB74220                   ; alloc 0x1C
00B88EA6  66 8b 5d 10              mov  bx, word [ebp+0x10]         ; ★ arg3 长度字
00B88EB3  0f b7 d3                 movzx edx, bx
00B88EB6  57                       push edi                        ; 0
00B88EB7  52                       push edx                        ; len
00B88EB8  8b c8                    mov  ecx, eax
00B88EBA  e8 e1 15 92 ff           call 0x4AA4A0                   ; 建流对象
00B88EF2  89 be f4 35 00 00        mov  [esi+0x35F4], edi
00B88F06  8b 55 0c                 mov  edx, [ebp+0xC]             ; arg2 缓冲
00B88F09  8b 8e f4 35 00 00        mov  ecx, [esi+0x35F4]
00B88F0F  0f b7 c3                 movzx eax, bx
00B88F12  50                       push eax
00B88F13  52                       push edx
00B88F14  e8 e7 ce fe ff           call 0xB75E00                   ; ★ 写流
00B88F19  84 c0                    test al, al
00B88F1B  75 1b                    jne  0xB88F38
00B88F1D  e8 ae a6 cb ff           call 0x8435D0
00B88F22  32 c0                    xor  al, al                     ; ★ 出口 B -> 返回 0
00B88F35  c2 28 00                 ret  0x28
00B88F38  8b ce                    mov  ecx, esi
00B88F3A  66 89 9e f8 35 00 00     mov  word [esi+0x35F8], bx      ; 记录长度
00B88F41  c7 46 14 20 00 00 00     mov  dword [esi+0x14], 0x20     ; 状态=0x20
00B88F48  e8 93 1a 01 00           call 0xB9A9E0                    ; ★ 交给握手核心
00B88F5E  c2 28 00                 ret  0x28                       ; ★ 返回值 = al
```

### 2.3 `0xB88CC0` 返回 0 的**全部**静态条件

| # | 出口 VA | 判据 | 是否可能命中（本链） |
|---|---|---|---|
| 1 | `0xB88CEB` | `[objA+0x20] != 0`（对象已在连接中） | 可排除：`0xB9A2C0` 构造末尾置 0 |
| 2 | `0xB88F1D` | `0xB75E00` 返回 0 | 基本可排除：新流对象 `[obj+0xC]==0` 时直接返回 1 |
| 3 | `0xB88F5E` | `0xB9A9E0` 返回 0（`al=0`） | **当前实际命中点** |

`0xB75E00` 的"不会失败"证据：

```asm
00B75E07  8b 56 0c        mov  edx, [esi+0xC]     ; 容量成员
00B75E0A  32 db           xor  bl, bl
00B75E0C  85 d2           test edx, edx
00B75E0E  75 0e           jne  0xB75E1E
00B75E10  8b 45 0c        mov  eax, [ebp+0xC]     ; 本次长度
00B75E13  01 46 08        add  [esi+8], eax
00B75E16  5e              pop  esi
00B75E17  b0 01           mov  al, 1              ; ★ 直接成功
00B75E19  5b              pop  ebx
00B75E1A  5d              pop  ebp
00B75E1B  c2 08 00        ret  8
```

`0x4AA4A0` 构造时把 `[obj+0xC]` 置 0（`0x4AA4C3 mov [esi+0xC], ecx`，`ecx=0`）。

### 2.4 `0xB88CC0` 调用的子函数、作用与成败条件

| 子函数 VA | 在 `0xB88CC0` 中的调用点 | 作用 | 成败条件 |
|---|---|---|---|
| `0x8435D0` | `0xB88DA7`、`0xB88F1D` | 错误/日志钩子 | 返回值未检查，不影响 `al` |
| `0xC42DE0` | `0xB88D42`、`0xB88DD7`、`0xB88E37`、`0xB88E88` | `memset` 清缓冲 | 无失败返回检查 |
| `0xC427F0` | `0xB88D9C`、`0xB88E1E`、`0xB88E6F` | `memcpy` 拷贝字符串 | 无失败返回检查 |
| `0xB74220` | `0xB88E9B` | 分配 `0x1C` 字节流对象 | 返回 0 不设正常 bool；后续会以空对象继续，属于 OOM 异常路径 |
| `0x4AA4A0` | `0xB88EBA` | 构造流对象；`arg3` 传入容量参数 | 其返回值直接存入 `[objA+0x35F4]`，无显式失败标志 |
| `0xB75E00` | `0xB88F14` | 把 arg2 缓冲区写入流 | **返回 0 → `0xB88CC0` 返回 0**；新流对象容量 0 时返回 1 |
| `0xB9A9E0` | `0xB88F48` | TLS + HTTP 握手核心 | **其 `al` 原样成为 `0xB88CC0` 返回值** |

补充：`0xB75E00` 除零容量快路径外，唯一失败路径是 `len > [obj+0xC] - ([obj+8]-[obj+0x14])`，
也就是"流剩余容量不足"（`0xB75E28–0xB75E58`），随后 `bl=0` 返回。

---

## 3. 完整反汇编 `0xB88B80`（objA 构造器）

```asm
00B88B80  55                 push ebp
00B88B81  8b ec              mov  ebp, esp
00B88B83  8b 45 10           mov  eax, [ebp+0x10]      ; arg3
00B88B86  8b 55 08           mov  edx, [ebp+8]         ; arg1
00B88B89  53                 push ebx
00B88B8A  56                 push esi
00B88B8B  8b f1              mov  esi, ecx             ; this = 新对象
00B88B8D  8b 4d 0c           mov  ecx, [ebp+0xC]       ; arg2
00B88B90  50                 push eax                  ; arg3
00B88B91  51                 push ecx                  ; arg2
00B88B92  52                 push edx                  ; arg1
00B88B93  8b ce              mov  ecx, esi
00B88B95  e8 06 16 01 00     call 0xB9A1A0             ; 基类构造
00B88B9A  c7 06 7c 9a d5 00  mov  dword [esi], 0xD59A7C  ; ★ objA vtable
00B88BA4  89 9e b0 31 00 00  mov  [esi+0x31B0], ebx
00B88BAA  89 9e f4 35 00 00  mov  [esi+0x35F4], ebx      ; 流对象 = 0
00B88BB0  66 89 86 f8 35 00 00 mov word [esi+0x35F8], ax
00B88BB7  89 86 fc 35 00 00  mov  [esi+0x35FC], eax
00B88BBD  6a 40              push 0x40
00B88BC5  8d 8e 0c 36 00 00  lea  ecx, [esi+0x360C]
00B88BD9  e8 02 a2 0b 00     call 0xC42DE0             ; memset +0x360C,0,0x40
00B88BDE  68 00 04 00 00     push 0x400
00B88BE3  8d 96 58 36 00 00  lea  edx, [esi+0x3658]
00B88BFD  e8 de a1 0b 00     call 0xC42DE0             ; memset +0x3658,0,0x400
00B88C02  68 00 04 00 00     push 0x400
00B88C07  8d 86 58 3a 00 00  lea  eax, [esi+0x3A58]
00B88C0F  e8 cc a1 0b 00     call 0xC42DE0             ; memset +0x3A58,0,0x400
00B88C17  c7 86 58 3e 00 00 03 00 00 00  mov [esi+0x3E58], 3
00B88C21  c7 46 18 ff ff 00 00  mov [esi+0x18], 0xFFFF
00B88C28  8b c6              mov  eax, esi
00B88C2D  c2 0c 00           ret  0xC
```

### 3.1 host/port 怎么进去

构造器 **3 个参数**（`ret 0xC`）：arg1、arg2、arg3，全部原样转交给基类 `0xB9A1A0`：

```asm
00B9A1CB  8b 45 08        mov  eax, [ebp+8]         ; arg1
00B9A1D0  c7 06 ec a2 d5 00  mov [esi], 0xD5A2EC
00B9A1D6  89 46 10        mov  [esi+0x10], eax      ; ★ arg1 -> +0x10
00B9A257  66 8b 55 10     mov  dx, word [ebp+0x10]  ; arg3 (word)
00B9A263  66 89 96 70 21 00 00  mov word [esi+0x2170], dx ; ★ port -> +0x2170
00B9A2A2  8b 45 0c        mov  eax, [ebp+0xC]       ; arg2
00B9A2B0  e8 2b fc ff ff  call 0xBA9EE0             ; host 写入 +0x1570 缓冲组
```

调用点：

```asm
007F2BAF  0f b7 3d c4 9e a9 08  movzx  edi, word [0x81A9EC4]   ; ★ port (16-bit)
007F2BDD  68 a8 76 1a 08        push   0x81A76A8            ; ★ host 字符串
007F2BE2  53                    push   ebx                  ; arg1（0x81A9EB8 的值）
007F2BE5  e8 96 5f 39 00        call   0xB88B80
```

`0xBA9EE0` 把 字符串复制进三个 1024 字节缓冲（`+0x1570`、`+0x1970`、`+0x1D70`，见 `0xBA9F1D` 起的 `lea edi,[ebx+0x400]` / `[ebx+0x800]`）。

### 3.2 host 有没有格式校验？

**没有。** `0xB88B80` → `0xB9A1A0` → `0xBA9EE0` 只做：

- `strlen`
- 截断到 `0x3FF`
- `memcpy` + 结尾置 0

结论：**host 的合法性、是不是 IP、能不能解析，全都不在这里判断**；非法/不可达只会在后续 cURL 解析或连接时失败。端口也只是存成 `word`，**不做 0/65535 之外的合法性检查**。

---

## 4. 完整反汇编 `0xB9A9E0`（连接/握手核心）

函数帧：`sub esp, 0x2B3C`（`0xB9A9F1 mov eax,0x2B3C` + `0xC43280`），结束时 `ret`（无栈参数，`thiscall`）。

### 4.1 阶段总览

```text
阶段 1  objA vtable+0xC → 0xB88940：选择 host 缓冲索引
阶段 2  JSON 参数装配（三组 BC4BB0/BC48D0）
阶段 3  URL = https://<host>:<port>/auth/   （0xD5A2CC 模板，0xBA9EB0 取 host 缓冲）
阶段 4  objA vtable+0x2C 生成一次性数据
阶段 5  HTTP vtable+0x04 设置 URL/方法、+0x08/+0x0C 加头部、+0x14 设置 body、+0x1C 设置接收缓冲
阶段 6  HTTP vtable+0x28 执行 cURL，HTTP 状态必须 200..299
阶段 7  HTTP vtable+0x2C 必须返回 3 → 成功；否则写错误码返回 0
```

### 4.2 阶段 1：选择 host 缓冲索引

```asm
00B9AA14  8b 06              mov  eax, [esi]
00B9AA16  8b 50 0c           mov  edx, [eax+0xC]        ; ★ objA vtable 槽 +0xC
00B9AA19  8d 8d c4 d4 ff ff  lea  ecx, [ebp-0x2B3C]
00B9AA1F  51                 push ecx
00B9AA20  8b ce              mov  ecx, esi
00B9AA22  b3 01              mov  bl, 1
00B9AA24  ff d2              call edx
00B9AA26  84 c0              test al, al
00B9AA28  75 11              jne  0xB9AA3B
00B9AA2A  e8 a1 8b ca ff     call 0x8435D0
00B9AA2F  c7 86 6c 15 00 00 e7 02 00 00  mov [esi+0x156C], 0x2E7   ; ★ 错误码 0x2E7
00B9AA39  32 db              xor  bl, bl
```

该槽的真身是 `0xB88940`：

```asm
00B88940  8b 81 58 3e 00 00  mov eax, [ecx+0x3E58]
00B88946  83 f8 03           cmp eax, 3
00B88949  75 14              jne 0xB8895F
00B8894B  e8 7d ac cb ff     call 0x8435D0
00B88950  8b 45 08           mov eax, [ebp+8]
00B88953  c7 00 00 00 00 00  mov dword [eax], 0       ; 3 规范化为 0
00B88959  b0 01              mov al, 1
00B8895B  c2 04 00           ret 4
00B8895F  8b 4d 08           mov ecx, [ebp+8]
00B88962  89 01              mov [ecx], eax
00B88964  b0 01              mov al, 1
00B88967  c2 04 00           ret 4
```

`0xB88B80` 把 `[objA+0x3E58]` 置 3，因此这里输出 `[ebp-0x2B3C]=0`；`0xBA9EB0` 随后选择 host 缓冲 `+0x1570`。

### 4.3 阶段 2/3：JSON 装配与 URL 拼装

三处 `0xBC4BB0` 写入请求参数（[反汇编] `0xBC4BB0` 即 `0xBC4AB0` 的薄包装，做 JSON 键值对 append）：

```asm
00B9AAB6  68 28 a2 d5 00     push 0xD5A228      ; "auth_task"
00B9AAC1  e8 ea a0 02 00     call 0xBC4BB0
00B9AAD5  68 14 a1 d5 00     push 0xD5A114      ; "iv_seed"
00B9AAE0  e8 cb a0 02 00     call 0xBC4BB0
00B9AAF1  68 c0 7a db 00     push 0xDB7AC0      ; "title_id"
00B9AAFC  e8 af a0 02 00     call 0xBC4BB0
00B9AB0A  68 3c 38 cc 00     push 0xCC383C      ; "identity"
00B9AB15  e8 b6 9d 02 00     call 0xBC48D0
```

条目值来自对象成员 `[esi+0x14]`（状态字）、`[esi+0x2174]`、`[esi+0x10]`（host）、`[esi+0x2170]`（port）。

URL 拼装（`0xB9AC1D` 起）：

```asm
00B9AC2F  50                 push eax                 ; strlen(host)
00B9AC30  8b ce              mov  ecx, esi
00B9AC32  e8 09 f8 ff ff     call 0xB9A440            ; 分配 + 存 host 到 +0x164/+0x168
00B9AC4C  e8 9f 7b 0a 00     call 0xC427F0            ; memcpy(host)
00B9AC6B  0f b7 96 70 21 00 00  movzx edx, word [esi+0x2170]   ; ★ port
00B9AC72  8b 85 c4 d4 ff ff  mov  eax, [ebp-0x2B3C]
00B9AC7B  52                 push edx
00B9AC7C  50                 push eax
00B9AC7D  8d 8e 70 15 00 00  lea  ecx, [esi+0x1570]
00B9AC83  e8 28 f2 00 00     call 0xBA9EB0            ; 选 host 缓冲组
00B9AC88  50                 push eax
00B9AC89  68 cc a2 d5 00     push 0xD5A2CC           ; ★ "https://%s:%d/auth/"
00B9AC94  68 00 02 00 00     push 0x200
00B9AC9A  e8 d1 06 be ff     call 0x77B370            ; sprintf_s -> [ebp-0x228]
00B9ACA6  e8 25 89 ca ff     call 0x8435D0            ; 日志
```

`0xBA9EB0` 是按 index 选缓冲：`0→+0x1570`、`1→+0x1970`、`2→+0x1D70`（[反汇编] `0xBA9EB0–0xBA9ADD`）。

### 4.4 阶段 4：HTTP 头 + cURL 设置 + 发送

```asm
00B9ACAE  e8 fd 84 aa ff     call 0x6431B0          ; 取/建一个全局对象
00B9ACB5  e8 26 c5 fd ff     call 0xB771E0          ; 取 8 字节事务 ID
00B9ACBC  8b 06              mov  eax, [esi]        ; objA vtable
00B9ACBE  6a 01              push 1
00B9ACC0  8d 8d b8 d4 ff ff  lea  ecx, [ebp-0x2B48]
00B9ACC8  8b 50 2c           mov  edx, [eax+0x2C]   ; ★ objA 槽 +0x2C
00B9ACCB  51                 push ecx
00B9ACCC  8b ce              mov  ecx, esi
00B9ACCE  ff d2              call edx               ; 生成对象相关数据
00B9ACD0  53                 push ebx
00B9ACD1  57                 push edi               ; 事务 ID
00B9ACD2  68 7c 9e d5 00     push 0xD59E7C         ; "%I64u"
00B9ACE3  e8 88 06 be ff     call 0x77B370
00B9ACE8  8b 8e 60 01 00 00  mov  ecx, [esi+0x160]  ; ★ HTTP 客户端对象
00B9ACEE  8b 11              mov  edx, [ecx]
00B9ACF0  8b 52 04           mov  edx, [edx+4]      ; ★ HTTP vtable 槽 +0x04
00B9ACF6  68 98 3a 00 00     push 0x3A98
00B9ACFB  8d 85 d8 fd ff ff  lea  eax, [ebp-0x228]  ; URL
00B9AD01  50                 push eax
00B9AD02  6a 03              push 3                 ; ★ method=3 -> CURLOPT_POST
00B9AD04  ff d2              call edx               ; 设置 URL/方法
```

`0xC75F80`（HTTP vtable `+0x04`）证明 `method==3` 走 `0xC76191`，最终设置 `CURLOPT_POST`；`0xC75B45` 调 `0xC75050` 执行 cURL。

`method=3` 到 `CURLOPT_POST` 的映射证据（[反汇编] `0xC76038–0xC761AD`）：

```asm
00C7603D  83 f9 05                 cmp  ecx, 5
00C76046  ff 24 8d f4 61 c7 00     jmp  dword ptr [ecx*4+0xC761F4]
; 跳转表 0xC761F4（ecx = method-1）：
;   [0]=0xC7604D  [1]=0xC76191  [2]=0xC76191  [3]=0xC7615D
;   [4]=0xC7605E  [5]=0xC76091
; 其中 method=3（POST）落到 0xC76191：
00C76191  84 c0                    test al, al
00C76195  6a 01                    push 1                 ; 1 = enabled
00C76197  6a 2f                    push 0x2F              ; ★ 0x2F = CURLOPT_POST(47)
00C76199  8b 4e 20                 mov  ecx, [esi+0x20]
00C7619C  51                       push ecx
00C7619D  e8 0e 32 e5 ff           call 0xAC93B0          ; curl_easy_setopt
```

相关 `curl_easy_setopt`：

| 位置 | option | 含义 |
|---|---|---|
| `0xC76020` | `0x2712` | `CURLOPT_URL` (10002)，参数是 `0xB9AC94` 生成的 URL |
| `0xC76055` 所属分支 | `0x50` | 属于别的 method，不走本链 |
| 本链 `method=3` | `0x2F` | `CURLOPT_POST` = 1 |

`0xB9AD0A/0xB9AD25` 随后的两次 `[objA+0x160] vtable+0x0C` 是加头部：

```asm
Content-Type: application/json       ; 0xD5A1D4 / 0xD5A1E4
X-TransactionID: <u64>               ; 0xD59E6C / 0xD59E7C
```

`0xB9AD99` 再调用 `0xC767D0` 设置 POST body；该包装的 `+0x14` 最终落到 `0xC76210`：

```asm
00C767D0  55              push ebp
00C767D1  8b ec           mov  ebp, esp
00C767D3  8b 01           mov  eax, [ecx]
00C767D5  8b 40 14        mov  eax, [eax+0x14]     ; ★ HTTP vtable 槽 +0x14 -> 0xC76210
00C767D8  5d              pop  ebp
00C767D9  ff e0           jmp  eax
```

`0xC767E0` 则转 `+0x1C -> 0xC764C0`，用于接收缓冲：

```asm
00C767E0  55              push ebp
00C767E1  8b ec           mov  ebp, esp
00C767E3  8b 01           mov  eax, [ecx]
00C767E5  8b 40 1c        mov  eax, [eax+0x1C]     ; ★ HTTP vtable 槽 +0x1C
00C767E8  5d              pop  ebp
00C767E9  ff e0           jmp  eax
```

`0xC76210` 在 arg2（body 长度）非 0 时会把长度格式化为十进制并加入 `Content-Length`：

```asm
00C76243  8b 7d 0c        mov  edi, [ebp+0xC]      ; body 长度
00C7624A  57              push edi
00C7624B  68 68 7b db 00  push 0xDB7B68          ; "%u"
00C76250  ...             sprintf_s
00C76267  68 b8 4b d3 00  push 0xD34BB8          ; "Content-Length"
00C7626E  ff d2           call vtable+0xC
```

该路径随后设置 cURL 的读写回调和 `POSTFIELDSIZE` 类参数，因此请求体有明确长度；服务端应优先按 `Content-Length` 读取，
不能假定固定 187 字节（长度随 JSON 字段值变化）。

### 4.5 阶段 5/6：响应判定（**核心**）

```asm
00B9AD85  8b 86 68 01 00 00  mov  eax, [esi+0x168]   ; write callback 记录长度
00B9AD8B  8b 8e 64 01 00 00  mov  ecx, [esi+0x164]
00B9AD99  e8 32 ba 0d 00     call 0xC767D0          ; ★ 设置 POST body/上传回调
00B9AD9E  84 c0              test al, al
00B9ADA0  74 31              je   0xB9ADD3
00B9ADA2  8b 8e 60 01 00 00  mov  ecx, [esi+0x160]   ; ★ HTTP 客户端对象
00B9ADAD  8d 86 6c 01 00 00  lea  eax, [esi+0x16C]
00B9ADB4  e8 27 ba 0d 00     call 0xC767E0          ; 槽 +0x1C
00B9ADB9  84 c0              test al, al
00B9ADBB  74 16              je   0xB9ADD3
00B9ADBD  8b 8e 60 01 00 00  mov  ecx, [esi+0x160]
00B9ADC3  8b 11              mov  edx, [ecx]
00B9ADC5  8b 42 28           mov  eax, [edx+0x28]   ; ★ 槽 +0x28（读状态）
00B9ADC8  ff d0              call eax
00B9ADCA  83 f8 03           cmp  eax, 3             ; ★ 状态必须 == 3
00B9ADCD  75 04              jne  0xB9ADD3
00B9ADCF  b3 01              mov  bl, 1
00B9ADD5  8b 8e 60 01 00 00  mov  ecx, [esi+0x160]
00B9ADDB  8b 11              mov  edx, [ecx]
00B9ADDD  8b 42 2c           mov  eax, [edx+0x2C]
00B9ADE0  ff d0              call eax
00B9ADE2  84 db              test bl, bl
00B9ADE4  74 0c              je   0xB9ADF2
00B9ADE6  83 f8 03           cmp  eax, 3
00B9ADE9  75 25              jne  0xB9AE10
00B9ADEB  c7 46 20 01 00 00 00  mov dword [esi+0x20], 1     ; ★ 连接对象标记为已连接
00B9ADF2  8a c3              mov  al, bl                                  ; ★ 返回 bl
00B9AE0F  c3                 ret
00B9AE10  50                 push eax
00B9AE11  e8 ba 87 ca ff     call 0x8435D0
00B9AE19  c7 86 6c 15 00 00 05 00 00 00  mov [esi+0x156C], 5                     ; ★ 错误码 5
00B9AE23  32 c0              xor  al, al
00B9AE25  eb cd              jmp  0xB9ADF4
```

`0xC767F0`（状态编码器，[反汇编] `0xC767F0–0xC76853`）：

```asm
00C767F0  55              push ebp
00C767F3  8b 55 08        mov  edx, [ebp+8]
00C767F6  32 c0           xor  al, al
00C767F8  83 fa 05        cmp  edx, 5
00C767FB  77 52           ja   0xC7684F
00C767FD  ff 24 95 54 68 c7 00  jmp dword ptr [edx*4+0xC76854]
; arg==3 分支（0xC7681A）：
00C7681A  83 79 04 03     cmp  dword ptr [ecx+4], 3
00C7681E  0f 94 c0        sete al                     ; ★ 只有状态成员==3 才为真
; arg==4/5 分支（0xC76830）：
00C76830  8b 49 04        mov  ecx, [ecx+4]
00C76833  83 f9 05        cmp  ecx, 5
00C76838  83 f9 06        ... 6
00C7683D  83 f9 07        ... 7
00C76842  83 f9 04        ... 4 -> true
```

状态 `3` 的来源（**HTTP 200..299**，[反汇编] `0xC752BC–0xC75320`）：

```asm
00C752BC  8b 4e 20              mov  ecx, [esi+0x20]
00C752BF  8d 45 fc              lea  eax, [ebp-4]
00C752C3  68 02 00 20 00        push 0x200002           ; CURLINFO_RESPONSE_CODE(0x200002)
00C752C9  e8 19 43 e5 ff        call 0xAC95F0           ; curl_easy_getinfo
00C752DD  89 96 64 04 00 00     mov  [esi+0x464], edx   ; ★ 保存 HTTP 状态码
00C752E3  81 fa c8 00 00 00     cmp  edx, 0xC8          ; 200
00C752E9  7c 35                 jl   0xC75320
00C752EB  81 fa 2c 01 00 00     cmp  edx, 0x12C         ; 300
00C752F1  7d 2d                 jge  0xC75320
00C752F3  ...                    ; ★ 2xx：状态 = 5，成功路径
00C75320  ...                    ; 否则状态 = 6，失败路径
```

而 `0xC767F0(arg=3)` 判定 `[ecx+4]==3`，`[ecx+4]` 就是 cURL 句柄经 `0xC75050` 推进后的内部状态；`0xC75050` 的成功返回把 `[esi+4]` 置 3（`0xC750FA mov dword [esi+4],3`，先经 `0xC754E0` 的证书设置与 `0xC74ED0` 重置）。

### 4.6 `0xB9A9E0` 失败的**每一个**分支与判据

| # | 分支 VA | 判据（[反汇编]） | 含义 | 错误码 |
|---|---|---|---|---|
| 1 | `0xB9AA28` | `mov edx,[eax+0xC]` 调用返回 `al==0`（`0xB9AA26 test al,al / jne`） | 请求对象 URL/参数初始化失败 | `[+0x156C]=0x2E7` |
| 2 | `0xB9AB22` | 任一 `0xBC4BB0`/`0xBC48D0` 返回 0（`0xB9AAA5…0xB9AB1C`） | JSON 参数装配失败（缓冲区不足/字段无效） | — |
| 3 | `0xB9ABF7` | 三组 JSON 装配 + `0xBC4540` 任一失败（`0xB9AB5E…0xB9ABF1`） | auth 参数构造失败 | `[+0x156C]=0x2DE` |
| 4 | `0xB9ADD3` | 三条前置检查任一为 0：`0xC767D0` 设置 body、`0xC767E0` 设置接收缓冲、或 `HTTP vtable+0x28` 执行结果 `cmp eax,3` | body/接收缓冲/传输执行失败 | 未在此分支设置 |
| 5 | `0xB9AE10` | `bl==1` 但 `[obj+0x160]` 的 `vtable+0x2C` 返回值 `!= 3` | 请求未完成（传输/证书/HTTP 状态非 2xx） | `[+0x156C]=5` |

超时/重试/状态机（[反汇编]）：

- 状态机：`bl` 是一路串联的成功标志；`edi`（`0xB9ACBA`）保存 "已发送字节数"，`0xB9AD4D–0xB9AD7F` 是**响应头回填循环**（对每个已发送字段再次 `vtable+0xC`）。
- `0xC75F80` 的 method 分派是一个显式状态机：`[esi+4]` 取值 1..7，`0xC74ED0` 重置到 1，`0xC750FA` 置 3，`0xC75226` 置 7，`0xC75398` 写 5 或 6。
- 超时：`0xC75ACB push 0x3C / push 0x4E` 设置 `CURLOPT_CONNECTTIMEOUT(78)=60` 秒；本链没有找到明确的 `CURLOPT_TIMEOUT`。
- **未发现显式重试计数**：本链没有循环重发逻辑；失败即返回 0，由外层 FSM 把 `sub_state` 置 0。

### 4.7 `0xB9A9E0` 调用的主要子函数、作用与成败条件

| 子函数 VA | 调用阶段 | 作用 | 成功/失败条件 |
|---|---|---|---|
| `0xB88940` | URL 前 | `objA vtable+0xC`：读取/规范化 host 选择索引；构造器值为 3，输出 0 | 正常路径总返回 1 |
| `0xC73380` | 请求体前 | 生成 `iv_seed` 使用的 8 字节值 | 返回值只作为数据，不参与 bool |
| `0xBC4230` | JSON 初始化 | 绑定 JSON 输出缓冲及容量（0x1400） | 无 bool 返回 |
| `0xBC4540` | JSON 开始 | 写入 JSON 对象开始标记 `{` | 返回 0/1；失败进入 `0xB9AB22` |
| `0xBC4BB0` | JSON 标量字段 | 追加 `auth_task/iv_seed/title_id` | 任一返回 0 → auth 构造失败 |
| `0xBC48D0` | JSON 字符串字段 | 追加 `identity/extra_data` | 返回 0 → `0x2DE` 错误路径 |
| `0xBC42C0` | JSON 收尾 | `}`/`]` 收尾并检查栈 | 返回 0 → 失败 |
| `0xBC4270` | JSON 检查 | 确认对象非空且无未闭合层 | 返回 0 → 失败 |
| `0xBC4260` | JSON 清理 | 清对象状态 | 不产生失败 |
| `0xB9A440` | URL/body 分配 | 释放旧缓冲、分配新缓冲并记录长度 | 未检查返回值；分配失败属异常路径 |
| `0xBA9EB0` | URL 拼装 | 按索引选择 host 缓冲 | 索引 0/1/2 有效，否则返回 0 |
| `0x77B370` | URL/头部格式化 | `sprintf_s` 风格格式化 | 返回值进入长度检查；越界走失败 |
| `0xC75F80` | HTTP 设置 | URL + method；method 3 设 `CURLOPT_POST` | 返回 bool；失败总体失败 |
| `0xC758A0` | HTTP 头 | 追加 `Content-Type` / `X-TransactionID` | 返回 bool；失败总体失败 |
| `0xC76210` | POST body | 追加 `Content-Length`，设置读写回调/长度 | 返回 bool；失败总体失败 |
| `0xC764C0` | 响应缓冲 | 绑定 `[objA+0x16C]`、容量 `0x1400` | 返回 bool；失败总体失败 |
| `0xC75A50` | 执行 | 设置 cURL 选项并执行 | 返回状态；只有 3 可通过 `0xB9ADCA` |
| `0xBC1190` | 状态读取 | HTTP 对象 `vtable+0x2C`，返回 `[obj+4]` | `bl==1` 时必须 ==3 |
| `0xC75050` | 响应收尾 | 取 HTTP 状态、判定 2xx、置状态 3/5/6/7 | `0xC752E3–0xC752F1` |
| `0xC767F0` | 状态谓词 | 对 `arg==3` 只认 `[obj+4]==3` | 该链最终用 `arg=3` |

---

## 5. 回答核心问题：本地服务器必须做什么

### 5.1 一句话规格

**在 `host:port` 上开一个 TLS 服务器，证书能被客户端的 `cacert.pem` 链验证通过；收到 `POST /auth/` 后返回完整的 HTTP `200`（任意 2xx），响应体可任意。**

### 5.2 必须满足的协议栈

| 层 | 要求 | 证据 |
|---|---|---|
| TCP | 接受 `0x81A9EC4` 指定的端口连接 | `0x7F2BAF` / `0xB9A257` |
| TLS | **必须**完成 TLS 握手（不是裸 HTTP） | cURL 句柄 `0x6431B0`、`0xAC9370`，URL 是 `https://` |
| 证书 | 证书链必须能被客户端验证：`SSL_VERIFYPEER=1`、`SSL_VERIFYHOST=2`、CA 来自 `cacert.pem` | `0xC75532–0xC75587`、`0xC754E3` |
| HTTP | HTTP/1.1，`POST /auth/` | `0xD5A2CC` 模板 |
| 状态码 | **200..299** | `0xC752E3` |

### 5.3 "收到 X 就回 Y"

```text
收到：
  （TLS 握手完成）
  POST /auth/ HTTP/1.1
  Host: <host>[:<port>]
  Content-Type: application/json
  X-TransactionID: <十进制 u64>
  Content-Length: <n>

  {"auth_task":...,"iv_seed":...,"title_id":...,"identity":...,"extra_data":{...}}

回：
  HTTP/1.1 200 OK
  Content-Length: <任意，含 0>
  Connection: close        （或按正常 keep-alive 处理）
  <任意 body>
```

补充说明：

1. 请求体的精确值：`auth_task`、`iv_seed`、`title_id`、`identity`、`extra_data` 的**值**由运行期对象字段决定，静态镜像里没有常量；但**键名固定**（VA 已列在 §4.3 与 `connect_spec.json`）。
2. 已捕获证据（[既有]，任务书提供）：实际链路上曾见到 `POST /auth/`、`auth_task:"10"`、约 187 字节 JSON，并被本地 TLS 探针正确应答——与本轮静态结论一致。
3. `0xB9A9E0` **不解析响应体**：`0xC75050` 之后只读 `CURLINFO_RESPONSE_CODE`，没有 JSON 解析调用。所以"回什么内容"不重要，**"回 2xx"才重要**。

### 5.4 时序要求

```text
1. 客户端解析 host:port（0x81A76A8 / 0x81A9EC4）
2. TCP 连接 + TLS 握手（证书验证必须过）
3. 发送 POST /auth/ + JSON
4. 服务端在客户端超时前返回完整 2xx
5. 客户端 0xB9A9E0 返回 1 → [objA+0x20]=1、sub_state 保持推进
```

---

## 6. 其它必须先满足的前置条件

| # | 对象 | 要求 | 证据 | 性质 |
|---|---|---|---|---|
| 1 | `0x331C5C0` | **非 0**，否则 `0x7F2BC0`/`0x7F2C6B` 走降级路径，不创建 objA | `[反汇编]` 0x7F2BA0/0x7F2C64 | 事实 |
| 2 | `0x81A76A8` | host 字符串，非空，指向本地服务 | `[反汇编]` 0x7F2BDD | 事实 |
| 3 | `0x81A9EC4` | 16 位端口，指向本地 TLS 端口 | `[反汇编]` 0x7F2BAF | 事实 |
| 4 | `cacert.pem` | 必须存在且含签发本地证书的 CA，否则 `SSL_VERIFYPEER` 失败 | `[反汇编]` 0xB9A100/0xC7556D | 事实 |
| 5 | `0x331C5D8` | arg2 内容必须**全 ASCII**（`<0x80`），否则 `0x73` 分支 | `[反汇编]` 0xB88D00 | 事实 |
| 6 | `0x331C65C` | 16 字节模式缓冲，首字节成为 `objA+0x3650` 模式标志 | `[反汇编]` 0xB88E90 | 事实 |
| 7 | `0x331C658` | 长度字（非端口）；0 不会导致 `0xB88CC0` 失败 | `[反汇编]` 0xB75E0C | 事实 |
| 8 | `0x849B501` | 决定 arg10 是 `0` 还是 `0x80`（间接影响 `[objA+0x3650]`） | `[反汇编]` 0x7F2C71 | 事实（语义未解） |

---

## 7. 事实 / 推断 / 未解

### 事实（VA 级）

1. `0xB88CC0` 是 `thiscall + ret 0x28`，全镜像唯一调用者 `0x7F2D2A`；它只做参数暂存 + 建流对象 + 调 `0xB9A9E0`。
2. `0xB88CC0` 的两个本地返回 0 出口（`0xB88CEB`、`0xB88F1D`）在本链均可排除；返回 0 来自 `0xB9A9E0`。
3. `0xB9A9E0` 构造 `https://<host>:<port>/auth/`，`POST` 一个含 `auth_task/iv_seed/title_id/identity/extra_data` 的 JSON。
4. 成功要求响应码 `200..299`（`0xC752E3`），对应状态 `3`（`0xC767F0` 的 `arg==3` 分支）。
5. 证书校验是开启的：`VERIFYPEER=1`、`VERIFYHOST=2`、`CAINFO=cacert.pem`。
6. `0xB88B80` 对 host **无任何格式校验**，只做 strlen/截断/memcpy；端口只存 `word`。

### 推断

1. 实测"改了 `0x331C5C0` 仍失败"的原因就是本链 `0xB9A9E0` 在 TLS/HTTP 阶段返回 0，而当前本地服务尚未满足"受信证书 + 2xx"这两个条件。
2. `0x331C5D8`（arg2）在正常 TCLS 形态下应非空；为空虽然在 `0xB75E00` 不报错，但可能影响后续 auth 参数。

### 未解

1. `auth_task/iv_seed/title_id/identity/extra_data` 的**取值**语义（值来自运行期对象字段，静态无常量）。
2. `[objA+0x16C]`（1024 字节）在响应后的回填/校验逻辑，`0xB9ADBD` 之后未见解析响应体。
3. `0xB9ACF6` 的 `0x3A98` 由 HTTP vtable `+0x04` 的 `0xC75F80` 最终经 `+0x24 → 0xC74F60` 存入对象 `+0x08`；其业务语义未解，**不能证明是超时**。
4. `0x849B501` 的语义。

---

## 8. 复现命令（脚本纯 ASCII，`py_compile` 通过）

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL
python -X utf8 CODOLServer\_subagents\_ch_dis.py disasm 0xB88CC0 0xB88F60
python -X utf8 CODOLServer\_subagents\_ch_dis.py disasm 0xB88B80 0xB88CC0
python -X utf8 CODOLServer\_subagents\_ch_dis.py disasm 0xB9A9E0 0xB9AE27
python -X utf8 CODOLServer\_subagents\_ch_dis.py disasm 0xC752BC 0xC75320
python -X utf8 CODOLServer\_subagents\_ch_dis.py disasm 0xC767F0 0xC76860
python -X utf8 CODOLServer\_subagents\_ch_dis.py dump   0xD5A2CC 0x30
python -X utf8 CODOLServer\_subagents\_ch_evidence.py > CODOLServer\_subagents\_ch_evidence.json
python -m py_compile CODOLServer\_subagents\_ch_dis.py CODOLServer\_subagents\_ch_evidence.py
```

---

## 9. 总结（区分事实与推断）

**事实**：这条链是 `libcurl` 的 HTTPS 请求，`0xB88CC0` 只是构造器；真正的网络动作在 `0xB9A9E0`，它把 JSON `POST` 到 `https://<host>:<port>/auth/`（模板 `0xD5A2CC` 就在镜像里）。成功判据是 HTTP `200..299`（`0xC752E3`），且 `0xB88CC0` 返回 0 的一切实测都落在 `0xB9A9E0` 的 TLS/HTTP 失败分支上，`0xB75E00` 在新对象上不会失败。

**事实**：证书校验是**开启**的（`VERIFYPEER=1`、`VERIFYHOST=2`、`CAINFO=cacert.pem`），所以自签证书必须在客户端 `cacert.pem` 体系里被信任，否则 TLS 阶段就断。

**推断**：之前"改了 `0x331C5C0` 仍失败"，最可能的原因是本地服务同时不满足"受信证书"与"返回 2xx"中的至少一条；只要补上 TLS 证书信任并回 `200`，`0xB9A9E0` 就应返回 1、`[objA+0x20]` 置 1、外层 FSM 不再把 `sub_state` 清零。

**未解**：请求体各字段的取值语义、响应体是否在别处被校验、以及超时/重试细节，静态上仍未证明。

---

## 附录 A：`0xB88CC0` 全量反汇编（`0xB88CC0–0xB88F5E`）

```asm
00B88CC0  55                   push ebp
00B88CC1  8b ec                mov  ebp, esp
00B88CC3  6a ff                push -1
00B88CC5  68 7b bf c8 00       push 0xC8BF7B
00B88CCA  64 a1 00 00 00 00    mov  eax, fs:[0]
00B88CD0  50                   push eax
00B88CD1  53                   push ebx
00B88CD2  56                   push esi
00B88CD3  57                   push edi
00B88CD4  a1 40 f2 e3 00       mov  eax, [0xE3F240]
00B88CD9  33 c5                xor  eax, ebp
00B88CDB  50                   push eax
00B88CDC  8d 45 f4             lea  eax, [ebp-0xC]
00B88CDF  64 a3 00 00 00 00    mov  fs:[0], eax
00B88CE5  8b f1                mov  esi, ecx
00B88CE7  83 7e 20 00          cmp  dword [esi+0x20], 0
00B88CEB  0f 85 31 02 00 00    jne  0xB88F22
00B88CF1  8b 5d 1c             mov  ebx, [ebp+0x1C]
00B88CF4  85 db                test ebx, ebx
00B88CF6  74 16                je   0xB88D0E
00B88CF8  8a 03                mov  al, [ebx]
00B88CFA  8b cb                mov  ecx, ebx
00B88CFC  84 c0                test al, al
00B88CFE  74 0e                je   0xB88D0E
00B88D00  0f 88 a1 00 00 00    js   0xB88DA7
00B88D06  8a 41 01             mov  al, [ecx+1]
00B88D09  41                   inc  ecx
00B88D0A  84 c0                test al, al
00B88D0C  75 f2                jne  0xB88D00
00B88D0E  8b 45 08             mov  eax, [ebp+8]
00B88D11  8b 08                mov  ecx, [eax]
00B88D13  89 8e 90 31 00 00    mov  [esi+0x3190], ecx
00B88D19  8b 50 04             mov  edx, [eax+4]
00B88D1C  89 96 94 31 00 00    mov  [esi+0x3194], edx
00B88D22  8b 48 08             mov  ecx, [eax+8]
00B88D25  68 5c 08 00 00       push 0x85C
00B88D2A  89 8e 98 31 00 00    mov  [esi+0x3198], ecx
00B88D30  8b 50 0c             mov  edx, [eax+0xC]
00B88D33  8d be fc 35 00 00    lea  edi, [esi+0x35FC]
00B88D39  6a 00                push 0
00B88D3B  57                   push edi
00B88D3C  89 96 9c 31 00 00    mov  [esi+0x319C], edx
00B88D42  e8 99 a0 0b 00       call 0xC42DE0
00B88D47  8b 45 18             mov  eax, [ebp+0x18]
00B88D4A  89 86 4c 36 00 00    mov  [esi+0x364C], eax
00B88D50  8b 45 14             mov  eax, [ebp+0x14]
00B88D53  8b 08                mov  ecx, [eax]
00B88D55  89 0f                mov  [edi], ecx
00B88D57  8b 50 04             mov  edx, [eax+4]
00B88D5A  89 57 04             mov  [edi+4], edx
00B88D5D  8b 48 08             mov  ecx, [eax+8]
00B88D60  89 4f 08             mov  [edi+8], ecx
00B88D63  8b 50 0c             mov  edx, [eax+0xC]
00B88D66  83 c4 0c             add  esp, 0xC
00B88D69  89 57 0c             mov  [edi+0xC], edx
00B88D6C  85 db                test ebx, ebx
00B88D6E  74 5c                je   0xB88DCC
00B88D70  8b 55 1c             mov  edx, [ebp+0x1C]
00B88D73  8b c2                mov  eax, edx
00B88D75  8d 9e 0c 36 00 00    lea  ebx, [esi+0x360C]
00B88D7B  8d 78 01             lea  edi, [eax+1]
00B88D7E  8b ff                mov  edi, edi
00B88D80  8a 08                mov  cl, [eax]
00B88D82  40                   inc  eax
00B88D83  84 c9                test cl, cl
00B88D85  75 f9                jne  0xB88D80
00B88D87  2b c7                sub  eax, edi
00B88D89  85 db                test ebx, ebx
00B88D8B  74 52                je   0xB88DDF
00B88D8D  8b f8                mov  edi, eax
00B88D8F  83 f8 3f             cmp  eax, 0x3F
00B88D92  72 05                jb   0xB88D99
00B88D94  bf 3f 00 00 00       mov  edi, 0x3F
00B88D99  57                   push edi
00B88D9A  52                   push edx
00B88D9B  53                   push ebx
00B88D9C  e8 4f 9a 0b 00       call 0xC427F0
00B88DA1  c6 04 3b 00          mov  byte [ebx+edi], 0
00B88DA5  eb 35                jmp  0xB88DDC
00B88DA7  e8 24 a8 cb ff       call 0x8435D0
00B88DAC  c7 86 6c 15 00 00 73 00 00 00  mov [esi+0x156C], 0x73
00B88DB6  b0 01                mov  al, 1
00B88DB8  8b 4d f4             mov  ecx, [ebp-0xC]
00B88DBB  64 89 0d 00 00 00 00 mov  fs:[0], ecx
00B88DC2  59                   pop  ecx
00B88DC3  5f                   pop  edi
00B88DC4  5e                   pop  esi
00B88DC5  5b                   pop  ebx
00B88DC6  8b e5                mov  esp, ebp
00B88DC8  5d                   pop  ebp
00B88DC9  c2 28 00             ret  0x28
00B88DCC  6a 40                push 0x40
00B88DCE  8d 86 0c 36 00 00    lea  eax, [esi+0x360C]
00B88DD4  6a 00                push 0
00B88DD6  50                   push eax
00B88DD7  e8 04 a0 0b 00       call 0xC42DE0
00B88DDC  83 c4 0c             add  esp, 0xC
00B88DDF  8b 55 24             mov  edx, [ebp+0x24]
00B88DE2  8b 45 20             mov  eax, [ebp+0x20]
00B88DE5  89 86 54 36 00 00    mov  [esi+0x3654], eax
00B88DEB  85 d2                test edx, edx
00B88DED  74 3a                je   0xB88E29
00B88DEF  8b c2                mov  eax, edx
00B88DF1  8d 9e 58 36 00 00    lea  ebx, [esi+0x3658]
00B88DF7  8d 78 01             lea  edi, [eax+1]
00B88E00  8a 08                mov  cl, [eax]
00B88E02  40                   inc  eax
00B88E03  84 c9                test cl, cl
00B88E05  75 f9                jne  0xB88E00
00B88E07  2b c7                sub  eax, edi
00B88E09  85 db                test ebx, ebx
00B88E0B  74 32                je   0xB88E3F
00B88E0D  8b f8                mov  edi, eax
00B88E0F  3d ff 03 00 00       cmp  eax, 0x3FF
00B88E14  72 05                jb   0xB88E1B
00B88E16  bf ff 03 00 00       mov  edi, 0x3FF
00B88E1B  57                   push edi
00B88E1C  52                   push edx
00B88E1D  53                   push ebx
00B88E1E  e8 cd 99 0b 00       call 0xC427F0
00B88E23  c6 04 3b 00          mov  byte [ebx+edi], 0
00B88E27  eb 13                jmp  0xB88E3C
00B88E29  68 00 04 00 00       push 0x400
00B88E2E  8d 86 58 36 00 00    lea  eax, [esi+0x3658]
00B88E34  6a 00                push 0
00B88E36  50                   push eax
00B88E37  e8 a4 9f 0b 00       call 0xC42DE0
00B88E3C  83 c4 0c             add  esp, 0xC
00B88E3F  8b 55 28             mov  edx, [ebp+0x28]
00B88E42  85 d2                test edx, edx
00B88E44  74 34                je   0xB88E7A
00B88E46  8b c2                mov  eax, edx
00B88E48  8d 9e 58 3a 00 00    lea  ebx, [esi+0x3A58]
00B88E4E  8d 78 01             lea  edi, [eax+1]
00B88E51  8a 08                mov  cl, [eax]
00B88E53  40                   inc  eax
00B88E54  84 c9                test cl, cl
00B88E56  75 f9                jne  0xB88E51
00B88E58  2b c7                sub  eax, edi
00B88E5A  85 db                test ebx, ebx
00B88E5C  74 32                je   0xB88E90
00B88E5E  8b f8                mov  edi, eax
00B88E60  3d ff 03 00 00       cmp  eax, 0x3FF
00B88E65  72 05                jb   0xB88E6C
00B88E67  bf ff 03 00 00       mov  edi, 0x3FF
00B88E6C  57                   push edi
00B88E6D  52                   push edx
00B88E6E  53                   push ebx
00B88E6F  e8 7c 99 0b 00       call 0xC427F0
00B88E74  c6 04 3b 00          mov  byte [ebx+edi], 0
00B88E78  eb 13                jmp  0xB88E8D
00B88E7A  68 00 04 00 00       push 0x400
00B88E7F  8d 86 58 3a 00 00    lea  eax, [esi+0x3A58]
00B88E85  6a 00                push 0
00B88E87  50                   push eax
00B88E88  e8 53 9f 0b 00       call 0xC42DE0
00B88E8D  83 c4 0c             add  esp, 0xC
00B88E90  8a 4d 2c             mov  cl, [ebp+0x2C]
00B88E93  6a 1c                push 0x1C
00B88E95  88 8e 50 36 00 00    mov  [esi+0x3650], cl
00B88E9B  e8 80 b3 fe ff       call 0xB74220
00B88EA0  83 c4 04             add  esp, 4
00B88EA3  89 45 2c             mov  [ebp+0x2C], eax
00B88EA6  66 8b 5d 10          mov  bx, word [ebp+0x10]
00B88EAA  33 ff                xor  edi, edi
00B88EAC  89 7d fc             mov  [ebp-4], edi
00B88EAF  3b c7                cmp  eax, edi
00B88EB1  74 0e                je   0xB88EC1
00B88EB3  0f b7 d3             movzx edx, bx
00B88EB6  57                   push edi
00B88EB7  52                   push edx
00B88EB8  8b c8                mov  ecx, eax
00B88EBA  e8 e1 15 92 ff       call 0x4AA4A0
00B88EBF  8b f8                mov  edi, eax
00B88EC1  8b 86 f4 35 00 00    mov  eax, [esi+0x35F4]
00B88EC7  c7 45 fc ff ff ff ff mov  [ebp-4], -1
00B88ECE  85 c0                test eax, eax
00B88ED0  74 20                je   0xB88EF2
00B88ED2  83 c0 04             add  eax, 4
00B88ED5  50                   push eax
00B88ED6  ff 15 14 81 ca 00    call dword [0xCA8114]
00B88EDC  85 c0                test eax, eax
00B88EDE  75 12                jne  0xB88EF2
00B88EE0  8b 8e f4 35 00 00    mov  ecx, [esi+0x35F4]
00B88EE6  85 c9                test ecx, ecx
00B88EE8  74 08                je   0xB88EF2
00B88EEA  8b 01                mov  eax, [ecx]
00B88EEC  8b 10                mov  edx, [eax]
00B88EEE  6a 01                push 1
00B88EF0  ff d2                call edx
00B88EF2  89 be f4 35 00 00    mov  [esi+0x35F4], edi
00B88EF8  85 ff                test edi, edi
00B88EFA  74 0a                je   0xB88F06
00B88EFC  83 c7 04             add  edi, 4
00B88EFF  57                   push edi
00B88F00  ff 15 28 81 ca 00    call dword [0xCA8128]
00B88F06  8b 55 0c             mov  edx, [ebp+0xC]
00B88F09  8b 8e f4 35 00 00    mov  ecx, [esi+0x35F4]
00B88F0F  0f b7 c3             movzx eax, bx
00B88F12  50                   push eax
00B88F13  52                   push edx
00B88F14  e8 e7 ce fe ff       call 0xB75E00
00B88F19  84 c0                test al, al
00B88F1B  75 1b                jne  0xB88F38
00B88F1D  e8 ae a6 cb ff       call 0x8435D0
00B88F22  32 c0                xor  al, al
00B88F24  8b 4d f4             mov  ecx, [ebp-0xC]
00B88F27  64 89 0d 00 00 00 00 mov  fs:[0], ecx
00B88F2E  59                   pop  ecx
00B88F2F  5f                   pop  edi
00B88F30  5e                   pop  esi
00B88F31  5b                   pop  ebx
00B88F32  8b e5                mov  esp, ebp
00B88F34  5d                   pop  ebp
00B88F35  c2 28 00             ret  0x28
00B88F38  8b ce                mov  ecx, esi
00B88F3A  66 89 9e f8 35 00 00 mov  word [esi+0x35F8], bx
00B88F41  c7 46 14 20 00 00 00 mov  dword [esi+0x14], 0x20
00B88F48  e8 93 1a 01 00       call 0xB9A9E0
00B88F4D  8b 4d f4             mov  ecx, [ebp-0xC]
00B88F50  64 89 0d 00 00 00 00 mov  fs:[0], ecx
00B88F57  59                   pop  ecx
00B88F58  5f                   pop  edi
00B88F59  5e                   pop  esi
00B88F5A  5b                   pop  ebx
00B88F5B  8b e5                mov  esp, ebp
00B88F5D  5d                   pop  ebp
00B88F5E  c2 28 00             ret  0x28
```

## 附录 B：`0xB88B80` 全量反汇编（`0xB88B80–0xB88C2D`）

```asm
00B88B80  55                   push ebp
00B88B81  8b ec                mov  ebp, esp
00B88B83  8b 45 10             mov  eax, [ebp+0x10]
00B88B86  8b 55 08             mov  edx, [ebp+8]
00B88B89  53                   push ebx
00B88B8A  56                   push esi
00B88B8B  8b f1                mov  esi, ecx
00B88B8D  8b 4d 0c             mov  ecx, [ebp+0xC]
00B88B90  50                   push eax
00B88B91  51                   push ecx
00B88B92  52                   push edx
00B88B93  8b ce                mov  ecx, esi
00B88B95  e8 06 16 01 00       call 0xB9A1A0
00B88B9A  c7 06 7c 9a d5 00    mov  dword [esi], 0xD59A7C
00B88BA0  33 c0                xor  eax, eax
00B88BA2  33 db                xor  ebx, ebx
00B88BA4  89 9e b0 31 00 00    mov  [esi+0x31B0], ebx
00B88BAA  89 9e f4 35 00 00    mov  [esi+0x35F4], ebx
00B88BB0  66 89 86 f8 35 00 00 mov  word [esi+0x35F8], ax
00B88BB7  89 86 fc 35 00 00    mov  [esi+0x35FC], eax
00B88BBD  6a 40                push 0x40
00B88BBF  89 86 00 36 00 00    mov  [esi+0x3600], eax
00B88BC5  8d 8e 0c 36 00 00    lea  ecx, [esi+0x360C]
00B88BCB  53                   push ebx
00B88BCC  89 86 04 36 00 00    mov  [esi+0x3604], eax
00B88BD2  51                   push ecx
00B88BD3  89 86 08 36 00 00    mov  [esi+0x3608], eax
00B88BD9  e8 02 a2 0b 00       call 0xC42DE0
00B88BDE  68 00 04 00 00       push 0x400
00B88BE3  8d 96 58 36 00 00    lea  edx, [esi+0x3658]
00B88BE9  53                   push ebx
00B88BEA  52                   push edx
00B88BEB  89 9e 4c 36 00 00    mov  [esi+0x364C], ebx
00B88BF1  89 9e 54 36 00 00    mov  [esi+0x3654], ebx
00B88BF7  88 9e 50 36 00 00    mov  byte [esi+0x3650], bl
00B88BFD  e8 de a1 0b 00       call 0xC42DE0
00B88C02  68 00 04 00 00       push 0x400
00B88C07  8d 86 58 3a 00 00    lea  eax, [esi+0x3A58]
00B88C0D  53                   push ebx
00B88C0E  50                   push eax
00B88C0F  e8 cc a1 0b 00       call 0xC42DE0
00B88C14  83 c4 24             add  esp, 0x24
00B88C17  c7 86 58 3e 00 00 03 00 00 00  mov dword [esi+0x3E58], 3
00B88C21  c7 46 18 ff ff 00 00 mov  dword [esi+0x18], 0xFFFF
00B88C28  8b c6                mov  eax, esi
00B88C2A  5e                   pop  esi
00B88C2B  5b                   pop  ebx
00B88C2C  5d                   pop  ebp
00B88C2D  c2 0c 00             ret  0xC
```

## 附录 C：`0xB9A9E0` 全量反汇编（`0xB9A9E0–0xB9AE0F`）

```asm
00B9A9E0  55                   push ebp
00B9A9E1  8b ec                mov  ebp, esp
00B9A9E3  6a ff                push -1
00B9A9E5  68 56 de c8 00       push 0xC8DE56
00B9A9EA  64 a1 00 00 00 00    mov  eax, fs:[0]
00B9A9F0  50                   push eax
00B9A9F1  b8 3c 2b 00 00       mov  eax, 0x2B3C
00B9A9F6  e8 85 88 0a 00       call 0xC43280
00B9A9FB  a1 40 f2 e3 00       mov  eax, [0xE3F240]
00B9AA00  33 c5                xor  eax, ebp
00B9AA02  89 45 f0             mov  [ebp-0x10], eax
00B9AA05  53                   push ebx
00B9AA06  56                   push esi
00B9AA07  57                   push edi
00B9AA08  50                   push eax
00B9AA09  8d 45 f4             lea  eax, [ebp-0xC]
00B9AA0C  64 a3 00 00 00 00    mov  fs:[0], eax
00B9AA12  8b f1                mov  esi, ecx
00B9AA14  8b 06                mov  eax, [esi]
00B9AA16  8b 50 0c             mov  edx, [eax+0xC]
00B9AA19  8d 8d c4 d4 ff ff    lea  ecx, [ebp-0x2B3C]
00B9AA1F  51                   push ecx
00B9AA20  8b ce                mov  ecx, esi
00B9AA22  b3 01                mov  bl, 1
00B9AA24  ff d2                call edx
00B9AA26  84 c0                test al, al
00B9AA28  75 11                jne  0xB9AA3B
00B9AA2A  e8 a1 8b ca ff       call 0x8435D0
00B9AA2F  c7 86 6c 15 00 00 e7 02 00 00  mov [esi+0x156C], 0x2E7
00B9AA39  32 db                xor  bl, bl
00B9AA3B  68 ff 13 00 00       push 0x13FF
00B9AA40  8d 85 d9 d5 ff ff    lea  eax, [ebp-0x2A27]
00B9AA46  6a 00                push 0
00B9AA48  50                   push eax
00B9AA49  c6 85 d8 d5 ff ff 00 mov  byte [ebp-0x2A28], 0
00B9AA50  e8 8b 83 0a 00       call 0xC42DE0
00B9AA55  83 c4 0c             add  esp, 0xC
00B9AA58  84 db                test bl, bl
00B9AA5A  0f 84 92 03 00 00    je   0xB9ADF2
00B9AA60  e8 1b 89 0d 00       call 0xC73380
00B9AA65  68 00 14 00 00       push 0x1400
00B9AA6A  89 86 74 21 00 00    mov  [esi+0x2174], eax
00B9AA70  8d 86 6c 01 00 00    lea  eax, [esi+0x16C]
00B9AA76  6a 00                push 0
00B9AA78  50                   push eax
00B9AA79  e8 62 83 0a 00       call 0xC42DE0
00B9AA7E  83 c4 0c             add  esp, 0xC
00B9AA81  68 00 14 00 00       push 0x1400
00B9AA86  8d 8d d8 d5 ff ff    lea  ecx, [ebp-0x2A28]
00B9AA8C  51                   push ecx
00B9AA8D  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AA93  e8 98 97 02 00       call 0xBC4230
00B9AA98  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AA9E  c7 45 fc 00 00 00 00 mov  [ebp-4], 0
00B9AAA5  e8 96 9a 02 00       call 0xBC4540
00B9AAAA  84 c0                test al, al
00B9AAAC  74 74                je   0xB9AB22
00B9AAAE  8b 46 14             mov  eax, [esi+0x14]
00B9AAB1  6a 01                push 1
00B9AAB3  99                   cdq
00B9AAB4  52                   push edx
00B9AAB5  50                   push eax
00B9AAB6  68 28 a2 d5 00       push 0xD5A228        ; "auth_task"
00B9AABB  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AAC1  e8 ea a0 02 00       call 0xBC4BB0
00B9AAC6  84 c0                test al, al
00B9AAC8  74 58                je   0xB9AB22
00B9AACA  8b 96 74 21 00 00    mov  edx, [esi+0x2174]
00B9AAD0  6a 01                push 1
00B9AAD2  6a 00                push 0
00B9AAD4  52                   push edx
00B9AAD5  68 14 a1 d5 00       push 0xD5A114        ; "iv_seed"
00B9AADA  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AAE0  e8 cb a0 02 00       call 0xBC4BB0
00B9AAE5  84 c0                test al, al
00B9AAE7  74 39                je   0xB9AB22
00B9AAE9  8b 46 10             mov  eax, [esi+0x10]
00B9AAEC  6a 01                push 1
00B9AAEE  6a 00                push 0
00B9AAF0  50                   push eax
00B9AAF1  68 c0 7a db 00       push 0xDB7AC0        ; "title_id"
00B9AAF6  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AAFC  e8 af a0 02 00       call 0xBC4BB0
00B9AB01  84 c0                test al, al
00B9AB03  74 1d                je   0xB9AB22
00B9AB05  68 3c a3 d5 00       push 0xD5A33C
00B9AB0A  68 3c 38 cc 00       push 0xCC383C        ; "identity"
00B9AB0F  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AB15  e8 b6 9d 02 00       call 0xBC48D0
00B9AB1A  84 c0                test al, al
00B9AB1C  74 04                je   0xB9AB22
00B9AB1E  b3 01                mov  bl, 1
00B9AB20  eb 02                jmp  0xB9AB24
00B9AB22  32 db                xor  bl, bl
00B9AB24  68 ff 13 00 00       push 0x13FF
00B9AB29  8d 8d d9 e9 ff ff    lea  ecx, [ebp-0x1627]
00B9AB2F  6a 00                push 0
00B9AB31  51                   push ecx
00B9AB32  c6 85 d8 e9 ff ff 00 mov  byte [ebp-0x1628], 0
00B9AB39  e8 a2 82 0a 00       call 0xC42DE0
00B9AB3E  83 c4 0c             add  esp, 0xC
00B9AB41  68 00 14 00 00       push 0x1400
00B9AB46  8d 95 d8 e9 ff ff    lea  edx, [ebp-0x1628]
00B9AB4C  52                   push edx
00B9AB4D  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9AB53  e8 d8 96 02 00       call 0xBC4230
00B9AB58  c6 45 fc 01          mov  byte [ebp-4], 1
00B9AB5C  84 db                test bl, bl
00B9AB5E  74 45                je   0xB9ABA5
00B9AB60  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9AB66  e8 d5 99 02 00       call 0xBC4540
00B9AB6B  84 c0                test al, al
00B9AB6D  74 36                je   0xB9ABA5
00B9AB6F  8b 06                mov  eax, [esi]
00B9AB71  8b 50 28             mov  edx, [eax+0x28]
00B9AB74  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9AB7A  51                   push ecx
00B9AB7B  8b ce                mov  ecx, esi
00B9AB7D  ff d2                call edx
00B9AB7F  84 c0                test al, al
00B9AB81  74 22                je   0xB9ABA5
00B9AB83  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9AB89  e8 32 97 02 00       call 0xBC42C0
00B9AB8E  84 c0                test al, al
00B9AB90  74 13                je   0xB9ABA5
00B9AB92  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9AB98  e8 d3 96 02 00       call 0xBC4270
00B9AB9D  84 c0                test al, al
00B9AB9F  74 04                je   0xB9ABA5
00B9ABA1  b3 01                mov  bl, 1
00B9ABA3  eb 02                jmp  0xB9ABA7
00B9ABA5  32 db                xor  bl, bl
00B9ABA7  8d 8d c8 fe ff ff    lea  ecx, [ebp-0x138]
00B9ABAD  c6 45 fc 00          mov  byte [ebp-4], 0
00B9ABB1  e8 aa 96 02 00       call 0xBC4260
00B9ABB6  84 db                test bl, bl
00B9ABB8  74 3d                je   0xB9ABF7
00B9ABBA  8d 85 d8 e9 ff ff    lea  eax, [ebp-0x1628]
00B9ABC0  50                   push eax
00B9ABC1  68 ec 9a d5 00       push 0xD59AEC        ; "extra_data"
00B9ABC6  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9ABCC  e8 ff 9c 02 00       call 0xBC48D0
00B9ABD1  84 c0                test al, al
00B9ABD3  74 22                je   0xB9ABF7
00B9ABD5  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9ABDB  e8 e0 96 02 00       call 0xBC42C0
00B9ABE0  84 c0                test al, al
00B9ABE2  74 13                je   0xB9ABF7
00B9ABE4  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9ABEA  e8 81 96 02 00       call 0xBC4270
00B9ABEF  84 c0                test al, al
00B9ABF1  74 04                je   0xB9ABF7
00B9ABF3  b3 01                mov  bl, 1
00B9ABF5  eb 0c                jmp  0xB9AC03
00B9ABF7  32 db                xor  bl, bl
00B9ABF9  c7 86 6c 15 00 00 de 02 00 00  mov [esi+0x156C], 0x2DE
00B9AC03  8d 8d c8 d4 ff ff    lea  ecx, [ebp-0x2B38]
00B9AC09  c7 45 fc ff ff ff ff mov  [ebp-4], -1
00B9AC10  e8 4b 96 02 00       call 0xBC4260
00B9AC15  84 db                test bl, bl
00B9AC17  0f 84 d5 01 00 00    je   0xB9ADF2
00B9AC1D  8d 85 d8 d5 ff ff    lea  eax, [ebp-0x2A28]
00B9AC23  8d 50 01             lea  edx, [eax+1]
00B9AC26  8a 08                mov  cl, [eax]
00B9AC28  40                   inc  eax
00B9AC29  84 c9                test cl, cl
00B9AC2B  75 f9                jne  0xB9AC26
00B9AC2D  2b c2                sub  eax, edx
00B9AC2F  50                   push eax
00B9AC30  8b ce                mov  ecx, esi
00B9AC32  e8 09 f8 ff ff       call 0xB9A440
00B9AC37  8b 8e 68 01 00 00    mov  ecx, [esi+0x168]
00B9AC3D  8b 86 64 01 00 00    mov  eax, [esi+0x164]
00B9AC43  51                   push ecx
00B9AC44  8d 95 d8 d5 ff ff    lea  edx, [ebp-0x2A28]
00B9AC4A  52                   push edx
00B9AC4B  50                   push eax
00B9AC4C  e8 9f 7b 0a 00       call 0xC427F0
00B9AC51  68 ff 01 00 00       push 0x1FF
00B9AC56  8d 8d d9 fd ff ff    lea  ecx, [ebp-0x227]
00B9AC5C  6a 00                push 0
00B9AC5E  51                   push ecx
00B9AC5F  c6 85 d8 fd ff ff 00 mov  byte [ebp-0x228], 0
00B9AC66  e8 75 81 0a 00       call 0xC42DE0
00B9AC6B  0f b7 96 70 21 00 00 movzx edx, word [esi+0x2170]
00B9AC72  8b 85 c4 d4 ff ff    mov  eax, [ebp-0x2B3C]
00B9AC78  83 c4 18             add  esp, 0x18
00B9AC7B  52                   push edx
00B9AC7C  50                   push eax
00B9AC7D  8d 8e 70 15 00 00    lea  ecx, [esi+0x1570]
00B9AC83  e8 28 f2 00 00       call 0xBA9EB0
00B9AC88  50                   push eax
00B9AC89  68 cc a2 d5 00       push 0xD5A2CC        ; "https://%s:%d/auth/"
00B9AC8E  8d 8d d8 fd ff ff    lea  ecx, [ebp-0x228]
00B9AC94  68 00 02 00 00       push 0x200
00B9AC99  51                   push ecx
00B9AC9A  e8 d1 06 be ff       call 0x77B370
00B9AC9F  8d 95 d8 fd ff ff    lea  edx, [ebp-0x228]
00B9ACA5  52                   push edx
00B9ACA6  e8 25 89 ca ff       call 0x8435D0
00B9ACAB  83 c4 18             add  esp, 0x18
00B9ACAE  e8 fd 84 aa ff       call 0x6431B0
00B9ACB3  8b c8                mov  ecx, eax
00B9ACB5  e8 26 c5 fd ff       call 0xB771E0
00B9ACBA  8b f8                mov  edi, eax
00B9ACBC  8b 06                mov  eax, [esi]
00B9ACBE  6a 01                push 1
00B9ACC0  8d 8d b8 d4 ff ff    lea  ecx, [ebp-0x2B48]
00B9ACC6  8b da                mov  ebx, edx
00B9ACC8  8b 50 2c             mov  edx, [eax+0x2C]
00B9ACCB  51                   push ecx
00B9ACCC  8b ce                mov  ecx, esi
00B9ACCE  ff d2                call edx
00B9ACD0  53                   push ebx
00B9ACD1  57                   push edi
00B9ACD2  68 7c 9e d5 00       push 0xD59E7C        ; "%I64u"
00B9ACD7  89 85 c0 d4 ff ff    mov  [ebp-0x2B40], eax
00B9ACDD  8d 45 d8             lea  eax, [ebp-0x28]
00B9ACE0  6a 18                push 0x18
00B9ACE2  50                   push eax
00B9ACE3  e8 88 06 be ff       call 0x77B370
00B9ACE8  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9ACEE  8b 11                mov  edx, [ecx]
00B9ACF0  8b 52 04             mov  edx, [edx+4]
00B9ACF3  83 c4 14             add  esp, 0x14
00B9ACF6  68 98 3a 00 00       push 0x3A98
00B9ACFB  8d 85 d8 fd ff ff    lea  eax, [ebp-0x228]
00B9AD01  50                   push eax
00B9AD02  6a 03                push 3
00B9AD04  ff d2                call edx
00B9AD06  84 c0                test al, al
00B9AD08  74 39                je   0xB9AD43
00B9AD0A  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9AD10  8b 01                mov  eax, [ecx]
00B9AD12  8b 50 0c             mov  edx, [eax+0xC]
00B9AD15  68 e4 a1 d5 00       push 0xD5A1E4        ; "application/json"
00B9AD1A  68 d4 a1 d5 00       push 0xD5A1D4        ; "Content-Type"
00B9AD1F  ff d2                call edx
00B9AD21  84 c0                test al, al
00B9AD23  74 1e                je   0xB9AD43
00B9AD25  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9AD2B  8b 01                mov  eax, [ecx]
00B9AD2D  8b 40 0c             mov  eax, [eax+0xC]
00B9AD30  8d 55 d8             lea  edx, [ebp-0x28]
00B9AD33  52                   push edx
00B9AD34  68 6c 9e d5 00       push 0xD59E6C        ; "X-TransactionID"
00B9AD39  ff d0                call eax
00B9AD3B  84 c0                test al, al
00B9AD3D  74 04                je   0xB9AD43
00B9AD3F  b0 01                mov  al, 1
00B9AD41  eb 02                jmp  0xB9AD45
00B9AD43  32 c0                xor  al, al
00B9AD45  8b 9d c0 d4 ff ff    mov  ebx, [ebp-0x2B40]
00B9AD4B  33 ff                xor  edi, edi
00B9AD4D  85 db                test ebx, ebx
00B9AD4F  74 30                je   0xB9AD81
00B9AD51  84 c0                test al, al
00B9AD53  74 25                je   0xB9AD7A
00B9AD55  8b 84 fd bc d4 ff ff mov  eax, [ebp+edi*8-0x2B44]
00B9AD5C  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9AD62  8b 11                mov  edx, [ecx]
00B9AD64  8b 52 0c             mov  edx, [edx+0xC]
00B9AD67  50                   push eax
00B9AD68  8b 84 fd b8 d4 ff ff mov  eax, [ebp+edi*8-0x2B48]
00B9AD6F  50                   push eax
00B9AD70  ff d2                call edx
00B9AD72  84 c0                test al, al
00B9AD74  74 04                je   0xB9AD7A
00B9AD76  b0 01                mov  al, 1
00B9AD78  eb 02                jmp  0xB9AD7C
00B9AD7A  32 c0                xor  al, al
00B9AD7C  47                   inc  edi
00B9AD7D  3b fb                cmp  edi, ebx
00B9AD7F  72 d0                jb   0xB9AD51
00B9AD81  84 c0                test al, al
00B9AD83  74 4e                je   0xB9ADD3
00B9AD85  8b 86 68 01 00 00    mov  eax, [esi+0x168]
00B9AD8B  8b 8e 64 01 00 00    mov  ecx, [esi+0x164]
00B9AD91  50                   push eax
00B9AD92  51                   push ecx
00B9AD93  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9AD99  e8 32 ba 0d 00       call 0xC767D0
00B9AD9E  84 c0                test al, al
00B9ADA0  74 31                je   0xB9ADD3
00B9ADA2  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9ADA8  68 00 14 00 00       push 0x1400
00B9ADAD  8d 86 6c 01 00 00    lea  eax, [esi+0x16C]
00B9ADB3  50                   push eax
00B9ADB4  e8 27 ba 0d 00       call 0xC767E0
00B9ADB9  84 c0                test al, al
00B9ADBB  74 16                je   0xB9ADD3
00B9ADBD  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9ADC3  8b 11                mov  edx, [ecx]
00B9ADC5  8b 42 28             mov  eax, [edx+0x28]
00B9ADC8  ff d0                call eax
00B9ADCA  83 f8 03             cmp  eax, 3
00B9ADCD  75 04                jne  0xB9ADD3
00B9ADCF  b3 01                mov  bl, 1
00B9ADD1  eb 02                jmp  0xB9ADD5
00B9ADD3  32 db                xor  bl, bl
00B9ADD5  8b 8e 60 01 00 00    mov  ecx, [esi+0x160]
00B9ADDB  8b 11                mov  edx, [ecx]
00B9ADDD  8b 42 2c             mov  eax, [edx+0x2C]
00B9ADE0  ff d0                call eax
00B9ADE2  84 db                test bl, bl
00B9ADE4  74 0c                je   0xB9ADF2
00B9ADE6  83 f8 03             cmp  eax, 3
00B9ADE9  75 25                jne  0xB9AE10
00B9ADEB  c7 46 20 01 00 00 00 mov  dword [esi+0x20], 1
00B9ADF2  8a c3                mov  al, bl
00B9ADF4  8b 4d f4             mov  ecx, [ebp-0xC]
00B9ADF7  64 89 0d 00 00 00 00 mov  fs:[0], ecx
00B9ADFE  59                   pop  ecx
00B9ADFF  5f                   pop  edi
00B9AE00  5e                   pop  esi
00B9AE01  5b                   pop  ebx
00B9AE02  8b 4d f0             mov  ecx, [ebp-0x10]
00B9AE05  33 cd                xor  ecx, ebp
00B9AE07  e8 03 14 0a 00       call 0xC3C20F
00B9AE0C  8b e5                mov  esp, ebp
00B9AE0E  5d                   pop  ebp
00B9AE0F  c3                   ret
```
