# 04 — 0x78772D 职责归属 / FUNCTION ATTRIBUTION

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 函数边界（PROVEN）

| 项 | 值 |
|---|---|
| 入口 | 0x78772D |
| 结尾 | 0x787779（0x78777A 起 int3） |
| 大小 | 0x4C 字节 |
| 调用者 | 无直接 call；数据指针引用 = 0 |

注意：0x78772D 与 0x787780 是相邻但不同的函数。0x787780 才是解析体主体（sub esp,0x84）。

## 2. 0x78772D 的语义（PROVEN）

    787732  lea eax,[ebp-8] / push eax
    787736  call [0xBAE1C0]             ; GetSystemTimeAsFileTime
    78773C  mov eax,[ebp-8] / mov ecx,[ebp-4]
    787744  add eax,0x2AC18000
    787749  push 0x989680                ; 10,000,000
    78774E  adc ecx,0xFE624E21
    787756  call 0xB50980               ; 64 位除法（时间基准换算）
    78775B..787768  结果 > 0x7FFFD27F 时返回 -1
    78776E  mov ecx,[ebp+8] / test / mov [ecx],eax   ; 写输出参数
    787777  leave / ret

裁定（PROVEN）：0x78772D 是 64 位时间戳/纪元换算函数（GetSystemTimeAsFileTime + 大数除法），输出到一个 dword 出参。与网络、游戏会话、ICMP 均无关。

## 3. 0x78772D 的数据指针与调用者（PROVEN）

| 检查 | 结果 |
|---|---|
| 数据指针引用 | 0 |
| 直接 call 调用者 | 0 |
| 是否被 0x1B0430 引用 | 否 |
| 是否含 .tvm0 调用 | 否 |

## 4. 与 0x1B0430 的关系

| 检查 | 结果 |
|---|---|
| 共享对象 [0x7474EAC] | 否 |
| 共享全局变量 | 否 |
| 调用边 | 无 |
| 数据流边 | 无 |

裁定（REFUTED）：0x78772D 与 0x1B0430 之间不存在可证调用边或数据流边。

## 5. E-13 的 ".tvm0 调用" 定性更正（重要）

E-13 记录：0x787982 call 0xDBEF28A 落入 .tvm0。

本轮更正：0xDBEF28A 属于 .data 段（BSS 区），不是 .tvm0（.tvm0 起始 RVA = 0xD958000）。

| 段 | RVA 范围 |
|---|---|
| .data | 0x8F1000 .. 0xD945420 |
| .tvm0 | 0xD958000 .. 0xDC11000 |

实际调用形态：

    78797E  push esi              ; 长度
    78797F  push 0x3D             ; 等号字符
    787982  call 0xDFEF28A        ; BSS 别名（.rimp 修复伪影）

语义（INFERRED）：memchr(buffer, 等号, len) 类查找。

裁定：E-13 的 ".tvm0 混淆边界" 定性为 REFUTED（实为 .rimp 指针修复伪影）；该处不是混淆代码。

## 6. 0x787780 的职责（INFERRED，供参考）

0x787780 解析 host:port 形式字符串（memchr 找冒号、htons 于 0x787835、比较串 "1234567890."），是端点字符串解析器。与 0x1B0430 的服务器表（0x2CCA3C8）可能配合（两者都属服务器列表子系统），但无已证调用边。

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 0x78772D 边界 | PROVEN（0x78772D..0x787779） |
| 0x78772D 语义 | PROVEN（时间戳换算） |
| 0x78772D 是否有调用者 | PROVEN（0） |
| 0x78772D 是否属游戏协议 | REFUTED |
| 0x78772D 与 0x1B0430 的关系 | REFUTED（无调用/数据流边） |
| E-13 的 ".tvm0 边界" 定性 | REFUTED（实为 .rimp/BSS 伪影） |