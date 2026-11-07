# CODOL 在线模式闸门确认记录

日期：2026-09-27
目的：确认 `[100] 无法连接大厅服务` 的测试运行是否真正进入在线大厅初始化，而不是停在本地启动/IIPS阶段。
方法：只读解析已有 `watch.jsonl`，没有启动游戏、没有改网络配置、没有修改原始文件。

## 结论

**在线模式已经进入。**

证据链在多次独立运行中重复出现：

```text
flag_61f = 1
uA78     = 2          DW_DNS_COMPLETE
uA50     = 2
sub_state = 6         /auth/阶段
```

因此，当前失败不能再归因于“游戏根本没有进入在线模式”。

## 原始证据

### 运行 A：`_auto_b2`

文件：

```text
CODOLServer\_mainline\_auto_b2\watch.jsonl
```

统计：

```text
rows=126
flag_61f=1 行数=90
uA78=2 行数=3
sub_state=9 行数=0
```

关键采样：

```text
t=19.04  flag_61f=1  uA78=2  uA50=2  sub_state=6  dw_state=1  DW_DNS_COMPLETE
t=20.04  flag_61f=1  uA78=2  uA50=2  sub_state=7  dw_state=1  last_err=741
t=20.54  flag_61f=1  uA78=0  uA50=0  sub_state=0  dw_state=10 DW_ACCOUNT_ERROR
```

### 运行 B：`_auto_b3`

文件：

```text
CODOLServer\_mainline\_auto_b3\watch.jsonl
```

统计：

```text
rows=146
flag_61f=1 行数=107
uA78=2 行数=3
sub_state=9 行数=0
```

关键采样：

```text
t=20.54  flag_61f=1  uA78=2  uA50=2  sub_state=6  dw_state=1  DW_DNS_COMPLETE
t=21.54  flag_61f=1  uA78=2  uA50=2  sub_state=7  dw_state=1  last_err=741
t=22.05  flag_61f=1  uA78=0  uA50=0  sub_state=0  dw_state=10 DW_ACCOUNT_ERROR
```

### 运行 C：`_lobby_run_fixed`

文件：

```text
CODOLServer\_mainline\_lobby_run_fixed\watch.jsonl
```

关键采样：

```text
t=25.05  flag_61f=1  uA78=2  uA50=2  sub_state=0  dw_state=1  DW_DNS_COMPLETE
t=25.55  flag_61f=1  uA78=2  uA50=2  sub_state=6  dw_state=1  DW_DNS_COMPLETE
```

本次采样没有推进到 `sub_state=9`，但已明确进入 `/auth/` 阶段。

## 排除结论

下列假设不能再作为当前主因：

```text
游戏完全没有进入在线模式       排除
flag_61f 没有打开                排除（上述运行中为 1）
dwauth.ini 完全没有被读取        排除（host/port 已进入采样）
DNS 阶段完全没有运行             排除（uA78=2）
服务器尚未被客户端请求             对这些运行不成立
```

## 当前真实失败位置

当前状态机实际是：

```text
在线闸门打开
    -> DW_DNS_COMPLETE
    -> uA50=2 / sub_state=6
    -> sub_state=7
    -> last_err=741
    -> DW_ACCOUNT_ERROR / dw_state=10
```

所以主线现在应该集中在：

```text
/auth/响应解析
ticket / lsg_server_ticket
[obj+0x240]
[obj+0x1400]
[httpobj+0x464]
vtable 0xD5A1F8 的 +0x20/+0x24/+0x28
```

不应再把主因退回到“在线模式闸门没有打开”。

## 重要区分

某些更早或不同配置的运行确实可能出现 `flag_61f=0`，那是另一类失败；但本记录确认了用于大厅联调的关键运行已经越过该阶段。

本记录只证明“在线模式与 DNS 阶段已通过”，不证明大厅已经连接成功。大厅成功仍需：

```text
sub_state=9
或主状态进入 DW_LOBBY_CONNECTED / state=3
```
