# 学习报告 046（重开）— `fake_auth_tls.py` 应答构造与 TLS 处理（全文完）

**学习范围**：`bundle\fake_auth_tls.py`（17,600 B / 413 行）第 239–413 行
**性质**：全实测
**★★★ 本报告收录**200 应答的完整 JSON 形态**、**`extra_data` 的五字段**、**close-notify 的实现**

---

## 一、★★★ `display_name` 的收尾（第 239–254 行）

```python
if doc.get("schemaVersion") != 1:        # ★ 必须 schemaVersion == 1
    continue
name = sanitize(doc.get("displayName"))
if name:
    return name, path
except Exception:
    continue
try:
    with open(os.path.join(root, "Identity.json"), encoding="utf-8") as handle:
        name = sanitize(_json.load(handle).get("username"))
    if name:
        return name, "migration seed"
except Exception:
    pass
return "Client青", "hardcoded fallback"
```

★★★ **⇒ 三个返回值的 `name_src` 标记：**
```
<path>              ← 从 1004\<UID>\Identity.json 读到
"migration seed"    ← 从根 Identity.json 的 username 读到
"hardcoded fallback" ← ★ 兜底 "Client青"
```

★★ **⇒ `schemaVersion != 1` 的文件被**跳过**（严格校验）。**

---

## 二、★★★★★ `build_response` 的完整 200 应答（第 257–332 行）

### 2.1 ★★★ docstring 的六条说明（第 258–265 行，逐字）

```python
"""★ 完全照抄三方 CodolLocalLobbyServer.cs 的 200 应答形态:
   - 顶层有 ret/code/auth_task/status/success
   - 票据字段同时放顶层与 data 内层, 且都以【字符串】给 _size
   - 额外带 DW-* 响应头(校验器会读)
   - iv_seed 回显请求里的值(三方就是回显)
   - 【不含 extra_data】(三方没有; 我们也拿不到那个 749B 模板)
   - 2026-10-05 17:0x：`profile.name` 改从 backend 权威档案读（见 display_name()）
"""
```

★★★ **⇒ 六条里第 5 条**已被推翻**（第 282–303 行后来补了 `extra_data`）。**

★ **⇒ 这是**docstring 与代码的时序差**（docstring 写于 17:0x，extra_data 补于 17:1x）。**

### 2.2 ★★★★★ `fields` 的七个字段（第 275–280 行）

```python
fields = ('"member_position":"1","estimated_wait_time":"0","next_poll_after":"1",'
          '"iv_seed":"%s",'
          '"client_ticket":"%s","client_ticket_size":"128",'
          '"server_ticket":"%s","server_ticket_size":"128",'
          '"lsg_server_ticket":"%s","lsg_server_ticket_size":"128"'
          % (iv_seed, ticket_b64, ticket_b64, ticket_b64))
```

### ★★★★★ 完整的七字段

| # | 字段 | 值 |
|---|---|---|
| **1** | `member_position` | **`"1"`** |
| **2** | `estimated_wait_time` | **`"0"`** |
| **3** | `next_poll_after` | **`"1"`** |
| **4** | `iv_seed` | **回显请求值** |
| **5** | `client_ticket` + `_size` | **`ticket_b64`** + `"128"` |
| **6** | `server_ticket` + `_size` | **`ticket_b64`** + `"128"` |
| **7** | `lsg_server_ticket` + `_size` | **`ticket_b64`** + `"128"` |

★★★ **⇒ 三个 ticket **完全相同**（都是 `ticket_b64`）。**

★★ **⇒ 所有 `_size` 都是**字符串** `"128"`（不是数字）。**

### 2.3 ★★★★★ `extra_data` 的五个字段（第 304–313 行）

```python
extra = ('{"encrypted_register_codoid_data":"%s","encrypted_codoid":"%s",'
         '"extended_data":"%s","time_to_live":9999,"username":"%s"}'
         % (base64.b64encode(b"Shippo fuute, mofu-mofu!").decode(),
            base64.b64encode(b"Hedgehogscience0").decode(),
            "eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0="
            ".AAAA...=.AAAA...==.W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=.AAAAAAAA",
            base64.b64encode(name.encode("utf-8")).decode()))
```

### ★★★★★ 五字段完整表

| # | 字段 | 值 |
|---|---|---|
| **1** | `encrypted_register_codoid_data` | **`b64("Shippo fuute, mofu-mofu!")`** |
| **2** | `encrypted_codoid` | **`b64("Hedgehogscience0")`** |
| **3** | `extended_data` | ★★★ **一个预制的 JWE 壳** |
| **4** | `time_to_live` | **`9999`**（数字，不是字符串） |
| **5** | **`username`** | ★★★★★ **`b64(name)`** —— **名字的真正载体** |

★★★ **⇒ 第 1、2 项是**老外的占位常量**：**
```
"Shippo fuute, mofu-mofu!"   （23 字节）
"Hedgehogscience0"           （15 字节）
```

★★ **⇒ 与报告 044 的 `sessionKey` 注释呼应 —— `"Shippo fuute, mofu-mofu!"` 也是默认会话密钥（上一轮报告 012）。**

### 2.4 ★★★ `extended_data` 的 JWE 壳（第 308–311 行）

```python
"eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0="
".AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
"=.AAAAAAAAAAAAAAAA==.W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=.AAAAAAAA"
```

★★★ **⇒ 解 base64 第一段（header）：**
```
eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0=
        ↓
{"__v":1,"alg":"RSA-OAEP","enc":"A12OCBC-HS256","kid":"umb_1"}
```

★★★ **⇒ 注意 `"enc":"A12OCBC-HS256"` —— 应为 `"A128CBC-HS256"`（★ 疑似拷贝错误，但**照抄**了）。**

★ **⇒ 末段 `W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=`：**
```
[Encrypted data.. much secret..]
```

★★ **⇒ 这是**老外的幽默占位串** —— 内容是假的，只要结构对。**

### 2.5 ★★★★★ 最终 JSON 的三层嵌套（第 315–317 行）

```python
js = ('{"ret":0,"code":700,"auth_task":%d,"status":0,"success":true,%s,'
      '"data":{%s},"profile":{"id":1,"name":"%s"},"extra_data":"%s"}'
      % (resp_task, fields, fields, name_json, extra_json)).encode()
```

### ★★★★★ 完整的应答结构

```json
{
  "ret": 0,
  "code": 700,
  "auth_task": <resp_task>,
  "status": 0,
  "success": true,
  <fields>,                    ← ★ 扁平层（7 字段）
  "data": { <fields> },        ← ★★ 内层重复（同样的 7 字段）
  "profile": {"id": 1, "name": "<name_json>"},
  "extra_data": "<extra_json>" ← ★★★ 字符串（不是对象）
}
```

★★★ **⇒ 三个关键设计：**
```
① `fields` 在**顶层和数据内层各放一遍**
② `profile.name` 是**界面显示名**
③ `extra_data` 是**字符串**（JSON 转义后的）
```

★ **⇒ 与老外的 `Auth3Protocol.cpp:300-313`（报告 012）**完全对应**：**
```cpp
Json response{
    { "client_ticket", ticket64 }, { "server_ticket", ticket64 },
    { "code", "700" }, { "extra_data", extraData.dump() },
    { "auth_task", std::to_string(authTask + 1) }, ...
};
```

★★★ **⇒ 但**两处差异**（上一轮报告 012 已记录）：**
```
C++ 版：code 是**字符串** "700"
本 shim：code 是**数字** 700

C++ 版：auth_task 恒 +1
本 shim：TASK_MAP（32→57）
```

### 2.6 ★★★ 日志（第 318–319 行）

```python
log("  [name] profile.name=%r  extra_data.username(base64)=%r  来源=%s"
    % (name, base64.b64encode(name.encode("utf-8")).decode(), name_src))
```

★★★ **⇒ 三个信息：名字、b64 后的名字、来源。**

★ **⇒ `name_src` 就是 `display_name` 的第二个返回值（路径 / `"migration seed"` / `"hardcoded fallback"`）。**

---

## 三、★★★★★ DW-* 响应头（第 321–331 行）

```python
head = ("HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        "Content-Length: %d\r\n"
        "DW-Ticket-Seed: %s\r\n"
        "DW-Client-Ticket-Size: 128\r\n"
        "DW-Client-Ticket: %s\r\n"
        "DW-Server-Ticket-Size: 128\r\n"
        "DW-Server-Ticket: %s\r\n"
        "Connection: close\r\n"
        "X-Local-Emulator: unsigned-protocol-experiment\r\n\r\n"
        % (len(js), iv_seed, TICKET_B64, TICKET_B64)).encode()
```

### ★★★★★ 九个响应头

| # | 头 | 值 |
|---|---|---|
| **1** | 状态行 | `HTTP/1.1 200 OK` |
| **2** | `Content-Type` | `application/json; charset=utf-8` |
| **3** | `Content-Length` | JSON 长度 |
| **4** | **`DW-Ticket-Seed`** | **回显 `iv_seed`** |
| **5** | **`DW-Client-Ticket-Size`** | **`128`** |
| **6** | **`DW-Client-Ticket`** | **`TICKET_B64`** |
| **7** | **`DW-Server-Ticket-Size`** | **`128`** |
| **8** | **`DW-Server-Ticket`** | **`TICKET_B64`** |
| **9** | `Connection: close` | ★ 每个请求一个连接 |
| **10** | `X-Local-Emulator` | `unsigned-protocol-experiment` |

★★★ **⇒ 第 4–8 是**DW-* 头**（注释说"校验器会读"）—— 与 JSON body **双份**提供。**

★ **⇒ 且 `DW-Client-Ticket` 与 `DW-Server-Ticket` **是同一个值**（`TICKET_B64`）。**

★★ **⇒ 注意：`TICKET_B64` 是**常量**（第 42 行），不是 `ticket_b64`（带名字的）。**
**⇒ 所以 HTTP 头里的 ticket **没有名字**，JSON body 里的**有名字**。**

★★★ **⇒ 这是一个**潜在的不一致**（可能无关紧要，但值得记录）。**

---

## 四、★★★★ `handle` 的 TLS 处理（第 335–395 行）

### 4.1 ★★★ TLS 握手（第 336–345 行）

```python
try:
    conn.settimeout(30)                          # ★ 30 秒超时
    ss = CONTEXT.wrap_socket(conn, server_side=True)
except Exception as e:
    log("TLS 握手失败 %s: %r" % (addr, e))
    try:
        conn.close()
    except Exception:
        pass
    return
```

★★ **⇒ 握手失败时**关闭原始 socket**并返回。**

### 4.2 ★★★ HTTP 请求解析（第 348–371 行）

```python
data = b""
while b"\r\n\r\n" not in data:                  # ★ 读到头部结束
    c = ss.recv(4096)
    if not c:
        break
    data += c
head, _, rest = data.partition(b"\r\n\r\n")
clen = 0
for ln in head.split(b"\r\n")[1:]:
    k, _, v = ln.partition(b":")
    if k.strip().lower() == b"content-length":
        try:
            clen = int(v.strip())
        except Exception:
            clen = 0
body = rest
# Expect: 100-continue -> 先回 100, 再收 body
if b"100-continue" in head.lower() and len(body) < clen:
    ss.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
while len(body) < clen:                          # ★ 补读 body
    c = ss.recv(4096)
    if not c:
        break
    body += c
```

★★★ **⇒ 四个步骤：**
```
① 读到 `\r\n\r\n`（头部结束）
② 解析 `Content-Length`
③ ★ 若客户端发 `Expect: 100-continue` ⇒ **先回 `100 Continue`**
④ 补读 body 到 `clen`
```

★★★ **⇒ 第 ③ 步是**HTTP/1.1 的必需行为**：**
```
客户端发 `Expect: 100-continue`
        ↓
服务端**必须先回 `100 Continue`**
        ↓
否则客户端会**等超时**（不会发 body）
```

### 4.3 ★★★ 完整日志（第 372–378 行）

```python
log("[%s] %s  Host=%s  blen=%d" % (head.split(b"\r\n")[0].decode("latin1", "replace"),
                                   addr, addr, len(body)))
for ln in head.split(b"\r\n")[1:]:
    if ln:
        log("      " + ln.decode("latin1", "replace"))
if body:
    log("      body: " + body.decode("utf-8", "replace"))
```

★★ **⇒ 打印：请求行、所有头、body（UTF-8 解码）。**

★ **⇒ `decode("latin1")` 用于头部（避免非 ASCII 崩溃），`utf-8` 用于 body。**

### 4.4 ★★★★★ `close-notify` 的实现（第 382–388 行）

```python
# ★ 关键: 发 TLS close-notify (http.sys 不发, 这是契约的一部分)
try:
    ss.settimeout(1.5)
    ss.unwrap()                              # ★★★ 关键调用
    log("  TLS close-notify 已发")
except Exception as e:
    log("  close-notify: %r" % (e,))
```

★★★★★ **⇒ `ss.unwrap()` 是**唯一**能发 `close_notify` 的调用：**
```
`ss.close()`      →  直接断 TCP，**不发** close_notify
`ss.unwrap()`     →  ★★★ **发 close_notify**，然后正常收尾
```

★★ **⇒ 超时 **1.5 秒**（不为 close_notify 卡太久）。**

★ **⇒ 与 docstring 的"http.sys 不发 close_notify ⇒ SSLEOFError"**完全对应**。**

### 4.5 ★★★ `finally` 的清理（第 391–395 行）

```python
finally:
    try:
        ss.close()
    except Exception:
        pass
```

★ **⇒ 无论成功失败都关闭。**

---

## 五、★★★ `__main__` 的启动（第 398–412 行）

```python
if __name__ == "__main__":
    certfile, keyfile = build_pem_files()        # ★★★ 第一行就崩（_rsa.txt 缺失）
    CONTEXT = make_context(certfile, keyfile)
    log("==== fake_auth_tls 启动 %s:%d (cert=%s) ====" % (BIND, PORT, os.path.basename(certfile)))
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((BIND, PORT))                        # ★ 绑 127.0.0.1:3074
    srv.listen(16)                                # ★ 队列 16
    log("[*] 监听 %s:%d" % (BIND, PORT))
    while True:
        try:
            c, ad = srv.accept()
        except Exception:
            continue
        threading.Thread(target=handle, args=(c, ad), daemon=True).start()
```

★★★ **⇒ 五个要点：**
```
① **`build_pem_files()` 第一行就崩**（`_rsa.txt` 缺失）
② 绑 **`127.0.0.1:3074`**（`BIND` / `PORT`）
③ `SO_REUSEADDR`
④ `listen(16)` 队列
⑤ ★ 每个连接一个 **daemon 线程**
```

★★ **⇒ 第 ① 条是**交付包的第一个硬故障**（报告 001 已确认）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★ 三个 `name_src` | `<path>` / `"migration seed"` / **`"hardcoded fallback"`** |
| 2 | ★ `schemaVersion` | 必须 **`== 1`** |
| 3 | ★★★ `fields` 七字段 | `member_position` / `estimated_wait_time` / `next_poll_after` / `iv_seed` / 三个 ticket |
| 4 | ★★ 三个 ticket | **完全相同**（`ticket_b64`） |
| 5 | ★★ `_size` 类型 | **字符串 `"128"`** |
| 6 | ★★★ **`extra_data` 五字段** | `encrypted_register_codoid_data` / `encrypted_codoid` / `extended_data` / `time_to_live` / **`username`** |
| 7 | 占位常量 | **`"Shippo fuute, mofu-mofu!"`** / **`"Hedgehogscience0"`** |
| 8 | ★ `extended_data` | JWE 壳，header 解出 `{"__v":1,"alg":"RSA-OAEP","enc":"A12OCBC-HS256","kid":"umb_1"}` |
| 9 | ★ 疑似拼写 | **`A12OCBC`** 应为 `A128CBC`（照抄） |
| 10 | ★ 幽默占位 | **`[Encrypted data.. much secret..]`** |
| 11 | ★★★ 三层嵌套 | 扁平层 + **`data` 内层重复** + `profile` + `extra_data`（字符串） |
| 12 | ★★ 与 C++ 版差异 | `code` 数字 vs 字符串；`auth_task` 用 `TASK_MAP` vs 恒 +1 |
| 13 | ★★★ **DW-* 五头** | `DW-Ticket-Seed` / `DW-Client-Ticket(-Size)` / `DW-Server-Ticket(-Size)` |
| 14 | ★★ 不一致 | HTTP 头用 **`TICKET_B64`（无名字）**，body 用 `ticket_b64`（**有名字**） |
| 15 | ★★★ `Expect: 100-continue` | 必须先回 **`100 Continue`** |
| 16 | ★★★★★ **close-notify** | **`ss.unwrap()`**（不是 `ss.close()`），超时 **1.5 秒** |
| 17 | ★★★ 启动 | **`build_pem_files()` 第一行崩**（`_rsa.txt` 缺失） |
| 18 | 监听 | **`127.0.0.1:3074`**，`listen(16)` |

---

## 七、结论

### 1. ★★★★★ **`extra_data.username`（base64）是名字的真正载体**

★★ **⇒ 与 `profile.name` **双保险**（两处都放）。**

### 2. ★★★★★ **`ss.unwrap()` 是发 close_notify 的唯一方式**

★ **⇒ `ss.close()` 不发 ⇒ 客户端 `SSLEOFError`。**

### 3. ★★★ **三层嵌套**：扁平层 + `data` 内层重复 + `profile` + `extra_data`

### 4. ★★★ **`Expect: 100-continue` 必须先回 `100 Continue`**

### 5. ★★ **HTTP 头里的 ticket 无名字，body 里的有**（潜在不一致）

### 6. ★★ **`build_pem_files()` 第一行就崩**（`_rsa.txt` 缺失）—— 交付包第一个硬故障

---

## 八、下一步

- `stun_local.py`（7,618 B）
- `force_display_name.py`（19,288 B）
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
