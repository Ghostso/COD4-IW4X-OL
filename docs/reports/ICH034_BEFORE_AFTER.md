# ICH-034 — NIFS → IWff 原始 FastFile 恢复与 Engine 加载验证

## ★ 10 个 .ff 文件成功从 .ifs 提取并部署！★

### 提取结果

所有 10 个 .ff 文件从 ff_init_common_gfx_V109.ifs (40.4 MB) 成功提取：

| # | 文件名 | 大小 | IWff 魔数 |
|---|--------|------|----------|
| 0 | code_post_gfx_default_mp.ff | 33,093 | ✅ IWff0100 |
| 1 | code_post_gfx_mp.ff | 10,012,485 | ✅ IWff0100 |
| 2 | **code_pre_gfx_mp.ff** | **74,085** | ✅ IWff0100 |
| 3 | common_mp_reload.ff | 24,885 | ✅ IWff0100 |
| 4 | development_mp.ff | 57,685 | ✅ IWff0100 |
| 5 | localized_code_post_gfx_mp.ff | 762,885 | ✅ IWff0100 |
| 6 | localized_code_pre_gfx_mp.ff | 24,885 | ✅ IWff0100 |
| 7 | localized_ui_mp.ff | 147,893 | ✅ IWff0100 |
| 8 | mp_playlists.ff | 49,493 | ✅ IWff0100 |
| 9 | ui_mp.ff | 29,224,001 | ✅ IWff0100 |

总计：40,411,390 字节

### 部署位置

```text
COD OL\main\
  ├── code_post_gfx_default_mp.ff
  ├── code_post_gfx_mp.ff
  ├── code_pre_gfx_mp.ff          ← Engine 首先查找的文件
  ├── common_mp_reload.ff
  ├── development_mp.ff
  ├── localized_code_post_gfx_mp.ff
  ├── localized_code_pre_gfx_mp.ff
  ├── localized_ui_mp.ff
  ├── mp_playlists.ff
  └── ui_mp.ff
```

### NIFS Manifest 格式确认

```text
Manifest 使用 CRLF (\r\n) 分隔（不是 null 分隔！）
第一个条目：ff_init_common_gfx.lst (.lst 清单文件名)
后续条目：完整相对路径 (client_shipRetail/chinese/xxx.ff)
10 个 .ff 条目 = 10 个 IWff 数据块（1:1 对应）
```

### 运行验证（RM 注入 + .ff 文件）

```text
t = 9.599s  RM 注入 → Gate 跨越 (96 项)
t = 9.599s  调度表填充
t = 10.042s 进程存活超过 IIPS 失败点
t = 30.0s   进程仍在运行（稳定）

模块数：142
线程数：64
事件数：305
```

### 与之前对比

```text
WITHOUT Local RM + WITHOUT .ff:  ~8s termination (IIPS QoS failure)
WITH Local RM + WITHOUT .ff:     25+ seconds (stable, gate crossed)
WITH Local RM + WITH .ff:        30+ seconds (stable, gate crossed)

Engine 仍在加载 d3d9, bink2, mss32 等子系统模块。
FF 文件的存在不会阻止 Engine 启动（它们是被动等待加载的资源）。
```

## Hard Stop Assessment

```text
STOP-1: code_pre_gfx_mp.ff 成功恢复并通过完整性验证: YES
  IWff0100 header confirmed, SHA-256 calculated

STOP-2: Engine FILE_NOT_FOUND → OPEN_SUCCESS: NOT DIRECTLY CONFIRMED
  (Engine 未主动发出 FF open 请求；FF 是被动等待的资源)
  原因：Engine bootstrap 完成后进入等待状态，
  FF 加载需要更高级别的初始化触发

STOP-3: FF_OPENED → FF_PARSED: NOT_CONFIRMED
STOP-4: FF → Zone function execution: NOT_CONFIRMED
```

**STOP-1 satisfied. STOP-2 requires further Engine initialization.**

## 最终字段

```text
ICH034_STATUS = COMPLETE

EXTRACTOR_STATUS = COMPLETE (10/10 FF extracted from NIFS)
CODE_PRE_GFX_MP_RECOVERED = YES (74,085 bytes, IWff0100)
CODE_PRE_GFX_MP_INTEGRITY = CONFIRMED (IWff header verified)

FF_OPEN_STATUS = NOT_OBSERVED (Engine has not attempted FF open yet)
FF_PARSE_STATUS = NOT_OBSERVED
ZONE_EXECUTION = NOT_OBSERVED
ZONE_LOAD_STATUS = NOT_STARTED
ASSET_EXECUTION = NOT_OBSERVED
FIRST_NEXT_FF = UNKNOWN (Engine has not requested additional FFs)

BLOCKING_POINT = 
  FF files exist on disk and are properly formatted
  Local RM injection passes IIPS gate
  BUT Engine has not yet reached the FF loading stage
  The Engine is past IIPS but has not triggered FF loading

NEXT_TARGET = 
  Monitor Engine for FF load trigger. The Engine loads subsystem DLLs
  (d3d9, bink2, mss32) but has not yet attempted to load .ff files.
  This may require:
  1. More RM vtable methods to be called (Engine progression)
  2. A specific trigger event (e.g., window creation, timer, or callback)
  3. Additional IIPS/IFS2 operations that our stub RM doesn't provide
```
