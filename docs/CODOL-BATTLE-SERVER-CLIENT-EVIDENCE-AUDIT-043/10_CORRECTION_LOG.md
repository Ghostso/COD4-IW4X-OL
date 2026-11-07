# 10_CORRECTION_LOG — 042 勘误记录(不改写历史交付物)

本文件**只记录**对 `CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042` 的勘误与证据;
**未修改** 042 任何既有文件(遵守任务约束)。

---

## C-1. `0x87A890` 语义:helper → **长度编码写入器**(重要性:高)

- **042 原文:** "net-buffer sizeinfo helper",按阈值 128/256/65536 选宽度并比较剩余长度。
- **043 实测:**
  - 函数体 `mov byte ptr [ebx], 0xC`(RVA `0x87A92F`)→ **写出 sizeinfo 标签字节 0xC**。
  - 随后按宽度写 `[ebx+1..4]`(大端),再按 `[ebp+0xC]` 元素**逐项写出输出缓冲**(`0x87A9C0..0x87AA27`)。
  - 首个 `ret` 在 `0x87A8EE`(+0x5E);`0x87AA40` 是**同族第二写入器**。
- **证据:** `evidence/dis_87A890_full.txt`,`dis_87A8xx_boundaries.txt`。
- **影响:** 结论**更强**(写入器确证);042 "helper"措辞低估。

## C-2. `0x744B20` 恒真 → 042 的"netfield 判定"分支无效(重要性:中)

- **042 原文:** `call 0xB44B20` 判是否为 netfield。
- **043 实测:** `0xB44B20` 体为 `mov eax,1; ret`(RVA `0x744B20`)→ **恒返回 1**;`0x87A8B7 je` 分支为**死代码**。
- **证据:** `evidence/dis_sizeinfo_helpers.txt`。
- **影响:** 删除"netfield 判定"这一语义;不影响阈值/写入结论。

## C-3. `0x87C110` "typed element 多路分派"表述过度(重要性:中)

- **042 原文:** "按 `[ebx+8]` 元素类型多路 + 逐元素搬运"。
- **043 实测:** 全函数**仅 2 处** `[ebx+8]`(`0x87C767`、`0x87C794`);`cmp eax,1; jle; sub 0x15; je; dec; je` 为**少数取值**,
  非完整类型表。主体是尺寸乘 + 边界比较 + 8 字节元素搬运。
- **证据:** `evidence/dis_deser_boundaries.txt`,`b_final_checks.txt`。
- **影响:** 类型域**未穷举** → 降级为 `UNKNOWN`;实际取值域见 `02 §2.2`。

## C-4. `0x85E6F0` "非业务"结论过度(重要性:高)

- **042 原文:** 判为 TQOS"平台层,**非**游戏业务数据通道"。
- **043 实测:** TQOS 归属**成立**(对象由 `0x85EB50`=`tqos_create_protohandle` 构造,字段 `QOSCSPkg/QOSSSPkg`);
  **但**"非业务"是**推断**——分派器函数体内**无** TQOS 字符串引用;TQOS 是可复用网络序列化框架。
- **证据:** `evidence/c_tqos_and_chain.txt`,`c_tqos_ctor_rel.txt`,`c_caller_attribution.txt`。
- **影响:** 改判为 `CROSS_VALIDATED(TQOS) + UNKNOWN(是否另有业务)`。

## C-5. `0x87C110` 与 `0x87D5A0` 的关系(补充,非错误)

- **042 未明确**。043 实测:两者**互相无调用**,但**共享** `0x87ED70`/`0x87EDB0` → `COMMON_CORE`,非 wrapper。
- **证据:** `evidence/b_final_checks.txt`。

## C-6. 读数核对的一致性(无错误)

- 042 的地址约定 `file_offset = RVA`、`ImageBase=0x400000`、`net-buffer 串 0x99EE98..`、`0x87C110`/`0x87D5A0`
  入口字节均在 043 独立复算下**一致**。
