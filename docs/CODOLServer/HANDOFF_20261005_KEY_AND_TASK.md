# §28 【2026-10-05】0x85 应答密钥口径修正 + 客户端任务帧首次解开

> 承接 `HANDOFF_20261004_DW_PUMP_STAGE.md` §27。本轮全部结论都用**本仓库自己
> 已抓到的数据离线复核**过，没有依赖任何新的实跑。

---

## 0. 一句话结论

```
0x85 的 AES 密钥一直是错的。
  我们一直用  codec_02a0(obj+0x620)[4:20] / [obj+0x608]+0x14
  真实密钥是  [provider+0x9C] 的前 16 字节（AES-128 key schedule 的首块）
  → 客户端把我们的应答解成乱码 → 内层 opcode 永远不是 0x87/0x89
  → [obj+0x644] 永远是 0 → §19~§26 追了十几轮的「arm 失败」全部是它的下游症状

改用正确密钥后，客户端 0x85 立刻解出合法 DW 任务帧：
  09 00 00 00 | 86 | 47 03 09 | …
  u32 declared | marker | service=0x47 | ver=3 | task=9
```

---

## 1. 决定性证据（可复现，只读）

来源：`run_codol_001\runs\IFS1_ELEVATED_20261005_012515\aboprobe_run\*_events.csv`

```
94.921,CODEC_KEYS,p604=3B8FF940 len=16 key=496994efaf55e96723ba566b07292982 \
  sched=ef5a75895bd53ee5721347187a2de25036c226536d1718b61f045fae6529bdfe, \
  p608=8BB44BD0 len= key= sched=,src620=8fca5c67657c2f98109d29dd29cdfb985787f615 \
  src60C=fec4a2844583b707614ed56cb196ee4f01b0378a
```

* `key=`（即 `[p604+0x14]`）与 `src620/src60C` 都**不是**密钥；
* `sched=`（即 `[p604+0x9C]`，32B）的前 16 字节 `ef5a75895bd53ee5721347187a2de250`
  才是 AES 密钥（AES-128 key expansion 的 w[0..3] 就是原密钥）。

用它对 `logs\E57A5C_20261005_012507_a1\plain.jsonl` 里的客户端 `hold_recv` 帧解密：

```
#1 seq=1 declared=212 marker=0x86 service=71 ver=3 task=4
#2 seq=2 declared=147 marker=0x86 service=71 ver=3 task=3
#3 seq=3 declared=370 marker=0x86 service=71 ver=3 task=7
#4 seq=4 declared=9   marker=0x86 service=71 ver=3 task=9
```

工具：`CODOLServer\_mainline\_dec85_tasks.py <run_log_dir> <aes_key_hex>`
（另有 `_dec85_probe.py` / `_dec85_scan.py` 做密钥候选枚举，均为只读）。

---

## 2. 客户端在说什么（解开后的原文）

`71/3`（UserWarning）与 `71/7`（ComError）的 payload 是明文：

```
UserWarning|…|1649370|1234605616436508552|16701785630074219790|${CODOID(…)}|Address Fail|result = -3

ComError|…|1649370|…|…||Windows 10|AMD Ryzen 7 5800H …|15725|NVIDIA GeForce RTX 3070 …|
[nvldumd.dll] 617.14|0|2162688|@SF_UI_DW_LIVE_DISCONNECTED|0|D4-93-90-18-55-10|
mp_ui_viewer|war|0|0||@SF_UI_DW_LIVE_DISCONNECTED|${ZONEID(16701785630074219790)}
```

* `1649370` = 客户端 build，与本仓库主手册一致；
* **`Address Fail | result = -3`** —— 客户端自报某个地址连不上；
* **`@SF_UI_DW_LIVE_DISCONNECTED`** —— 和弹窗字符串 `@SF_UI_DW_LIVE_CONNECTING_FAILED`
  同族，说明客户端自己就把 DW 大厅连接判成"断开"。

⇒ 弹窗不是我们某个字段写错，而是客户端**先**认为链路丢了，再走 UI 出口。
下一步应查 `Address Fail -3` 具体指向哪个地址（platform / QoS / publisher）。

---

## 3. 应答信封（照抄 F: 盘那份已验证能进大厅的实现）

客户端任务帧明文：

```
u32 declared | 0x86 | service | ver(3) | task | payload
```

服务端任务应答明文：

```
u32 inner_len | 0x01
  | tag10 + u64 replyId(应回显请求 seq)
  | tag8  + u32 status(0)
  | tag3  + u8  task(回显)
  | tag8  + u32 对象数
  [| tag8 + u32 对象数 | 各对象原始字节]
对象/文件 = 0x13 0x08 + u32 长度 + 原始字节
```

* 出站 `seq` **每帧严格 +1**，不能复用请求 seq、也不能跳号（F: 盘 §13.8 实测教训）；
* 失败/超时路径用 `71/7 ClientException` 上报，**不是**断连原因。

---

## 4. 本轮代码改动（全部为新增、默认关，零回归）

| 文件 | 改动 |
|---|---|
| `lobby_server\lobby_plain_probe.py` | 新增 `--reply-85-task` / `--secrets-file`；新增 `read_secrets()`（含 `blob`→`hmac_out/hmac_in` 还原）、`decrypt_client_task()`、`build_task_reply()`；`aes_in` 缺失时回退 `aes_out` |
| `_mainline\_e57a5c_experiment.py` | 新增 `--reply-85-task`；给 observer 传 `-SecretsFile`；透传到 probe |
| `restore_iips_contract_001\observer2\AboProbe.cs` | `secrets.txt` 判据去掉 `ainOk`（本 build `[p608+0x9C]` 恒 0，旧判据会把**有效**的 `aes_out` 一起丢掉）；启动时清 secrets.txt |
| `_mainline\_dec85_*.py` | 新增离线解码工具（只读） |

自检：`py_compile` 通过；`dotnet publish` 通过；
用**真实抓包**跑 `decrypt_client_task()` + `build_task_reply()` 往返，
4 条任务全部解出、应答 TLV 正确（`0a<replyId> 08<status> 03<task> 08<count>`）。

---

## 5. 下一轮跑法

```powershell
# 1) 提权代理（UAC）
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping      # 期望 debug_privilege=true

# 2) 账号服务
Start-Process -FilePath "python.exe" -ArgumentList @('-X','utf8','-u','CODOLServer\lobby3074\fake_auth_tls.py') -WorkingDirectory "D:\BaiduNetdiskDownload\使命召唤OL" -WindowStyle Hidden

# 3) 主实验：只加 DW 任务应答，不要 87-gate / 不要强推 644
python -X utf8 "CODOLServer\_mainline\_multiround.py" --tag KEYTASK --need 1 `
  --compat4 --patch-delay 42 --serve-delay 30 `
  --patch-85-pass --reply-85-task
```

跑完看：

1. `logs\E57A5C_*_a1\plain.jsonl` 里有没有 `rx_task`（service/task 列表）
   与 `tx_task_reply`；
2. `...\a1\secrets.txt` 是否出现，且 `aes_out` 是否非零；
3. `AboProbe` 的 `POST83_SAMPLE` 里 `644` 是否从 0 变 1（这是本轮的唯一判据）。

---

## 6. 风险 / 未定

1. `[p608+0x9C]` 在本 build 恒 0 ⇒ 应答先用 `aes_out` 回发（假设收发同键）。
   若 `644` 仍不翻，说明收发异键，需要另找接收侧密钥来源。
2. 若保留 `--patch-85-pass`（跳过 MAC 校验）能翻 644，而关掉后不能，则说明
   `hmac_in` 还原表（`_HK_W2/_HK_I2`）或 `blob` 读取起点仍需校正。
3. **不要**再用 `--patch-87-gate`（它会把 0x89 也送进 arm 分支，破坏自然观测）。

---

# §29 【2026-10-05】实跑结果：DW 任务应答已在实机跑通

## 29.1 两轮实跑

| 轮次 | run dir | life | st | 结果 |
|---|---|---:|---|---|
| KEYTASK | `IFS1_ELEVATED_20261005_113615` | 110.0 | 4→5 | `secrets.txt` 已写出，但**程序读不到** |
| KEYTASK2 | `IFS1_ELEVATED_20261005_113927` | 102.8 | 4→5 | ★ 实时解任务 + 回应答全部成功 |

第一轮暴露一个我们自己的 bug：观察器写的是 `key=value`（`aes_out=…`），
而 `read_secrets()` 只按空格切 → `have_aes_out=false`。已修（两种格式都收）。

## 29.2 KEYTASK2：实测日志（`logs\E57A5C_20261005_113919_a1\plain.jsonl`）

```
rx_task  seq=2  hmac_ok=true  marker=0x86 service=71 task=3 declared=147  have_aes_out=true have_aes_in=true
tx_task_reply reply_id=2 seq=1 task=3 len=66
rx_task  seq=3  hmac_ok=true  marker=0x86 service=71 task=7 declared=370
tx_task_reply reply_id=3 seq=2 task=7 len=66
rx_task  seq=4  hmac_ok=true  marker=0x86 service=71 task=9 declared=9
tx_task_reply reply_id=4 seq=3 task=9 len=66
```

* **`hmac_ok=true`** ⇒ `blob` → `hmac_out` 的还原表（`_HK_W1/_HK_I1`）也是对的；
* 出站 seq = 1,2,3 **每帧 +1**，`reply_id` 回显客户端 seq ⇒ 与参考实现一致；
* 客户端侧 `POST83_SAMPLE`：`5ec 1 → 4`（**收下并消费了我们的三帧应答**）；
  `644` 仍为 0。

## 29.3 密钥模型二次独立验证

新会话（`113919_a1`，与首轮密钥完全不同）：

```
aes_out=5ec9290a511cc7453eccf16cdabd40ff   （取 [p604+0x9C][:16]）
blob=b20a2f4e…16e7b7549407c079           ⇒ hmac_out=41483e5c47751b02e95e5c4d5cc9827c8fc4ac4d
4 条任务帧 hmac_ok 全部 = True
```

⇒ AES 密钥位置（provider `+0x9C`）与 HMAC 还原规则**各在两个独立会话上成立**。

## 29.4 修正后的判据

`644`（0x87 arm）**不是**进大厅的必要条件：它是 0x87/0x89 那条子协议的输入，
在正确的 DW 任务应答流里根本不会被驱动。§19~§27 追的"arm 失败"应整体作废。

当前真正的判据是**客户端还抱不抱怨**：

```
71/3 UserWarning … Address Fail | result = -3
71/7 ComError    … @SF_UI_DW_LIVE_DISCONNECTED … ${ZONEID(16701785630074219790)}
```

只要这两条还在，客户端就仍把 DW 大厅判成断开。

## 29.5 同一轮的 ETW 网络图（`runs\NET_CAPTURE_ELEVATED_20261005_113924\game_rt_report.md`）

```
connect 36 次：成功 27 / 失败 9
  成功：127.0.0.1:3074（auth）、127.0.0.2:8446（我们的明文大厅）
  失败：0.0.0.1:8081 / :80 / :443（err 0xC000006C）
        101.226.156.189:8081|:80|:443、140.206.164.16:8081|:80|:443（err 10054）
另有 3 台外网 121.51.232.79/93/95:3074 各 48 包（平台侧）
```

⇒ 下一步方向：查 `Address Fail -3` 具体指向（优先 `0.0.0.1` 与那两台被 reset 的 IP），
以及 71/3 是在 0x83 之后 0.01 s 就上报的这件事——说明客户端在握手一完成就去连了某个地址。
