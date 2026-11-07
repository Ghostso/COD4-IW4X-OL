# CODOL Keyflow 独立实现说明（001）

> 任务：**CODOL-KEYFLOW-INDEPENDENT-VERIFY-001**
> 依据：`CODOL-DEMONWARE-RUNTIME-VALIDATION-001`（G2 优先任务）与已冻结证据基线
> 性质：纯离线 / 只读。**不**执行运行时握手，**不**修改游戏二进制，**不**宣称真实 Demonware 服务端兼容性。
> 执行前基线复核：任务依据 6/6 文件哈希通过；证据包 94/94；冻结输入 4/4；参考源码 6/6（见 §5）。

## 1. 独立性的定义与本任务的判定口径

本任务区分三类"独立"，任何一类都不能自动升级为"真实服务端兼容"：

| 层次 | 含义 | 本任务判定 |
|---|---|---|
| **原语独立** | 基础密码原语（SHA-1/HMAC-SHA1/AES）不共用实现 | **达成**（新实现自写 SHA-1/HMAC-SHA1/AES；与 OpenSSL/pycryptodome 交叉校验） |
| **参数独立** | 协议参数（常量表/置换/标签/长度）不来自同一份报告的文本值，而来自**独立 artifact**（冻结镜像机器码） | **达成**（直接从 `codol2697-static-candidate.bin` 机器码提取） |
| **规范独立** | 算法描述（结构/顺序/方向）来自与既有实现无派生关系的独立规范 | **未达成**（算法结构描述仍与既有项目记录**同源**） |

**结论口径**：本实现达到**原语独立 + 参数独立**；**规范描述仍然共享**。因此本任务只能支持
"**独立原语 + 独立 artifact 参数下的一致**"，**不能**宣称"与真实 Demonware 服务端兼容"。这一点在 G2 判定（`CODOL_KEYFLOW_G2_DECISION_001.md`）中如实体现。

## 2. 既有实现的依赖与来源审查（先审查，后实现）

### 2.1 三份既有实现的来源链

| 实现 | 文件 | 原语来源 | 协议逻辑来源 |
|---|---|---|---|
| C++ | `_e1_regression/ol-mod-olfinal/src/backend/Demonware/Crypto.cpp` | Windows **BCrypt**（`BCryptOpenAlgorithmProvider`/`BCryptHashData`） | `ol-mod` 项目自述 |
| Python | `REF_LOBBY_KIT/codol_crypto.py` | 标准库 **hashlib/hmac** | 文件头自述："依据三方 `CodolLocalLobbyServer.cs` 逐字段照抄" |
| C# | `REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs` | .NET `AesCryptoServiceProvider`/`HMACSHA1`（`DecodeKey` 为自写） | 三方实现（`codol_crypto.py` 的原始依据） |

### 2.2 已确认的派生关系（关键）

1. `codol_crypto.py` 与 C#：Python **照抄** C#（其文件头与 `expand_key` docstring 均注明）。**同源**。
2. C++ `ol-mod` 与 Python：两者使用**同一组 KAT**（`sessionKey="Shippo fuute, mofu-mofu!"`、`transcript=00..3F`、
   `response_id=ea09fd53...`）。`codol_crypto.py` 的 `__main__` 自测**直接引用** `ol-mod` 的 KAT 出处
   （`DemonwareTests.cpp:2455-2478`）。**KAT 同源**。
3. 因此 **"C++ ↔ Python ↔ C#" 的输出一致**只能证明**同一谱系内部自洽**，**不构成**独立外部验证。
   这正是上一轮 `CODOL_KEYFLOW_GOVERNANCE`/G2 判定"现有参考不满足独立性"的原因。

### 2.3 本任务采用的独立性策略

- **原语层**：**完全自写** SHA-1（FIPS 180-4）、HMAC-SHA1（RFC 2104）、AES-128（FIPS 197，含 CBC）。
  **不** import `hashlib`/`hmac`/`cryptography`/`Crypto` 参与被测路径。
- **参数层**：Codec 的常量表与置换表**从冻结镜像的机器码独立提取**（解析 `mov dword [ebp-x], imm32`
  指令与寄存器填充项），**不读取**任何报告的十六进制文本。
- **校验层**：自写原语与**外部标准实现**（OpenSSL `hashlib/hmac`、pycryptodome）交叉比对；
  协议输出与**项目记录的 KAT**（作为"被检验的主张"）比对。
- **负对照**：另做变异测试，证明评估器确实能捕获错误（见 §6）。

## 3. 独立实现清单

| 文件 | 作用 | 说明 |
|---|---|---|
| `_tools/indep_primitives.py` | 自写 SHA-1 / HMAC-SHA1 / AES-128（ECB 块 + CBC） | 零外部密码依赖 |
| `_tools/extract_codec.py` | 从冻结镜像机器码提取 Codec 常量表/置换表 | 独立 artifact oracle |
| `_tools/indep_protocol.py` | 独立 KDF（`expand_key` / `derive_session_keys`）与 Codec 变换 | 依据算法结构描述 |
| `_tools/run_kat.py` | 执行 TC-01…TC-11，产出结果 CSV 与原始日志 | 主执行器 |
| `_tools/negative_controls.py` | 变异 / 负对照 | 证明评估器有效性 |

## 4. 算法步骤、依据与与既有实现的差异

### 4.1 KDF

| 步骤 | 本实现的依据 | 与既有实现的差异 |
|---|---|---|
| `sha1(transcript)` | FIPS 180-4 自写；结构 = 项目记录"transcript 摘要=SHA-1" | 原语独立（自写 vs BCrypt hashlib） |
| `secret = HMAC-SHA1(key=SHA1(transcript), data=sessionKey24)` | RFC 2104 自写；参数序 = 项目记录公式 | 原语独立；**参数序仍沿用共享描述** |
| `expand_key(secret, label, size)`：`prev = HMAC(secret, prev‖label‖counter)`, `counter` 自 1 递增，拼接后截断 | 结构 = 项目记录 `expandKey` 描述 | 原语独立；**结构与 counter 起点沿用共享描述** |
| 标签 `CLIENTCHAL`（10B→16B）、`BDDATA`（6B→72B） | 标签字面**从冻结镜像 `.rdata` 独立复读**；长度**从 KDF 调用序列的 `push 0x0A/0x06/0x10/0x48` 立即数独立确认** | 参数独立（不再依赖报告文本） |
| 72B 分段 20/20/16/16（+ `challenge[8:16]`） | 分段边界 = 项目记录；切片长度与 KAT 四切片比对 | 分段结构沿用共享描述 |

**KDF 参数独立取证（从冻结镜像机器码）**

```text
0xAAB8B8  6a 10            push 0x10        ; outLen  = 16
0xAAB8C0  c8 50            (lea ...)        ;
0xAAB8C2  6a 0a            push 0x0A        ; labelLen= 10
0xAAB8C4  68 44 b1 c5 00   push 0x00C5B144  ; "CLIENTCHAL"
0xAAB8CB  6a 14            push 0x14        ; secretLen=20
0xAAB8F8  6a 48            push 0x48        ; outLen  = 72
0xAAB901  6a 06            push 0x06        ; labelLen= 6
0xAAB903  68 3c b1 c5 00   push 0x00C5B13C  ; "BDDATA"
```

- `.rdata` 字面复读：`BDDATA` @ `0x00C5B13C` = 6 字节；`CLIENTCHAL` @ `0x00C5B144` = 10 字节。

### 4.2 Codec

| 步骤 | 本实现的依据 | 与既有实现的差异 |
|---|---|---|
| `out[j] = in[j] XOR CONST[PERM[j]]`（20B，4×5） | 结构 = 项目记录指令级语义 | **参数独立**：`CONST_A/B`、`PERM_A/B` 从冻结镜像机器码提取 |
| STORE（dl≠0）/ LOAD（dl=0）同掩码 | 结构 = 项目记录 | 原语与参数独立 |
| 往返 `LOAD(STORE(x))==x` | 掩码定义式自洽 | 独立于既有实现 |

**Codec 参数独立取证（从冻结镜像机器码）**

```text
A_CONST = 411309ae3fa3bcf31872eabc093211cc124254f4
A_PERM  = [7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]
B_CONST = 8022deaa0b1c21f400ffee37279210ceaaf43c21
B_PERM  = [19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]
掩码 M_A = f342111272f4324109ae3f1813eabca354bc09cc   （按 CONST_A[PERM_A[i]] 展开）
掩码 M_B = 213cff0bf422ee0092deceaa27aa1cf480102137
```

提取方法（不读报告）：解析序言区 `mov dword [ebp-x], imm32`（`C7 45 xx imm32`）与
`mov [ebp-x], edx/edi/ebx`（寄存器填充项，通过 `mov edx,9` / `lea ebx,[edx+9]` / `mov edi,4` / `mov edx,0x10` 追踪寄存器值），
按 `[ebp-0x68] + 4k` 顺序还原 20 项置换。

## 5. 执行前基线复核（本任务 §2.3 / §3.3）

| 对象 | 期望 | 实测 | 结果 |
|---|---|---|---|
| 任务依据 6 文件（`SHA256SUMS_RUNTIME_VALIDATION_001.txt`） | 5+1 条 | 5/5 通过 | **通过** |
| 证据包外层清单 | 94 | 94/94 | **通过** |
| 冻结客户端恢复镜像 | `24b4ef25…97e4` | 一致 | **通过** |
| 冻结打包客户端 | `35375404…d6e1` | 一致 | **通过** |
| 冻结服务端 | `80816711…0ea1` | 一致 | **通过** |
| 参考源码 6 份 | 见 §2.1 | 6/6 一致 | **通过** |

**输入一致，未触发停止条件。**

## 6. 原语自校验与负对照

**原语自校验（与外部标准实现交叉）**

| 检验 | 自写实现 | 外部 oracle | 结果 |
|---|---|---|---|
| SHA-1("") | `da39a3ee…80709` | OpenSSL `da39a3ee…80709` | 一致 |
| SHA-1(0..1000B 共 11 长度) | — | OpenSSL | 全部一致 |
| HMAC-SHA1(RFC 2202 #1) | `b6173186…6be00` | OpenSSL | 一致 |
| AES-128 FIPS-197 附录 B | `69c4e0d8…4c55a` | pycryptodome | 一致 |
| AES 随机 64 组（加/解密） | — | pycryptodome | 全部一致 |
| AES-CBC 2 块 | — | pycryptodome | 一致 |

**负对照（证明评估器能捕获错误，`_data/negative_controls.json`）**

| # | 检验 | 期望行为 | 结果 |
|---|---|---|---|
| N1 | 篡改 1 字节 → MAC | 必须不匹配 | OK |
| N2 | 交换 2 项置换 | 输出必须改变 | OK |
| N3 | counter 起点 0 vs 1 | 输出必须不同 | OK |
| N4 | 标签大小写变化 | 输出必须不同 | OK |
| N5 | 截断 1 字节 | 输出必须不同 | OK |
| N6 | HMAC key/data 顺序互换 | 输出必须不同 | OK |
| N7 | SHA-1 边界长度 | 与 OpenSSL 一致 | OK |
| N8 | 自写 AES vs pycryptodome | 一致 | OK |
| N9 | 自写 CBC vs pycryptodome | 一致 | OK |

> N1–N6 证明：若参数/顺序/截断有误，评估器会报 FAIL，不会"永远 PASS"。

## 7. 仍然共享的部分（明确标记）

| 共享项 | 性质 | 影响 |
|---|---|---|
| 算法**结构描述**（transcript 组成、secret 参数序、expandKey 计数器结构、codec 变换式、20/20/16/16 分段） | 来源于项目既有报告（与 C++/Python/C# 同源的项目记录） | **规范独立性未达成** |
| **KAT 测试向量**（`response_id`、四切片；`DemonwareTests.cpp:2455-2478`） | 与 `ol-mod` 和 `codol_crypto.py` **同一来源** | KAT 只能作为"被检验主张"，**不能**作为独立 oracle 的唯一依据 |
| C# `DecodeKey` 常量（TC-11） | 与 Python 同源 | 仅作**跨 artifact 一致性**，不作独立验证 |

**因此**：本任务的一致性结论 = "**独立原语 + 独立 artifact 参数**，在**共享规范**下复现了既有 KAT 与结构"。 
它**加强**了静态证据，但**不能**替代"真实 Demonware 服务端兼容性"验证（后者需 G4/G5）。

## 8. 结论边界（必须遵守）

- **可以**："在独立自写原语与从冻结镜像独立提取的参数下，KDF 输出与 Codec 掩码逐字节复现了既有 KAT 与结构。"
- **可以**："自写 SHA-1/HMAC-SHA1/AES 与 OpenSSL/pycryptodome 在给定向量上一致。"
- **不可以**："已完成互操作验证" / "与真实 Demonware 服务端兼容"。
- **不可以**："TC-11 构成独立验证"（C# 与 Python 同源）。
- **不可以**："G3/G4/G5 已通过"（本任务只覆盖 G2；运行时状态仍为 `NOT-OBSERVED`）。
