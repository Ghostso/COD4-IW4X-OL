# 05 复用性判定

## 判定：**REUSE-PARTIAL**

> 定义回溯（任务书 §六）：密码学或帧格式部分匹配，但关键字段、状态机或消息语义仍有缺口。

### 支持复用的部分（PROVEN）

| 项 | 2697 客户端位置 | 参考对端位置 | 结论 |
|---|---|---|---|
| SHA-1 | `0x00A881B0`（名表 `0xC4461C`=`sha1`） | `sha1()` | 同算法 |
| HMAC-SHA1 | `0x00AA95C0` | `hmacSha1()` | 同算法 |
| secret 层 | key=`SHA1(transcript)`，data=`sessionKey24` @`0xAAB884` | `hmacSha1(sessionKey, transcriptHash)` | 同参数语义 |
| `expandKey` | `0x00AA9CE0`（HMAC-SHA1 计数器模式） | `expandKey()` | 同结构 |
| `CLIENTCHAL` | len=`0x0A`，out=`0x10` | 10B -> 16B | 同 |
| `BDDATA` | len=`0x06`，out=`0x48` | 6B -> 72B | 同 |
| 密钥切分 | challenge[8:16] + data 20/20/16/16 | 同 | **同** |
| 帧格式 | `u32len｜AB｜85｜seq｜iv16｜ct｜tag8` | 同 | 同 |
| MAC | HMAC-SHA1 over `frame[:-8]`，取前 8B | 同 | 同 |
| 接收序列号 | 严格递增（`[+0x5D0]`） | 顺序校验 | 同 |
| 消息码/阶段 | `{81,82,83,84,85}` 与阶段推进 | 同 | 同构 |

### 缺口（决定不能给 REUSE-SUPPORTED）

**首个已证实的结构差异：客户端在 `expandKey` 之后插入了额外的 20B/16B 密钥混淆层（codec），参考对端没有。**

证据：

```asm
; 0x00AAB911  call 0xAA9CE0  expandKey(secret,"BDDATA",72) -> [ebp-0xA8]
0x00AAB921  push 1                       ; 方向
0x00AAB923  lea  ecx,[ebp-0xA8]          ; data[0:20]
0x00AAB92C  call 0xAA8D70                ; <- codec_A，输出写 this+0x5F9
0x00AAB931  push 1
0x00AAB933  lea  edx,[ebp-0x94]          ; data[20:40]
0x00AAB93C  call 0xAA8BF0                ; <- codec_B，输出写 this+0x60D
```

`0xAA8D70` 与 `0xAA8BF0` 的函数体各自内联：

- 一组 20 字节常量（如 `0xAE091341...` / `0xAADE2280...`），
- 一组固定置换表（`[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]` / `[19,18,9,4,17,1,10,8,13,2,15,3,12,5,7,0,14,6,11]`），
- 逐字节 `dst[i] = CONST[PERM[i]] XOR src[i]`。

两个 codec 的调用者各仅 **2** 处：一处位于密钥派生路径（`0xAAB92C` / `0xAAB93C`），另一处位于 0x85 帧路径（发送 `0xAAACE3` / 接收 `0xAAB046`）用于安装帧密钥。即同一 codec 在“会话密钥派生”和“逐帧密钥装载”两处复用。参考对端（`Crypto.cpp`、`codol_crypto.py`、`_ref/CodolLocalLobbyServer.cs`）**均无此常量、此置换、此 XOR 步骤**（对常量与置换字节做全工作区文本扫描，0 命中）。

**独立佐证**：`REF_LOBBY_KIT/codol_crypto.py` 自身注释（L596-604）记录：以票据 24B x 12 种 transcript x 2 种 HMAC 参数序 x 2 种标签序穷举 5040 组，与真实内存密钥**全部不命中**，并因此把 `derive_session_keys` 降级为“仅用于诊断/互校”。这与“客户端另有 codec 层”在静态上互相印证。

### 为何不是 REUSE-REFUTED

- 参考定义的**算法族、标签、长度、切分、帧布局、MAC 覆盖/截断、序列号、消息码**与 2697 客户端**逐项一致**，不存在“协议语义冲突”。
- codec 层目前只能证明“客户端在派生值之上还有一层变换”，**不足以证明线上密钥 != 参考派生值**：该 codec 的输出落在对象的 `+0x5F9/+0x60D` 暂存区，而 AES/HMAC provider 句柄在 `+0x5F0/+0x5F4`；两者是否在 provider 装载前再次等价抵消，需进一步静态或离线定标才能判定。
- 因此这是**缺口**，不是**冲突**。

### 剩余最小缺失证据（用于升级到 SUPPORTED 或降级到 REFUTED）

1. 追踪 `0xAA8D70` 的 20B 输出（`this+0x5F9`）与 `0xAA8BF0` 的 16B 输出（`this+0x60D`）是否被 `AES_set_encrypt_key`/`HMAC_Init_ex` 的实参直接引用；若是，则线上密钥 = codec(派生值)，参考对端**必须补此层**。
2. 追踪 2697 客户端**出站**帧尾 HMAC 的 key 装载点（`obj+0x5F4` 的写入者）。
3. 用 `DemonwareTests.cpp:2455-2478` 的已知答案向量，对 2697 客户端做**离线重算**（不运行客户端），比对是否与参考 KAT 一致；若一致而线上仍不匹配，则 codec 层即为根因。

### 明确不作声明

- 本判定**仅表示静态复用性部分成立**，**不表示已完成，也未经任何实时互操作验证**（NOT-OBSERVED）。
- 不宣称 2697 客户端可连上参考对端；不宣称参考对端可直接服务 2697。
