# BAP-0004D — 讨论：`PointerToRawData` 失效会污染多少既有结论

对应正论文：`BAP-0004_SECTION_TABLE.md`

本文是本体系建立以来**最重要的自我审计**。核心问题：
我们过去所有"从镜像读数据"的结论，有多少是按错误映射读的？

---

## 1. 我的判断可能错在哪

### 断言：`PointerToRawData` 在节 3–6 失效，必须用 `RVA = file_offset`

**替代假设 H1：`PointerToRawData` 是对的，我在它指向的地方读到了空洞页。**

节 4 的 RawPtr `0x00A79000` 处全零，RVA `0x0E5C9000` 处是资源目录。
若 `0x00A79000`–`0x00A83000` 是一片**未提交的零页**（内存转储的空洞），
那么"RawPtr 失效"就是假的——真实情况是"RawPtr 有效但内容被转储成零"。

**反证**：`0x00A79000` 属于节 2（`0x00A16000`–`0x0E5C7CC0`）。
节 2 在文件里是**有内容的**（`0x00A16000` 处是
`01 00 00 00 01 00 00 00 02 00 00 00 …`，非零）。
且文件总长 = `SizeOfImage`，无截断。

⇒ 若是空洞页，`0x00A16000` 起整段都该是零。实测非零。
⇒ **H1 被反证**（E3）。

**但 H1 的一个变体值得保留**：内存转储**可能按页复制时，
同一物理页映射到两个 VA**（节别名），转储工具只写了一处。
这能解释"节 3 两处都是零"——零页被共享，写哪都一样。
这对节 4/5/6 不成立，因为两处内容**不同**。

### 替代假设 H2：文件是"内存镜像"，`RVA = file_offset` 是提取脚本刻意铺的

若提取脚本把每个页按 VA 顺序写到 `offset = VA`, 那么
`file_offset = VA`，而不是 `RVA`。

**反证**：入口点 `AddressOfEntryPoint = 0x0E5DC690`，实测在
`file_offset 0x0E5DC690` 处读到 `ff 15 65 c6 9d 0e`。
若 `file_offset = VA`，则应在 `0x0E5DC690` 读到同一字节…
等等，这两种情况**相同**，因为 `VA − RVA = 0x400000` 是常数。

**关键判别**：找任意一个"其值 = 某 RVA"的指针，看它能否解析。

实测（BAP-0004 §2.2）：资源目录在 `file_offset = RVA = 0x0E5C9000` 处
能正确解析。若映射是 `file_offset = VA`，则资源目录应在
`0x0E5C9000` 处 —— 相同。仍然不能区分。

**真正能区分的证据**：节 0 的 `VirtualAddress = 0x00001000`。
若 `file_offset = VA`，则节 0 数据应位于文件偏移 `0x40001000`。
实测 `0x00001000` 处是函数序言 `55 8b ec 83 ec 50`，
而 `0x40001000` 处是什么？**必须查**。

⇒ 这是本讨论的**决定性实验 E-A**。

### 替代假设 H3：`file_offset = RVA` 正确，但节 3–6 是"仅存在于内存的页"

加壳器在运行期把节 3–6 的内容搬到新 VA，原 RawPtr 位置被清零
（避免磁盘上残留解密代码）。那么磁盘原件里节 4/5/6 就是零，
而内存里有内容 —— 我们恰好转储了内存。

⇒ 这与 H1 的结论相同（RawPtr 无效），但**机理不同**，
且意味着"磁盘上读不到资源/导入表"。

---

## 2. 决定性实验与结果

### E-A：`file_offset = RVA` vs `file_offset = VA`

| 位置 | 期望（若 RVA 映射） | 实测 |
|---|---|---|
| `0x00001000` | 节 0 首字节 = 函数序言 | `55 8b ec 83 ec 50 ...` ✅ |
| `0x40001000` | 若是 VA 映射，这里才是节 0 | 待测 |

（结果回填见 §6）

### E-B：既有工具是否踩了 RawPtr 坑

逐份检查我们已有的读镜像脚本：

| 工具 | 用 RawPtr? | 用 RVA? | 受影响 |
|---|---|---|---|
| `extract_image_from_dump.py` | 否（按页整段写） | — | 否 |
| `rtti_inventory.py` | 否 | 全文件扫描 | 否 |
| `vtable_map.py` | 否 | 全文件扫描 | 否 |
| `vtable_annotate.py` | 否 | RVA 直读 | 否 |
| `xref_va.py` | 否 | RVA 直读 | 否 |
| `room_push_encoder.py` | — | 纯 Python 编码 | 否 |
| `hunt_nuked_key.py` | — | 活进程内存扫 | 否 |

⇒ **好消息：现有工具全部按全文件扫描或按 RVA 直读，
没有一个使用 `PointerToRawData`。** 所以 BAP-0004 的发现
**没有推翻任何既有结论**（E3，可复核每份源码）。

### E-C：历次论文中"VA−0x400000"的用法复核

| 论文 | 用法 | 判定 |
|---|---|---|
| BAP-0001 | 无 | 不受影响 |
| BAP-0002 | 无 | 不受影响 |
| BAP-0003 §3.4 | `call [0x0E9DC665]` 槽 → 减 0x400000 得 `0x0E5DC665` | **正确**（VA 是绝对地址，须减 ImageBase 转 RVA） |
| BAP-0003 `SECURITY` | `0x00777048` 当 RVA 直读 | **正确** |
| BAP-0004 | 全篇用 RVA | 正确 |

**唯一的错误在 BAP-0004 之前的中间草稿**（未落盘），
以及 BAP-0004 §0 记录的过程性误判。**已修正，无下游污染。**

---

## 3. 若判断成立，下游会怎样

1. **镜像可用性确认**：`RVA = file_offset`，且文件长度 = `SizeOfImage`。
   这是后续一切工作的基石，现在有了 E3 级证明。
2. **导入表**：`IMPORT` 目录 Size=0，但描述符表完整，
   且只有一个 DLL：**`codoMP_client_shipRetailBase.dll`**。
   ⇒ 这是**客户端唯一的外部依赖**，大厅逻辑的宿主。
   这条对后续"Base.dll 里有什么"的追问是决定性线索。
   *（注：描述符只有 1 项 + 终止项，说明导入表被裁剪到只剩这一条，
     不代表运行时只导入这个 DLL —— 可能是加壳器的"最小导入"策略。）*
3. **资源可读**：节 4 的资源目录完整（5 类），
   `VERSION`/`MANIFEST` 均可解析 ⇒ BAP-0008 可正常展开。
4. **节 6 RWX** 是后续定位"真实代码"的第一候选区。

---

## 4. 最小可证伪实验

**E-A**（已列出）：读 `0x40001000` 处 32 字节。若也是函数序言，
说明镜像里存在两份拷贝，需要重新界定映射。若是垃圾/零，确认 RVA 映射。

**E-D**：找一个"其值为某个已知 RVA"的绝对指针，验证它减/减不 0x400000。

候选：`EXPORT.AddressOfFunctions = 0x00A155D8`（RVA）。
该处应存 22 个函数的 RVA。实测 BAP-0006 已解析成功
（22 个 `Scaleform::` 导出）⇒ **E3，RVA 映射确认**。

---

## 5. 本次讨论改变了什么

1. BAP-0004 §0 新增"我的错误"一节，公开记录偏移误判与纠正。
2. **新增全局纪律**（写入 `00_PAPER_SYSTEM.md`）：
   > PE 里只有 `VirtualAddress` 是 **RVA**（相对 ImageBase）。
   > 任何"VA"必须显式写 `RVA + 0x400000`。
   > 凡出现"VA"字样，论文必须注明它是 RVA 还是绝对地址。
3. 确认**导入表只有一个 DLL：`codoMP_client_shipRetailBase.dll`**。
   这改写了对客户端架构的描述——见 BAP-0009。
4. 确认既有工具**无 RawPtr 依赖**，BAP-0004 的发现不推翻旧结论。

---

## 6. 回填

### E-A 结果

### E-A 结果 — **决定性确认**

| 位置 | 内容 | 判定 |
|---|---|---|
| `0x00001000`（RVA 映射） | `55 8b ec 83 ec 50 a1 40 f2 e3 00 33 c5 89 45 fc` = `push ebp / mov ebp,esp / sub esp,0x50 / mov eax,[img+0x3F240] / xor eax,ebp / mov [ebp-4],eax` —— **标准 MSVC 函数序言 + stack cookie** | **✅ 节 0 在这里** |
| `0x00401000`（VA 映射） | `00 8d 4c 24 68 e8 d6 47 37 00 … 8b e5 5d c3 cc cc` | 是节 0 的**中段**，不是起点 |

⇒ **`file_offset = RVA` 成立，`file_offset = VA` 不成立。**（E3）

### E-D 结果 — 导出表 RVA 逐项反汇编

`AddressOfFunctions = 0x00A155D8`，前 8 项 RVA 处的字节：

| # | RVA | 该处字节 | 反汇编 |
|---|---|---|---|
| 0 | `0x000364F0` | `55 8b ec 8b 45 0c 56 8b f1 8b 4d 08` | `push ebp / mov ebp,esp / mov eax,[ebp+0xC] / push esi / mov esi,ecx / mov ecx,[ebp+8]` ✅ |
| 1 | `0x000364A0` | `55 8b ec 83 ec 20 33 c0 56 8b f1 b9` | `push ebp / mov ebp,esp / sub esp,0x20 / xor eax,eax / push esi / mov esi,ecx` ✅ |
| 2 | `0x000363F0` | `c7 01 2c 35 d6 00 c3` | `mov dword ptr [ecx],0x00D6352C / ret` —— **vftable 写入** ✅ |
| 3 | `0x000363F0` | 同上 | 与 #2 同址（两个析构函数合并） ✅ |
| 4 | `0x00036510` | `e9 8b e1 3e 00` | `jmp 0x004246A0`（尾调用） ✅ |
| 5 | `0x00036470` | `6a 00 6a 00 e8 b7 cf 3e 00 c3` | `push 0 / push 0 / call … / ret` ✅ |
| 6 | `0x00036460` | `6a 00 6a 01 e8 d7 e4 3e 00 c3` | `push 0 / push 1 / call … / ret` ✅ |
| 7 | `0x00036480` | `6a 00 6a 01 e8 c7 d0 3e 00 c3` | `push 0 / push 1 / call … / ret` ✅ |

**8/8 项全部是合法 x86 代码**。⇒ 导出表按 RVA 解析正确（E3/E4）。
若按 `file_offset = VA` 读，这些 RVA 会指向 `0x400364F0` 附近，
内容不可解析。

### E-E 结果 — 字符串字段的双向对照

| 字段 | 值 | 当 RVA | 当 VA |
|---|---|---|---|
| 导入 `Name` | `0x0E5DC66D` | **`b'codoMP_client_shipRetailBase.dll'`** ✅ | `b''` ❌ |
| `EXPORT.Name` | `0x00A156B4` | **`b'codoMP_client_shipRetail.exe'`** ✅ | 乱码 `8b 57 78 50 …` ❌ |
| TLS `StartOfRawData` | `0x0E9C8000` | OUT（文件只到 `0x0E659000`） | `0x0E5C8000` 处全零 → **见 §6.2** |

⇒ 前两条**双向对照，一条通过一条失败**，是最强的单点判据（E3）。

### E-F 结果 — 关键 RVA 直读 vs 减基址

| 描述 | RVA 直读 | RVA−BASE 直读 |
|---|---|---|
| 入口点 `0x0E5DC690` | `ff 15 65 c6 9d 0e` ✅ `call [0x0E9DC665]` | 全零 ❌ |
| 导出表 `0x00A155B0` | `00 00 00 00 da 90 96 60 …` ✅ | 乱码 ❌ |
| 资源目录 `0x0E5C9000` | `…04 00 00 00 00 00 05 00` ✅ | 全零 ❌ |
| TLS 目录 `0x009E8EB8` | `00 80 9c 0e 30 80 9c 0e …` ✅ | 乱码 ❌ |
| DEBUG 目录 `0x008ADA60` | `00 00 00 00 0a 93 96 60 …` ✅ | 乱码 ❌ |
| 首个 DllName `0x0E5DC66D` | `63 6f 64 6f 4d 50 …` ✅ | 数据 ❌ |

**6/6 全部支持 RVA 映射。**（E3）

---

## 6.1 已应用的修订

- `00_PAPER_SYSTEM.md` §3 增加"RVA vs VA"纪律
- BAP-0003 §3.5 目录表的"RVA"列加注：这些是 **RVA**，`file_offset = RVA`
- **BAP-0003 §3.4 的入口点分析确认正确**：`call [0x0E9DC665]` 里是**绝对 VA**，
  转 RVA 后 `file_offset = 0x0E5DC665`。

## 6.2 新发现：TLS 目录字段是 **VA**，且 `StartOfRawData` 越界

TLS 目录 `0x009E8EB8` 的四个字段（按 `IMAGE_TLS_DIRECTORY32`）：

```
StartOfRawData     = 0x0E9C8000   ← 绝对 VA
EndOfRawData       = 0x0E9C8030   ← 绝对 VA
AddressOfIndex     = 0x0196930C   ← 绝对 VA
AddressOfCallBacks = 0x00CADA3C   ← 绝对 VA
```

按 `offset = VA − 0x400000`：

| 字段 | VA | file_offset | 状态 |
|---|---|---|---|
| `StartOfRawData` | `0x0E9C8000` | `0x0E5C8000` | **IN**（节 3，全零，48 字节——正是 TLS 模板数据） |
| `AddressOfIndex` | `0x0196930C` | `0x0156930C` | **IN**（节 2 内） |
| `AddressOfCallBacks` | `0x00CADA3C` | `0x008ADA3C` | **IN**（节 0 内） |

⇒ **TLS 目录字段是标准 VA，我的转换正确。**
`StartOfRawData` 指向节 3（48 字节全零）= TLS 未初始化模板，
符合"C++ 全局对象未构造完"的预期。

⚠ 但注意：`AddressOfCallBacks = 0x00CADA3C`，按 VA 转 RVA 后
`file_offset = 0x008ADA3C`，落在**节 0（代码段）**内。
回调表应在数据节，不应在代码段。**必须实读该处**（下篇）。
