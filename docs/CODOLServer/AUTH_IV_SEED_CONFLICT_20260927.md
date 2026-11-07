# /auth/ iv_seed 矛盾核对

日期：2026-09-27
目的：解释 `sub_state=7 -> last_err -> DW_ACCOUNT_ERROR`。

## 1. 客户端契约证据

文件：`CODOLServer\SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md`

运行期反汇编记录：

```asm
00B984B2  push 0xd5a114       ; key "iv_seed"
00B984BD  call 0xbc3e10      ; get_int64
00B984E7  cmp  [ebp-0xE4], 0  ; iv_seed must equal 0
```

同一报告的契约表将此列为：

```text
iv_seed == 0
```

## 2. 当前服务器实际行为

文件：`CODOLServer\lobby_server\lobby_probe_server.py`

当前代码在模板替换阶段把请求值放入响应：

```python
NUMERIC = ("IV_SEED",)
...
raw = req.get(key, None)
if key.upper() in NUMERIC:
    val = str(int(str(raw).strip())).encode("ascii")
```

因此请求与响应是：

```text
请求 iv_seed = 2626567019
响应 iv_seed = 2626567019
```

真实日志：

```text
CODOLServer\_mainline\_auto_20260926_171802\probe.20260926_171802.jsonl
CODOLServer\_mainline\_fix1_20260926_192043\probe.20260926_192043.jsonl
```

两份日志均记录请求 `iv_seed` 与响应 `iv_seed` 相同。

## 3. 状态机对应关系

同批次状态采样：

```text
flag_61f=1
uA78=2
uA50=2
sub_state=6
sub_state=7
last_err=741 (0x2E5)
DW_ACCOUNT_ERROR
```

这证明网络连接、TLS、HTTP POST 和响应读取至少推进到了业务解析阶段；
失败发生在响应处理之后，而不是在线闸门之前。

## 4. 当前判断

```text
CONFIRMED:
  客户端解析路径存在 iv_seed == 0 的检查。
  当前探针把请求 iv_seed 回显到响应。
  当前状态在 sub_state=7 后进入错误。

HIGH-VALUE HYPOTHESIS:
  回显非零 iv_seed 触发失败分支，导致后续对象状态没有变成期望值。

UNKNOWN:
  stage 32 的另一条 ticket 解析路径是否也要求 iv_seed=0。
  vtable +0x20/+0x24/+0x28 是否覆盖该检查。
```

## 5. 单变量验证方案

只改变响应 JSON 的 `iv_seed`：

```text
当前: 响应 iv_seed = 请求 iv_seed
测试: 响应 iv_seed = 0
```

保持不变：

```text
固化启动链
TLS 证书
auth_task 映射
client_ticket/server_ticket
lsg_server_ticket
HTTP 状态 200
连接关闭/读取逻辑
游戏文件
```

验收：

```text
若 last_err=741 消失或 sub_state=7 -> 9：假设成立。
若变为 735：进入 ticket/tag 路径，需要继续查 vtable。
若仍为 741：查 HTTP response code 保存与收尾路径。
```
