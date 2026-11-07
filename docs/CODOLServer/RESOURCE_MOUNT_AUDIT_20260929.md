# CODOL 资源挂载审计（2026-09-29）

本记录承接 `HANDOFF_20260929_LOBBY_PROTOCOL.md`，只覆盖
`mp/marketplace.json`、IIPS `.ifs` 容器、TCLS 修复链和客户端 zone 注册链。
本轮没有启动游戏，没有写游戏进程内存，没有修改 `.text`，也没有停止或修改
ACE 组件。

## 1. 新增只读工具

```text
CODOLServer/_mainline/ifs_zone_audit.py
```

用法：

```powershell
python -X utf8 CODOLServer\_mainline\ifs_zone_audit.py `
  "COD OL\IIPS\IIPSDownload\ff_init_common_gfx_V109.ifs" `
  "run_codol_001\sandbox_ifs1_20260923\main"
```

工具只读取 `.ifs` 和目标目录，检查：

* `nifs` 容器头与内嵌 `.lst` 名称；
* 每个 `IWff0100` / `IWffu100` fastfile 的大小、SHA-256 和 `0x1CD` 元数据；
* 目标 `main\` 中是否存在同名 `.ff`，以及是否逐字节一致。

## 2. 容器完整性结果

### 基础启动包

输入：`ff_init_common_gfx_V109.ifs`，40,412,080 字节。

结果：

```text
清单：ff_init_common_gfx.lst
内嵌 zone：10
10/10 的 fastfile 元数据均为 0x1CD
10/10 均存在于 sandbox_ifs1_20260923\main
10/10 SHA-256 与 main\ 文件完全一致
```

因此当前 `main\` 不是随意拷贝的一组文件，而是基础 `.ifs` 清单的精确展开结果。

### Marketplace 包

输入：`ff_init_common_marketplace_V95.ifs`，33,097,234 字节。

结果：

```text
清单：ff_init_common_marketplace.lst
内嵌 zone：3
3/3 的魔数为 IWff0100
3/3 的元数据为 0x1CD
3/3 当前不在 sandbox_ifs1_20260923\main
```

三个 zone 为：

```text
common_marketplace_lite.ff
common_marketplace_lite1.ff
localized_common_marketplace_lite.ff
```

这排除了“marketplace `.ifs` 损坏”这一解释。容器中的 fastfile 是合法的，
实际缺口是它们没有进入启动时使用的 zone 集合。

## 3. 客户端 zone 链

运行期解密镜像 `image_best.bin` 的只读反汇编得到：

```text
0x4FCC00  构造 4 项 code_pre_gfx_mp 清单 -> call 0x49E160
0x4FCCA0  构造 5 项 code_post_gfx_mp 清单 -> call 0x49E160
0x4FD07F  启动期调用 0x4FCC00
0x4FCE71  调用 0x4FCCA0
0x49F07D  唯一调用 0x483DB0
0x483DB0  读取已选定 zone 的 IWff 魔数与 0x1CD 元数据
```

`0x483DB0` 是 zone 读取/校验器，不是目录扫描器，也不是清单发现器。
它的输入由上游已经构造好的记录提供；`0x49E160` 接收的也是已构造的
zone 记录数组。当前启动清单没有 marketplace 三项，所以仅把合法 `.ff`
放进 `main\` 不会让它们进入注册表。

资产查询链也已独立确认：

```text
0x4A93E0
  -> 0x49D3B0 / 0x49D3D0("mp/marketplace.json", 0x24)
  -> 0x49CA70
  -> 0x49C870 名字哈希
  -> 0x1E2D338 哈希桶
  -> 0x239B120 stride=0x1C 的资产记录
  -> 0xE5C8C0 reader 表
```

资源未注册时，`0x49CA70` 返回空，`0x4A93E0` 在 `0x4A936E` 直接返回，
这与实跑中 `gec=0 / gate=0 / cfg=0 / cfgobj=0` 完全一致。

## 4. IIPS/TCLS 修复链边界

客户端内部还存在一条容易混淆的路径：

```text
0x65A4BF -> 0x658E40
0x65A5CD -> 0x658E40
0x659A23 -> 0x659140
```

静态语义：

* `0x65A4BF` 位于 IIPS 资源管理器初始化结果检查中；返回异常且不是
  `0x60000026` 时，调用 `0x658E40`。
* `0x65A5CD` 是 IIPS 管理器为空时的失败分支，同样调用 `0x658E40`。
* `0x658E40` 使用字符串 `TCLS\\Repair.exe`、` -ifs_file`、`TCLS\\ifs_file`
  和 `IIPS\\IIPSDownload\\%s` 构造修复/检查任务参数。
* `0x659140` 被 `0x659A23` 调用，用于清单项的字符串/记录比较和处理。

这条链没有调用 `0x49E160`、`0x483DB0`，也没有对
`0x239B120`/`0x1E2D338` 资产表执行注册操作。因此它是 IFS 下载/修复与
`.lst` 校验链，不是把新 fastfile 加入游戏启动 zone 集合的入口。

## 5. 已完成与未完成

已完成：

```text
· 证明基础 ff_init_common_gfx_V109.ifs -> main\ 的 10/10 精确对应关系
· 证明 marketplace ff_init_common_marketplace_V95.ifs 内部 3 个 zone 合法
· 证明 marketplace 三个 zone 不在当前启动清单和 main\ 中
· 证明 0x483DB0 只负责读取已选定 zone
· 证明 IIPS/TCLS 修复链不调用 zone 注册链
```

未完成：

```text
· 没有在当前安全边界内找到能把 marketplace 三项加入启动 zone 清单的外部入口
· 第一档 DW 保活/配置状态仍未闭合
```

当前安全边界内的结论：

```text
正常资源文件、正常 IIPS 下载结果、裸 fastfile 拷贝和 IIPS 修复链都不能
改变当前 zone 清单；继续推进需要改变客户端代码/运行期状态，或使用一个
真正实现 marketplace zone 装载的独立受控客户端环境。
```

实验性文件
`run_codol_001\sandbox_ifs1_20260923\mp\marketplace.json`
仍保留在磁盘，内容带有 `_result: NEGATIVE` 自述标记；本轮没有擅自删除，
以保留历史证据。
