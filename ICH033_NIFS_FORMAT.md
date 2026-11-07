# ICH-033 — IFS2 / NIFS 格式与 FF 映射逆向

## 核心发现

### .ifs 文件 = NIFS 容器 = 多个 IWff FastFile 数据块的封装

**NIFS 容器格式已确认：**

```text
Header (172 bytes / 0xAC):
  +0x00: magic "nifs" (4 bytes)
  +0x04: header_size = 172 (constant across all files)
  +0x08: format_version = 0x00050000 (5.0)
  +0x0C: total_data_size (correlates with file size)
  +0x14: compressed_size
  +0x34: entry_count (~329-814, matches .ff file count)
  +0x3C: chunk_count
  +0x54: alignment = 0x4000 (16KB)

Manifest (starting at ~+0x90):
  Null-separated path strings:
    "ff_dlc17_common.lst" (manifest name)
    "client_shipRetail/chinese/code_pre_gfx_mp.ff"
    "client_shipRetail/chinese/code_post_gfx_mp.ff"
    "client_shipRetail/chinese/common_mp_reload.ff"
    ... (one entry per .ff file)

Data blocks:
  Each .ff file stored as IWff0100 format block
  10 manifest entries = 10 IWff blocks in sample file
```

### IWff0100 = IW4 FastFile 格式（版本 0100）

```text
IWff magic: 49 57 66 66 ("IWff")
Version: 30 31 30 30 ("0100")
数据块紧跟 manifest 之后
每个 IWff block 对应 manifest 中的一个 .ff 条目
```

### IFS2.dll 角色

```text
CreateIFSLibDll():
  1. LoadLibrary("i") → 加载自身内部 IFS 引擎
  2. GetProcAddress("CreateDebugInterface") → 调试接口
  3. 返回 8 字节 handle: [vtable, IFS_object]
  4. IFS Handle VTable: 15 个方法 (0x10080F3C)

DestoryIFSLibDll():
  1. 调用 [handle→IFS_object→vtable+0x38] (析构)
  2. 清空 handle

IFSDllVerifyApiCompatable():
  简单检查参数 == 1, 返回 TRUE/FALSE

IFS2 角色 = VIRTUAL_FS + UNPACKER
  输入: .ifs 文件路径
  输出: 虚拟 .ff 文件（Engine 通过 IFS2 读取 .ff 内容）
  机制: IFS2 解析 NIFS manifest → 将 .ff 路径映射到 .ifs 内的 IWff 数据块
```

### code_pre_gfx_mp.ff 映射确认

```text
ff_init_common_gfx_V109.ifs (40,412,080 bytes) 包含:
  Manifest entry: "client_shipRetail/chinese/code_pre_gfx_mp.ff"
  IWff data block: 存在于文件内（10 个 IWff 块之一）

映射: code_pre_gfx_mp.ff → ff_init_common_gfx_V109.ifs 内的某个 IWff 块
```

## 格式总结

```text
.ifs 文件 = NIFS 容器
  = [NIFS header (172 bytes)]
  + [manifest (null-separated .ff paths)]
  + [多个 IWff0100 数据块]

每个 IWff 块 = 一个编译后的 .ff fastfile
Engine 的 loadfastfile("code_pre_gfx_mp.ff")
  → IFS2 在 NIFS manifest 中查找该路径
  → 定位对应的 IWff 数据块
  → 返回 FF 数据给 Zone/Asset 系统
```

## IFS2 本地测试可能性

IFS2.dll 的 `CreateIFSLibDll()` 使用 `LoadLibrary("i")` 
这是对自身或内部模块的调用。IFS2 可能可以独立打开本地 .ifs 文件，
但需要通过 CreateIFSLibDll → 获取 handle → 通过 vtable 方法操作。

测试方法：通过代码调用 IFS2 的 vtable 方法传入 .ifs 路径，
观察是否能读取 manifest 和 IWff 数据。

## FF Recovery Path

```text
路径 1（最直接）: 从 .ifs 提取 IWff 块 → 保存为独立 .ff 文件
  - 读取 NIFS manifest 获取 .ff 路径列表
  - 定位每个 .ff 对应的 IWff 数据块
  - 提取 IWff 数据 → 写为独立 .ff 文件
  - Engine 即可正常加载

路径 2（虚拟 FS）: 实现 IFS2 兼容层
  - 拦截 Engine 的文件请求
  - 从 .ifs 容器中读取对应 IWff 数据
  - 返回给 Engine

路径 3（最小补丁）: 修改 Engine 的 FF 加载路径
  - 不推荐（需要修改原始 EXE）
```

## 最终字段

```text
ICH033_STATUS = COMPLETE

NIFS_FORMAT = CONFIRMED
  Magic: "nifs"
  Header: 172 bytes
  Manifest: null-separated .ff paths
  Data: IWff0100 blocks

IFS2_ROLE = VIRTUAL_FS + UNPACKER
  IFS2 提供 NIFS 容器的虚拟文件系统接口
  Engine 通过 IFS2 读取 .ff 内容

IFS2_INPUT = .ifs file path (NIFS container)
IFS2_OUTPUT = Virtual .ff file content (IWff data blocks)

IFS2_LOCAL_OPEN = UNKNOWN (not yet tested)
FF_IFS_MAPPING = CONFIRMED
  code_pre_gfx_mp.ff → ff_init_common_gfx_V109.ifs

IFS2_DEPENDENCY = Unknown (needs local testing)

FF_RECOVERY_PATH = 
  Option 1: Extract IWff blocks from .ifs → save as .ff files
  Option 2: Implement IFS2 virtual FS compatibility layer
  Option 3: Modify Engine (not recommended)

NEXT_TARGET = 
  Extract IWff blocks from .ifs containers → create local .ff files
  → Test Engine with .ff files available → monitor FastFile/Zone loading
```
