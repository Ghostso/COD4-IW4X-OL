# -*- coding: utf-8 -*-
import os
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
D = lambda n: os.path.join(root, n)
docs = {}

docs["05_FINAL_VERDICT.md"] = r"""# 05 最终判定

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
"""

docs["06_NEGATIVE_EVIDENCE_AND_LIMITS.md"] = r"""# 06 负证据与边界

## 1. 已执行的否定搜索

| # | 搜索 | 范围 | 方法 | 结果 | 边界 |
|---|---|---|---|---|---|
| N1 | codec A/B 直接调用者 | `.text` 全节 | `E8 rel32` 调用图 | 各 **2** 处，共 4 处 | 不含 `FF15/FFD2` 间接调用（另由 N2 覆盖） |
| N2 | codec A/B 函数地址字面量 | 全镜像（`.text/.rdata/.data/.tvm0/.rimp`） | 32-bit LE 扫描 | **0** | 证明无函数指针调用 |
| N3 | `+0x5F0`/`+0x5F4` 写入点 | `.text` 全节 | 指令级编码扫描+边界校验 | 各 2 处（KDF new + 重置置 0） | 未含跨对象类型混淆的候选（已按调用点上下文排除） |
| N4 | `+0x5F8`/`+0x60C` 写入点 | `.text` 全节 | 同上 | 仅 codec STORE 分支 | — |
| N5 | `.tvm0` 内字段偏移字面量 | `.tvm0` 全 raw | dword 精确搜索 | `5F0/5F8/5F9/5FC/60C/60D` **0**；`5F4` 2 处**均为误命中**（`sub esp,0x5F4`、非指令边界字节） | 字面量扫描；未做 VM 语义还原 |
| N6 | `.tvm0` 内 codec 常量/置换/标签 | `.tvm0` 全 raw | 精确字节搜索 | **全部 0** | 同上 |
| N7 | AES `setKey`（vtable[1]）调用点 | `.text` 全节 | 调用图 + 上下文 | 各 provider **1** 处（`0xAAB99A`、`0xAAB9FE`） | 证明无第二条注入路径 |
| N8 | `expandKey`/`secret` 第二来源 | `.text` 全节 | 调用图 | expandKey 1 个实现 2 个调用者；HMAC-SHA1 1 个调用者 | — |
| N9 | `BDDATA`/`CLIENTCHAL` 第二引用 | `.text` 全节 | 立即数扫描 | 各 **1** 处 | — |
| N10 | 参考对端 C# 的 codec 等价实现 | `REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs` | 源码逐项 | `DecodeKey` 常量/置换/变换式**完全一致** | 该文件为三方实现，非 2697 生态内材料 |

## 2. 盲区（不得据此断言）

| 盲区 | 说明 |
|---|---|
| `.tvm0` VM 完整语义 | 未逐指令还原。本任务只验证与 codec/字段/常量/标签的**交集**（N5/N6 全 0），未做"绝对不参与"的更强证明 |
| 间接调用 | 全节 `E8` 扫描不含 `call [reg]`/`call [mem]`。但 codec A/B 的函数地址在全镜像字面量为 0，且函数为 `ret` 终结的纯函数，因此无函数指针入口（N2） |
| 运行时密钥样本 | 未采样；等价性为**静态**推论，无 bit 级运行时比对 |
| 1.1.1.13 / 3.3.3.3 客户端 | 未核对；不得用其余构建推断 2697 |
| 打包客户端 `.tp3` | 加壳段，无法就地核对 |

## 3. 措辞边界（必须遵守）

- 可以："客户端四个最终消费点的密钥材料与参考对端 `deriveSessionKeys` 输出逐字节相同（静态证明）。"
- 可以："参考对端 C# 路径已实现同一 codec（`DecodeKey`），且用途一致。"
- 可以："本轮不改写 NOT-OBSERVED。"
- 不可："已完成互操作验证"或"客户端已能连上参考对端"。
- 不可："`ol-mod` C++ 缺少 codec 因此不兼容。"（其派生输入本就在洁净域，codec 净恒等，故其输出即正确值。）
- 不可："`.tvm0` 已被完整排除。"（仅证明三条交集为空，未做完整 VM 语义还原。）

## 4. 本轮对上轮报告的更正（保留旧报告原文，仅增量更正）

| 上轮表述 | 本轮更正 | 依据 |
|---|---|---|
| 05 号报告："参考对端均无此常量、此置换、此 XOR 步骤" | **不完整**：`ol-mod` C++/Python 无；但 `REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs`（三方实现）**有**，且逐字节一致 | 03 §3 / 05 §3 |
| 05 号报告称 `obj+0x5F0/+0x5F4` 为"密码学 provider 候选位置"、`+0x5F9/+0x60D` 为"codec 输出位置" | 前者**正确**（是 provider 指针）；后者措辞不准（是写法定址常量，真实缓冲区为 `+0x5F8..0x60B` / `+0x60C..0x61F`） | 02 §0 |
| 06 号报告称 `.tvm0` VA = `0x0D955000` | **笔误**；正确 VA = `0x0DD58000`（RVA `0x0D958000`） | 01 §0 / 04 §0 |
| 05 号报告称 codec 调用者"各仅 2 处，全部位于密钥派生路径" | 措辞含糊：4 处 = 派生 **STORE** 2 处 + 帧路径 **LOAD** 2 处 | 01 §5 |

## 5. 与既有结论的关系

- 上轮 REUSE-PARTIAL 的**唯一决定性缺口**（codec 层）在本轮被证明不成立（净恒等 + 参考已有等价实现）。
- 上轮其余结论（SHA-1/HMAC-SHA1/expandKey/标签/长度/切分/帧格式/MAC/序列号/消息码）**原样保留**，本轮无异议。
- E-27 的服务端侧负证据（2697 服务端生态不含 Demonware）**不受影响**。
"""

docs["07_QUESTION_REGISTER_DELTA.md"] = r"""# 07 问题登记簿增量（以 CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001 为起点）

## 1. 开工基线核对

上轮交付值（`07_QUESTION_REGISTER_DELTA.md` §3/§4）：

| 项 | 值 |
|---|---:|
| 总权重 | 570 |
| 加权得分 | 294.5 |
| 认知完备率 | 51.67% |
| I4 权重 | 312 |
| I4 加权得分 | 161.6 |
| I4 完备率 | 51.79% |
| 实时互操作 | NOT-OBSERVED |

复算：`294.5/570 = 51.667%` ✓；`161.6/312 = 51.795%` ✓。基线一致，沿用。

## 2. 本轮新增问题

| Q ID | 协议层 | 问题 | 影响 | 权重 | 状态 | 解决度 | 加权贡献 | 证据 |
|---|---|---|---|---|---|---|---|---|
| Q-103 | 密钥流/Codec | 两 codec 的调用约定、常量 XOR、置换、方向语义 | I4 | 8 | PROVEN | 1.0 | 8.0 | 01 §1–§5 |
| Q-104 | 密钥流/字段 | `+0x5F0/+0x5F4` 与 `+0x5F9/+0x60D` 的真实语义 | I4 | 8 | PROVEN | 1.0 | 8.0 | 02 §0（更正上轮错标） |
| Q-105 | 密钥流/def-use | codec 输出的唯一写入者与唯一读取者 | I4 | 8 | PROVEN | 1.0 | 8.0 | 02 §4–§5 |
| Q-106 | 密钥流/消费 | 四个最终消费点的密钥来源与方向 | I4 | 8 | PROVEN | 1.0 | 8.0 | 03 §1–§3 |
| Q-107 | 密钥流/等价 | codec 是否改变最终消费值（STORE/LOAD 同掩码） | I4 | 8 | **PROVEN（等价）** | 1.0 | 8.0 | 03 §4 / 05 §2 |
| Q-108 | 对端/适配 | 参考对端是否已有该 codec 的等价实现 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | 05 §3（`DecodeKey` 逐字节一致） |
| Q-109 | 方法学 | 上轮"对端无 codec"与 `.tvm0` 地址口径 | I2 | 3 | **REFUTED** | 0.0 | 0.0 | 06 §4 |
| Q-110 | `.tvm0` | VM 段是否存在与 codec/字段的交集路径 | I4 | 8 | PROVEN（交集全空） | 1.0 | 8.0 | 04 §1（`5F0/5F8/5F9/5FC/60C/60D` 全 0；`5F4` 2 处误命中） |
| Q-111 | `.tvm0` | VM 段完整语义是否已还原 | I3 | 5 | **BLOCKED** | 0.0 | 0.0 | 04 §5（未逐指令还原） |

## 3. 重算（统一口径，未改动评分尺度）

- 权重合计 +`8+8+8+8+8+8+3+8+5 = 64` → **新总权重 634**
- 得分合计 +`8+8+8+8+8+8+0+8+0 = 56.0` → **新加权得分 350.5**
- **新认知完备率 = 350.5 / 634 = 55.28%**
- I4 新增：Q-103(+8)、Q-104(+8)、Q-105(+8)、Q-106(+8)、Q-107(+8)、Q-108(+8)、Q-110(+8) → I4 权重 `312+56 = 368`
- I4 得分 `8×7 = 56` → `161.6+56 = 217.6`
- **I4 加权完备率 = 217.6 / 368 = 59.13%**
- 实时互操作：**NOT-OBSERVED（未变）**

## 4. 校验

- 权重：`570 + 64 = 634` ✓
- 得分：`294.5 + 56.0 = 350.5` ✓
- I4 权重：`312 + 56 = 368` ✓
- I4 得分：`161.6 + 56 = 217.6` ✓
- I4 率：`217.6 / 368 = 59.1304%` ≈ 59.13% ✓
- 主率：`350.5 / 634 = 55.2839%` ≈ 55.28% ✓

## 5. 历史修订保留

- Q-92…Q-102（上轮）**原样保留**；其中 **Q-101**（"参考对端是否实现客户端 codec 层"，上轮 REFUTED）本轮**被推翻为"参考 C# 路径确实实现了，且逐字节一致"**——按登记簿纪律**新增 Q-108 记录该更正**，不删除 Q-101 原文。
- E-19/E-21/E-22/E-23/E-25/E-26/E-27 的既有 REFUTED 记录**原样保留**。
- 本轮**新增更正**（不删旧文）：上轮 06 §4 两处措辞、`.tvm0` VA 笔误、codec 调用点枚举，均见 06 §4。
- 认知完备率上升来自真实解析，非口径放宽；同时新增 1 项 REFUTED（Q-109）与 1 项 BLOCKED（Q-111）。**认知完备率不代表互操作完成率。**
"""

for name, text in docs.items():
    with open(D(name), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", name, len(text))

files = sorted(f for f in os.listdir(root) if f.endswith(".md"))
lines = []
for f in files:
    lines.append("%s  %s" % (hashlib.sha256(open(D(f),"rb").read()).hexdigest(), f))
for d in ("_data",):
    dd = os.path.join(root, d)
    if os.path.isdir(dd):
        for f in sorted(os.listdir(dd)):
            fp = os.path.join(dd, f)
            lines.append("%s  %s/%s" % (hashlib.sha256(open(fp,"rb").read()).hexdigest(), d, f))
open(D("SHA256SUMS.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("SHA256SUMS:", len(lines), "entries")
