# TARGET_DLL_PE_MAP — 主 DLL PE 结构与地址映射

## 1. 指纹与 PE 头

| 项 | 值 |
|---|---|
| 文件 | `COD OL\codoMP_client_shipRetailBase.dll` |
| 大小 | 60,327,992 B |
| SHA256 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |
| Machine | `0x14C` (i386) |
| TimeDateStamp | `0x5E551315` |
| Characteristics | `0x2102` |
| ImageBase | `0x10000000` |
| SizeOfImage | `0x3991000` |
| EntryPoint | `0x149C` |
| SectionAlignment | `0x1000` |
| FileAlignment | `0x200` |
| DllCharacteristics | `0x140` |

## 2. 数据目录

| 目录 | RVA | Size |
|---|---:|---:|
| EXPORT | `0x952D60` | `0x41` |
| IMPORT | `0x9F67B8` | `0x3C` |
| RESOURCE | `0xB07000` | `0x2B9C` |
| SECURITY | `0x3985248` | `0x35F0` |
| BASERELOC | `0x393B000` | `0x55D4C` |
| DEBUG | `0x746060` | `0x1C` |
| IAT | `0xB02000` | `0xC00` |
| TLS | 无目录项 | — |

## 3. 节区

| 节区 | VA | VSize | RAW | RSize | 权限 | 熵 | 判定 |
|---|---:|---:|---:|---:|---|---:|---|
| `.text` | `0x1000` | `0x742000` | `0x400` | `0x741C00` | R+X | 6.994 | 主要可分析代码 |
| `.rdata` | `0x743000` | `0x26C000` | `0x742000` | `0x26B200` | R | 4.903 | 字符串/表 |
| `.data` | `0x9AF000` | `0x153000` | `0x9AD200` | `0x14AA00` | R+W | 2.162 | 全局数据 |
| `.idata2` | `0xB02000` | `0x4EBA` | `0xAF7C00` | `0x5000` | R+W | 5.403 | 导入/IData |
| `.rsrc2` | `0xB07000` | `0x2B9C` | `0xAFCC00` | `0x2C00` | R+W | 5.482 | 资源 |
| `.tls` | `0xB0A000` | `0xED3000` | `0xAFF800` | `0xED2600` | R+X | **7.532** | 高度加密/保护，不可直接反汇编 |
| `.tvm0` | `0x19DD000` | `0x1F5E000` | `0x19D1E00` | `0x1F5D600` | R+X | 7.023 | VM/保护，不可直接反汇编 |
| `.reloc` | `0x393B000` | `0x56000` | `0x392F400` | `0x55E00` | R | 6.588 | 重定位 |

## 4. 重定位摘要

- 4819 个重定位块，156,506 个条目。
- 类型分布：`{3: 153482, 0: 3024}`。
- 类型 3 = `IMAGE_REL_BASED_HIGHLOW`，说明存在大量优先 VA 数据指针，必须结合重定位才能解释数据表引用。

## 5. 导入/导出

### 常规导入

| DLL | 导入 |
|---|---|
| `kernel32.dll` | `LoadLibraryA`、`GetProcAddress` |
| `libcef.dll` | `cef_string_utf16_clear` |

**注意：** 网络 API 不在常规导入表中，而是在 `.rdata/.idata2` 中作为字符串出现，表明使用动态解析或延迟绑定。

### 导出

| 序号 | RVA |
|---:|---:|
| 1 | `0x1D6582C`（位于 `.tvm0`） |
| 2 | `0x203D4F7`（位于 `.tvm0`） |
| 3 | `0x1AA13B0`（位于 `.tvm0`） |

**判定：** 三个导出都位于 `.tvm0`，进一步表明外部入口可能通过 VM 层暴露。

## 6. 地址换算规则

```text
RVA → file offset:
  file_offset = PointerToRawData + (RVA - VirtualAddress)   (目标节区)
VA = ImageBase + RVA = 0x10000000 + RVA
```

**不得**使用 EXE 的 `file_offset = RVA` 约定。

## 7. 交叉引用

- `evidence/pe_map.txt`
- `evidence/tls_reloc_resources.txt`
- `scripts/pe_map.py`
