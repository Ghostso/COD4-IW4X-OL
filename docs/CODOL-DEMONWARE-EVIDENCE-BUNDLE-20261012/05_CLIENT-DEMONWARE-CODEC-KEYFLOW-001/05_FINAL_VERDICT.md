# 05 最终判定

## 判定：**KEYFLOW-EQUIVALENT**

> 定义（任务书 §7）：已证明客户端最终消费值与参考对端派生值等价。

这是本任务四类非 BLOCKED 结论中**最强**的一类，且它**同时蕴含** `KEYFLOW-DIRECT`/`KEYFLOW-TRANSFORMED` 所要回答的问题：数据流不仅闭合，而且最终消费的密钥字节与参考对端 `deriveSessionKeys` 的输出**逐字节相同**。

## 1. 最终消费矩阵（客户端实测）

| 消费点 | 指令 VA | 密钥材料 | 是否经 codec | 参考对端对应变量 |
|---|---|---|---|---|
| 出站 AES 加密 | `0xAAACB5`（vtable[2]） | `data[40:56]` | **否** | `decrypt`（对端解客户端帧） |
| 出站 HMAC 签名 | `0xAAACE3`（codec A LOAD）→ `0xAAB884` | `data[0:20]` | 是（存取往返） | `requestHmac` |
| 入站 HMAC 验签 | `0xAAB046`（codec B LOAD）→ `0xAAB085` | `data[20:40]` | 是（存取往返） | `responseHmac` |
| 入站 AES 解密 | `0xAAB140`（vtable[3]） | `data[56:72]` | **否** | `encrypt`（对端加密应答） |

其中 `data[0:72] = expandKey(HMAC_SHA1(key=SHA1(transcript), data=sessionKey24), "BDDATA", 72)`。

## 2. 等价性证明（bit-exact）

**前提（均已 PROVEN）**

1. `expandKey` 的输入材料、标签字节、输出长度与参考对端逐项相同（上轮 01/02 号报告，本轮复核无异议）。
2. 四切片 `data[0:20]/[20:40]/[40:56]/[56:72]` 的栈地址与长度与参考对端四变量一一对应（本轮 03 §2）。

**codec 的净效果**

```text
clientStore_A(x) = x XOR M_A        (0xAAB92C, dl=1)
clientLoad_A(y)  = y XOR M_A        (0xAAACE3, dl=0)
  同一函数 0x00AA8D70；M_A 由同一常量表 + 同一置换表决定（无第二份表）
⇒ clientLoad_A(clientStore_A(x)) = x    逐字节恒等
```
Codec B（`0x00AA8BF0`，`M_B`）同理。

**逐字节结论**

```text
K_client, HMAC-request  = clientLoad_A(clientStore_A(data[0:20]))  = data[0:20]  = requestHmac
K_client, HMAC-response = clientLoad_B(clientStore_B(data[20:40])) = data[20:40] = responseHmac
K_client, AES-out       = data[40:56]                              = decrypt
K_client, AES-in        = data[56:72]                              = encrypt
```

⇒ **四个最终被密码学操作实际消费的密钥材料，与参考对端 `deriveSessionKeys` 的输出逐字节相同。**

## 3. 独立佐证：参考对端第三方实现已含同一 codec

`REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs`（三方权威实现，`codol_crypto.py` 的原始依据）在读取客户端内存密钥时实现了 `DecodeKey`：

```csharp
// line 264-276
private static byte[] DecodeKey(byte[] source, int start, uint[] words, int[] indices) {
    byte[] array = new byte[words.Length * 4];
    ...
    for (int j = 0; j < indices.Length; j++)
        array2[j] = (byte)(source[start + j] ^ array[indices[j]]);
    return array2;
}

// line 315: HmacOut
DecodeKey(array2, 0,  new uint[5]{2919830337,4089226047,3169481240,3423678985,4099162642},
         new int[20]{7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15});
// line 320: HmacIn
DecodeKey(array2, 20, new uint[5]{2866684544,4095810571,938409728,3457192487,557642922},
         new int[20]{19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11});
```

逐字节核对（本轮）：

| 项 | 2697 客户端 | 参考 C# | 一致 |
|---|---|---|---|
| 常量表 A | `411309ae 3fa3bcf3 1872eabc 093211cc 124254f4` | 同 | ✅ |
| 常量表 B | `8022deaa 0b1c21f4 00ffee37 279210ce aaf43c21` | 同 | ✅ |
| 置换 A | `[7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]` | 同 | ✅ |
| 置换 B | `[19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]` | 同 | ✅ |
| 变换式 | `out[j] = src[j] XOR CONST[PERM[j]]` | `array2[j] = source[start+j] ^ array[indices[j]]` | ✅ |
| 应用位置 | `data[0:20]`→HmacOut；`data[20:40]`→HmacIn | 同 | ✅ |
| 作用对象 | codec 输出（去掩码）即洁净密钥 | 内存读到的原始 40B 先解掩码再用 | ✅ |

即：**参考对端（C# 那条路径）早已把这个 codec 纳入实现，且用途与客户端完全一致**。`ol-mod` C++ 与 `REF_LOBBY_KIT` Python 走的是另一条更"干净"的路径（直接持有 `expandKey` 原值），**不需要**该 codec，因为它们的派生输入本身就在洁净域。

## 4. 对 REUSE-PARTIAL 的影响

| 项 | 上轮 | 本轮 | 说明 |
|---|---|---|---|
| 首个差异（"客户端 codec，对端没有"） | 记为缺口，判定 REUSE-PARTIAL | **REFUTED** | 该缺口不成立：codec 净效果为恒等，且参考对端 C# 路径本就实现了它 |
| `K_client,consumed ?= K_reference,derived` | 未决 | **相等（PROVEN，静态）** | 四个消费点全部 bit-exact |
| 复用性判定 | REUSE-PARTIAL | **建议升级为 REUSE-SUPPORTED（静态）** | 见 §5 |
| 实时互操作 | NOT-OBSERVED | **NOT-OBSERVED（不变）** | 本轮为纯静态审计，未做任何运行时验证 |

## 5. 建议的复用性判定（供登记簿采纳，不在本任务自动改写旧报告）

**REUSE-SUPPORTED（仅限静态）**：
上轮列为唯一决定性缺口的 codec 层，本轮证明为**可逆表示变换**且**参考对端已有等价实现**；四个最终消费点与参考派生值 bit-exact。因此上轮"REUSE-PARTIAL"的降级理由消失。

**但必须保留的两条限定**：

1. **NOT-OBSERVED 不得改写**：本任务全程静态，未启动客户端/服务端，未做任何握手或帧级实测。`REUSE-SUPPORTED` 只表示"静态证据支持复用"，**不等于互操作成功**。
2. **等价性前提**是"客户端在同一函数、同一常量表/置换表下按 `dl` 两分支执行"。该前提已由指令级证据确定，但未用运行时样本二次验证。

## 6. 证据等级汇总

| 结论 | 等级 |
|---|---|
| codec 仅作用于 `data[0:20]`/`[20:40]`（HMAC），AES 密钥不经 codec | PROVEN |
| codec STORE/LOAD 同掩码 ⇒ 逐字节恒等 | PROVEN |
| 四个消费点与参考四变量一一对应（含方向） | PROVEN |
| 参考 C# `DecodeKey` 与客户端常量/置换逐字节相同 | PROVEN |
| `K_client,consumed = K_reference,derived` | **PROVEN（静态、bit-exact）** |
| 实时互操作 | **NOT-OBSERVED** |
