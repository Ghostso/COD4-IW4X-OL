# 08_HYPOTHESIS_AND_CONTRADICTION_LEDGER — 竞争假设与矛盾账本

**口径:** `CONFIRMED` / `CROSS_VALIDATED` / `INFERRED` / `UNKNOWN` / `BLOCKED`。

---

## 1. 竞争假设:net-buffer 解码器 (`0x87C110`/`0x87D5A0`) 的归属

| 假设 | 支持证据 | 反证 | 缺失证据 | 判定 |
|---|---|---|---|---|
| H-A:纯 TQOS/QoS 内部私有格式 | 唯一可复核直接调用者=`0x85D3A0/0x85D430/0x85D5A0/0x85E6F0`(TQOS 族);对象字段 `QOSCSPkg*`/`QOSSSPkg*`;`udp://%s:%d`;`tqos_*` | 解码器是**通用 net-buffer 原语**(错误串含 `net_start/net_end/sizeinfo_size`),非 QoS 专有命名 | 是否存在非 TQOS 调用者;输入缓冲来源 | **CROSS_VALIDATED(调用者为 TQOS) + UNKNOWN(是否独占)** |
| H-B:游戏业务 netchan 序列化原语(被 TQOS 复用) | net-buffer 语义串;元素类型/元素数/尺寸乘;与 2697 服务端 netfield 概念同构 | 未定位任何业务调用者;未见 gamestate/configstring/snapshot 关联 | 业务调用链;**接收点** | **INFERRED(可能) / BLOCKED(未闭合)** |
| H-C:两者皆是(共享库,多消费者) | 同上 | 同 H-A/H-B | 多消费者证据 | **UNKNOWN** |

**裁定:** 不强行选定。042 的"已确认非业务"超出证据;可确证的是 **TQOS 是已证实的消费者之一**,
**不足以排除**业务消费者。→ 采 **H-C(UNKNOWN)**。

---

## 2. 竞争假设:`0x85E6F0` 的性质

| 假设 | 支持 | 反证 | 判定 |
|---|---|---|---|
| 平台 QoS 分派器 | 属 `tqos_create_protohandle`(0x85EB50)构造的对象;类型字 4/6 | 分派器函数体内**无** TQOS 字符串引用(靠对象归属而非自身引用) | **CROSS_VALIDATED**(对象归属) |
| 游戏业务分派器 | 形状为"读包→类型字→分派" | 无业务消息语义串;处理函数无 netfield 关联 | **UNKNOWN(未排除)** |

**裁定:** 归为 **TQOS(平台)**,但"**非**业务"是**推断**,不是确证。

---

## 3. 矛盾账本(保留,不消除)

| ID | 矛盾 | 事实 | 影响 | 状态 |
|---|---|---|---|---|
| CX-01 | 目标宿主 `out.exe` | 工程记录 `E3823FD6…F37B`;本机不存在;实际制品 `3699…b537` 不匹配 | 服务器实现对象未定 | **UNKNOWN/BLOCKED** |
| CX-02 | 加壳 vs 去壳 | OLMod 记录 `out.exe` 为去壳;本机制品为加壳(`.tp3/.tvm0`) | 运行时解壳一致性未知 | **UNKNOWN** |
| CX-03 | `E3823FD6…` 版本归属 | 上游称其为 3.3.3.3 QA 客户端,非 OLfinal 目标 | 若属实,042 镜像与工程目标**版本**关系待定 | **UNKNOWN**(沿用上游说法) |
| CX-04 | OLMod 工作树 | 多个工作树,未提交修改与不同构建哈希 | 实现基线不稳 | **UNKNOWN** |
| CX-05 | 042 措辞 | `0x87A890` 称"helper"、`0x87C110` 称"类型分派器"、`0x85E6F0` 称"非业务" | 影响证据解释 | **CONFIRMED(043 勘误,不改历史)** |
| CX-06 | `image_best.bin` 多副本 | 4 个构建同尺寸不同哈希 | 引用若不绑 SHA 则不可复核 | **CROSS_VALIDATED** |

> CX-01~CX-04 若无法在当前任务解决,继续登记为 `UNKNOWN/BLOCKED`(**不丢弃**)。

---

## 4. 反过度声称声明

1. 本报告**不**主张已恢复客户端完整消息格式或 opcode 表。
2. **不**据函数名/相邻字符串/单个 IAT 引用/结构相似性单独认定业务语义。
3. **不**据服务端(OLD/2697/OLMod)实现反推客户端协议。
4. **不**据 CoD4x/IW4X 架构相似认定协议相同。
5. 041 的 ICMP 结论**仅**适用其接收簇,不外推。
