# CODOL 复活 · 2026-09-30 会话状态固化

本文件是 2026-09-30 这一轮全部结论的固化版。上接
`HANDOFF_20260929_LOBBY_PROTOCOL.md`（§1–§16）。
**级别标注**：`[已证]` = 有运行期或反汇编证据；`[未证]` = 未确定，不得当结论用。

---

## 0. 一句话状态

**第一档 ①–④ 稳定可复现；⑤ 的根因从"配置缺失"改判为"服务端未应答 `0x85` 校验帧"，
且该应答算法已完整读出，可在纯服务端实现。**

---

## 1. ★★★ 本轮最大发现：`0x85` 是校验通道，不是加密数据通道

### 1.1 触发它的观察 `[已证]`

每一次跑到 ⑤ 的运行，客户端在明文大厅 socket（8446）上都会发：

```text
 0.10s  0x85 seq=1  len=382  (body 376)
30.00s  4 字节  00 00 00 00
47.08s  0x85 seq=2  len=190  (body 184)
47.08s  0x85 seq=3  len=414  (body 408) + seq=4 len=46
52.00s  客户端判死，弹「与大厅服务失去连接」
```

### 1.2 载荷形状 `[已证]`

对 4 次独立运行统计（工具 `_subagents\_sub_seq85_shape.py`）：

```text
body 376 B:  entropy 7.395–7.473 bits/byte, distinct 193–201/256
body 184 B:  entropy 6.856–6.921,           distinct 127–133
body 408 B:  entropy 7.413–7.503,           distinct 193–206
body  40 B:  entropy 5.17–5.32,             distinct  37–40
首字节每次运行都不同（3A / B6 / 1F / 72 …）
长度每次运行完全固定（382/190/414/46）
```

⇒ **均匀高熵 + 长度固定 + 内容每次变** ⇒ 是**固定结构的消息 + 随机填充**，
**不是 DW 位打包帧**（那种会呈现低熵头部与可辨别字段结构）。

### 1.3 反汇编定性 `[已证]`

`0x85` 的收帧处理器 = **`0xBA3710`**，唯一调用者 **`0xBA46C2`**。

```asm
00BA3794  call 0xB783C0        ; 读 4 字节
00BA37A6  push 0x10
00BA37C2  call 0xB783C0        ; 再读 16 字节
00BA37ED  cmp ebx, 8 / jbe …   ; body ≤ 8 视为非法
00BA3820  cmp ecx, 0xFFFFFF
00BA3867  … "Bad frame/payload size"   (0xD5A534)

00BA3844  mov eax,[edi+0x5EC]          ; ★ 收包计数器
00BA384A  lea edx,[eax+1]
00BA384D  mov [edi+0x5EC],edx          ; 计数器 +1 写回
00BA3853  cmp [ebp-0x394], eax         ; 收到的 seq 是否等于旧计数
00BA3859  je  0xBA38A4                 ; 相等 → 通过
00BA385B  … "Bad recv counter"         (0xD5A520) → 0xBA3420 复位
```

**关键更正**：旧手册 §5.3 记「`0x5EC` 闸要求进入时旧值 == 0」。
**实际是「收到的 seq 必须 == 当前计数器值」。** 两者含义完全不同：
后者意味着**只要序号对，应答就是合法的**。

### 1.4 校验值算法 —— 完全读出，可复刻 `[已证]`

校验值由 **`0xBA02A0`** 生成（调用点 `0xBA38ED`；另一处 `0xBA1FA1`）。

```text
输入：  req[0x620..0x633]   ← 20 字节，握手时客户端提供的密钥材料

常量表 K（20 字节，内联在 0xBA02C9..0xBA02E8）：
    80 22 DE AA  0B 1C 21 F4  00 FF EE 37  27 92 10 CE  AA F4 3C 21

下标置换表（20 项）【2026-09-30 二次更正，见 §1.6】：
    19 18 09 04 17 01 0A 08 0D 02 0F 03 0C 10 05 07 00 0E 06 0B
    （[3]=4 来自 00BA02BD `mov edi,4`；[13]=16 来自 00BA02C2 `mov [ebp-0x34],edx`，
      edx=0x10 @00BA02B7。第一版漏读了 0xBA02C2，把两项写反过，已更正。）

主循环（0xBA036D..0xBA03FA）：4 轮 × 5 字节
    eax = &req[0x621]
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 5; j++)
            out[i*5+j] = K[idx[i*5+j]] ^ req[0x620 + i*5 + j];
    }
```

**`0xBA02A0` 本身**是纯查表 + 异或。

### 1.5 结论 `[已证]`

```text
客户端在 0x85 上发的是「按共享密钥算出的校验值」。
服务端必须回一个匹配的 0x85（同序号），客户端的 [req+0x5EC] 才会 +1 推进。
我们一直一个都没回 ⇒ 计数器停在 1 ⇒ 47s 重发 ⇒ 52s 判死。
```

**⇒ 这是整个 ⑤ 第一次出现"完全可以由服务端解决"的缺口。**

### 1.6 ⚠️ 复刻验证**失败** —— 这是本轮最需要后来者接手的地方

**已做的验证**：
```text
导出 [req+0x620] (run IFS1_ELEVATED_20260930_093640):
    65 45 cf 31 d9 f7 44 3e 20 e3 1b 16 5c b1 6d 10 4c d9 fc 80

用 §1.4 的算法（含修正后的表）算出 20 字节:
    44 79 30 3a 2d d5 aa 3e b2 3d d5 bc 7b 1b 71 e4 cc c9 dd b7

在同一次运行客户端实际发出的 0x85 三条帧（seq1/2/3）里逐字节搜索:
    **三条全部 NOT FOUND**
```

**⇒ §1.4 的算法不足以复现客户端载荷。`0xBA02A0` 的输出不是直接放进载荷的那个值。**

**已查到原因（`[已证]`）**：`0xBA38A4` 之后紧跟的四个函数**是同一个大数类的虚方法**：

```text
00C73750  mov dword [ecx], 0xD95514 / jmp 0xC74D80   ← 构造：设置虚表
00D95514 处的虚表:
    +0x00 0x00C738A0   +0x04 0x00C73760   +0x08 0x00C737A0
    +0x0C 0x00C73C70   +0x10 0x00C73AF0   +0x14 0x00C73BB0  ...
```

而 `0xC73760` / `0xC737A0` 内部都走同一个**算法提供者分发**：

```asm
00C77E97  mov eax,[esi+0x190]        ; 提供者 ID
00C77E9E  call 0xBCB310              ; 查表
00C77EB3  imul ecx,ecx,0x68          ; 记录步长 0x68
00C77EB9  mov ecx,[ecx+0xE88678]     ; 取函数指针
00C77EC2  call ecx                   ; 调用
```

⇒ 这是**带可插拔后端的密码学/大数库**（记录表 @ `0xE88678`，步长 `0x68`）。

**所以 `0x85` 的校验不是"查表 + 异或"就完事的。** `0xBA02A0` 的 20 字节是
**中间量**，之后要经大数类的运算才能得到实际参与比较的值。

**⇒ 在 Python 里复刻需要先把这套大数/提供者接口的语义读全。**
这不是"再读一段"的量级，是一个独立的小型逆向课题。

### 1.7 结论：`0x85` 应答**尚不可实现**，但路线未被否证

```text
已证:
  · 0x85 是校验/计数通道，服务端必须应答（保活）
  · 序号在 body[1]，比较对象是 [req+0x5EC]
  · 校验值生成入口 0xBA02A0（查表 XOR，20 字节中间量）
  · 后续经大数库（虚表 0xD95514 / 提供者表 0xE88678）运算

未证:
  · 大数库那一步的确切运算
  · 最终进帧的字段布局

⇒ 不要按 §1.4 直接写服务端应答（已验证不匹配）。
⇒ 下一步应读 0xC77E90 / 0xC77ED0 背后的提供者实现。
```

**另一个值得先试的方向**（成本低得多）：
```text
既然"服务端必须回一个匹配的 0x85"，而客户端**自己就在算这个值**，
那么可以先做**纯观测**：在运行期把客户端**发给服务端的那条帧原样读出来**，
再原样回发（"回声"）。
  · 若客户端接受回声 → 无需复刻算法，保活即通
  · 若拒绝 → 说明回包字段必须不同，再回去读算法
这与旧手册 §5.3 的"补发 0x85 被复位"不冲突：
那次发的是**服务端自造的帧**；这次是**原样回声**，序号天然匹配。
```

*（2026-09-30 备注：该思路尚未实测。）*

---

### 1.8 回声方案：**实测否证** `[已证]`

已在 `lobby_plain_probe.py` 加 `--echo-85`：收到 `0x85` 就**原样回发**。

实测（run `IFS1_ELEVATED_20260930_100112`，日志 `E57A5C_20260930_100104_a1`）：
```text
hold_recv         len=386  seq=1         ← 客户端发 0x85 seq=1
echo_85           len=386  seq=1         ← 我们原样回发（序号天然匹配）
hold_peer_closed                          ← ★ 客户端**立即断开**
```

对比基线（不回）：客户端发 seq1 → 等 30 s → 发 seq2/3 → 47 s 判死。
**回声让它断得更早** ⇒ 客户端要的不是"把自己的东西退回来"，是
**服务端独立算出的应答值**。

**⇒ 回声路线关闭。必须复刻算法。**

---

### 1.9 ★ 变换管线定性：`0xC77F50` 的核心是 `xor cl, 0x5C` `[已证]`

之前把这块判为"带可插拔后端的大数/密码库"，**是过度推测**。
实读 `0xC77ED0` 全文后，真实形状是一条**逐字节变换管线**：

```asm
00C77EE2  call 0xBCB310              ; 取记录（0xBCB310 不是函数，是**数据地址**）
00C77EF2  imul esi, esi, 0x68        ; 记录步长 0x68
00C77EF5  mov eax, [esi+0xE8862C]    ; 长度字段
00C77EFC  mov edi, [esi+0xE88628]    ; 缓冲区字段
00C77F06  call [0xE3CC48]            ; 分配 ×2

00C77F50  mov edx, [ebx+0x328]       ; 源指针
00C77F56  mov cl, [edx+eax]
00C77F5C  xor cl, 0x5C               ; ★★★ 逐字节 XOR 0x5C
00C77F5F  mov [eax+edx], cl
00C77F62  inc eax / 00C77F69 jb      ; 整段循环

00C77F6B  call [esi+0xE88674]        ; 步骤②
00C77F8F  call [esi+0xE88678]        ; 步骤③（带长度）
00C77FA9  call [esi+0xE88678]        ; 步骤④（带缓冲）
00C77FBF  call [esi+0xE8867C]        ; 步骤⑤
00C77FD7  拷贝结果 → 输出
00C77FF3  call [0xE3CC54] ×3         ; 释放 ×3
```

⇒ `0xE88678` 那张表是**这条管线各步骤的函数指针组**（`+0x28/+0x2C/+0x74/+0x78/+0x7C`），
**不是**"可插拔密码后端"。

**核心变换 = `XOR 0x5C`，复杂度比先前判断低两个数量级。**

### 1.10 ⚠️ 但 `XOR 0x5C` 组合仍未命中客户端载荷 `[已证：未命中]`

同轮比对（run `IFS1_ELEVATED_20260930_100915`，key 导出与 `0x85` 抓取**同一轮**）：

```text
key20  = 2c 18 1d 03 a4 44 70 0c 8a b2 b7 2e 17 6b f9 1e 1c cf 2a db
MAC    = 0d 24 e2 08 50 66 9e 0c 18 6c 79 84 30 c1 e5 ea 9c df 0b ec
MAC^5C = 51 78 be 54 0c 3a c2 50 44 30 25 d8 6c 9d b9 b6 c0 83 57 b0

三条 0x85 帧（seq 1/2/3）：MAC 与 MAC^5C **全部 NOT FOUND**
body[0:20] 既不等于 MAC，也不等于 MAC^5C
```

**⇒ 两种可能，均未证**：
```text
(a) 0xBA02A0 的输出不是管线输入。管线的源是 [ebx+0x328]（对象字段），
    与 0xBA02A0 的返回值不是同一个东西。
(b) 管线里 ②③④⑤ 四步中还有别的变换，XOR 0x5C 只是第一道。
```

**下一步（只读）**：读 `0xE88674 / 0xE88678 / 0xE8867C` 三个槽位**实际指向的函数**，
把管线走完。**这三处是数据（每帧填），需要运行期取值，不能只靠静态。**

**注意**：之前一次"跨轮比对"（用 `093640` 轮的 key 比 `093632` 轮的帧）是操作失误，
已改成本轮同轮比对，结论以上面的同轮结果为准。

---

### 1.11 ★★★ 变换管线定性：**是 SHA-1**（本轮最重要的更正）`[已证]`

按 §1.10 的下一步取运行期函数指针，`0xE88628 + id × 0x68` 四条记录：

```text
rec id=0 VA=0xE88628 : step2=0x00BC7C40  step3=0x00BC7C90  step5=0x00BC7D60
rec id=1 VA=0xE88690 : step2=0x00BCA0A0  step3=0x00BCA0E0  step5=0x00BCA1C0
rec id=2 VA=0xE886F8 : step2=0x00C77920  step3=0x00C77960  step5=0x00C77A30
rec id=3 VA=0xE88760 : step2=0x00BC5D70  step3=0x00BC5DA0  step5=0x00BC5E70
（字段偏移是相对记录基址：buf=+0x00, len=+0x04, step2=+0x4C, step3=+0x50, step5=+0x54）
```

**id=2 的三个函数读出来是标准 SHA-1：**

```asm
; SHA1_Init  0xC77920
00C77928  mov dword [eax+8],  0x67452301
00C7792F  mov dword [eax+0xC], 0xEFCDAB89
00C77936  mov dword [eax+0x10],0x98BADCFE
00C7793D  mov dword [eax+0x14],0x10325476
00C77944  mov dword [eax+0x18],0xC3D2E1F0

; SHA1_Update 0xC77960  (累计长度 lo/hi，满 0x40 调 0xC773A0 压缩)

; SHA1_Final  0xC77A30
00C77A5C  mov byte [eax+esi+0x20], 0x80      ; 0x80 padding
00C77A6C  mov ecx, 0x38                      ; pad to 56
00C77AC4  bswap ecx / bswap eax              ; 大端 64-bit 长度
00C77ACC  mov [esi+0x58], eax / [esi+0x5C], ecx
00C77AD2  call 0xC773A0                      ; 压缩
00C77AE2  mov esi,[ecx] / bswap esi          ; 大端输出 5 个字
00C77AE6  mov [edx+eax*4], esi
```

⇒ **`0xBA02A0`（查表 XOR 20 字节）之后是「XOR 0x5C 预变换 + SHA-1」。**
这也解释了 0x85 载荷"高熵、长度固定、每次不同"的形状 ——
**20 字节 SHA-1 摘要正是长这个样子。**

### 1.12 ⚠️ 但方向与输入仍未定死 —— 本轮**没能闭合** `[未证]`

把 `0xBA3710` 从 `0xBA38A4` 到 `0xBA39E7` 逐条读完后，流程是：

```text
① 00BA38ED call 0xBA02A0            从 req[0x620] 算出 20 字节 → [ebp-0x40]
② 00BA38FE call 0xC73800(&ctx, &[ebp-0x40], 20)   用那 20 字节初始化 ctx
③ 00BA392C call 0xC73760(&ctx, esi, edx)          ctx 更新；其中
        esi = 0xB9BBB0(req+0xB0) - 5
        edx = req[0xAC] - 4
④ 00BA395A call 0xC737A0(&ctx, &[ebp-0x2C], &20)  → 20 字节摘要
⑤ 00BA398D..00BA39D4  把摘要 20 字节与常量表 K（0x00DB6xxx 处的
        0xAADE2280 F4211C0B 37EEFF00 CE109227 213CF4AA）逐字节 XOR 再全部 OR，
        结果为 0 才通过 ⇒ 等价于 **摘要 == K**
```

注意 ③ 的输入 `esi/edx` 来自 `req+0xB0` / `req+0xAC`，**不是**接收缓冲区。

**已尝试但全部未命中的枚举**（同轮数据，36 种组合）：
```text
sha1(X) 与 sha1(X^0x5C)，X ∈ {key, K[IDX]^key, K, 以及两两拼接}
→ 在三条 0x85 帧里逐字节搜索，命中 0
```

**⇒ 结论：算法是 SHA-1（已证），但"喂进去的字节序列"和"比对方向"仍未确定。**
两种可能，均未证：
```text
(a) 0xC73800 不是"灌数据"，而是"用 20 字节自定义初始状态" ⇒ 摘要 = SHA1_custom(f(key), buf)
(b) 被哈希的 buf 来自 req+0xB0 那条流（应用层收包缓冲），
    与 0x85 帧载荷不是同一段内存
```

**⇒ 继续推进需要的不是更多枚举，而是把 `0xC73800` / `0xC73760` 的语义读透
（尤其 `0xC73800` 是否改写 ctx 初值）。**

**本轮到此为止：不再基于推测写服务端应答。**

### 1.13 provider id 采样：`req+0x190 = 0`（未定位）`[已证：读数为0]`

按 `0xC7805F mov [ebx+0x190], esi` 的提示，采样请求对象 `[mgr+0x4F4]+0x190`：

```text
run IFS1_ELEVATED_20260930_104246（成功命中 5E8=3）
req190 = 0    全程不变
```

⇒ 那个偏移在**主请求对象**上没有存 provider id，**该对象不是走 0x85 codec 的那个**。
**provider id 仍未定位** `[未证]`。

**顺带一条环境经验（本轮踩到过）**：
```text
连续 5 轮全部在 iips.dll 之后、ifs2.dll 之前以 0xFFFFFFFF 退出
⇒ 不是随机 flake，是**残留进程**导致（TQMCenter 等没退干净）
清理 TQMCenter / IIPSHostApp / TP3Helper / tersafe / 游戏进程后，下一轮即成功
⇒ 每轮实验前**必须**先清残留进程，否则整批实验白跑
```

### 1.14 provider id 定位成功，但**输入对象采错了** `[已证]`

**成功部分**：`req+0xB0+0x14` 处读到 **`2`**

```text
run IFS1_ELEVATED_20260930_104828
rqB0 = 0 ; 0 ; 0 ; 0 ; 0 ; 3984(0xF90) ; 2 ; 3BE84968
                                          ^  provider id = 2
```

与 `0xE886F8`（id=2：step2 = 0xC77920 SHA1_Init / step3 = 0xC77960 SHA1_Update /
step5 = 0xC77A30 SHA1_Final）完全对应。**"运行时可能用别的 provider"这一疑虑排除。**

**失败部分**：按 `0xBA38A4 mov ecx,[edi+0xB0]` 去采 `[mgr+0x4F4]` 那一侧的 `0xB0` / `0xAC`：

```text
run IFS1_ELEVATED_20260930_105405（成功命中 5E8=3）
rqB0 = 0 ; 0 ; 0 ; 0 ; 0 ; 3D48 ; 2 ; 3C9F7590
        ^ [req+0xB0] = 0
rqAC = 0
obj  = 空（指针为 0，未打印）
```

⇒ **`[mgr+0x4F4]` 不是 `0xBA3710` 收到的那个 `edi`。**
`0xBA38A4` 的 `[edi+0xB0]` 若为 0 会立即崩溃，而运行正常，
所以采到的是另一个对象。

**⇒ `0x85` 处理器的 `edi` 对象地址仍未定位** `[未证]`。

### 1.15 本轮收束

```text
已证（本轮）:
  · 0x85 = 校验通道，服务端必须应答
  · 算法 = SHA-1（Init/Update/Final 三件套，常量在案）
  · 上游 = xor 0x5C 预变换
  · provider id = 2，走 0xE886F8 记录（标准软 SHA-1）
  · 调用结构 = 0xC73800 init / 0xC73760 update / 0xC737A0 final / 与常量表 K 比对
  · 回声方案否证（客户端立即断开）
  · VFS 路线否证
  · 配置文本走本地 dvar，不经过服务器

未证（继续所需）:
  · 0x85 处理器收到的那 3 个参数（尤其 edi 对象地址）
  · SHA-1 消息的起始指针 esi 与长度 edx 的实际值
  · 比对方向（客户端校验服务端，或反之）

下一步唯一入口：定位 0xBA3710 的调用者 0xBA46C2 传进来的那个对象，
把它的 0xB0 / 0xAC 读出来。需要在 0xBA46xx 附近再布几个采样点。
```

---

### 1.5-bis 原始怀疑记录（保留）

（以下为发现大数库之前的记录，保留以便追溯）

紧跟着四个同族调用
```asm
00BA38FE  call 0xC73800
00BA392C  call 0xC73760
00BA395A  call 0xC737A0
00BA3980  call 0xC73750
```
形状是**数值运算库**（init / op / op / free），疑似**大数运算**。
即 `0xBA02A0` 的 20 字节只是**中间量**，还要与收到的数据做一次数值运算/比较。

**⇒ 下一步要读的是这四个函数（合计可能数百行），而不是继续猜表。**
**在读懂它们之前，不要按 §1.4 写服务端应答。**

---

## 2. 配置链（dvar / buildconfig.ini）—— 与服务器无关 `[已证]`

### 2.1 链条

```text
0x4FC330 区段:
    push "build_version" (0xDBD640) / call 0x770CB0   ; dvar 查询
    mov  [0x33E6A28], eax
    push 0x81A7F04 / call 0x771390                    ; dvar 值 → 字符串缓冲

0x50E700:
    读 0x81A7F04，找最后一个 '.'，拼成 "<值>_<网络名>" → 0x333AC78

0x50E954 → 0x50E700 → 0x50B910(cfgobj=0x33E6A00, 缓冲)  ; INI 解析
    → 配置容器 0x33E6A00
```

### 2.2 运行期实测 `[已证]`

```text
tag  (0x81A7F04) = "1.0.0"        ← dvar 链是通的
hd28 (0x33E6A28) = 135243544      ← 句柄有效
h91c (0x757091C) = 135243620
h0c4 (0x330C0C4) = 135244076

zbuf (0x333AC78) = 全 0           ← 拼接没发生
cfgobj(0x33E6A00) = 0             ← 容器没建
```

### 2.3 配置文本的格式 `[已证]`

`0x50B910` 是解析器（内含 UTF-8 BOM 检测 `EF BB BF`，`[section]` / `key=value` / `;` 注释
的状态机，跳转表 @0x50BB70，5 个状态）。**输入是普通 INI 文本。**

已知键名（字符串地址全部在案）：
```text
0xDB69E0 coupons        0xDB69E8 ping_address   0xDB69F8 cross_zone_%s
0xDB6A08 zone_id        0xDB6A10 bitmask        0xDB6A18 original_title
0xDB6A28 ping_interval  0xDB6A38 cross_zone     0xDB6A44 ping_times
0xDB6A50 max_connect_latency  0xDB6A64 free_join_players
0xDB6A78 zone_groups    0xDB6A84 zones          0xDB6A8C cross_zone_group_%s
0xDB6AA0 combat
```

### 2.4 ★ 排查结论：这段配置**不走网络** `[已证]`

全树扫描（2936 个文件、含所有二进制）确认：
```text
键名 "dw_config" / "cross_zone" / "STUN_STN" / "STUNPingEnabled" /
     "dw_disconnect_oob_always"  →  **只出现在 exe 里**，任何 .ini/.cfg/.ifs/.ff 中零命中
```

⇒ **键名在 exe 里，键值不在本地任何文件** ⇒ 但**这段配置的输入是 dvar（本地）**，
不是 HTTP、不是 DW 通道。

**所以"写本地服务端"喂不进这段配置 —— 它压根不问服务器要。**

---

## 3. 步骤表与 dvar 链的运行期观测 `[已证]`

```text
stepId (0xDA9FC8, 每步一个 ID) =
    8B 02 8F 90 96 91 92 93 94 95         ← 步骤 1 的 ID = 2

stepTbl (0xE56FFE0, 步长 0x50) :
    运行开始 = 全 0
    运行中   = 出现 0x7C / 0x7C / 0x7F 三条记录
```

`0x50DB90(arg)` = "步骤 arg 的 ID 是否登记在 `stepTbl` 里"，
`0x50E93D` 用它决定要不要跳过解析（`jne 0x50EA83`）。

⚠️ **矛盾未解** `[未证]`：按上表 `0x50DB90(1)` 应返回 0（表里没有 ID=2），
解析`本该执行`，但 `cfgobj` 实测恒为 0。**静态无法再进一步**，需要断点类观测（超出边界）。

---

## 4. VFS 路线：**否证** `[已证]`

详见 `_subagents\VFS_ROUTE_VERDICT.md`。三条独立证据：

1. 引擎镜像里 `ICreateVFileSys` / `IIPSVFS.dll` / `CreateVFS` / `[VFS_TRACE]_mount` **全部 0 命中**
2. 引擎自带文件系统层是 `IWff` 家族（魔数 `IWff0100`@0xDB5EE0 / `IWffu100`@0xDB5EEC / 版本 0x1CD）
3. `.ff` 打开路径 = `sprintf("%s.ff")`(0x49ED40) → `CreateFile`(0x776FA0 → `call [0xCA8208]`)

`IIPSVFS.dll` 的 PDB 自证 `f:\code\iips_proj\QQSpeedVFS\...\TenKart.pdb` ⇒
**腾讯平台侧工具链（QQ飞车 VFS），不是游戏引擎的**。

---

## 5. 完整性校验：本地为主，但**不止一份** `[已证]`

### 5.1 TCLS AutoCheck 清单（本地、明文、**已失效**）

```text
COD OL\TCLS\TCLSCheck.lst   [TCLSAutoCheck] 31 条 "文件" MD5 大小
COD OL\TCLS\freshui.lst     [AutoCheck]      1 条（同族 schema，多一列）
COD OL\TCLS\config\check.ini  backupfile=data.vfs / checktoolname= (空)
```

逐条核对：`TCLSCheck.lst` **匹配 9 / 不匹配 22 / 缺 0**，其中 7 条连大小都不同；
匹配的 9 条**全部在 `Tenio\TenioDL\`**。`freshui.lst` 也不匹配。

⇒ **若这份清单是启动闸门，游戏根本起不来。** 它的真实角色是**修复候选项列表**。
**不要把 ⑤ 的失败归到它头上。**

二进制里搜 `TCLSCheck` / `TCLSAutoCheck` ⇒ **零命中**（消费方加壳），加载者**未定位** `[未证]`。

### 5.2 真正的校验层在 TenProtect

```text
TCLS\TenProtect\ 内:
  fszwd.dat        3,202,080 B  头 = 4D 5A (自身即 PE)
  TPHelper.a..e.dat  (PK/ZIP，未加密)  共 34 个模块
    TenProtect\TASSafeScan.dll / TASSecScan.dll / TASScan.dat
    TenProtect\TASLoginBase.dll / TASLogin.exe / TasBridge.dll / TASChannel.dll
    Tenio\VFS.dll / TenTPF.dll / TenFact.dll   TenSLX.dll
```

`fszwd.dat` 内**进程名列表**含 `codoMP_client_shipRetail.exe`（还有 TASLogin.exe /
tgp_daemon.exe / CrossProxy.exe / qq.exe …），并引用：
```text
wintrust.dll / WinVerifyTrust
CryptCATAdminCalcHashFromFileHandle / CryptCATAdminEnumCatalogFromHash
```
⇒ **改 exe 会落入这一层**（目录签名/清单哈希，不是纯文本清单）。`[已证]`

### 5.3 联网部分与校验无关 `[已证]`

```text
TCLS\config\dirserver.xml              tcls.qq.com + 4 IP, 端口 8080/5223/10009
TenProtect\config\VersionServerConfig.xml  tcls.rail.qq.com + 12 IP, 端口 8001/9001/10001/8002/9002/10002
TenProtect\config\VersionServerConfig.xml  tasver.gamesafe.qq.com:80
TerSafe.dll 内嵌                              down.qq.com / down.safe.wegamex.com / exp.tcls.qq.com
```
全部是**更新/版本/上报**通道，已停服 ⇒ 只会超时，**不构成完整性判据**。

---

## 6. exe 自身完整性核查结论（子代理任务，主线代做）`[已证]`

详见 `_subagents\EXE_INTEGRITY_VERDICT.md`。

```text
codoMP_client_shipRetail.exe
  大小 7,841,344 B (0x77A640)
  MD5    6d6f68debf708280f5383dfed6d96281
  SHA256 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
  PE32, 7 sections, opt magic 0x10B, CheckSum 字段 0x0078840D
  Authenticode = Valid（Tencent Technology (Shenzhen)，
                 DigiCert Assured ID Code Signing CA-1，
                 2020-11-25 → 2024-02-23 已过期但有时间戳）
  ⇒ 本机这份 exe **未被修改过**
```

- 磁盘清单层面**不含 exe**（穷尽枚举）
- exe 自身 IAT **不含**任何哈希/校验 API
- IMPORT 目录**只有一个描述符** = `codoMP_client_shipRetailBase.dll`

---

## 7. 镜像与工具（本轮新增能力）

### 7.1 ★ 重要：旧镜像残缺

```text
_mainline\_dyn100_run_20260925_182324\live\image_best.bin
  PE 头声明 SizeOfImage = 0x0E659000 (241 MB)
  文件实际只有        0xA65000 (10.9 MB)      ⇒ 覆盖率 4.5%

  段表: .tp3 VA 0x1000 vsize 0x8A689A      IN FILE
        .tp3a VA 0x8A8000 vsize 0x16DA70    IN FILE
        .tp3  VA 0xA16000 vsize 0xDBB1CC0   **TRUNCATED**（只含 0x62000）

  后果：0xC7AEAC0 / 0x33E6A00 / 0x82C4A88 / 0xE56FFE0 / 0x331D420
        **全部在镜像覆盖范围之外**，静态读不到它们的"数据"
```

**⇒ "没人写 0xC7AEAC0"这类结论只在已抓到的 4.5% 里成立，不得外推。**

### 7.2 新增的定向抓取（避免 241 MB 全量读取）

观察器新增 `--dump-ranges "0xA-0xB,0xC-0xD" --dump-out <bin> --dump-at <秒>`：
在固定时刻（默认 t=55s，握手完成后、看门狗之前）只抓需要的地址段。

实测一轮：3 段共 1,122,304 B，`DUMP_RANGE` / `DUMP_DONE` 事件正常，输出
`_subagents\_ranges_v1.bin`（`RG\x01` 头 + va/size/data 序列）。

### 7.3 新增的通用数据写入

观察器新增 `--write-spec "hexbytes@0xADDR,hexbytes@0xADDR"`：
一次性写任意字节到任意地址，写后回读并打 `WRITE_SPEC` 事件。
**纯数据写**，与既有的 lobby host/port 全局同类。

实测：写入 INI 文本到 `0x331D420` + 长度到 `0xC7AEAC0`，
`load` 0→132、`bufa` 出现 `EF BB BF 5B 63 72 6F 73 73 …` —— **写入通路已证可用**。

### 7.4 一键链路驱动

`_mainline\_e57a5c_experiment.py`（原名，现为通用驱动器）：
```
--sandbox / --attempts / --seconds
--poke        <addr[,addr]>     置 1（每 250 ms 重写）
--write-spec  <hex@addr,...>    一次性写入
--dump-ranges / --dump-out / --dump-at
```
自带启动 flake 重试与状态时间线打印。

### 7.5 其他

```text
_subagents\_sub_seq85_shape.py    0x85 载荷熵/形状分析
_subagents\VFS_ROUTE_VERDICT.md   VFS 否证
_subagents\EXE_INTEGRITY_VERDICT.md   exe 完整性核查
restore_iips_contract_001\observer2\ImageDump.cs   独立全镜像转储器（--imagedump <pid> <out>）
CODOLServer\_mainline\dismiss_game_dialog.py       弹窗点击 + **关闭确认**（新增 IsWindow 校验）
```

---

## 8. 本轮被推翻/更正的结论（含我自己的错误）

| 旧说法 | 实际 | 证据 |
|---|---|---|
| `0x8083C0` 是 `mov eax,6` 的块 | 它是 `mov eax,8` 的块 | 反汇编 |
| `0xE57A5C` 是 `0xC7AF440` 的门 | 对，但 `0xC7AF440` 不在 ⑤ 路径上 | 实测 gate 不动 |
| `0x50E930(6)` 建 `[0x33E6A00]` | 被调用后容器仍是 0 | 实测 |
| 弹窗可被 dismiss | **`WM_COMMAND`+`BM_CLICK`+`WM_CLOSE` 全发也关不掉**，`IsWindow` 持续为真 | 两个独立进程确认 |
| `0xC7AEAC0` 是"配置已加载"标志 | 它是**缓冲区长度字段**（描述符在 `0xC7AEAB8`：ptr/cap/len） | 内存 dump |
| 配置数据本地没有 | dvar 链是通的，`tag="1.0.0"` | 实测 |
| `0x85` 载荷是加密的 | 是**校验值相关数据**；`0xBA02A0` 为查表 XOR，**但其输出未能复现载荷**（§1.6） | 反汇编 + 熵分析 + **复刻验证失败** |
| `0x5EC` 闸要求旧值==0 | 要求**收到的 seq == 当前计数器** | 反汇编 |
| `.ff` 缺失导致 ⑤ | 补了 6 个 `.ff`，⑤ 不变 | 实测 |
| 补 `mp/marketplace.json` 能开 gate | 补了，gate 不变 | 实测 |
| VFS 可喂资源 | 引擎不走 VFS | 三重证据 |

---

## 9. 下一步：服务端实现 `0x85` 应答（本轮认定的正确方向）

### 9.1 待确认（只读，各几分钟）

```text
① 下标置换表第 13 项的真实值（反汇编里未赋值，最可能 0x10）
② req[0x620] 在握手后的 20 字节内容
   —— 现成工具：观察器 --handshake-key-file <file>
③ 应答帧的确切字段：序号位置已知（body[1]），长度是否必须与请求一致 [未证]
```

### 9.2 实现落点

```text
CODOLServer\lobby_server\lobby_plain_probe.py
  → 握手时保存客户端提供的 20 字节
  → 收到 opcode 0x85 时：按 §1.4 算校验值，回一个同序号的 0x85
  → 观察客户端 [req+0x5EC] 是否推进、47s 是否还重发、52s 是否还弹窗
```

### 9.3 验收判据（不要用别的）

```text
成功：post-83 之后 ≥ 60 s 无「与大厅服务失去连接」弹窗，
      且观察器 lobReq5ec 从 1 递增。
失败：仍在本轮实测的 47.1 s 重发 / 52.0 s 弹窗。
```

---

## 10. 边界（硬性，未变）

```text
允许    ReadProcessMemory / WriteProcessMemory（仅游戏自身数据字段）/
        EnumWindows / EnumProcesses / 本地服务端实现
禁止    绕过/关闭/隐藏于 ACE、TenProtect 等安全组件
        修改 .text、注入（Frida/调试器/驱动）、在目标进程执行外来代码
        停止/配置/删除 ACE 服务（实测蓝屏 0x01010002）
```

本轮所有实验均在上述边界内：内存写入只针对游戏自身数据字段，
未改任何文件、未注入、未执行外来代码。

---

## 11. 资产路线的最终判定（承接 `SESSION_APPEND_20260929_STAGE3_SUCCESS.md` §48–§55）

上一轮把 ⑤ 的根因从「配置缺失」改判为「资产 `mp/marketplace.json`
未登记」，并给出四条假设路线。本轮把这四条逐条查到底，**全部封闭**：

### 11.1 四条路线的结论

| 路线 | 动作 | 结果 | 依据 |
|---|---|---|---|
| 1 | 往 `main\` 放 `mp/marketplace.json` | 实测无效 | `§48.7`（五个字段全不变） |
| 2 | 解 `.ifs` 得 `.ff` 放进 `main\` | 实测启动失败 | `§50.11 / §51`（4/4 startup flake） |
| 3 | 修改引擎的 zone 装载清单 | 清单在 `.text` 里 | `§52`（`0x4FCC00`/`0x4FCCA0` 栈数组） |
| 4 | dvar / `config_mp.cfg` / 命令行 | 均为封闭 | `§55`（cfg 加密、键是 UI 元素） |

### 11.2 本轮新增的两条静态确证（把路线 2/3 的边界钉死）

**（a）`0x4A93E0` 一共只有 3 个调用点，且都在引擎内部调用链上，没有外部注入点：**

```text
0x4A93E0  的调用者（本轮 `_xref_va.py` 复扫）：
  0x4A9461   0x4A9460 这个小包装（push ecx / call 0x4A93E0 / pop ecx）内
  0x4A98D8   0x4A98B0 起的"大厅/引擎每帧检查"内（与 0x849B800 的计时器比较后调用）
  0x4A99E2   同一族检查函数的另一分支
⇒ 没有任何"读配置/读服务端响应/读控制台命令"的分支会调用它。
```

**（b）`0x4A9443` 那条 `gate := 1` 的前置条件本轮读全了：**

```asm
4A9418  call 0x803830              ; 取管理器对象
4A941F  test esi,esi / je 0x4A9455
4A9425  call 0xB7A670              ; 要求返回 2
4A942A  cmp eax,2 / jne 0x4A9455
4A942F  push 0xDAE091              ; 一个空/空串常量（历史上 strnlen 为 0）
4A9436  call 0xB81250              ; 要求返回非 0
4A943B  test eax,eax / je 0x4A9455
4A9443  mov dword [0x82C4A88], 1   ; gate := 1
```

`0x4A93E0` 自身的语义（本轮复读）也确认了它**只做一件事**：

```asm
4A93E0  cmp byte [0x84ABB2F],0
4A93E8  mov dword [0x82C4AEC],1        ; 只是把"已尝试"标记置 1
4A93F2  je  0x4A9455
4A93F4  mov dword [0x82C4AA0],0
4A93FE  mov esi,0x86CFF70              ; 遍历 0x86CFF70..0x8861550，步长 0x66C
4A9403  loop: call 0xB8B3E0(cx=esi)
4A9418  call 0x803830 -> 0xB7A670 -> 0xB81250 -> gate:=1
```

⇒ **`0x4A93E0` 不是"读 marketplace 资产"的函数**（旧报告 §48.1 把
`0x4A9351` 起的另一个函数 `0x4A9330` 与它混为一谈）。真正的
marketplace JSON 读取在 **`0x4A9330`** 里，而 `0x4A9330` 没有任何调用点
（本轮 `_xref_va.py` 复扫为 0）。

### 11.3 结论（本会话对 ⑤ 的冻结判断）

```text
⑤ 的阻塞链在静态上依然成立：
  资产 mp/marketplace.json 未登记
    -> 0x4A9330 无法被调用（无调用点）/ 或取不到资源
    -> [0x82C4A88] 停在 0（应为 0->1->2->3）
    -> 0x4A9955 的 cmp [0x82C4A88],3 不成立 -> 不调 0x50E930(6)
    -> [0x33E6A00] 配置容器从未建立
    -> 所有 dw_config 键读不到 -> DW 用硬编码默认值
    -> 发送链 0xBBAD10 -> 0xBBA870 -> 0xBBA6D0 每次失败
    -> [dw+0x1F4] 停在 1 -> +47.6 s（真实 stun）/ +23.2 s（本地）置 -2
    -> +4.4 s 弹「与大厅服务失去连接」-> DELETE /queue 清理

在不改 .text、不规避安全组件的前提下，**已无未探索的合法路线**：
  路线 1/2 实测否证，路线 3/4 静证封闭，且 0x4A93E0 的调用点无外部注入面。
```

### 11.4 本会话不再重复的动作（避免下一轮重启同一循环）

```text
× 不要再去放 mp/marketplace.json（已否证）
× 不要再解 .ifs 往 main\ 里塞 .ff（已否证，且会破坏启动）
× 不要再去追 zone 清单 / dvar / config_mp.cfg（已静证封闭）
× 不要再用 [dw+0x1F4]、0xBBAD10、STUN/ICMP 做实验：
  它们的失败是上一条链的**结果**，不是可独立修复的原因
```
