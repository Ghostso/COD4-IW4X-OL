# E5 — 协议兼容性矩阵

> 阶段 E · CODOL 2697 · 仅静态分析。未启动游戏或服务端，未注入，未打补丁，未编译，未修改任何样本。
> 等级：`VERIFIED` = 二进制指令或调用链直接支持；`STATIC-INFERENCE` = 有依据的语义解释；`NOT-OBSERVED` = 尚无运行时或互通观测；`BLOCKED` = 样本、工具或调用链条件不足。矩阵中的 `BLOCKED/UNKNOWN` 表示“当前未闭合”，不是“证明不存在”。

## 1. 总览矩阵

| 主题 | 服务端写入证据 | 客户端读取证据 | 当前结论 |
|---|---|---|---|
| Gamestate 注册门控 | `_CODOL2697_WriteNativeGamestate` RVA `0xA3DAB` 检查资源对象 `+0x78F4` 和注册结构 `+0x6408`；任一失败即不编码返回。`_CODOL2697_ReadRegistration` RVA `0xA3EA0` 在栈 blob `+0x6408` 写入校验成功标志，再由 `memcpy` 复制到全局注册结构。`_CODOL2697_WriteGamestate` RVA `0xA21B8` 有真实调用者；`_CODOL2697_WriteConfigstrings` RVA `0xA0468` 在 `0xA22C1` 被调用。 | 未找到可验证的客户端 `0x03` gamestate 网络读取或 switch。字符串 `gamestateupdate %d` 的真实代码引用位于 RVA `0x56893`、`0xA2994`；`0xA2660` 仅是状态/表更新候选。 | 服务端门控和调用链：`VERIFIED`。客户端网络解析/状态机：`BLOCKED/UNKNOWN`。互通：`NOT-OBSERVED`。 |
| EOF `0x06` | `_CODOL2697_WriteSnapshotReached` RVA `0xA4860` 在 `_CODOL_WriteGlass` 后于 `0xA4CAF` 写入字节 `6`，之后仍用同一 writer 继续写入。这支持“内部子记录/阶段终止符”，不能单独证明它等于整条网络消息的最终 EOF。`_SV_EndClientSnapshot` RVA `0x86F7D` 的 `0x87104..0x87120` 根据 `_CODOL_Target2697ArchivesActive` 选择：false 写 `0x05`，true 写 `0x06`。E1 另记录 gamestate 尾 `0xA22F8`、configstrings 尾 `0xA0997` 写 `0x06`；legacy 路径记录写 `0x05`。 | 未找到可复现的客户端 `0x06` 指令级读取、长度检查或终止分支。当前搜索镜像中 `UNEXPECTED_EOF` 没有直接代码引用证据。 | 服务端写入/选择：`VERIFIED`。内部字节语义：`STATIC-INFERENCE`。客户端处理：`NOT-OBSERVED/BLOCKED`。 |
| Reliable `0x02` | `_SV_WriteReliableCommand` RVA `0x8612E`：返回 `<0` 调用 `Com_Error`；`==0` 写 `0x01 | long | string`；`>0` 写 `0x02 | long | short(length) | data[length]`。`_SV_ProfileCommand2697` RVA `0x860DE` 在目标 archives 未激活或 `CODOL2697_PROFILE_WIRE=text` 时返回 0，否则调用 `_CODOL2697_ProfileCommandBytes` RVA `0x85D32`。写入调用点 `0x8622B`、`0x862AC`；上游调用点包括 `0x710B7`、`0x86DE0`、`0x873E4`。 | 候选 RVA `0xA2E50` 读取 `long(4) + short(2) + payload` 并更新槽；字段形状与服务端 `0x02` 负载匹配。未找到直接调用者、`0x02` 比较或可验证 switch。 | 服务端分支/编码：`VERIFIED`。客户端字段形状：`VERIFIED`；绑定到 opcode `0x02`：`STATIC-INFERENCE`；分派：`BLOCKED/UNKNOWN`。互通：`NOT-OBSERVED`。 |
| Snapshot | `_CODOL2697_WriteSnapshot` RVA `0xA4FA0` 在 `0xA4FF7` 包装调用 `_CODOL2697_WriteSnapshotReached` RVA `0xA4860`；`0xA4860` 另有一个直接调用点 `0xA26EB`（`_CODOL2697_PrepareHistory` RVA `0xA249D`）。已观察序列包括 player fields/arrays、animations、actors/entities、clients、glass、内部 `0x06`、HUD、第二遍 actors/entities，随后把 `0x728`、`0x2C38`、`count*0x1F8`、`count*0x13C`、`count*0x5C` 区域复制到输出。 | 候选 snapshot/delta 解析器 `0x6E060`、`0x6D340`；`0x6D340` 附近有与 `5`、`6` 的比较。delta 解码、区域拼接、EOF 和调用者仍未闭合。 | 服务端已观察调用序列/常量：`VERIFIED`。wire 分帧/子段语义：`STATIC-INFERENCE`。客户端解码/delta/EOF：`BLOCKED/UNKNOWN`。互通：`NOT-OBSERVED`。 |
| Configstring | `_CODOL2697_WriteConfigstrings` RVA `0xA0468` 在 `0xA07F8` 写 opcode `0x04`，随后写 short count、编码字符串、bit/配方字段，并在 `0xA0997` 写终止 `0x06`。legacy writer 使用 `0x03` 与 `0x05`。 | 未发现可验证的客户端 `0x04` 网络读取或消费路径。`EXE_CONFIGSTRINGMISMATCH` 在当前搜索镜像中没有直接代码引用证据。 | 服务端编码：`VERIFIED`。客户端读取/消费：`BLOCKED/UNKNOWN`。互通：`NOT-OBSERVED`。 |

## 2. 已建立的事实

### 2.1 服务端侧

- 样本 SHA-256：`80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`；ImageBase `0x400000`。
- 2697 gamestate/configstring/snapshot 代码与 legacy 代码共存于同一 EXE。共存为 `VERIFIED`；运行时最终选择路径为 `NOT-OBSERVED`。
- 注册门控由两个字段共同控制：资源对象 `+0x78F4` 与注册结构 `+0x6408`。后者由 `_CODOL2697_ReadRegistration` 校验真实文件格式与 CRC 后置位，再复制进全局结构。
- 外层 snapshot 终止符由 `_CODOL_Target2697ArchivesActive` 选择：false 为 `0x05`，true 为 `0x06`。
- reliable command writer 直接选择 `0x01` 或 `0x02`；`0x02` 还受 archives 激活、`CODOL2697_PROFILE_WIRE` 环境值和命令成功编码的控制。

### 2.2 客户端侧

- 打包客户端：`D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe`，SHA-256 `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`。
- 主要反汇编镜像：`D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin`，SHA-256 `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`，ImageBase `0x400000`。它是静态恢复镜像，不是已验证的运行时映射。
- 已校验映射示例：`0x1AC1D0 -> VA 0x5AC1D0 -> 文件偏移 0x1AB5D0`；`0xA2E50 -> VA 0x4A2E50 -> 文件偏移 0xA2250`；字符串 `gamestateupdate %d` 位于 RVA `0x8B8378`，真实代码引用为 RVA `0x56893`、`0xA2994`。
- 客户端 `0xA2E50` 的字段形状是服务端 reliable payload 的可信候选，但它尚未通过指令级分派链绑定到 opcode `0x02`。

## 3. 明确未知与非证据项

| 项目 | 状态 | 原因 |
|---|---|---|
| 客户端 `0x02` 分派 | `BLOCKED/UNKNOWN` | 未找到通向 `0xA2E50` 的可验证比较/switch；直接 E8 与指针搜索未命中调用者。未命中不能证明不存在。 |
| 客户端 `0x06` EOF/EOS 处理 | `NOT-OBSERVED/BLOCKED` | 未找到可复现读取或终止指令。服务端写入不能证明客户端支持。 |
| 客户端 `0x03` gamestate parser | `BLOCKED/UNKNOWN` | `gamestateupdate` 引用与 `0xA2660` 仅为候选。 |
| 客户端 `0x04` configstring parser | `BLOCKED/UNKNOWN` | 未定位可复现网络 reader 或 consumer。 |
| Snapshot 子区域边界 | `BLOCKED` | 可见服务端复制和内部 `0x06`，但外层 Msg 分帧和客户端重组未闭合。 |
| 恢复客户端镜像的运行时行为 | `NOT-OBSERVED` | 未执行、未注入、未做运行时 dump 对照、未抓包。 |
| 端到端互通 | `NOT-OBSERVED` | 静态字段形状匹配不等于运行时互通。 |

## 4. 任务指定四项矩阵

| 主题 | 服务端写入证据 | 客户端读取证据 | 当前结论 |
|---|---|---|---|
| Gamestate 注册门控 | RVA `0xA3DAB`、`0xA3E00`、`0xA3EA0`、`0xA21B8`、`0xA0468`；指令级双门控和编码路径。 | 仅有字符串/状态候选；无可验证的 `0x03` 读取、switch 或状态转换。 | 服务端门控 `VERIFIED`；客户端链接 `BLOCKED/UNKNOWN`；互通 `NOT-OBSERVED`。 |
| EOF `0x06` | RVA `0xA4CAF` 内部写入；RVA `0x87104` 外层 `0x05/0x06` 选择；gamestate/configstring 尾部写入。 | 无可验证读取或终止。 | 服务端写入 `VERIFIED`；内部角色 `STATIC-INFERENCE`；客户端 `NOT-OBSERVED/BLOCKED`。 |
| Reliable `0x02` | RVA `0x8612E` 分支与 `0x02` 字段序列；`0x860DE` 控制门控；`0x85D32` 编码器。 | RVA `0xA2E50` 读取匹配的 `long+short+payload`；无 `0x02` 分派。 | 服务端 `VERIFIED`；负载形状匹配 `VERIFIED`；opcode 绑定 `STATIC-INFERENCE`；分派 `BLOCKED`；互通 `NOT-OBSERVED`。 |
| Snapshot | RVA `0xA4FA0 -> 0xA4860`；调用点 `0xA26EB`、`0xA4FF7`；有序 writer 调用和内部 `0x06`。 | 候选解析器 `0x6E060`、`0x6D340`；delta/EOF 未闭合。 | 服务端序列 `VERIFIED`；分帧/客户端解码 `BLOCKED/UNKNOWN`；互通 `NOT-OBSERVED`。 |

## 5. 结论

静态证据确认了若干服务端协议选择，并找到一个可信的客户端负载形状候选，但尚未建立完整双向状态机。当前跨端证据最强的是 reliable-command 负载形状；最弱的是客户端 EOF `0x06`，因为尚未找到客户端指令级证据。本文所有端到端兼容性陈述均保持 `NOT-OBSERVED`。
