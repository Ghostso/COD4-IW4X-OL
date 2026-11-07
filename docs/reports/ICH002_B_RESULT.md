# ICH-002-B — IW4X Filesystem / IWD / Zone / Asset Loading 差分

ICH002_B_STATUS = COMPLETE

FILESYSTEM =
IW4X_USES_ORIGINAL_FILESYSTEM = YES
IW4X 依赖原始 IW4 filesystem 作为核心读取层。
Game::FileSystem.cpp 绑定全部原始 FS API（FS_FOpenFileRead, FS_Read, FS_FCloseFile, FS_ListFiles, FS_Restart 等）。
Components/Modules/FileSystem.cpp 的所有 File/FileReader/FileWriter 包装均通过原始 FS API 实现读写。
IW4X 未创建独立的 filesystem；所有文件 I/O 仍经过原始 IW4 searchpath 机制。
但 IW4X 通过 hook 原始 FS 启动/路径/Dvar 值来扩展行为。

FILESYSTEM_MODIFICATION =
1. 注册额外搜索目录：userraw（+zonebuilder 模式下 zonedata）
   — FS_AddLocalizedGameDirectory(fs_cdpath, "userraw")
   — source: src/Components/Modules/FileSystem.cpp:247-266, hook at line 454
2. 替换默认安装路径：Sys_DefaultInstallPath_Hk 返回 CWD
   — source: src/Components/Modules/FileSystem.cpp:337-341, hook at line 487
3. 替换 fs_homepath/fs_cwd/fs_basepath dvar 值
   — source: src/Components/Modules/FileSystem.cpp:354-374, hooks at lines 499-502
4. 移除 basePath 有效性检查
   — source: src/Components/Modules/FileSystem.cpp:493-496 (Nop + Jump)
5. 增大 Sys_ListFiles 最大文件数（8191→65528）
   — source: src/Components/Modules/FileSystem.cpp:505-517
6. FS 操作线程安全包装（mutex + sync stubs）
   — source: src/Components/Modules/FileSystem.cpp:9-10, 298-317, hooks at lines 467-481
7. 替换 FS_Alloc/FS_Free 为 IW4X allocator
   — source: src/Components/Modules/FileSystem.cpp:444-445
8. 读文件 fallback 到 BASE_INSTALL 路径
   — source: src/Components/Modules/FileSystem.cpp:343-352, hook at line 490

IWD =
IWD_SUPPORT = YES
IWD_IMPLEMENTATION = ORIGINAL_IW4
IWD_MODIFICATION = EXTEND_ONLY
IWD_ROLE =
IW4X 不自建 IWD 读取器。
所有 IWD 操作通过原始 IW4 函数：
- Game::FS_IsShippedIWD = 0x642440 (src/Game/FileSystem.cpp:29)
- Game::iwd_t 结构 (src/Game/Structs.hpp:6224)
- Game::unzClose (src/Components/Modules/Maps.cpp:94)
IW4X 的 IWD 交互仅限于：
1. 用户地图 IWD 动态注入到 fs_searchpaths 链表头部
2. IWD 释放时的生命周期同步
3. 移除"main 目录无 IWD"限制

IWD_MODIFICATION =
1. UserMap IWD 动态注册到 fs_searchpaths
   — source: src/Components/Modules/Maps.cpp:35-58
   — FS_IsShippedIWD 原始函数调用 (line 44)
   — fs_searchpaths 链表直接操作 (lines 53-54)
2. IWD 释放拦截
   — source: src/Components/Modules/FileSystem.cpp:331-335
   — 调用原始 Z_Free (0x4291A0) (line 334)
   — hook at line 484
3. 移除 IWD 数量限制
   — source: src/Components/Modules/FileSystem.cpp:460-461

ZONE_LOADER =
ZONE_LOADER = ORIGINAL_IW4
ZONE_FORMAT = EXTENDED
IW4X 仍依赖原始 IW4 Zone/Fastfile loader 的核心解析/加载管线。
Game::Database.cpp 绑定原始 DB_LoadXAssets(0x4E5930), DB_ReadXFile(0x445460), DB_FindXAssetHeader(0x407930)。
FastFiles::LoadZonesStub 调用原始 0x5BBAC0 (src/Components/Modules/FastFiles.cpp:453)。
FastFiles 构造函数中所有 Hook 均是对原始函数的包装/前置处理，不是替换。
但 IW4X 扩展了 Zone 格式：
1. 支持 IW4X 自定义 header (XFILE_HEADER_IW4X = 'IW4x')
2. 支持 CODO 版本 zone（version 316-360, 423-461）
3. 对 IW4X zone 添加 XOR/rotate 解密层
4. 添加自定义 zone 路径（patch/dlc/usermaps/iw4x/x86）

ZONE_MODIFICATION =
1. Zone 路径重定向
   — GetZoneLocation 优先检查 usermaps/patch/dlc/ZoneConvert/zone paths
   — source: src/Components/Modules/FastFiles.cpp:244-299
   — hook: Utils::Hook(0x44DA90, GetZoneLocation, HOOK_JUMP) at line 584
2. 版本兼容：CODO zone 版本映射到 IW4 XFILE_VERSION
   — source: src/Components/Modules/FastFiles.cpp:329-346, hook at line 587
3. IW4X zone header 识别与转换
   — source: src/Components/Modules/FastFiles.cpp:348-369, hook at line 590
   — XFILE_HEADER_IW4X / XFILE_VERSION_IW4X 定义: src/STDInclude.hpp:166-167
4. IW4X zone 自定义解密
   — source: src/Components/Modules/FastFiles.cpp:468-484, hook at line 593
5. signed zone 加密解密（RSA + AES-CTR）
   — source: src/Components/Modules/FastFiles.cpp:371-423, hooks at lines 626-636
6. unsigned fastfile (IWffu) 支持去除 hash 检查
   — source: src/Components/Modules/FastFiles.cpp:604-623
7. 自定义 zone 注入到初始加载队列
   — iw4x_patch_mp / iw4x_ui_mp / iw4x_code_post_gfx_mp / iw4x_localized_*
   — source: src/Components/Modules/FastFiles.cpp:136-223, hooks at lines 598-600
8. zone 文件存在性检查扩展（Default + Custom path）
   — source: src/Components/Modules/FastFiles.cpp:509-545, hook at line 578
9. ZoneConvert: x64→x86 fastfile 自动转换
   — 检测 x64 zone, 调用 Unlinker.exe --convert-to IW4
   — source: src/Components/Modules/ZoneConvert.cpp:61-72, 141-145, 1462-1464, 1882-1912
   — SearchPath 返回 zone/iw4x/x86/{group}/
   — ZoneConvert constructor calls zone::convert() (line 1911)

FASTFILE =
FASTFILE_LOADER = ORIGINAL_IW4
FASTFILE_MODIFICATION = EXTEND_IW4
IW4X 不替换原始 fastfile 解析管线。
Game::DB_ReadXFile / DB_ReadXFileUncompressed / DB_LoadXAssets 均为原始函数绑定。
FastFiles::ReadXFileStub 是在原始 DB_ReadXFile 之后追加 IW4X 解密层。
FastFiles::LoadZonesStub 调用原始 DB_LoadXAssets 前置处理。
但 IW4X 在原始 loader 前后插入了格式检测/解密/版本兼容/路径重定向层。

ASSET_DB =
ASSET_DB = ORIGINAL_IW4
ASSET_DB_MODIFICATION = EXTEND_IW4
IW4X 依赖原始 IW4 asset database（DB_XAssetPool, g_poolSize, db_hashTable, g_zones）。
Game::Database.cpp:22-38 直接访问原始全局地址（0x7998A8, 0x7995E8, 0x12412B0, 0x14C0F80）。
IW4X 不建立独立 asset database。
但 IW4X 扩展了 asset lookup 和 pool 管理。

ORIGINAL_LOADER_DEPENDENCY =
IW4X_USES_ORIGINAL_FILESYSTEM = YES
IW4X_USES_ORIGINAL_IWD = YES
IW4X_USES_ORIGINAL_ZONE_LOADER = YES
IW4X_USES_ORIGINAL_ASSET_DB = YES

IW4X_LOADER_MODEL =
Original IW4 loader + additional compatibility/extensions
IW4X 的 loader 模型是"原始 loader 前后插层"，不是独立替换。

CORE_FINDING =
IW4X 的数据加载链完整依赖原始 IW4 的 filesystem/IWD/Zone/Fastfile/AssetDB 基础设施。
它通过 hook 原始函数的入口（而非替换整个函数体）来插入额外行为：
- FileSystem: 额外目录注册、路径重定向、文件数扩展
- IWD: 动态 usermap IWD 注入 fs_searchpaths
- Zone/Fastfile: 格式扩展（IW4x header + CODO version + 自定义解密）+ 路径扩展
- AssetDB: hook DB_FindXAssetHeader 支持 IW4X 自定义 asset handler + 扩大 asset pool
模型：Original IW4 loader + compatibility extensions。
IW4X ZoneConvert 是唯一的"非运行时加载"组件（启动时转换 x64 fastfile），但它转换后仍由原始 loader 消费。

CODOL_RELEVANCE =
CODOL 如需复用此模式，核心约束是：不能替换原始 loader 管线，只能在原始函数前后插入 hook。
IW4X 的 Zone 格式扩展（自定义 header + 自定义解密）是为承载 IW4X 专有资产。
CODOL 需要评估是否复用此格式或创建独立格式。

NEXT_STEP =
ICH-003 应分析 IW4X 的网络层 / 会话管理 / 服务器列表与原始 IW4 的差异，
或分析 IW4X 的 ZoneBuilder 组件（自建 fastfile 构建器）。
---

## 机制溯源表

### FS-01. 额外搜索目录注册

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::RegisterFolders / StartupStub
line number:        258-266 / 268-283
hook line:          454 (Utils::Hook(0x482647, StartupStub, HOOK_JUMP))
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          FS_AddLocalizedGameDirectory(fs_cdpath, "userraw") for cdpath/basepath/homepath。
                    StartupStub 是 naked asm：call RegisterFolders → jmp original 0x48264D。
                    在原始 FS_Startup 中执行，注册后返回原始流程。
```

### FS-02. 默认安装路径替换

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::Sys_DefaultInstallPath_Hk
line number:        337-341
hook line:          487 (Utils::Hook(0x4326E0, ..., HOOK_JUMP))
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          返回 std::filesystem::current_path().string() 替换原始安装路径。
                    使 IW4X 可从非标准目录启动。
```

### FS-03. fs_homepath / fs_cwd / fs_basepath dvar 重定向

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    Sys_HomePath_Hk / Sys_Cwd_Hk / Sys_DefaultCDPath_Hk
line number:        354-374
hook lines:         499-502
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          HomePath 返回 Utils::GetBaseFilesLocation()（BASE_INSTALL 环境变量）。
                    Cwd 返回 Sys_DefaultInstallPath_Hk()。
                    这些是原始 IW4 dvar 注册时的默认值 hook。
```

### FS-04. basePath 有效性检查移除

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::FileSystem (constructor)
line number:        493-496
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Nop 0x4290D8 (5 bytes) + Set 0x4290DF = 0xEB (jump)。
                    绕过 FS_IsBasePathValid 检查以支持容器化运行。
```

### FS-05. 文件列表上限扩展

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::FileSystem (constructor) / Hunk_UserCreate_Stub
line number:        505-517 / 376-380
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          将 NEW_MAX_FILES_LISTED (8191*8=65528) 写入固定地址。
                    Hunk_UserCreate_Stub 传入 maxSize*8 倍以适配更大的文件列表。
```

### FS-06. FS 线程安全包装

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FsStartupSync / FsRestartSync / FsShutdownSync / DelayLoadImagesSync / LoadTextureSync
line number:        298-329
hook lines:         467-481
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          在原始 FS_InitFilesystem / FS_Restart / FS_Shutdown / DB_LoadDelayedImages
                    调用前后加 std::lock_guard(FSMutex)。
                    不修改原始函数逻辑，仅保证线程安全。
```

### FS-07. FS allocator 替换

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    AllocateFile / FreeFile
line number:        444-445 (hooks)
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          将原始 FS_Alloc / FS_FreeFile 替换为 MemAllocator.allocateArray/free。
                    使 IW4X 的 FileSystem::File 读取的内存由 IW4X allocator 管理。
```

### FS-08. 读文件 fallback 到 BASE_INSTALL

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FS_FileOpenReadText_Hk
line number:        343-352
hook line:          490
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          优先尝试 BASE_INSTALL 路径 + file，如果存在则打开；否则回退原始路径。
                    支持 IW4X rawfiles 安装在独立目录的场景。
```

### FS-09. exec 白名单移除

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::FileSystem (constructor)
line number:        456-458
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Nop 0x609685 (5 bytes) + Nop 0x60968C (2 bytes)。
                    移除 FS 的 exec 文件白名单检查。
```

### FS-10. IWD 数量限制移除

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::FileSystem (constructor)
line number:        460-461
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Nop 0x642A4B (5 bytes)。
                    跳过原始 "no iwd files found in main" 的致命错误检查。
```

---

### IWD-01. UserMap IWD 动态注入

```
source file:        src/Components/Modules/Maps.cpp
symbol/function:    Maps::UserMapContainer::loadIwd
line number:        35-58
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          构建路径 usermaps/{mapname}/{mapname}.iwd。
                    调用原始 FS_IsShippedIWD(0x642440) 解析 IWD。
                    成功后创建 Game::searchpath_s 并插入 fs_searchpaths 链表头部。
                    freeIwd (lines 78-102) 在 FS_Restart 时卸载。
```

### IWD-02. IWD 释放生命周期同步

```
source file:        src/Components/Modules/FileSystem.cpp
symbol/function:    FileSystem::IwdFreeStub
line number:        331-335
hook line:          484
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          在原始 IWD free 函数调用前，通知 Maps::GetUserMap()->handlePackfile(iwd)。
                    使 UserMapContainer 知道其 IWD 已被原始系统释放。
                    然后调用原始 free (0x4291A0)。
```

---

### FF-01. Zone 路径重定向

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    FastFiles::GetZoneLocation
line number:        244-299
hook line:          584 (Utils::Hook(0x44DA90, GetZoneLocation, HOOK_JUMP))
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          按优先级检查:
                    1. fs_game (mod)
                    2. usermaps/{zone}/{zone}.ff
                    3. FastFiles::ZonePaths (patch/dlc)
                    4. ZoneConvert::SearchPath (zone/iw4x/x86/)
                    5. 原始 zone/{lang}/
                    返回第一个存在的 .ff 文件路径前缀。
```

### FF-02. Zone 版本兼容（CODO→IW4）

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    FastFiles::ReadVersionStub
line number:        329-346
hook line:          587
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          读取原始 zone version。
                    如果 version 在 [316,360] 或 [423,461] 范围内，改写为 XFILE_VERSION (276)。
                    使原始 loader 认为这是标准 IW4 zone。
                    Zones::SetVersion() 保存真实版本供后续 Zones.cpp 资产加载使用。
```

### FF-03. IW4X zone header 识别与转换

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    FastFiles::ReadHeaderStub
line number:        348-369
hook line:          590
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          读取 8 字节 header。
                    如果 header[0] == XFILE_HEADER_IW4X ('IW4x')，设 IsIW4xZone = true。
                    验证 XFILE_VERSION_IW4X (3)。
                    将 header 改写为 XFILE_MAGIC_UNSIGNED ('IWff0100')。
                    使原始 loader 接受 IW4X 自定义 zone 格式。
```

### FF-04. IW4X zone 自定义解密

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    FastFiles::ReadXFileStub / ReadXFileHeader
line number:        456-484 / 318-327
hook line:          593 (Utils::Hook(Game::DB_ReadXFile, ReadXFileStub, HOOK_JUMP))
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          先调用原始 DB_ReadXFile。
                    如果 IsIW4xZone，对 buffer 逐字节执行:
                    XOR LastByteRead → RotLeft 4 → XOR 0xFF → RotRight 6。
                    更新 LastByteRead 作为链式解密状态。
                    ReadXFileHeader 额外读取 1 字节 pad 以对齐。
```

### FF-05. Signed fastfile 加密解密

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    AuthLoadInitCrypto / AuthLoadInflateCompare / InflateInitDecrypt / AuthLoadInflateDecryptBase
line number:        371-437
hook lines:         626-636
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Zones::Version >= 319 时:
                    1. AuthLoadInitCrypto: 读 256 字节加密 key, RSA decrypt with embedded ZoneKey。
                    2. InflateInitDecrypt: CTR 解密 inflate 输入。
                    3. AuthLoadInflateCompare: CTR 解密 hash 对比输入。
                    4. AuthLoadInflateDecryptBase: CTR 解密 8192 字节块。
                    全部在调用原始函数前执行解密，然后交给原始函数继续处理。
```

### FF-06. Unsigned fastfile 支持去除 hash 检查

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    FastFiles::FastFiles (constructor)
line number:        604-623
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          多处 Nop/Set 绕过原始 hash 检查。
                    允许加载 IWffu (unsigned) 格式的 fastfile。
```

### FF-07. 自定义 zone 注入到初始加载队列

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    LoadInitialZones / LoadDLCUIZones / LoadGfxZones / LoadLocalizeZones
line number:        136-223
hook lines:         598-600
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Hook 原始 zone 加载调用点。
                    在原始 XZoneInfo 数组后追加:
                    - iw4x_patch_mp
                    - iw4x_ui_mp (或 fallback dlc1_ui_mp + dlc2_ui_mp)
                    - iw4x_code_post_gfx_mp
                    - iw4x_localized_{lang}
                    然后调用 Game::DB_LoadXAssets (0x4E5930)。
                    全部最终由原始 DB loader 处理。
```

### FF-08. Zone 文件存在性检查扩展

```
source file:        src/Components/Modules/FastFiles.cpp
symbol/function:    DB_FileExists_Hk / Sys_CreateFile_Stub
line number:        509-545 / 548-569
hook lines:         576-578
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          先用 DefaultInstallPath，再用 HomePath 检查 .ff 是否存在。
                    Sys_CreateFile fallback 到 HomePath 和 ZoneBuilder 路径。
```

### FF-09. ZoneConvert 启动时 x64→x86 fastfile 转换

```
source file:        src/Components/Modules/ZoneConvert.cpp
symbol/function:    zone::convert / ZoneConvert::ZoneConvert (constructor)
line number:        1811-1912
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          启动时扫描 zone/ 目录下的 x64 fastfile (IWff0100 magic + version 276)。
                    调用 Unlinker.exe --game IW4MS --convert-to IW4 将 x64 zone 转为 x86。
                    输出到 zone/iw4x/x86/{group}/。
                    ZoneConvert::SearchPath (lines 1902-1906) 返回此路径。
                    FastFiles::GetZoneLocation 使用此路径作为搜索目标。
                    转换后的文件由原始 IW4 loader 消费。
                    注意: ZoneConvert 是启动阶段一次性转换，不是运行时动态转换。
```

---

### AH-01. DB_FindXAssetHeader hook（自定义 asset lookup）

```
source file:        src/Components/Modules/AssetHandler.cpp
symbol/function:    AssetHandler::FindAssetStub
line number:        160-223 (implementation) / 564 (hook install)
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          naked asm hook 替换原始 DB_FindXAssetHeader 入口。
                    先检查 HasThreadBypass():
                    - bypass=true → 跳过自定义 handler, fallback 到原始 0x40793B
                    - bypass=false → call AssetHandler::FindAsset (type callbacks)
                    如果自定义 handler 返回有效 asset → 直接返回。
                    如果 ShouldSearchTempAssets → 检查 TemporaryAssets map。
                    否则 → jmp 0x40793B 继续原始 DB_FindXAssetHeader 后半段。
                    这是 IW4X 对原始 asset lookup 的"前置拦截"，不是替换。
```

### AH-02. DB_AddXAsset hook（自定义 asset 注入）

```
source file:        src/Components/Modules/AssetHandler.cpp
symbol/function:    AssetHandler::AddAssetStub
line number:        567 (hook) / implementation in 180-220
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          拦截原始 DB_AddXAsset，允许 IW4X 将自定义 asset 写入原始 pool。
```

### AH-03. Asset entry pool 重分配

```
source file:        src/Components/Modules/AssetHandler.cpp
symbol/function:    AssetHandler::reallocateEntryPool
line number:        503-548
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          分配更大的 XAssetEntry pool (789312 或 1183968 条)。
                    用 Utils::Hook::Set 将 23 个固定地址的 pool 指针替换为新 pool。
                    原始 pool 全局地址不变，仅内容指针被重定向。
```

### AH-04. Asset pool 尺寸扩展

```
source file:        src/Components/Modules/AssetHandler.cpp
symbol/function:    AssetHandler::AssetHandler (constructor)
line number:        600-624
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Game::ReallocateAssetPool(type, newSize) 修改原始 DB_XAssetPool[type]
                    和 g_poolSize[type]（地址 0x7998A8 / 0x7995E8）。
                    为 IW4X 增加的自定义 asset 提供更多空间。
```

### AH-05. 原始 asset 查找 fallback

```
source file:        src/Components/Modules/AssetHandler.cpp
symbol/function:    AssetHandler::FindOriginalAsset
line number:        464-471
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          SetBypassState(true) → 调用原始 Game::DB_FindXAssetHeader → SetBypassState(false)。
                    用于 IW4X 需要直接访问原始 asset 的场景。
```

---

## 分类汇总

### RESTORE_ORIGINAL

- 无独立 RESTORE_ORIGINAL 机制。
- IW4X 调用原始 CRT (ICH-002-A) 和原始 FS/Zone/AssetDB (ICH-002-B)，但这些是依赖，不是"恢复被损坏的原始环境"。

### EXTEND_IW4

以下机制属于"在原始 IW4 管线上添加兼容/扩展层"：

| # | 机制 | source |
|---|------|--------|
| FS-01 | 额外搜索目录 (userraw) | FileSystem.cpp:258-266 |
| FS-02 | 默认安装路径替换 | FileSystem.cpp:337-341 |
| FS-03 | fs_homepath/fs_cwd 重定向 | FileSystem.cpp:354-374 |
| FS-04 | basePath 检查移除 | FileSystem.cpp:493-496 |
| FS-05 | 文件列表上限扩展 | FileSystem.cpp:505-517 |
| FS-08 | BASE_INSTALL fallback | FileSystem.cpp:343-352 |
| FS-09 | exec 白名单移除 | FileSystem.cpp:456-458 |
| FS-10 | IWD 数量限制移除 | FileSystem.cpp:460-461 |
| IWD-01 | UserMap IWD 动态注入 | Maps.cpp:35-58 |
| FF-01 | Zone 路径重定向 | FastFiles.cpp:244-299 |
| FF-02 | Zone 版本兼容 | FastFiles.cpp:329-346 |
| FF-03 | IW4X zone header 识别 | FastFiles.cpp:348-369 |
| FF-04 | IW4X zone 解密 | FastFiles.cpp:456-484 |
| FF-05 | Signed fastfile 解密 | FastFiles.cpp:371-437 |
| FF-06 | Unsigned fastfile 支持 | FastFiles.cpp:604-623 |
| FF-07 | 自定义 zone 注入 | FastFiles.cpp:136-223 |
| FF-08 | Zone 存在性检查扩展 | FastFiles.cpp:509-569 |
| FF-09 | ZoneConvert x64→x86 | ZoneConvert.cpp:1811-1912 |
| AH-01 | DB_FindXAssetHeader hook | AssetHandler.cpp:160-223 |
| AH-02 | DB_AddXAsset hook | AssetHandler.cpp:567 |
| AH-03 | Asset entry pool 重分配 | AssetHandler.cpp:503-548 |
| AH-04 | Asset pool 尺寸扩展 | AssetHandler.cpp:600-624 |
| AH-05 | 原始 asset fallback | AssetHandler.cpp:464-471 |

### REPLACE_PLATFORM

- 无。IW4X 未替换原始 filesystem/IWD/Zone/AssetDB 平台。
- CEG/Steam 等平台绕过已在 ICH-002-A 中分析，不属于本 ICH 范围。

### IW4X_ONLY

| # | 机制 | source |
|---|------|--------|
| FS-06 | FS 线程安全包装 | FileSystem.cpp:298-329 |
| FS-07 | FS allocator 替换 | FileSystem.cpp:444-445 |
| IWD-02 | IWD 释放同步 | FileSystem.cpp:331-335 |

这些是 IW4X 自身基础设施，不修改原始 IW4 行为。

### UNKNOWN

- 0x6BAC0F 处被 patch 前的原始指令内容（host binary 不在本仓库）
- Unlinker.exe 内部转换算法（仅确认调用参数 --convert-to IW4）
- IW4X zone 自定义解密的具体设计意图（仅确认算法实现）

---

## 控制流

```
External Bootstrap
      ↓
IW4X DllMain
      ↓
Environment                                    [ICH-002-A]
      ↓
Patches                                        [ICH-002-A]
      ↓
Original IW4 CRT                               [ICH-002-A]
      ↓
Original IW4 Filesystem                        [EXTEND: FS-01~10]
  ├─ FS_Startup (0x4823A0)                     [IW4X sync wrapper: FS-06]
  ├─ RegisterFolders → userraw                 [EXTEND: FS-01]
  ├─ Sys_DefaultInstallPath → CWD              [EXTEND: FS-02]
  ├─ fs_basepath/homepath/cwd → redirected     [EXTEND: FS-03]
  └─ FS allocator → IW4X MemAllocator          [IW4X_ONLY: FS-07]
      ↓
Original IW4 IWD                               [EXTEND: IWD-01, IWD-02]
  ├─ FS_IsShippedIWD (0x642440)                [原始]
  ├─ UserMap IWD → fs_searchpaths inject      [EXTEND: IWD-01]
  └─ IwdFreeStub → original Z_Free (0x4291A0)  [IW4X_ONLY: IWD-02]
      ↓
Original/Extended Zone Loader                  [EXTEND: FF-01~09]
  ├─ GetZoneLocation (0x44DA90) → redirected   [EXTEND: FF-01]
  ├─ ZoneConvert → zone/iw4x/x86/              [EXTEND: FF-09]
  ├─ ReadVersionStub → version compat          [EXTEND: FF-02]
  ├─ ReadHeaderStub → IW4x header → IWff magic [EXTEND: FF-03]
  ├─ AuthLoadInitCrypto → RSA decrypt key      [EXTEND: FF-05]
  ├─ AuthLoadInflateCompare → CTR decrypt      [EXTEND: FF-05]
  ├─ DB_ReadXFile → ReadXFileStub              [EXTEND: FF-04]
  │    → original read + IW4X XOR/rotate decrypt
  ├─ DB_LoadXAssets (0x4E5930)                 [原始]
  │    ← LoadInitialZones injects iw4x zones   [EXTEND: FF-07]
  └─ DB_BuildOSPath → Default/Custom path      [EXTEND: FF-08]
      ↓
Original/Extended Asset DB                     [EXTEND: AH-01~05]
  ├─ DB_XAssetPool (0x7998A8) → reallocated    [EXTEND: AH-04]
  ├─ g_poolSize (0x7995E8) → expanded          [EXTEND: AH-04]
  ├─ XAssetEntry pool → 789K entries           [EXTEND: AH-03]
  ├─ DB_FindXAssetHeader (0x407930)            [原始]
  │    ← FindAssetStub intercepts first        [EXTEND: AH-01]
  │       → IW4X TypeCallbacks                 [IW4X custom]
  │       → TemporaryAssets                    [IW4X custom]
  │       → fallback to original 0x40793B      [原始]
  ├─ DB_AddXAsset (0x5BB650) → AddAssetStub    [EXTEND: AH-02]
  └─ DB_EnumXAssetEntries → original pool      [原始]
      ↓
IW4 Runtime
```

---

## 分析范围声明

- 本次分析仅针对 IW4X Client commit `0699a7e5716ded53bcfa6748bcb89a535f8f39f0` 的源码。
- 所有 Q1-Q5 均已明确回答，达到强制收口条件。
- 未分析 Renderer / Steam / Network / UI / Game Components / 所有 AssetHandler 子类 / 全部 Functions.cpp / CODOL。
- 未运行任何程序、未动态调试、未编译、未修改任何源码文件。
