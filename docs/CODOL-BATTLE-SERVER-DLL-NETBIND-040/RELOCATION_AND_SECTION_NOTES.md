# RELOCATION_AND_SECTION_NOTES — 节区 / 重定位 / 保护区

## 1. 地址约定

- ImageBase = `0x10000000` (ImageBase 应用后的运行时 VA; 文件内不存储此值, 由 PE 头 `ImageBase` 决定)。
- **RVA ≠ 文件偏移**: 必须按节区表换算。`.text` 的 `RVA_Start=0x1000`, `Raw=0x400`, 故 `.text` 内 `file_off = RVA - 0xC00`。
  例: `recvfrom` 调用 RVA `0x235F7E` → 文件偏移 `0x23537E`。
- 本报告所有 "VA" 均为 **未重定位** 的 `ImageBase + RVA` (即文件内的地址字面量)。若 DLL 在运行时被重定位 (DLL 有 `DllCharacteristics=0x140`, 支持 ASLR), 实际 VA 会平移, 但 IAT 槽的**相对 RVA 不变**。

## 2. 节区表 (来自目标 DLL PE 头)

| 节区 | VA(RVA) | VSize | Raw | RSize | 权限 | 熵 | 可分析性 |
|---|---:|---:|---:|---:|---|---:|---|
| `.text` | 0x1000 | 0x742000 | 0x400 | 0x741C00 | R+X | 6.994 | 主要静态分析区 |
| `.rdata` | 0x743000 | 0x26C000 | 0x742000 | 0x26B200 | R | 4.903 | 字符串/只读表 |
| `.data` | 0x9AF000 | 0x153000 | 0x9AD200 | 0x14AA00 | R+W | 2.162 | 全局数据 |
| `.idata2` | 0xB02000 | 0x4EBA | 0xAF7C00 | 0x5000 | R+W | 5.403 | **隐藏导入表 (本任务关键)** |
| `.rsrc2` | 0xB07000 | 0x2B9C | 0xAFCC00 | 0x2C00 | R+W | 5.482 | 资源 |
| `.tls` | 0xB0A000 | 0xED3000 | 0xAFF800 | 0xED2600 | R+X | **7.532** | **不可直接线性反汇编** |
| `.tvm0` | 0x19DD000 | 0x1F5E000 | 0x19D1E00 | 0x1F5D600 | R+X | **7.023** | **VM/受保护, 不可当普通 x86** |
| `.reloc` | 0x393B000 | 0x56000 | 0x392F400 | 0x55E00 | R | 6.588 | 重定位 |

> 数据目录只声明了 7 项: EXPORT(0x952D60/0x41)、IMPORT(0x9F67B8/0x3C)、RESOURCE(0xB07000/0x2B9C)、SECURITY、BASERELOC(0x393B000/0x55D4C)、DEBUG(0x746060/0x1C)、IAT(0xB02000/0xC00)。**注意 IAT 目录大小 0xC00 = 768 槽, 而 IMPORT 目录仅 0x3C = 3 个描述符** —— 这正是本任务的突破口。

## 3. 重定位

- 块数 4819, 条目 156506; 类型 3 (IMAGE_REL_BASED_HIGHLOW) 153482, 类型 0 (padding) 3024。
- `.idata2` 范围内被重定位的条目: 65。
- 含义: DLL 可被 ASLR 重定位; 内部绝对地址在加载时由 loader 修正。本报告引用的是**文件内的重定位前字面量**。
- IAT 槽本身存放的是导入名指针 (链接期) / 或解析后的函数地址 (运行期)。文件内看到的是**链接期占位**: NAME 槽 = 指向 `.idata2` 内 `IMAGE_IMPORT_BY_NAME` 的 RVA; ORDINAL 槽 = `0x80000000 | 序号`。

## 4. 保护区

### .tvm0 (RVA 0x19DD000, 31.4MB, 熵 7.023)
- 3 个 DLL 导出**全部**位于 `.tvm0`: ordinal 1 = RVA `0x1D6582C`, ordinal 2 = RVA `0x203D4F7`, ordinal 3 = RVA `0x1AA13B0` (均无名字)。
- 入口点 `AddressOfEntryPoint = 0x149C` 的第一条指令即 `jmp 0x11AA13B0` (RVA 0x1AA13B0, 即 ordinal 3, 位于 `.tvm0`)。**因此 DLL 的正常执行流从入口点立即进入 `.tvm0` VM。**
- 本报告**未**对 `.tvm0` 做线性反汇编, **未**据 E8/E9 字节推断任何调用关系。仅引用 PE 结构事实 (节区表、导出表、入口点机器码)。

### .tls (RVA 0xB0A000, 15.5MB, 熵 7.532)
- 线性反汇编前 0x2000 字节仅覆盖 564 字节 (039 记录), 明确不是正常 x86。本报告**未**将其按代码分析。
- PE `DIRECTORY_ENTRY_TLS` 未在本 DLL 中解析出回调 (无 TLS 目录), 但存在名为 `.tls` 的大节区 (命名与 PE TLS 无关, 属加壳者自定义节名)。

## 5. 本任务使用的区域

仅使用 `.text` (RVA/机器码证据)、`.idata2` (隐藏导入表)、`.rdata` (字符串归属)、`.data` (常规导入描述符)、`.reloc` (重定位统计)。`.tvm0`/`.tls` 只做结构引用, 不做语义反汇编。
