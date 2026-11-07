# CODOL Keyflow 差异报告（001）

> 任务：**CODOL-KEYFLOW-INDEPENDENT-VERIFY-001**
> 范围：TC-01…TC-11 的差异、失败根因、缺失规范与限制。
> 实际执行日期：2026-10-12（本地）。执行环境：Windows + Python 3.11.9；库 `hashlib/hmac`（OpenSSL）、`pycryptodome 3.23.0`。

## 1. 执行结果总览

| 指标 | 数量 |
|---|---:|
| 用例总数（TC-01…TC-11） | 11 |
| PASS | **11** |
| FAIL | **0** |
| BLOCKED-MISSING-ORACLE | **0** |
| BLOCKED-INSUFFICIENT-SPEC | **0** |
| 首个差异偏移 | **无（全部 byte_match=YES）** |

**逐用例原始结果**：`CODOL_KEYFLOW_KAT_RESULTS_001.csv`（含 `input_hash`、`expected_source`、`actual_output_hash`、`byte_match`、`first_difference`、`status`）。
**原始字节证据**：`_data/kat_execution_log.json`（含 expected/actual 十六进制、提取的 Codec 常量/置换/掩码、原语自校验值）。

## 2. 逐用例差异结论

| test_id | 内容 | 期望来源 | 差异 | 说明 |
|---|---|---|---|---|
| TC-01 | SHA-1(transcript) | OpenSSL | 0 | 自写 SHA-1 与 OpenSSL 在 64B transcript 上一致 |
| TC-02 | secret=HMAC-SHA1(SHA1(TR), SK24) | OpenSSL | 0 | 自写 HMAC-SHA1 与 OpenSSL 一致 |
| TC-03 | expandKey(CLIENTCHAL,16) + response_id | OpenSSL 实例 **且** 项目 KAT | 0 | 双 oracle 同时命中 |
| TC-04 | expandKey(BDDATA,72) + 20/20/16/16 四切片 | OpenSSL 实例 **且** 项目 KAT | 0 | 双 oracle 同时命中 |
| TC-05 | 计数器模式 4 轮中间值 | OpenSSL 实例 | 0 | 每轮 20B 逐字节一致 |
| TC-06 | 截断边界 72/16/1 | OpenSSL 实例 + 长度约束 | 0 | 长度自洽、前缀一致 |
| TC-07 | Codec A 变换 | 冻结镜像机器码提取参数 | 0 | 67 向量×20B；置换式=掩码折叠式 |
| TC-08 | Codec B 变换 | 冻结镜像机器码提取参数 | 0 | 67 向量×20B |
| TC-09 | LOAD(STORE(x))==x | 定义式自洽 | 0 | A/B 各 256 组随机向量全部恢复 |
| TC-10 | 置换索引域 | 结构约束 | 0 | A/B 各 20 项，索引全在 0..19 |
| TC-11 | C# DecodeKey 展开 vs 冻结镜像掩码 | C# 源码常量 | 0 | M_A‖M_B 逐字节一致 |

## 3. 失败根因分析

**无失败。** 因此本报告不含失败根因分支。

为满足"失败时保留输入/输出/首差异/最小复现"的要求，执行器已内置该能力，并由**负对照**证明其有效性
（`_data/negative_controls.json`）：当人为引入错误时，评估器会给出 `byte_match=NO` 与首个差异偏移。
具体负对照：

- N1 篡改 1 字节 → MAC 不匹配（OK）
- N2 交换置换两项 → 输出改变（OK）
- N3 counter 起点由 1 改 0 → 输出改变（OK）
- N4 标签大小写 → 输出改变（OK）
- N5 截断 1 字节 → 输出改变（OK）
- N6 HMAC key/data 顺序互换 → 输出改变（OK）

**推论**：11/11 PASS 不是"评估器恒真"造成的假通过。

## 4. 缺失规范（BLOCKED 相关）

**本任务范围内没有 `BLOCKED` 用例。** 但下列**规范缺口**必须记录，它们不阻塞 TC-01…TC-11，却阻塞更强的结论：

| # | 缺失规范/证据 | 影响 | 状态 |
|---|---|---|---|
| S-1 | 算法**结构描述**的独立规范来源（当前仍与既有项目记录同源） | 规范独立性未达成；一致性只能说"独立原语+独立参数" | 未消除 |
| S-2 | 真实 Demonware 服务端的原始 I/O 样本 | 无法验证 KAT 是否等于"原版服务端真实行为" | 未提供 |
| S-3 | 2697 客户端运行时段位样本（KDF 中间值/内存密钥） | KDF 与 codec 等价性仍为静态/离线性质 | 未提供 |
| S-4 | 对端实现（面向 1.1.1.13/3.3.3.3）在 2697 上的地址口径映射 | 影响后续 G3/G5 的适配判定 | 未提供 |
| S-5 | `.tvm0` 完整语义 | 不阻塞本任务；阻塞"绝对不参与"的更强命题 | 未提供（Q-111 BLOCKED） |

> 说明：S-1…S-5 均**不**满足"缺失可信预期值或必要规范"的 `BLOCKED-MISSING-ORACLE` /
> `BLOCKED-INSUFFICIENT-SPEC` 触发条件——因为 TC-01…TC-11 各自都有可用的预期来源（OpenSSL 实例、
> 冻结镜像机器码、定义式自洽、C# 源码常量）。它们影响的是**结论的强度**，不是**用例的可执行性**。

## 5. 结论强度与限制（不得夸大）

1. **原语层**：独立（自写实现 ↔ OpenSSL/pycryptodome 双实现一致）。
2. **参数层**：独立（Codec 常量/置换直接来自冻结镜像机器码；KDF 标签/长度直接来自冻结镜像 `.rdata` 与调用序列立即数）。
3. **规范层**：**共享**（算法结构描述仍来自既有项目记录）。
4. **KAT 层**：**同源**（`DemonwareTests.cpp` 与 `codol_crypto.py` 使用同一组向量）。KAT 在本任务中只作为**被检验的主张**，不作为独立 oracle 的唯一依据；独立 oracle 是 OpenSSL 实例与冻结镜像参数。
5. **TC-09 往返一致性 ≠ 算法正确性**；**两个实现一致 ≠ 与原版服务端一致**（`REUSE-SUPPORTED` 的限定继续有效）。
6. 本任务**未**产生任何运行时数据；`NOT-OBSERVED` 不变。

## 6. 复现步骤（最小可重复）

```powershell
# 工作目录：D:\BaiduNetdiskDownload\使命召唤OL
python -X utf8 "CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\indep_primitives.py"      # 原语自检
python -X utf8 "CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\extract_codec.py"         # 从冻结镜像提取 Codec 参数
python -X utf8 "CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\run_kat.py"               # 执行 TC-01..TC-11
python -X utf8 "CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\negative_controls.py"     # 负对照
```

预期：`run_kat.py` 输出 `rows=11 PASS=11 FAIL=0`；`negative_controls.py` 输出 `ALL True`。
