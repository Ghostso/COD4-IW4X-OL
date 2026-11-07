# E23 TLS / .rimp / 构造器审计

## 1. TLS 目录

| 项 | 值 | 说明 |
|---|---|---|
| TLS 数据目录 RVA | 0x008D7E00 | Size 0x00000018，位于 `.rdata` |
| StartAddressOfRawData | 0x0DD4E000 | = `.tls` 节区起点 |
| EndAddressOfRawData | 0x0DD4E018 | 24 字节 TLS 模板 |
| AddressOfIndex | 0x01867E44 | TLS 索引槽 |
| AddressOfCallBacks | 0x00BB33E0 | RVA 0x7B33E0，位于 `.rdata` |
| SizeOfZeroFill | 0x00000000 | 无零填 |
| Characteristics | 0x00000000 | — |
| **TLS 回调数组** | **首元素 = 0x00000000（空）** | 无 TLS 回调 |

**裁定**：**不存在 TLS 回调链**。因此"五个目标是否由 TLS 回调在加载期写入"这一路径被**排除**——没有任何回调可执行写入。

## 2. .rimp 修复表

| 项 | 值 |
|---|---|
| 节区 | `.rimp` VA 0x0DC11000，VirtualSize 0x00002964，RawSize 0x00002A00 |
| 非零字节 | 8863 / 10752 |
| 首 16 dword | 0x0DC1126C, 0x0DC11168, 0x007AE000, 0x0DC112C4, 0x0DC112A4, 0x007AE038, 0x0DC11478, 0x0DC112CC, 0x007AE040, 0x0DC11530, 0x0DC114C8, 0x007AE090, 0x0DC12118, 0x0DC11548, 0x007AE0A8, 0x0DC123A8 |

- `.rimp` 中的高地址密集落在 `0x0DC11xxx..0x0DC13xxx`（即 `.rimp` 自身范围）与 IAT RVA `0x007AE000` 附近，呈现"重定位/导入修复对（目标 RVA，导入槽 RVA）"特征。
- 对五个目标地址（VA 与 RVA 两种形式）、vtable `0xC5A31C`/`0xC5B0A4`、以及 `0xA87D50`/`0xA878A0`/`0xA85AD0`/`0xAAAE70` 做 4 字节精确扫描，**`.rimp` 中命中数均为 0**。

**裁定**：`.rimp` **不包含**指向五个目标或相关 vtable 的修复记录。五个目标不依赖 `.rimp` 重定位。

## 3. 显式构造器 / 初始化函数

- 对五个目标的 RVA（`.text` 内）启动 `0xCC` 反向扫描得到函数起点，均为标准 `push ebp; mov ebp,esp` 序言；**没有任何"构造器式"的 vtable 写入**（无 `mov dword ptr [reg], <vtable>` 写入这五个地址）。
- 与 `[edi+0x5F4]` 相关的构造器为 `0xA87BA0`（RVA 0x687BA0）：

```asm
687BC9  push 0x10
687BCB  call 0xA888A0          ; 基类构造
687BD0  push 0xC5BEB0          ; 类型描述符
687BDC  mov dword ptr [esi],0xC5A31C   ; <== 写入 vtable
687BE2  call 0xACBAF0
```

其静态调用者仅两个：`0x6AB97A`、`0x6AB9DA`（均在 RVA `0x6AB9xx` 段内，即设置 `[edi+0x5F4]` 的函数）。

## 4. 三重否定结论

| 机制 | 是否存在指向五个目标的写入 | 证据 |
|---|---|---|
| TLS 回调 | 否（回调数组为空） | 数据目录 TLS，AddressOfCallBacks 数组首元素=0 |
| .rimp 修复记录 | 否（0 命中） | `.rimp` 4 字节精确扫描 |
| 显式构造器/vtable 写入 | 否 | 无对五地址的 `mov [reg],imm`；C++ 构造器不作用于代码地址 |

## 5. 真实来源

五个目标**不需要**"初始化写入者"：它们是 `.text` 中的普通被调用函数，其"来源"就是 PE 磁盘镜像本身。E-22 所设的"BSS 加载期初始化"问题在基准纠正后**自动消解**，而非"仍未找到"。
