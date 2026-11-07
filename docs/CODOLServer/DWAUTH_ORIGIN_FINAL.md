# 「无法连接大厅服务」最上游溯源（含服务器地址来源）— 定论版

日期：2026-09-25
方法：运行期解密镜像静态反汇编（capstone, x86-32）+ pefile 节区核对
主证据镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
（加载基址 `0x400000`，大小 `0xA65000`；**换算：offset = VA - 0x400000**）

---

## 0. 一句话结论

**客户端要连哪台大厅服务器、哪个端口，不是算出来的，是「读文件」读出来的。**
文件名是 **`dwauth.ini`**，它必须放在**游戏进程的当前工作目录**（= exe 同级目录）。
本机（以及全部备份/沙箱）**没有任何 `dwauth.ini`**，所以：

```
dwauth.ini 缺失
  → 大厅主机串 [0x81A76A8] 为空
  → 大厅 DNS 步骤解析空主机失败
  → DW_DNS_ERROR
  → 状态机卡在 state=1
  → 弹窗 [100] 无法连接大厅服务!
```

这不是「服务器没写」，而是**客户端连"往哪里连"都没拿到**。写服务器之前，先把这个文件给出来。

---

## 1. 磁盘代码段是加密的（重要方法论纠正）

`.tp3` 节区在磁盘上是**密文**，运行期才解密。同一地址对比：

| VA | 磁盘 exe | 运行期镜像 |
|---|---|---|
| `0x4FD287` | `cc 89 00 00 50 8d 8f 9c ...` | `e8 c4 b3 30 00 6a 18 e8 ...` |
| `0x4FCEE0` | `43 03 21 d0 7f 7a 00 15 ...` | `55 8b ec 81 ec 34 04 00 00 ...` |
| `0x808650` | `f4 53 57 8b ce e8 8a 73 ...` | `55 8b ec 83 ec 08 53 56 ...` |

**⇒ 任何"反汇编磁盘 exe 代码段"的结论都不成立**，必须以运行期镜像为准。
（本报告全部代码结论均来自运行期镜像。）

---

## 2. 调用链：从 CRT 一直到大厅初始化

```
__tmainCRTStartup (call@0xC42783)
  └─ WinMain = 0x77EE40(lpCmdLine = [ebp+0x10])
       ├─ memcpy(0x81A76E8, lpCmdLine, 0x3FF)        ; 0x77EF08
       │     └ 0x81A76E8 = 命令行副本（4 字节尾部清零 @0x81A7AE7）
       ├─ fopen("dwauth.ini","r") / 逐字段 sscanf     ; 0x77EF57..0x77EFE9
       ├─ fopen("stun.ini","r")                       ; 0x77F056..0x77F08C
       └─ fopen("buildconfig.ini","r")                ; 0x77F08E..0x77F0F8
  ...
  主循环 → 0x4FD9B0
       └─ Com_Init = 0x4FCEE0(ecx = 0x81A76E8)
            ├─ memcpy(0x33E7060, 0x81A76E8, 0x3FF)   ; 0x4FCF03
            └─ 0x4FD287 ──► 0x808650                 ; 顺序指令，无条件
                 └─ 0x7E98F0   ★ 大厅总初始化
                      └─ 0x7E99F1  mov byte [0x849B61F], 1   ← dwLobby 总闸
                 └─ 注册 "ied-tqos.qq.com" (0xDD98A0)
                 └─ Live_Init (0xDBD820)
```

### 2.1 先纠正一个之前的错误推断

之前交接里写「`0x4FD287` 的触发条件 / 谁调用多人初始化」——
**`0x4FD287` 不是函数入口，也没有任何 call 指向它**（全镜像扫描 `call 0x4FD287` 命中数 = 0）。
它是 `0x4FCEE0` 内部的**顺序指令**：

```asm
004FD282  e899e21600     call 0x66B520
004FD287  e8c4b33000     call 0x808650     ; ← 直接顺序执行，前面没有分支跳过它
004FD28C  6a18           push 0x18
```

而 `0x4FCEE0` 的唯一调用点是 `0x4FDA03`（在 `0x4FD9B0` 内），
`0x4FD9B0` 的唯一调用点是 `0x77F8B3`（主模块）。

### 2.2 `0x7E98F0` 里总闸是无条件写的

```asm
007E99E4  833dccb5490800     cmp dword ptr [0x849B5CC], 0
007E99EB  8b35c884ca00       mov esi, dword ptr [0xCA84C8]
007E99F1  c6051fb6490801     mov byte ptr [0x849B61F], 1   ; ← 无任何条件保护
```

**⇒ 只要 `0x808650` 执行过，`[0x849B61F]` 必为 1。**
运行期实测长期为 0，说明这条在线初始化链在启动时根本没有被走到
（或走到之前就失败退出了）。这就是"没有任何大厅流量"的原因。

---

## 3. ★ 服务器地址的真正来源：`dwauth.ini`

`0x77EE40`（WinMain）里写了 7 个字段，全部来自 **`dwauth.ini`**，
按行/按空白顺序 `sscanf` 成：

| 顺序 | 格式串 | 目标全局 | 语义（证据） |
|---|---|---|---|
| 1 | `%59s\n` | `0x81A7F34` | 第二个待解析主机名（DNS 步骤会同时解析它） |
| 2 | `%hu\n` | `0x81A9780` | uint16，用于大厅连接建立（`0x7F38B3 movzx`） |
| 3 | `%59s\n` | **`0x81A76A8`** | **★ 大厅主机（HOST）** |
| 4 | `%hu\n` | **`0x81A9EC4`** | **★ 大厅端口（PORT）** |
| 5 | `%x\n` | `0x81A9EB8` | 32 位 hex（0x7F2BAA 取用） |
| 6 | `%x\n` | `0x81A56A4` | 32 位 hex |
| 7 | `%x\n` | `0x81A76E4` | 32 位 hex |

代码位置：
```asm
0077EF64  68 347f1a08    push 0x81A7F34   ; 字段1 目标
0077EF69  68 a8bddd00    push 0x00DDBDA8  ; "%59s\n"
0077EF6E  56             push esi         ; FILE*
0077EF6F  e8 de304c00    call 0x00C42052  ; = sscanf/fscanf 族
...
0077EF8A  68 a8761a08    push 0x81A76A8   ; 字段3 目标 = HOST
0077EF9D  68 c49e1a08    push 0x81A9EC4   ; 字段4 目标 = PORT
```

### 3.1 主机/端口在哪里被真正使用

**DNS 步骤（state 1）**，`0x7F34E0`：
```asm
007F3522  8d4dfc         lea ecx, [ebp-4]
007F3525  e8c6b83b00     call 0xBAEDF0        ; 取解析器上下文
007F352A  8b00           mov eax, [eax]
007F352C  8b0d70ba4a08   mov ecx, [0x84ABA70] ; 解析器对象 A
007F3532  50             push eax
007F3533  68 a8761a08    push 0x81A76A8       ; ★ HOST
007F3538  e873b53b00     call 0xBAEAB0        ; 注册/解析
007F353D  8ad8           mov bl, al           ; 成败在此
...
007F3589  68 347f1a08    push 0x81A7F34       ; ★ 字段1，第二个主机
007F358E  e81db53b00     call 0xBAEAB0
```
**两个主机都必须解析成功**，否则 `bl=0` → `[0x84ABA78]=0` → 状态名 = `DW_DNS_ERROR` → 弹窗 100。

**建连步骤（state 2）**，`0x7F2B90`：
```asm
007F2BA8  8b1db89e1a08   mov ebx, [0x81A9EB8]      ; 字段5
007F2BAF  0fb73dc49e1a08 movzx edi, word [0x81A9EC4] ; ★ PORT
007F2BDC  57             push edi                  ; port
007F2BDD  68 a8761a08    push 0x81A76A8            ; ★ HOST
007F2BE2  53             push ebx
007F2BE5  e8965f3900     call 0xB88B80             ; 建连（TLS 通道）
```

**HTTPS URL 构造**，`0x7F306C`：
```asm
007F306C  68 a8761a08    push 0x81A76A8   ; HOST
007F3071  68 e409de00    push 0x00DE09E4  ; "https://%s/"
007F3076  e80519f8ff     call 0x774980    ; sprintf
```

### 3.2 关键旁证：客户端自带 `cacert.pem`，连接是 TLS

```asm
007F2C33  68 a49cdc00    push 0x00DC9CA4   ; "cacert.pem"
007F2C38  8bc8           mov ecx, eax
007F2C3A  e8 c1743a00    call 0x00B9A100   ; 载入 CA 到连接对象
```

exe 内还含（同镜像字符串）：
```
0x00D5A2CC  https://%s:%d/auth/      ← ★ 大厅鉴权接口路径
0x00DC71CC  https://%s:%u/tlog
0x00D3682C  TLS change cipher / handshake / alert
0x00D39E30  X.509 part of OpenSSL 0.9.8p 16 Nov 2010
0x00D356B0  Peer certificate cannot be authenticated with given CA certificates
```

**⇒ 大厅服务器必须提供 HTTPS（TLS），路径 `/auth/`。**
客户端用 exe 同目录的 `cacert.pem` 做校验，所以本地测试要么
(a) 把自签 CA 追加进 `cacert.pem`，要么 (b) 让它指向一个证书链可信的终点。
**不需要动系统证书库、不需要动网络设置。**

---

## 4. 其它由 WinMain 读取的配置（一并列出）

| 文件 | 读取点 | 写入全局 | 说明 |
|---|---|---|---|
| `stun.ini` | `0x77F056` | `0x81A9C50`（步长 `0x3C` 的数组，至 `0x81A9EA8`） | STUN 主机列表 |
| `buildconfig.ini` | `0x77F08E` | `0x81A7F04` / `0x81A9770` / `0x81A7EF4` / `0x81A9C38` | 版本/分支 |

`stun.ini`（现存，69 字节，exe 同级）内容：
```
stun1-tub.codol.qq.com
stun2-tub.codol.qq.com
stun3-tub.codol.qq.com
```

`buildconfig.ini` 全局搜索**同样不存在**（与 `dwauth.ini` 一样缺失）。

`dwauth.ini` 全盘（`COD OL\`、`run_codol_001\sandbox*`、`backups\`、所有 `工具\*`）搜索：
**命中 0 个**。

---

## 5. 立刻可执行的实验（下一步）

在 **游戏工作目录**（固化启动器 = `run_codol_001\sandbox`；正式安装 = `COD OL\`）
创建 `dwauth.ini`，让客户端把大厅指向本机：

```
127.0.0.1          ; 字段1：第二个待解析主机（用回环，免 DNS）
0                  ; 字段2：uint16
127.0.0.1          ; 字段3：★ HOST
8443               ; 字段4：★ PORT（监听端口，可改）
0                  ; 字段5：hex
0                  ; 字段6：hex
0                  ; 字段7：hex
```

`127.0.0.1` 是字面量，**不触发 DNS、不改 hosts、不改网卡**，符合"不碰系统网络"的硬约束。

配套需要：一个监听 `127.0.0.1:8443` 的 **TLS 服务器**，
把自签 CA 追加进 exe 同目录的 `cacert.pem`（记得先备份原文件）。

验证判据：
1. 运行期 `[0x849B61F] == 1`（总闸开）
2. `[0x84ABA50]`（dw 状态）从 1 走到 3（`DW_LOBBY_CONNECTED`）
3. 我们的监听端收到 TCP/TLS 连接（第一条 ClientHello 就能确认）

---

## 6. 尚未确定 / 需要动态验证的点（诚实标注）

1. **字段 2/5/6/7 的准确语义**：只确认它们是 uint16 / 三个 hex32，
   在 `0x7F2BAA`、`0x7F38B3` 被取用，但**具体业务含义未定**（可能是 appid / 版本 / 会话类型）。
   给 0 是否会被服务器侧校验，需实跑才知道。
2. **`dwauth.ini` 原始取值**：现网原文件已不存在，无法直接还原原始 IP/端口，
   只能确认"格式是这 7 行"。原始大厅域名/IP 需要从别处（老启动器/备份包）补。
3. **总闸为何为 0**：静态上 `0x808650` 无条件执行，但运行期实测总闸=0。
   二者矛盾，**必须动态验证**（见 `_mainline` 下的门控探针）。
   在未验证前，不排除"启动参数/前置条件导致 `0x4FD9B0` 未被执行"。
4. **`dwauth.ini` 是否按月/按启动器生成**：TCLS/WeGame 启动链可能负责写它。

---

## 7. 证据索引

| 主题 | 位置 |
|---|---|
| 运行期明文镜像 | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` |
| 弹窗完整链 | `CODOLServer\POPUP_ORIGIN_FINAL.md` |
| WinMain / dwauth 解析 | 本文件 §2、§3（VA `0x77EE40`） |
| 大厅状态机 | VA `0x7F25B0/0x7F2580/0x7F2600/0x7F26C0/0x7F34E0/0x7F3600/0x7F3800` |
| 建连/TLS | VA `0x7F2B90`、`0x7F306C`、`0xB9A100` |
| 抓包数值报告 | `CODOLServer\_subagents\pcap_report.md` |
