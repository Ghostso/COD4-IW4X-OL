# `[100] 无法连接大厅服务` 本地根因定位

日期：2026-09-25
证据：`iips.dll` 字符串 + 运行观测 + 管道枚举

## 1. 完整因果链（来自 iips.dll 内嵌日志串）

```text
ResourceManagerII::Initialize()
  -> LaunchIIPSHostApp   (/mode iipslaunch)
  -> failed -> m_iipsClient.Start() failed
  -> "failed to conncet pipe"      (IIPSERR_PIPE_INIT)
  -> 命名管道  \\.\Pipe\...
  -> 依赖 IIPS\HostPid 里的 PID
```

`IIPSClient.ini [ErrMsg]` 给出的错误码表：

```text
7   IIPS初始化代理进程出错
8   IIPS初始化管道出错
9   IIPS创建共享内存出错
39  初始化失败, 打开Host进程的共享内存出错
38  初始化失败, 正在修复中
```

## 2. 实测结果（本机）

```text
沙箱 iips.ini 原本被改成：
    enable_iips=1
    iips_url="http://10.231.2.181/"      <- 不可达内网地址
沙箱 IIPS\HostPid 文件为空（0 字节）
原始目录 IIPS\HostPid = 20128
```

手工提权启动 `IIPSHostApp.exe /mode iipslaunch` 后：

```text
进程起来了（PID 5556）
HostPid 仍然为空
枚举 \\.\Pipe\ 时没有任何 IIPS/Tenio 管道（158 个管道里 0 命中）
TenioLog 全是 TPFUI 界面资源加载失败
```

⇒ **IIPSHostApp 没有完成初始化，因此既不创建命名管道也不写 HostPid。**
游戏拿不到 pipe，`ResourceManagerII::Initialize` 失败，抛 `8189fec`
（= `WIN_IIPS_INIT_ERROR`），大厅链根本没有开始。

## 3. 与"没有服务器"的关系

```text
[100] 发生在 IIPS 初始化阶段
      -> 位置早于 大厅/认证/GDP 任何网络请求
      -> 干净运行（不改主机名）时游戏发出的外连数为 0

所以 [100] 的当前直接原因不是"大厅服务器不可达"，
而是"游戏没能完成本地 IIPS host 管道握手"。
```

这不否定"有服务器才能进大厅"，但说明**当前这一层还没走到网络**。

## 4. 已确认的修复顺序

```text
第 1 步  IIPSHostApp 必须真正初始化成功
         - 需要它自带的完整运行环境（TPFUI 界面资源等）
         - 成功后才会创建 \\.\Pipe\<name> 并写 IIPS\HostPid
第 2 步  游戏 ResourceManagerII 连上 pipe
         - iips.ini 必须 enable_iips=1
         - iips_url 必须可达（不能是 10.231.2.181）
第 3 步  之后才会进入 TCLS/TQoS/GDP 网络层
```

## 5. 本轮工具

```text
CODOLServer\_mainline\fix_iips_local.py   修复 iips.ini / 启动 host
CODOLServer\_mainline\list_pipes.py       枚举命名管道
CODOLServer\_mainline\run_local_connection_test.py  端到端本地连接测试
CODOLServer\_mainline\probe_lobby_state.py          运行期状态探针
CODOLServer\_mainline\watch_connects.py             干净运行连接监测
```

备份：`backups\IIPS_FIX_20260925_155502`
