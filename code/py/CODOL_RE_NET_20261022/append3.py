part = """

### 4.6 auth 请求（实测抓包）

POST /auth/ HTTP/1.1
Host: formal-zone-auth.codol.qq.com:3074
Content-Type: application/json
X-TransactionID: 16165116171768878915
Content-Length: 190
Expect: 100-continue

body = {"auth_task":"10","iv_seed":"3480436955","title_id":"1002","identity":"356c4bc3",
        "extra_data":"{\\"version\\": \\"0\\", \\"user_id\\": \\"10995207597479878709\\", \\"extended_data\\": true}"}

响应 200，task 10 -> 11，2239 字节。

### 4.7 证书 / TLS 分支

- 0x7F2C33 push "cacert.pem" -> 0xB9A100 -> 0xC76600（写入 [obj+0x160]+0x45C）
- 0x7F2DB0 装 cacert.pem -> "https://%s/" -> 0x77B370
- 0x7F3100 SSL 错误处理；9/10 号 -> 弹 "@SF_UI_DW_LIVE_CERT_FAILED"
- 0x7F3190 TLS 握手轮询；0x22C4 判成功 -> state 9

0x331C5C0 = auth 模式开关：
- 非 0 -> 0xB88CC0（带 extra_data 的完整 /auth/）
- 为 0 -> 0x7F2D4D（"simplePassword" + 0xB992E0）

### 4.8 四个连接/探测对象

| 全局 | 构造 | vtable | 用途 |
|---|---|---|---|
| 0x84ABB08 | 0xB88B80 | 0xD59A7C | auth (HTTPS /auth/) |
| 0x84ABB14 | 0xB99090 | 0xD5A1F8 | lsg (第二通道, +0x31A8=3) |
| 0x84ABA70 | 0x7F34E0 内 | - | DW DNS 探测 A |
| 0x84ABA74 | 0x7F34E0 内 | - | DW DNS 探测 B |

### 4.9 完整时序

DW 泵 0x7EF0D0 (index 3)
 -> 0x7F2600 置 DW=1 "dwLogonStart"
    -> 0x7F26C0 switch(DW)
       DW=1 -> 0x7F3600 DNS -> 0x7F34E0
       DW=2 -> 0x7F28F0 switch(conn)
         0 -> 0x7F2B90 建 auth + lsg
         1 -> 0x7F29C0 发 auth
         2 -> 0x7F2AB0 轮询
         6 -> 0x7F2DB0 装 cert
         7 -> 0x7F3100 证书清理
         8 -> 0x7F3190 TLS 握手 -> 9
       DW=3 -> 0x7F3800 客户端就绪 -> 2 = DW_LOBBY_CONNECTED
       DW=4 -> 0x7F27B0 注册 CODOID

### 4.10 状态判定

0x7F2AD3 call 0xB9A0D0 取 [obj+0x156C] 错误码
0x7F2ADA cmp eax,0x2BC (700) 成功
0x7F2AE1 cmp eax,0x2C3 (707)
0x7F2AE8 [0x84ABA60]=3
0x7F2AF5 [0x84ABA60]=0
0x7F2B06 [0x84ABA5C]=eax

### 4.11 TLS 成功判据

0x7F31B1 call 0xB983B0
0x7F31B6 cmp eax,0x22C4
0x7F31FA [0x84ABA60]=9
"""
p = r'CODOL_SERVER_319_20261021\docs\SESSION_20261022_CLIENT_ARCH_AND_LOBBY_CHAIN.md'
open(p,'a',encoding='utf-8').write(part)
import os; print(os.path.getsize(p))
