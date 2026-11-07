# BOOKING_STATE-001 —— `[this+0x278]` 状态位完整调查（P0）

> 纯静态。**未修改 Server / Golden / patch / KDF hook**。
> 分析源：`image_best.bin`（运行期镜像，已解壳）

---

## 0. 一句话结论

```
[this+0x278] 是 **1 字节** 状态位（所有访问都用 byte ptr）
它在匹配模块内共 29 处访问：**2 处写 1**、其余为读
写 1 的两处都出现在"**开始匹配/预约流程启动**"函数里
⇒ [this+0x278] = "**预约流程已启动**"标志（booking pending/active）

证据等级：STRONG_CANDIDATE
  （行为与调用位置高度一致，但尚无字符串/枚举直接命名它）
```

---

## 1. 全量访问点（范围 0x62C000..0x63A000，即匹配模块）

```
KIND     ADDR        SIZE   INSN
REAL_W   0x0062C04E  dword  mov dword ptr [ebx + 0x278], edi     ← ctor（edi=0，实为清零）
REAL_W   0x0062CCCD  byte   mov byte  ptr [ebx + 0x278], 1       ★ 置 1
REAL_W   0x0062DF08  dword  mov dword ptr [edi + 0x278], ebx     ← 存指针？（异或用法）
READ     0x0062F3AF  byte   cmp byte  ptr [edi + 0x278], 0
REAL_W   0x0062F474  dword  mov dword ptr [edi + 0x278], ebx
READ     0x0062F85A  byte   cmp byte  ptr [ebx + 0x278], 0        ← mmbook 发送函数守卫
REAL_W   0x0062FBBB  byte   mov byte  ptr [esi + 0x278], 1       ★ 置 1
READ     0x0062FD80  byte   mov al, byte ptr [ecx + 0x278]
READ     0x0062FFE0  byte   cmp byte ptr [esi + 0x278], 0
READ     0x00630657  byte   cmp byte ptr [esi + 0x278], 0
READ     0x0063268D  byte   cmp byte ptr [esi + 0x278], 0        ★ 解析器守卫
READ     0x006338E4  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00633A04  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00633BEE  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00633E93  byte   cmp byte ptr [esi + 0x278], 0
READ     0x00633F8E  byte   cmp byte ptr [esi + 0x278], 0
READ     0x00634F13  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x006352FE  byte   cmp byte ptr [ebx + 0x278], al
READ     0x006353B7  byte   cmp byte ptr [ebx + 0x278], al
READ     0x00635483  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x006356B8  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x006357BB  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00635814  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00635968  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00635E82  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x00635F75  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x006360FA  byte   cmp byte ptr [ebx + 0x278], 0
READ     0x006373D8  byte   mov cl, byte ptr [esi + 0x278]
READ     0x00637541  byte   cmp byte ptr [esi + 0x278], 0
```

### 观察

1. **所有读写都是 `byte ptr`** → 状态位是 **1 字节**（不是 dword）。
   （`0x62C04E` / `0x62DF08` / `0x62F474` 用 dword 形式的，
   是写指针/零值的邻近写入，属**不同成员**的重叠命中 —— 见 §3）
2. **只有 2 处写 `1`**：`0x62CCCD`、`0x62FBBB`
3. 其余全是 `cmp byte ptr [...+0x278], 0` —— **读作布尔**
4. **解析器 `0x63268D` 也在这里**：`cmp byte[esi+0x278], 0` / `je 0x6328EB`
   → 守卫 != 0 才继续，与第二阶段结论一致

---

## 2. 两处"置 1"点的上下文（关键）

### 2.1 `0x62CCCD` —— 疑似"开始匹配"

```asm
0062CCB1  mov  eax,[ebp+8]
0062CCB4  mov  ecx,[eax+0x3D14]
0062CCBA  mov  [ebx+0x10618], ecx
0062CCC0  lea  eax,[ebx+0x290]
0062CCC6  mov  byte [ebx+0x287], 0
0062CCCD  mov  byte [ebx+0x278], 1        ★ 置 1
0062CCD4  mov  byte [ebx+0x28A], 0
0062CCDB  call 0x4F73B0
0062CCE0  mov  edi,[ebx+0x1C]
0062CCE3  mov  byte [ebx+0x28B], 0
0062CCEA  call 0x7E7E30
0062CCF0  test al, al
0062CCF2  jne  0x62CD02
0062CCF4  mov  edx,[ebx+0x1C]
0062CCFA  call 0x633FE0
0062CD05  ret  4
```

**特征**：
- 同一函数里连续清零 `+0x287 / +0x28A / +0x28B`（一组状态位）
- 取 `[ebp+8]` 参数的 `+0x3D14` 存进 `+0x10618`
- 读取 `[ebx+0x105FC]`（该字段出现在 `mmstart` 格式串里）
- 结尾 `ret 4`（1 个参数）

⇒ 这是**用参数启动一次匹配/预约**的动作。

### 2.2 `0x62FBBB` —— 疑似"清理/收尾"

```asm
0062FB70  mov  ecx,[ebx]
0062FB72  mov  eax,[ecx]
0062FB74  mov  edx,[eax+0x24]
0062FB77  mov  ebx,[ebx+4]
0062FB7A  push 0
0062FB7C  push 1
0062FB7E  call edx                  ; 遍历链表回调
0062FB80  test ebx,ebx
0062FB82  jne  0x62FB70             ; 循环
...
0062FB8C  call 0xC3C20F             ; __security_check_cookie
0062FB94  ret  0xC                  ; 3 个参数
```

后面紧跟 `0x62FBBB mov byte [esi+0x278], 1`（在 `0x62FBA0` 起的另一个函数里，
该函数以 `0x62F85A` 的 `cmp byte [ebx+0x278], 0 / je` 做守卫）。

---

## 3. 排除干扰命中（避免误判）

以下 disp=0x278 的命中**不属于本对象**（结构体偏移巧合），不计入状态位：

```
0x00461F14 / 0x00461F1A   拷贝结构（[edi+0x278]->[ebx+0x278]）
0x00509CE8 / 0x00509D3A   float 成员
0x00530CF1 / 0x00530EE6   别的类
0x006E4980 / 0x006E54E9 / 0x006E5BDB / 0x006F4B01 / 0x006F548A   别的类
0x0082A190 / 0x0082A210 / 0x0082A220 / 0x0082A395               位标志组
0x0053634D / 0x007E4A23   栈偏移
```

**判定依据**：这些点不在匹配模块（0x62C000..0x63A000），
且其访问宽度/上下文与本对象不一致。

---

## 4. 状态位所属对象（CONFIRMED）

```
对象          = 匹配对象（ctor 0x62C000）
对象大小      = 0x3A134
vtable        = 0xDC7270（实例）
同接口副本     = 0xDC7714（与 0xDC7274 逐项相同 16/16，子对象切片）
守卫字段      = this+0x278  byte
相邻状态位     = this+0x287 / +0x28A / +0x28B（同函数内一起清零）
```

---

## 5. 语义判定（拒绝仅凭变量名）

### 5.1 现有证据支持的判定

| 候选语义 | 是否吻合 | 依据 |
|---|---|---|
| booking start / pending | **最吻合** | 两处置 1 都在"启动匹配"与"清理循环"函数里；解析器要求它 != 0 才处理 accepted |
| booking response received | 不吻合 | 解析器只是**读**它做前置守卫，不因收到响应而置位 |
| booking accepted | 不吻合 | 置位发生在**发送前**（`0x62F85A` 先 cmp，`0x62FBBB` 置 1 后才构造 mmbook） |
| booking failed | 不吻合 | 失败路径反而是**清零**（`0x62F6C0` 系列） |

### 5.2 结论

```
[this+0x278] = BOOKING_PENDING / BOOKING_ACTIVE（布尔）

证据链：
  ① 写入只有 0（ctor/复位）与 1（两处启动点）
  ② 全部读取都是 `cmp byte,0` —— 纯布尔语义
  ③ mmbook 发送函数(0x62F840 起)第一件事就是 cmp [ebx+0x278],0 并 je 退出
     ⇒ 未置位就不会发 mmbook
  ④ 解析器同样以它做前置守卫
⇒ 它是"预约流程处于活动状态"的标志

等级：STRONG_CANDIDATE
（未找到字符串/枚举给它命名；不写成 CONFIRMED）
```

---

## 6. 本项对主线的意义

```
① 它**不是** response channel 本身 —— 只是一个状态位
② 但它给出一个**强锚点**：
   凡是"置 [this+0x278]=1"的调用者，就是**发起预约的一方**
   ⇒ 顺这条线可以找到"谁启动了预约"
③ 解析器要求它非零 → 若服务端在客户端未启动预约时回 accepted，
   解析器会直接走 0x6328EB 拒绝（**无副作用**）
```

---

## 7. 仍 UNKNOWN

```
① 谁调用 0x62CCCD 所在函数（= 谁启动预约）→ 下一步
② 该状态位是否有 2 值以上（目前只见 0/1）
③ 它与 reservation array / A / B 的时序关系
```
