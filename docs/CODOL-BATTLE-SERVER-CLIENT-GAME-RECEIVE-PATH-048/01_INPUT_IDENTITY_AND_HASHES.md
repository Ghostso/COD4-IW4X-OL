# 01 — 输入身份、哈希与版本

## 1. 基础结论

| 项 | 值 |
|---|---|
| 工作目录 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-GAME-RECEIVE-PATH-048` |
| 服务器工程 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` |
| 分析方式 | 只读静态(pefile + capstone);无运行时访问 |
| 地址口径 | 恢复映像 `file_offset == RVA`;`VA = RVA + 0x400000` |

## 2. 046 / 047 原始产物的继承与复核

本轮**读取并复核**了 046、047 的关键原始产物,未覆盖、未改写:

| 来源 | 路径 | 处置 |
|---|---|---|
| 046 报告 | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\00_INDEX.md` 等 10 份 | 只读 |
| 046 证据 | `...046\evidence\`(16 文件) | 只读,复核 TQOS 结论 |
| 046 脚本 | `...046\scripts\`(含 `verify_046.py`) | 只读 |
| 046 自验 | `verify_046.py` 的关键断言(TQOS 调用者集合、字符串 RVA) | 本轮用独立 harness 复现通过 |
| 047 报告 | `...047\00_INDEX.md`、`02`、`05`、`06`、`10` | 只读 |
| 047 证据 | `...047\evidence\047_workpackageD_*.json`(5 文件) | 只读 |
| 047 源码 | `...047\src\Codol.BattleServer\**` | 本轮在其分支上**新增**,不重写既有模块 |
| 047 基线 commit | `0b73aec` → 047 终态 `a9f0314` | 只读 |

**独立复现的 046 关键结论**(本轮 harness 重新推导,结果一致):

| 046 断言 | 本轮结果 |
|---|---|
| `0x85D870` 唯一调用者 `0x85EC01` | ✅ 一致 |
| `0x85D2E0` 唯一调用者 `0x85EBBB` | ✅ 一致 |
| `0x87C110` 唯一调用者 `0x85D49D` | ✅ 一致 |
| `0x87D5A0` 四个调用者 `0x85D3DB/0x85D418/0x85D9B5/0x85D9F7` | ✅ 一致 |
| `0x87BA50` 是 `jmp 0x87BE00` | ✅ 一致 |
| `udp://%s:%d` @ RVA `0x985AB0` | ✅ 一致 |
| `EXE_LOSTRELIABLECOMMANDS` @ RVA `0x9BB5E8`,上游 13 调用者 | ✅ 一致(13 个全部复现) |

> 结论:046 的 TQOS 归属与「13 个可靠命令上游调用者不成 P4/P5 交集」均**在相同映像上可复现**。
> 本轮不重复该工作量,只把它当作输入事实继续使用。

## 3. 样本身份(本轮实际读取的副本)

| 代码 | 文件 | 大小 | SHA-256 |
|---|---|---|---|
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |

三者 SHA-256 与 046 `evidence\00_identity.txt` 完全一致 → **同一构建**(A-07 身份项无新差异)。

## 4. PE 结构与恢复覆盖

### 4.1 磁盘 EXE(S-EXE,7 个节,全部名为 `.tp3/.tvm0 = 腾讯保护)

| 节 | VA | VSize | RawPtr | RSize | 说明 |
|---|---|---|---|---|---|
| .tp3 | 0x00001000 | 0x008A689A | 0x00001000 | 0x00593000 | 第一代码节(**磁盘上被压缩**) |
| .tp3 | 0x008A8000 | 0x0016DA70 | 0x00594000 | 0x0016E000 | 含 ws2_32 序号 IAT |
| .tp3 | 0x00A16000 | 0x0DBB1CC0 | 0x00702000 | 0x00062000 | |
| .tp3 | 0x0E5C8000 | 0x00000031 | 0x00764000 | 0x00001000 | |
| .tp3 | 0x0E5C9000 | 0x00009228 | 0x00765000 | 0x0000A000 | 资源 |
| .tvm0 | 0x0E5D3000 | 0x00004000 | 0x0076F000 | 0x00002000 | 腾讯 VM |
| .tp3 | 0x0E5D7000 | 0x00082000 | 0x00771000 | 0x00006000 | |

Import 目录:磁盘 EXE 只有 **1 个导入项**(`codoMP_client_shipRetailBase.dll`,1 个函数),
`ws2_32` 等**按序号(ordinal)解析**,故 `进口名` 需从序号槽恢复(见 §5)。
`AddressOfEntryPoint = 0x0E5DC690`(在 `.tvm0` 之后的 `.tp3` 节内,壳入口)。

### 4.2 恢复映像(S-IMG)

| 节 | VA | VSize | Raw(=VA) | RSize |
|---|---|---|---|---|
| .tp3 | 0x00001000 | 0x8A689A | 0x00001000 | 0x8A7000 |
| .tp3 | 0x008A8000 | 0x16DA70 | 0x008A8000 | 0x16E000 |
| .tp3 | 0x00A16000 | 0x0DBB1CC0 | 0x00A16000 | 0x00062000 |
| .tp3 | 0x0E5C8000 | 0x31 | 0x00A78000 | 0x1000 |
| .tp3 | 0x0E5C9000 | 0x9228 | 0x00A79000 | 0xA000 |
| .tp3 | 0x0E5D3000 | 0x4000 | 0x00A83000 | 0x4000 |
| .tp3 | 0x0E5D7000 | 0x82000 | 0x00771000 | 0x6000 |

- `EntryPoint = 0x0E5DC690`(与磁盘相同);
- 映像大小 `0x0A65000` = **恰好覆盖到第三节的 Raw 起点 `0xA16000` 之后 0x4F000 字节**;
  第三节的 VSize 声明为 `0xDBB1CC0`,但磁盘 RawSize 仅 `0x62000`(壳压缩),故
  **第 3 节区大部分在映像中不可读** —— 这正是 046/047 反复提到的 `RSize 0x62000` 缺口。
- **同一性验证(决定性):** 4 个代表性字符串在磁盘 EXE 中的原始偏移与 `disk_raw = 0x702000 + (RVA - 0xA16000)` 完全吻合:

| 字符串 | 映像 RVA | 磁盘偏移 | 校验 |
|---|---|---|---|
| `gamestateupdate %d` (0x9B4700) | 0x9B4700 | 0x6A0700 | ✅ = 0x702000+(0x9B4700-0xA16000) |
| `udp://%s:%d` (0x985AB0) | 0x985AB0 | 0x671AB0 | ✅ |
| `CG_ServerCommand: ` (0x9C61AD) | 0x9C61AD | 0x6B21AD | ✅ |
| `CL_VidRestartRelogin_f` (0x9BFCF0) | 0x9BFCF0 | 0x6ABCF0 | ✅ |

→ **S-IMG 与 S-EXE 的第一/第二节相同;S-IMG 额外包含第 3 节已解包的前 0x4F000 字节。**
两文件是**同一构建**,地址可直接互认。

## 5. ws2_32 序号 IAT 权威映射(本轮从磁盘 EXE 重新解析)

磁盘第 2 节 `va=0x8A8000 raw=0x594000`,故 `disk_raw = 0x594000 + (RVA-0x8A8000)`。
逐槽读取 4 字节,`0x80000000|ord` 形式解析序号:

| 槽 VA | 序号 | API | 槽 VA | 序号 | API |
|---|---|---|---|---|---|
| 0x00CA84E4 | 16 | **recv** | 0x00CA84E0 | 19 | **send** |
| 0x00CA84E8 | 18 | **select** | 0x00CA8518 | 20 | **sendto** |
| 0x00CA851C | 17 | **recvfrom** | 0x00CA8548 | 23 | **socket** |
| 0x00CA8554 | 2 | bind | 0x00CA84F0 | 4 | connect |
| 0x00CA84FC | 13 | listen | 0x00CA8500 | 1 | accept |
| 0x00CA8544 | 3 | closesocket | 0x00CA8540 | 10 | ioctlsocket |
| 0x00CA853C | 111 | WSASetLastError | 0x00CA8380/84 | 8/9 | htonl/htons |

**逐槽 `OK` 校验见 `evidence/` 中的分析 JSON;全部 14 个关键槽与 046 `a15_ws2_iat_usage.txt` 一致。**

## 6. 恢复覆盖的量化(负证据的边界)

对 S-IMG 做「≥32 连续相同字节」扫描:

- 长常量串共 **812** 段,合计 **90,197** 字节 = 映像的 **0.83%**;
- 其中填充字节以 `0x00` 为主(72,874 字节),`0xCC` 仅 2,099 字节;
- 第一代码节(0x1000..0x8A689A)内长串仅 11,220 字节(0.12%)。

**含义:** 恢复映像基本是完整代码,**没有大面积空洞**;但第 3 节区(0xA16000 之后仅 0x4F000 可读)
与数据段仍不完整。因此「在某范围内未找到某函数」只能陈述为该**范围内**的观察,
不能写成「程序中不存在」。此规定在 `05` §6 再次强调。

## 7. 本任务使用的具体副本列表

| 用途 | 副本 | 只读 |
|---|---|---|
| 接收路径静态分析 | S-IMG `image_best.bin` | ✅ |
| IAT/序号/导入解析 | S-EXE `codoMP_client_shipRetail.exe` | ✅ |
| 交叉核对(协议串是否存在) | S-DLL `codoMP_client_shipRetailBase.dll` | ✅ |
| 工程衔接 | 047 `baseline\`(只读副本)+ `src\` 新分支 | 新分支可写 |

## 8. 缺失项(明确标记)

| 编号 | 缺失 | 影响 | 状态 |
|---|---|---|---|
| E-048-1 | 第 3 节区 `0xA16000` 之后完整可读映像 | 可能藏 in-match 解析器 | `BLOCKED` |
| E-048-2 | 与预期构建 `E3823FD6..F37B` 匹配的第二样本 | 无法做构建差异性交叉验证 | `BLOCKED` |
| E-048-3 | S-EXE 的完整导入名表(仅 1 个 by-name 导入) | 只能按序号识别 ws2_32 | 已用序号法绕过 |
| E-048-4 | 受控只读调用栈采样(需单独授权) | 运行时确认 in-match 入口 | 未授权,未执行 |
