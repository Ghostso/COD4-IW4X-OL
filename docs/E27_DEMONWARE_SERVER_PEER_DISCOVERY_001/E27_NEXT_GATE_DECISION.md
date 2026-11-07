# E27 下一门禁决策

## 1. 决策

**维持 CONDITIONAL GO**，并把下一步从"继续在 2697 服务端内找 Demonware"**转向"对端复用性验证"**。本轮证明：Demonware 对端**已存在**（C++/Python 两套），只是**不在 2697 服务端包内**，且面向**另一客户端构建**。

## 2. 本轮获得的确定性收益

1. **生态清单闭合**（PROVEN）：12,511 文件 / 1742.0 MB / **4 个 PE** 全量枚举；`CLIENTCHAL`/`BDDATA` **0 命中**（100% 字节覆盖）。
2. **负面结论成立**（PROVEN）：2697 服务端生态**不含** Demonware 控制面；`codol_dedrun.exe` 是 iD-Tech 对局面（与 E-26 互证）。
3. **对端定位成功**（PROVEN）：`ol-mod-olfinal\src\backend\Demonware\`（C++）与 `REF_LOBBY_KIT\codol_crypto.py`（Python）实现了 `CLIENTCHAL`/`BDDATA` 密钥派生与 `0xAB85` 帧。
4. **派生一致性确认**（PROVEN）：两侧 `CLIENTCHAL`→16B、`BDDATA`→72B（切分 `20/20/16/16`）完全一致，与客户端 E-21 字符串对应。
5. **分层架构明确**（INFERRED 强）：Demonware = 大厅/认证控制面（TCP，`0xAB85`）；iD-Tech = 对局面（UDP 17733，3 位 clc）。
6. **适配度冲突定位**（PROVEN）：对端引用的客户端地址（`0x9CE310` 等）在 **2697 恢复镜像中不成立**。

## 3. 停止条件核对（任务书 §8）

| 停止条件 | 状态 |
|---|---|
| "找到疑似独立协议模块 → 只深入验证其协议入口与对应关系" | **部分适用**：对端已找到，但属**其它构建**；需先验证复用性 |
| "找到明确的 Demonware 服务端处理链 → 建立交叉表后停止" | 对端链**已存在**（生态外），交叉表已建（E27-CROSSWALK）；**2697 内**未找到 |
| "所有已枚举模块均无足够证据 → 报告覆盖范围、盲区与最小缺失证据" | **适用**（2697 生态内） |
| "不再扩展 `codol_dedrun.exe` 已确认不承载该握手的经典分派链" | **遵守** ✓ |

## 4. 剩余最小缺失证据

1. **2697 客户端的 Demonware 解码入口与帧魔数**：`0x686210` 为 `mov [ecx],0xDEADBEEF`（写入）；2697 是否用同一魔数、入口在哪，未闭合。
2. **对端的 2697 地址映射**：需把 `ol-mod`/`REF_LOBBY_KIT` 引用的 `1.1.1.13` 地址在 2697 恢复镜像上重新定位。
3. **2697 的 Demonware 服务端**：生态内外均未找到面向 **2.6.9.7** 的该组件。

## 5. 下一步唯一建议

**执行"对端复用性验证"**（同一工作区，无需新样本）：

1. 取 `ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` 的 `deriveSessionKeys` 与 `REF_LOBBY_KIT\codol_crypto.py` 的 `derive_session_keys`，用 `DemonwareTests.cpp` 的 KAT 向量验证实现自洽（`tests\backend\DemonwareTests.cpp:2455-2478`）。
2. 在 **2697 恢复镜像**中，以 `CLIENTCHAL`(VA `0xC5B144`)/`BDDATA`(`0xC5B13C`) 的**交叉引用**为锚，定位 `expandKey`/`hmacSha1`/`sha1` 的调用点，确认 2697 是否使用**同一派生公式**（标签、长度 16/72、切分 20/20/16/16）。
3. 若公式一致 → 记录"2697 与对端同构，可复用"；随后才值得把对端的 2697 地址映射补齐。
4. 若公式不一致 → 记录首个参数/长度/顺序差异，并判定"2697 需独立 Demonware 服务端实现"（架构级阻塞）。

不建议：
- 继续在 `server2697\` 内搜索 Demonware（已 100% 覆盖，0 命中）；
- 直接运行对端实现（本轮为只读静态分析；且其面向另一构建）；
- 把认知完备率当作互通完成率。
