# 大厅鉴权失败详细排查记录

日期：2026-09-27
范围：在线闸门已确认打开后的 `/auth/` 失败链

## 1. 已确认的状态链

多个独立运行均出现：

```text
flag_61f=1
uA78=2              DW_DNS_COMPLETE
uA50=2
sub_state=6         /auth/ 请求阶段
sub_state=7         响应处理阶段
随后复位
dw_state=10         DW_ACCOUNT_ERROR
```

代表文件：

```text
CODOLServer\_mainline\_auto_b2\watch.jsonl
CODOLServer\_mainline\_auto_b3\watch.jsonl
CODOLServer\_mainline\_fix1_20260926_192043\watch.jsonl
CODOLServer\_mainline\_hs1_20260926_201045\watch.jsonl
```

因此本报告不再把“未进入在线模式”作为这些运行的根因。

## 2. 错误码分成两类

### 2.1 `0x2E5` / 十进制 741

旧阶段运行中出现：

```text
last_err=741
dw_state=10
DW_ACCOUNT_ERROR
```

`lobby_probe_server.py` 自己的注释把此路径对应到：

```text
BD_EMPTY (0x2E5)
```

客户端 HTTP 对象的状态码保存位置：

```asm
0xC752DD  mov [esi+0x464], edx
0xC752E3  cmp edx, 0xC8
0xC752EB  cmp edx, 0x12C
```

如果 HTTP 状态没有被 cURL 正确写入，`[httpobj+0x464]` 可能为 0，随后走空响应/空对象错误路径。

### 2.2 `0x2DF` / 十进制 735

较新 stage 32 运行中出现：

```text
last_err=735
obj_code=735
```

已有脚本 `frida_auth_branch.py` 标出两个写入 735 的候选点：

```text
0xB9A59B  auth_task validator rejected
0xB9A7C7  ticket/tag path rejected
```

所以 735 不能与 741 混为同一个问题：

```text
741 / 0x2E5 -> HTTP/BD_EMPTY/响应收尾候选
735 / 0x2DF -> auth_task 或 ticket/tag 业务解析候选
```

## 3. 当前真实请求与响应

### 3.1 stage 10

真实请求示例：

```json
{
  "auth_task":"10",
  "iv_seed":"2626567019",
  "title_id":"0",
  "identity":"356c4bc3",
  "extra_data":"{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"
}
```

当前探针实际回应：

```json
{
  "auth_task":11,
  "code":700,
  "iv_seed":2626567019,
  "client_ticket":"<128B base64>",
  "server_ticket":"<128B base64>",
  "lsg_server_ticket_size":128,
  "lsg_server_ticket":"<128B base64>"
}
```

### 3.2 客户端反汇编契约

已有运行期反汇编记录：

```asm
0xB984B2  get_int64("iv_seed")
0xB984E7  cmp [ebp-0xE4], 0
```

该路径明确记录为：

```text
iv_seed 必须为 0
```

因此当前服务器的回显行为与该解析路径存在直接矛盾：

```text
客户端要求：response.iv_seed = 0
当前服务器：response.iv_seed = request.iv_seed
```

## 4. 服务器代码当前状态

文件：

```text
CODOLServer\lobby_server\lobby_probe_server.py
```

原逻辑对 `iv_seed` 做请求值回填。当前工作树已经暂时改成：

```python
if key.upper() in NUMERIC:
    val = b"0"
```

这只是单变量实验准备：

```text
不改变 auth_task
不改变 ticket
不改变 TLS
不改变端口
不改变启动链
只改变 response.iv_seed
```

模板原文件已备份：

```text
CODOLServer\lobby_server\lobby_response.json.bak_ivseed_before_20260927
```

注意：手工修改模板时曾经破坏过 lsg_server_ticket 的 base64，已恢复原模板；当前实验修改的是 Python 替换逻辑，ticket 未改。

## 5. HTTP 收尾风险

探针代码当前包含：

```python
conn.sendall(resp)
conn.unwrap()
```

其设计意图是避免客户端收到 TCP RST，导致：

```text
CURLINFO_RESPONSE_CODE 未写入
[httpobj+0x464] = 0
BD_EMPTY / 0x2E5
```

但目前已看到的 `probe.jsonl` 中，不能仅凭服务器日志证明客户端最终读取到了 HTTP 200。必须在同一次运行中同时满足：

```text
probe 日志：tls_ok + roundtrip + tls_close_notify
客户端采样：sub_state=7 时 http_status=200
```

如果 `http_status` 仍为 0，问题是 HTTP/TLS 收尾，不是 JSON 业务字段。

## 6. 必须分开的三轮验证

### 实验 A：iv_seed 单变量

```text
response.iv_seed = 0
其余全部保持当前值
```

验收：

```text
last_err=741 消失
或 sub_state=7 -> 9
```

### 实验 B：HTTP 状态单独验证

在 A 的基础上只观察：

```text
httpobj+0x464
httpobj 内部状态 [obj+4]
服务器 tls_close_notify
```

验收：

```text
httpobj+0x464 = 200
obj 内部状态 = 3
```

### 实验 C：735 分支定位

只在出现 `0x2DF/735` 时使用已有 hook：

```text
0xB9A59B  是否命中？ -> auth_task validator
0xB9A7C7  是否命中？ -> ticket/tag path
0xB9A809  obj+0xD8 tag 对比
```

735 若命中 `0xB9A7C7`，继续分析 ticket 内容/tag；若命中 `0xB9A59B`，分析 stage 32 的实际 expected auth_task。

## 7. 当前结论

```text
在线模式问题       已排除
DNS 问题            已排除（uA78=2）
TLS 到达问题        历史上已打通
/auth/ 请求到达     已打通
HTTP 最终状态读取   尚需与 httpobj+0x464 同步确认
iv_seed 契约         当前服务器行为与客户端反汇编矛盾
ticket/tag 路径      735 阶段仍未定位
socket 阶段          尚未真正进入
```

本轮最优先变量是 `response.iv_seed=0`，因为它是唯一已发现的“服务器当前明确违反客户端反汇编检查”的字段。
