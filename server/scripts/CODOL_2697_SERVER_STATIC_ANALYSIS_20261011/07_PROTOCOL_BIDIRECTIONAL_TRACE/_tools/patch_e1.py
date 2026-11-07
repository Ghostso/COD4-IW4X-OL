import io
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\E1_GAMESTATE_GATE.md"
s=io.open(p,encoding="utf-8").read()

old="""- 门控标志位于 `+0x6408`，处于该结构范围内。本次反汇编**未发现任何直接写该字段的指令**（`.text` 全量立即数扫描只命中 `0x7E1ED`/`0x7E5ED` 两处无关位置；全文件绝对地址扫描无命中）。
  → 该字段在本次静态范围内**只被发现“被读”，未发现“被写”**。等级：**VERIFIED（未命中）**；其写入者若存在应在间接/结构体路径，属于未决问题（见 §7）。"""
new="""- 门控标志位于结构偏移 `+0x6408`。
- **写入者已定位（VERIFIED）**：`_CODOL2697_ReadRegistration` 把校验结果写入**本地栈 blob** 的同布局区域。栈布局证据：

  | 指令 RVA | 内容 |
  | --- | --- |
  | `0xA3EB5` | `lea eax,[ebp-0xC820]` — 本地 blob 基址 |
  | `0xA43BC` | `mov dword [ebp-0x6418], 1` — 校验全部成功后写“成功”标志 |

  偏移换算：`0xC820 − 0x6418 = 0x6408`。即 `[ebp-0x6418]` 正好是本地 blob base `[ebp-0xC820]` 的 `+0x6408`。
- 随后 `0xA43DE` 的 `memcpy(out, [ebp-0xC820], 0xC814)` 把该 blob 整体拷到调用方提供的 `0x14973B00`。
  → 因此 `_CODOL2697_ReadRegistration` 返回 1 时，`[0x14973B00+0x6408] == 1`；任何一步失败（CRC 校验失败 / 字符集非法 / 行格式不合法）则保持 memset 后的 0。
- 等级：**VERIFIED（指令级 + 偏移算术）**。这解释了为什么不存在 `mov [0x14973B00+0x6408], …` 形式的直接写指令——写入发生在**栈副本**上。"""
assert old in s, "anchor1"
s=s.replace(old,new)

old2="""- **直接返回 0**：不延迟、不切旧通道、不入队、不重试。上层的 `_collect`/`calloc` 只有在门控**通过后**才会执行。**VERIFIED**
- 注意：这里“返回 0”是**新通道的自放弃**，不是“回退到旧 0x02/0x05 通道”。旧通道是否在主流程另有分支需在 `_SV_WriteGameState` 层确认（见 §4）。"""
new2="""- **直接返回 0**：不延迟、不切旧通道、不入队、不重试。上层的 `_collect`/`calloc` 只有在门控**通过后**才会执行。**VERIFIED**
- 两个门控条件的来源（VERIFIED）：

  | 条件 | 位置 | 写入者 | 写入指令 |
  | --- | --- | --- | --- |
  | ① `[resource+0x78F4] != 0` | 资源对象 | `_CODOL2697_InstallResources`（`0xA44A0`） | `0xA4505`：`mov dword [eax+0x78F4], 1` |
  | ② `[registration+0x6408] != 0` | `0x14973B00+0x6408` | `_CODOL2697_ReadRegistration`（`0xA3EA0`） | `0xA43BC`：`mov dword [ebp-0x6418], 1`（栈副本，随 memcpy 进入全局） |

  两者的共同上游都是 `_CODOL_SetTarget2697ServerResources`（`0xC311B`）：先调 `_CODOL2697_InstallResources`（`0xC34B3`），再按 CVar 决定是否调 `_CODOL2697_ReadRegistration`（`0xC332F`）。
- 注意：这里“返回 0”是**新通道的自放弃**，不是“回退到旧 0x02/0x05 通道”。旧通道是否在主流程另有分支需在 `_SV_WriteGameState` 层确认（见 §4）。"""
assert old2 in s, "anchor2"
s=s.replace(old2,new2)

old3="""1. **`[registration+0x6408]` 的写入者未在静态范围内定位。** 本次扫描未命中直接写指令。它可能由 `_CODOL2697_ReadRegistration` 通过结构内联字段写入（0x6408 处于 `0xC814` 结构内），但反汇编中未见显式 `mov [reg+0x6408], …`。需对 `ReadRegistration` 全函数做数据流分析。
   → 等级：**BLOCKED（部分）**。"""
new3="""1. ~~`[registration+0x6408]` 的写入者未定位。~~ **已解决（VERIFIED）**：由 `_CODOL2697_ReadRegistration` 在栈 blob `[ebp-0x6418]`（= blob base+0x6408）写成功标志 1，再随 `memcpy` 进入全局。见 §2.2。"""
assert old3 in s, "anchor3"
s=s.replace(old3,new3)

old4="""| 注册门控由两个全局状态 + 一个文件校验共同决定 | 是 | VERIFIED |"""
new4="""| 注册门控由两个全局标志（资源安装 + 注册校验）共同决定，两个写入者均已定位 | 是 | VERIFIED |"""
assert old4 in s, "anchor4"
s=s.replace(old4,new4)

old5="""| `evidence\\client-registration2697.txt` 的性质 | 磁盘上的**真实注册校验输入**，但只在 CVar 指名时才被读取；启动脚本确实指名了它 | VERIFIED |"""
new5="""| `evidence\\client-registration2697.txt` 的性质 | 磁盘上的**真实注册校验输入**（CRC32 校验通过后置门控标志），只在 CVar 指名时才被读取；启动脚本确实指名了它 | VERIFIED |"""
assert old5 in s, "anchor5"
s=s.replace(old5,new5)

io.open(p,"w",encoding="utf-8").write(s)
print("patched OK, len",len(s))
