# memory 里“旧未闭项”的原始清单（自动生成）

> 用途：`tasks.json` 只覆盖已重新推导并建成断言的条目；
> **本文件把 memory 散文中每一处 未闭/缺口/待办/尚未/未定 的原文抓出来**，
> 防止它们只活在散文里被忘掉。每条带 `文件:行号`，可直接回查。
> 转成正式任务时：在 `tasks.json` 增条目，并在此行标注 `[已转 Gx/Oxx]`。

**合计 176 处，涉及 72 个 memory 文件**（生成时快照；重跑 `inv.py` 刷新）。

---

## codol-102-is-messaging2.md  (1 处)

- `codol-102-is-messaging2.md:5` **取代**：115 卷的「102 语义名未定，Leaderboard 最强候选」

## codol-632680-is-booking-timeout-not-startgame.md  (1 处)

- `codol-632680-is-booking-timeout-not-startgame.md:53` ## 真实开局路径：仍未定（但已排除本条）

## codol-65-response-and-room-event-dispatch-138.md  (3 处)

- `codol-65-response-and-room-event-dispatch-138.md:21` u32 ???            → 写 [result+0x2c]   ← 数组基址/元素区长度（语义未定）
- `codol-65-response-and-room-event-dispatch-138.md:104` 1. `[obj+0x2c]` 语义未定（"元素总数"vs"单条字节长"，两者都与读序相容）
- `codol-65-response-and-room-event-dispatch-138.md:105` 2. `0x7FE980` 各 type 的**语义名未定**（只知道跳转目标与处理函数地址）

## codol-as-native-family-131.md  (1 处)

- `codol-as-native-family-131.md:53` - `UserComplaint` 第 6..11 六个 `%d` 的逐字段语义未定

## codol-as-registrar-reverify-134.md  (2 处)

- `codol-as-registrar-reverify-134.md:91` 1. `test al,0x8F; cmp al,0x0A` 语义未定
- `codol-as-registrar-reverify-134.md:111` 8. ★★ **一个假数字会生出一窝假结论**（838 假基数 → "9 个双注册"这个不存在的缺口）

## codol-as-registration-3layer-135.md  (3 处)

- `codol-as-registration-3layer-135.md:119` 1. `0x0A`（掩码 0x8F 后）的确切语义未定（只确定"标志位比较 → bool 实参"）。
- `codol-as-registration-3layer-135.md:120` 2. GFx 转发器各 slot 对应的具体 GFx/C++ 方法名未定（运行时 vtable，无静态立即数）。
- `codol-as-registration-3layer-135.md:122` 4. `0x730690` 局部 Value 第 4 个 dword（=6）语义未定。

## codol-as-registration-chain-133.md  (3 处)

- `codol-as-registration-chain-133.md:32` 剩 1 个未调用：可能死代码，可能 `call eax`（**只扫了 E8，未定案**）。
- `codol-as-registration-chain-133.md:63` 2. `test al,0x8F; cmp al,0x0A` 语义未定（只确定它是 registerFunction 的 bool 参数 = "是否作为函数注册"）
- `codol-as-registration-chain-133.md:72` 4. **同一缺口出现 ≥3 次 ⇒ 检查预设**（"诚实边界"可能是拖延）

## codol-as-static-closure-136.md  (6 处)

- `codol-as-static-closure-136.md:53` - ★ 两种 mangled 形态并存（`@?<n>??Init@` 与 `@?<n>@??Init@`），`OnSortClick` 在 ItemListView 以 25/300 两序号各现一次 ⇒ **成因未定案**（计数不受影响）。
- `codol-as-static-closure-136.md:97` ⇒ 注册器的 `[[edi+8]]->vt[0x14]` 是**对象接口方法槽**（槽名未定）。
- `codol-as-static-closure-136.md:101` 1. `0x0A`/`0x09`/`0x06`/`0x05`/`1` 的**类型名未定**（静态面不可达，已用关键字扫描证"这里没有"）。
- `codol-as-static-closure-136.md:102` 2. GFx 转发器 9 个 slot 的方法名未定（同一原因）。
- `codol-as-static-closure-136.md:103` 3. `?<n>@` / `?<n>??` 两种 mangled 形态成因未定案。
- `codol-as-static-closure-136.md:114` 5. ★ **"未定"要分"没找到"与"这里没有"**——先穷举，把全 0 写进结论。

## codol-as-vtable-829-objects-132.md  (2 处)

- `codol-as-vtable-829-objects-132.md:29` ## ★★★ 页名缺口闭合：注册关系写在 RTTI 名里
- `codol-as-vtable-829-objects-132.md:62` - 未见 `UiCppMainMenu` ⇒ 主菜单走另一条（未闭合的批量注册器 `0x64F620`/`0x644D60`）

## codol-badge-slot-and-unlock-items.md  (1 处)

- `codol-badge-slot-and-unlock-items.md:10` **徽章=背包同一机制**:`WL_GetMarketItemIdForBadgeIndex`(`0xE6C370`,impl`0x7D7560`)/`WL_GetIsBadgeSlotUnlocked`(`0xE6C3A0`,impl`0x7D74D0`),命名与背包族对称。徽章表@`0x8269B18`步进12`{A;exists;B}`,**`item=rol32(B^A^[0xE4DD90],8)`**,**表27项(第27项[…

## codol-battle-dtls-ack-tail-table-key-277.md  (2 处)

- `codol-battle-dtls-ack-tail-table-key-277.md:222` ## 八、仍未闭合（明确列清单）
- `codol-battle-dtls-ack-tail-table-key-277.md:295` ## 八之三、仍未闭合（更新）

## codol-battle-dtls-coverage-and-ct6-279.md  (14 处)

- `codol-battle-dtls-coverage-and-ct6-279.md:128` ## 七、防重放窗口初值：查证结果与仍未闭合的部分
- `codol-battle-dtls-coverage-and-ct6-279.md:141` - **`0x6F381B` 不在 `0xBBF040` 里** —— 说明还有一处"同布局对象"的初始化代码（哪个类/哪个对象未定）。
- `codol-battle-dtls-coverage-and-ct6-279.md:178` **⇒ 基准初值 -1 是"尚未收到任何包"的哨兵。**
- `codol-battle-dtls-coverage-and-ct6-279.md:184` **仍未闭合（保留）：**
- `codol-battle-dtls-coverage-and-ct6-279.md:185` 1. `0x6F37E0` 所属函数是哪个、初始化的是哪个类 —— 未定（与 `0xBBEFB0` 是不同的代码路径，需查清是否另一份同布局实现）。
- `codol-battle-dtls-coverage-and-ct6-279.md:518` | 0 | **3** | 尚未开始握手 |
- `codol-battle-dtls-coverage-and-ct6-279.md:973` **⇒ 协议层面未闭合的黑箱：0 个。**
- `codol-battle-dtls-coverage-and-ct6-279.md:1080` **⇒ 未下结论，列为待办：需要用一条真实 CT6 帧（含 MAC）验证。**
- `codol-battle-dtls-coverage-and-ct6-279.md:1218` ### 疑点（★ 未定，不可据此下结论）
- `codol-battle-dtls-coverage-and-ct6-279.md:1254` | 4 | HMAC 密钥可能是全局而非会话密钥 | **低（未定）** | §二十七疑点；参数映射不可靠 |
- `codol-battle-dtls-coverage-and-ct6-279.md:1353` 未逐条语义分析；`引擎+0x60` 那个容器是什么仍未定。
- `codol-battle-dtls-coverage-and-ct6-279.md:1574` - **尚未实机验证。**
- `codol-battle-dtls-coverage-and-ct6-279.md:2755` ## 五十四、⚠ 仍未闭合：每帧状态路径 `0x7F4F10 → 0xBB2520`（2026-11-06）
- `codol-battle-dtls-coverage-and-ct6-279.md:2787` ### 未闭合清单（下一轮的函数级任务）

## codol-battle-dtls-fullmap-and-codonlin-278.md  (1 处)

- `codol-battle-dtls-fullmap-and-codonlin-278.md:235` ## 七、待办（需用户批准才能落地 —— 属"修改文件"级副作用）

## codol-battle-security-key-fix-272.md  (1 处)

- `codol-battle-security-key-fix-272.md:65` - 战斗通道与大厅通道是否共用密钥材料 —— 未定。

## codol-battle-server-world-binding.md  (3 处)

- `codol-battle-server-world-binding.md:35` **★ 教训:这类"代码写好了但从未接线"的缺口,比"缺数据"更常见也更便宜。**
- `codol-battle-server-world-binding.md:38` **★ 教训2(157 卷补):记忆是快照不是实况。** 修完必须回头改记忆，否则「未闭合」会继续挂一个月。
- `codol-battle-server-world-binding.md:39` **★ 教训3(157 卷补):分类错误比结论错误更隐蔽。** 把自己项目的函数列进「客户端逆向未闭合」，导致长期误挂。

## codol-blob-0x13-typeA-inner.md  (2 处)

- `codol-blob-0x13-typeA-inner.md:13` - ★ **诚实边界**：`×4`/`<<10` **不是位长**（位长应为 ×8=`<<3`）。**长度字段成立 112/112 是硬事实；但标度单位（为什么 `<<10`）未定**。这条足以证明它是"长度"而非"元素数"。
- `codol-blob-0x13-typeA-inner.md:15` - **`b8-b9`(u16) 二段字段**：值域 {0x80,0xa8,0xd0,0xb8,0xe0,0xa0,0x78}，与长度不完全线性，语义未定。

## codol-byte-role-census-00-70.md  (6 处)

- `codol-byte-role-census-00-70.md:92` **★ 未定：blob 是客户端上报还是服务端下发（决定能否拦截改写 vs 构造）。**
- `codol-byte-role-census-00-70.md:220` **★ `31902622`(`71/4` 机器指纹，160/160 恒定，**穷举 FNV/djb2/sdbm/Java + md5/sha1/sha256 × MAC 4 写法 = 68 组合全不匹配 ⇒ 未定，非 MAC 哈希**）。**
- `codol-byte-role-census-00-70.md:222` **★ `932`(0x3A4，352 次，`4/13`×264+`4/4`×88 主值，**语义未定**；`4/13` 常态 932，仅 `ONCE_20261029_143736` 里变为 100/108/113/118/123/135/148)。**
- `codol-byte-role-census-00-70.md:253` **★ 未定：`102/1,2,5,7`（`102/7`=`08 50|[03 1|0a i]×50|00`=50元素数组，语义未定，疑内部/资源服务，不在任何审计映射里）。**
- `codol-byte-role-census-00-70.md:261` **★ 从客户端 EXE 扒出完整 Demonware 服务名：Matchmaking/Marketplace/Leaderboard/Presence/Messaging/Task/Stats/Reward/Friends/Notification/Session/Lobby/Party/Room/Clan。`Leaderboard`(19大写+16小写) 是 102 最强候选但**无服务号映射证据 ⇒ 语义名未定**。★ 语料未触发…
- `codol-byte-role-census-00-70.md:262` **★★ 阶段性终点：请求侧（客户端→服务端）已无字节黑箱（6848 条/55 task/12 标签全结构闭合，51/55 语义定名，102/* 结构全解但语义名未定且空应答安全）。剩余黑箱只在①应答侧（corpus 无应答样本，需真实抓包=授权）②102 语义名+未触发服务（需反汇编读侧或跑客户端=授权）。**

## codol-dwroom-47types-and-codenames-138e.md  (1 处)

- `codol-dwroom-47types-and-codenames-138e.md:145` 3. `0x12` 的 12~13 个 16 位槽、`0x1D` 的 15 个 8 位槽，**语义未定**（无字符串/名表落点）。

## codol-dwroom-msgtype-table.md  (2 处)

- `codol-dwroom-msgtype-table.md:86` **34/36 个成员字段的业务语义未定（序列化不带名字）。`0x02` 语义未知（断言已编空）。**
- `codol-dwroom-msgtype-table.md:87` **P2PInfo 的 67 字节结构未定。N 的实际取值范围未实测。**

## codol-dwroom-writers-and-srpc-gate.md  (1 处)

- `codol-dwroom-writers-and-srpc-gate.md:28` ③★★★★ **ChangeTeam 专用 `0x6281D0`** = 4 字段 `u32[+8] / u8[+0x10] / u32[+0x0C] / u64`（布局确定、语义未定）。

## codol-dwroommatchuber-never-created.md  (1 处)

- `codol-dwroommatchuber-never-created.md:3` description: "决定性发现：剧情卡「战斗开始」的真正缺口是 dwRoomMatchUber 对象从未被创建（[0x082E1518]=0），而不是闸门B/dvar3291。0x63C5E0 是这个类的虚函数 +0x68"

## codol-frameupdate-and-outbound-vtables-150.md  (1 处)

- `codol-frameupdate-and-outbound-vtables-150.md:135` ## 五、未闭合

## codol-handler-4f4-wildptr-145.md  (1 处)

- `codol-handler-4f4-wildptr-145.md:119` 1. **`[0x84ABB14]` 这个野指针是谁写的、何时释放的未定**。

## codol-hardcoded-security-key-and-gate.md  (2 处)

- `codol-hardcoded-security-key-and-gate.md:124` ## 未闭合
- `codol-hardcoded-security-key-and-gate.md:127` 4=?），推进它的应答路径未定。这是 `N+0x40` 插入的最终闸门。

## codol-image-plaintext-config-155.md  (3 处)

- `codol-image-plaintext-config-155.md:79` ⇒ 154 未闭合项 4 已解：`0x7FA560` 读的 dvar 默认值**内嵌 exe 明文**，非外部 config。
- `codol-image-plaintext-config-155.md:128` ## 九、未闭合
- `codol-image-plaintext-config-155.md:142` 6. **★ 前卷的「不查」会连锁压缩后续卷范围**；每卷弃权须写成显式待办并在下卷回检。

## codol-lobby-battle-handoff-138.md  (1 处)

- `codol-lobby-battle-handoff-138.md:102` 2. `[0x76446B0]` 的写入点与语义**未定位**（只知道要求 <3）

## codol-lobby-battle-handoff-defects-162.md  (1 处)

- `codol-lobby-battle-handoff-defects-162.md:64` | # | 缺口 |

## codol-lobby-ifs-and-aes-chain.md  (2 处)

- `codol-lobby-ifs-and-aes-chain.md:54` **唯一缺口：那 256 字节 RSA 密文的来源未定。**
- `codol-lobby-ifs-and-aes-chain.md:66` 1. RSA 的 256 字节密文来源（链唯一缺口）

## codol-lobby-state-machine-and-bitstream.md  (1 处)

- `codol-lobby-state-machine-and-bitstream.md:97` ## `6/5` 应答缺口

## codol-marketplace-empty-page-is-root-cause.md  (2 处)

- `codol-marketplace-empty-page-is-root-cause.md:66` - **`txn+0x24` = 本次返回条数**（响应侧，`0x4A801A add [0x82C4A94],eax`）；ctor 未定位。
- `codol-marketplace-empty-page-is-root-cause.md:67` - ★★ **`reply+0x05` 在上述 ctor 里完全没被写** ⇒ 属于另一个对象，其 ctor 仍未定位。**这是下一项的首要工作。**

## codol-marketplace-sku-19-field-fix.md  (1 处)

- `codol-marketplace-sku-19-field-fix.md:68` - UI 是否渲染取决于 `reply+5` 的写入逻辑，**231 卷未定位其写点**。

## codol-max-loadouts-5-and-purchase-frame.md  (1 处)

- `codol-max-loadouts-5-and-purchase-frame.md:10` **`WL_GetMaxNumLoadouts`(impl`0x7D73E0`)返回常量5**⇒背包0..4,**4/5号=仅有的两个扩展槽**。**购买帧58B、字段序列逐字节同构、只有一个SKU字段**(`93/131`×2+`80/154`×1)⇒**否掉248「组合包带多SKU」的猜测**;`parse_purchase` 取 `vals[1]/vals[3]` 本来就对。**组合包走资产不走商品**:`WL_EquipLoad…

## codol-mmrsv-securitykey-full-chain.md  (2 处)

- `codol-mmrsv-securitykey-full-chain.md:246` ## 未闭合
- `codol-mmrsv-securitykey-full-chain.md:251` 两条 16 字节路径**互不相同**，尚未证明谁先谁后或是否等价。

## codol-msgtype-minus-one-index-140.md  (1 处)

- `codol-msgtype-minus-one-index-140.md:58` ## 四、★ 主要未闭合：4 字节服务名的真实值

## codol-n40-insert-chain-and-21-1-key.md  (2 处)

- `codol-n40-insert-chain-and-21-1-key.md:135` **未定**：`[0xCA8008]` 指向的函数是随机生成还是别的来源（隐藏 IAT，静态读不出）；
- `codol-n40-insert-chain-and-21-1-key.md:142` 任务表已扩到 **61 条（全过 / 基线零差异）**，未闭 6 条：O1/O2/O3/O4/O9/O14。

## codol-open-items-closure-round2.md  (3 处)

- `codol-open-items-closure-round2.md:3` description: 第二轮收口——O1..O18 未闭清单的逐条结论（表构造器 0xB7FC20、21/3、0x7F5060、注册表 0x76F190、门 2 真实语义）
- `codol-open-items-closure-round2.md:110` ## 仍未闭
- `codol-open-items-closure-round2.md:115` - `0xB79360` 里 `[srpc+4]` 的 `+0x44` 所指向的**传输对象类**未定。

## codol-outbound-paths-149.md  (1 处)

- `codol-outbound-paths-149.md:98` ## 八、未闭合：房间动作的「入队 → 出网」

## codol-p2pinfo-and-peer-slot.md  (2 处)

- `codol-p2pinfo-and-peer-slot.md:84` 67 字节 blob 内部每项位布局**未定**（`0xb75630`/`0xb78350` 形参对应没钉死，不硬算）。
- `codol-p2pinfo-and-peer-slot.md:85` 槽字段语义（除 ID 槽）未定。P2PInfo `+0x08`/`+0x58`/`+0x60` 语义未定。

## codol-pe-layout-and-false-findings.md  (1 处)

- `codol-pe-layout-and-false-findings.md:61` - **★⑥ `netcalls_any.py` 对 `Base.dll` 结构性不可用。** 它只走 `pe.dd[1]`（PE 头 Import 目录）= 那个**幌子**表。实测输出「dir1 导入槽合计 3 个 / 命中 0 处」——**这个 0 是工具覆盖缺口，不是二进制事实**。Base.dll 必须用 `importmap.py` / `netcallers.py`。（该 0 仍承载一条真事实：**dir1 三槽零引用**…

## codol-playlist-gbk-gfx-symbols-157.md  (3 处)

- `codol-playlist-gbk-gfx-symbols-157.md:99` ## 六、仍未闭合（诚实）
- `codol-playlist-gbk-gfx-symbols-157.md:112` 5. **★ 引用旧记忆的「未闭合」前必须回源码确认**（记忆是快照非实况）；修完要回头改记忆。
- `codol-playlist-gbk-gfx-symbols-157.md:113` 6. **★ 「需单独处理」若只需一行代码，当场做掉，不立待办**（GBK 拖了一卷）。

## codol-re-verify-harness.md  (15 处)

- `codol-re-verify-harness.md:27` python -I verify.py graph      # 打印依赖图；强制"已闭任务不得依赖未闭"且无环
- `codol-re-verify-harness.md:47` 最初建校验器时我把未闭项从 **12 条收窄成 3 条** —— 没进 `tasks.json` 的就只活在散文里，
- `codol-re-verify-harness.md:50` 1. **未闭项只住在 `tasks.json`**，每条带 `status:"open"` 与 `blocked_on`（缺什么证据）。
- `codol-re-verify-harness.md:51` 2. `check`/`baseline` **每次都打印未闭清单**（含 `blocked_on`）。
- `codol-re-verify-harness.md:53` 新增的标 `⚠ 本次新增未闭（必须确认不是把旧项丢了）`。
- `codol-re-verify-harness.md:54` 4. `graph` 强制：**已闭任务不得依赖未闭任务**、不得成环。
- `codol-re-verify-harness.md:56` ## 当前覆盖（51 条：39 闭 / 12 未闭）
- `codol-re-verify-harness.md:62` **未闭 12 条（全量，不再收窄）**：
- `codol-re-verify-harness.md:64` | ID | 内容 | 缺口 |
- `codol-re-verify-harness.md:69` | O4 | `0xB79360` 传输对象类与 `vt[+4]` 本体 | `this=[srpc+4]` 已定；`[this+0x44]` 的类未定 |
- `codol-re-verify-harness.md:70` | O5 | `21/1` 应答目标 `singleton+0x258` 期待形状 | `0xB94940` 类已知，schema 未定 |
- `codol-re-verify-harness.md:72` | O7 | 谁把 RPC poll 从 1 推到 4 | 完成派发路径未定位 |
- `codol-re-verify-harness.md:73` | O8 | `[+0x105FD]`/`[+0x105FE]` 语义 | 来源已证（记录 `"1011"`/`"3265"` 的值），含义未定 |
- `codol-re-verify-harness.md:74` | O9 | `0x770940` 参数语义 | 注册器已识别（`0x76F190` 查名），arg2/arg4 未定 |
- `codol-re-verify-harness.md:87` 本机制**只做验证，不产生新结论**。任何新发现都必须以"新增一条任务 + 断言 +（若未闭）

## codol-room-action-outbound-153.md  (2 处)

- `codol-room-action-outbound-153.md:11` **153：房间动作入队→出网 全链闭合（关闭 148–152 遗留缺口的唯一一项）**
- `codol-room-action-outbound-153.md:86` ## 九、未闭合

## codol-room-audit-159.md  (5 处)

- `codol-room-audit-159.md:11` **159：房间专线剩余黑箱审计（六项当场闭，一项方向性缺口）**
- `codol-room-audit-159.md:91` ## 六、唯一仍开：4 字节服务名（方向性缺口）
- `codol-room-audit-159.md:113` - 框架层：`.ff` 的 **256 字节 RSA 密文来源**未定（唯一缺口）；`ui_mp.ff` 内部未解。
- `codol-room-audit-159.md:121` 5. **★ 「未闭合清单」项比新方向便宜**（已查过=地形熟，只差最后一刀；本卷 6 项都不足一小时）。
- `codol-room-audit-159.md:122` 6. **★ 方向性缺口单独成类**：C→S 齐 ≠ 协议齐。

## codol-room-button-path-148.md  (1 处)

- `codol-room-button-path-148.md:131` ## 七、未闭合

## codol-room-class-zero-170.md  (1 处)

- `codol-room-class-zero-170.md:15` 按类名扫（`dwRoom|dwParty|RoomMessage|EventHandler@dwRoom|InRoom|MyRoom` × 未闭合关键词），全库 185 卷**只剩 1 条真开项**：

## codol-room-countdown-next-steps.md  (3 处)

- `codol-room-countdown-next-steps.md:51` ## 仍未闭合：自定义房间拿不到"谁准备了"
- `codol-room-countdown-next-steps.md:63` 房间模式下这两个 token 不存在 ⇒ 日志一直打 `map=? gametype=?`）⇒ **选图尚未被服务端采纳**。
- `codol-room-countdown-next-steps.md:119` 第二推可能赶不上，故余量给足**。**这一版尚未实机验证。**

## codol-room-create-to-battle-five-gates-164.md  (1 处)

- `codol-room-create-to-battle-five-gates-164.md:109` | ⑤ security_key | **部分解**（客户端算法已明，战斗服要改成同款；会话16B用途未定） |

## codol-room-delivery-chain-138b.md  (5 处)

- `codol-room-delivery-chain-138b.md:138` 1. `0x7E7C90` 静态零引用 ⇒ **它的上层（从哪个 srpc task 调来）未定位**（三路 agent 正在挖）
- `codol-room-delivery-chain-138b.md:139` 2. 两个 blob 各自装什么（blob#1 vs blob#2 的分工）未定
- `codol-room-delivery-chain-138b.md:140` 3. `0x6374E0`/`0x637520`/`0x633D50` 三回调职责未定（agent 正在挖）
- `codol-room-delivery-chain-138b.md:141` 4. 阶段1 的表 `0xE56FFE0`（步长 0x50）身份未定
- `codol-room-delivery-chain-138b.md:142` 5. `[0x76446B0]`（开局闸门②，需 <3）写入点仍未定位

## codol-room-five-channels-154.md  (1 处)

- `codol-room-five-channels-154.md:96` ## 八、未闭合

## codol-room-open-7-after-fullscan-167.md  (3 处)

- `codol-room-open-7-after-fullscan-167.md:97` | S4 | 第二表 1002..1010 语义 | handler 地址全列，业务名未定 |
- `codol-room-open-7-after-fullscan-167.md:100` | T1 | `0x12` 12~13个16位槽 / `0x1D` 15个8位槽 | 槽数已知，语义未定 |
- `codol-room-open-7-after-fullscan-167.md:117` 3. **★ 底层卷（writeBits/位流）决定上层全部消息的解读** —— 84 卷一条"n 位还是 5 位未定"，悬着影响所有房间消息。

## codol-room-open-items-ledger-165.md  (9 处)

- `codol-room-open-items-ledger-165.md:3` description: "165：房间线未闭合项总账。扫遍所有房间卷的『未解/未闭合』小节，发现 10 项早期遗留从未回查：①11/4 内层分组表 4/6/8 组字段语义(40)；②02 02 形态变化字节13/14；③40×16(0204)/01×16(0208)位数组含义；④6/5 的 maxResults=20 是否硬编码；⑤房间控制台命令参数格式(43)；⑥room.changemap 对应报文；⑦22个数字dvar实际名字(…
- `codol-room-open-items-ledger-165.md:11` **165：房间线未闭合项总账（10 项老账）**
- `codol-room-open-items-ledger-165.md:13` ## 一、10 项未闭合（全开）
- `codol-room-open-items-ledger-165.md:26` | 10 | `0x13` 长度字段 `<<10` **标度物理含义** | 119 §诚实边界 | ❌ 开（112/112 精确，但为何 `<<10` 而非 `<<3` 未定） |
- `codol-room-open-items-ledger-165.md:45` **153–164 各卷的「未闭合」小节里，一次都没提这 10 项。**
- `codol-room-open-items-ledger-165.md:61` 本总账只扫「文件名含房间」+ 关键词「未闭合/未解/未定/待验证/未知/待查/尚未」。
- `codol-room-open-items-ledger-165.md:67` 建 `_byte_papers\OPEN_ITEMS.md`：每卷写完**追加自己的未闭合项**，闭掉时标记 `✅`。
- `codol-room-open-items-ledger-165.md:68` 这样「还有多少未闭合」= 一次 `grep ❌`。
- `codol-room-open-items-ledger-165.md:72` 1. **★★ 未闭合项会沉淀在早期卷末尾，而不是浮在 INDEX 里** —— 盘点要按卷扫，不能按印象列。

## codol-room-push-6field-rootcause.md  (2 处)

- `codol-room-push-6field-rootcause.md:72` ## 2026-11-03 字段对调后（部分修好，**尚未彻底解决**）
- `codol-room-push-6field-rootcause.md:146` ## 仍未闭合：处理器 24 内部 + StartGame 时机

## codol-room-static-blackbox-zero-166.md  (3 处)

- `codol-room-static-blackbox-zero-166.md:3` description: "166：房间线全量收口，13项逐条定案，静态未闭合=0。①[0x82E1400]=dwPartyImp(RTTI: 0xDC73DC/0xDC7474=.?AVdwPartyImp@@, 内含MyRoomImp@dwPartyImp+MyRoomEventHandler@dwPartyImp, 继承dwRoomImp) ⇒ 房间子系统是「房间+组队(内含房间)」两层；②0xE36E4D8=共享0x730B状态…
- `codol-room-static-blackbox-zero-166.md:11` **166：房间线全量收口（静态未闭合 = 0）**
- `codol-room-static-blackbox-zero-166.md:86` | ❌ **静态未闭合** | **0** |

## codol-room-subsystem-and-https-client-152.md  (1 处)

- `codol-room-subsystem-and-https-client-152.md:63` ## 六、未闭合

## codol-room-zero-open-169.md  (4 处)

- `codol-room-zero-open-169.md:3` description: "169：房间线静态未闭合=0（28项）。★6/5闭合：0x625520=dwRoomMessageManifold::serialize 逐指令解出位流=[3位type&7][8位type][8位0x00][32位count]头+每条[1位存在][1位值]，3+8+8+32=51位=7字节与67卷观察到的「7字节头」吻合。★67卷「8位是字段类型码」错——0xB77B10 正常路径下 cmp byte[ecx…
- `codol-room-zero-open-169.md:11` **169：房间线静态未闭合 = 0（28 项），`6/5` 闭合**
- `codol-room-zero-open-169.md:21` 2. 每个未闭合项必须是**可独立核验的任务**（地址/字节区间/调用边），不是"主题"。
- `codol-room-zero-open-169.md:95` | **静态未闭合** | **0** |

## codol-round3-full-sweep.md  (3 处)

- `codol-round3-full-sweep.md:3` description: "第三轮\"一轮打全 12 条未闭项\"结果——O5 闭合（21/1 应答形状本就正确）、O1 性质改变（S 是 UI 侧模型非报文字段）"
- `codol-round3-full-sweep.md:11` # 第三轮：一轮打全 12 条未闭项
- `codol-round3-full-sweep.md:62` `[taskObj+0x28]` 的真实类仍未知 ⇒ O7 缩小未闭。

## codol-section3-whitelist-playlist-156.md  (2 处)

- `codol-section3-whitelist-playlist-156.md:11` **156：未闭合项全清（段2 普查 / Whitelist / playlist / 0xE69D30）**
- `codol-section3-whitelist-playlist-156.md:110` ## 七、未闭合（诚实交接）

## codol-security-key-is-ecdh-derived-163.md  (1 处)

- `codol-security-key-is-ecdh-derived-163.md:90` ## 四、未定（有明确下一步）

## codol-srpc-registry-141.md  (1 处)

- `codol-srpc-registry-141.md:11` **★★★★★ 141：服务注册链追到底（补 140 的「4 字符服务名」缺口，并推翻 140 §3.4 的原因判断）**

## codol-srpc-session-chain-6-14-never-sent.md  (3 处)

- `codol-srpc-session-chain-6-14-never-sent.md:136` 任务表 **68 条全过 / 基线零差异**；未闭 2 条：O2 / O14。
- `codol-srpc-session-chain-6-14-never-sent.md:158` - **O2 新增实机证据（仍未闭）**：实机 `service=71` 用到 task **{2,3,4,7,10,13,15,18}**，
- `codol-srpc-session-chain-6-14-never-sent.md:189` **最终状态：任务 68 条全过 / 基线零差异；未闭只剩 O14**（缺口②需用户批准基线迁移）。

## codol-startgame-chain-and-mmI-arrays.md  (1 处)

- `codol-startgame-chain-and-mmI-arrays.md:37` ★ 仍需确认：`[ebp+8]`/`[ebp+0xC]` 是否真来自推送报文（vs 本地 session）。

## codol-startup-context-api-surface.md  (1 处)

- `codol-startup-context-api-surface.md:24` 函数头 `0x0e8331..0x0e836d` 是**混淆的自校验前导**：`mov eax,[0x10a07c8c]=0x88bbbb37; add eax,0x87c3fdfc; mov ecx,0x107fb933; xor eax,ecx` —— 结果恰为 **0**（ZF=1，`jne` 不跳），命中时改走 `[ecx]` 链表 +0x21c 分支。语义未定，标 MEDIUM。

## codol-state-machine-blocked-by-dwroomimp-gates.md  (1 处)

- `codol-state-machine-blocked-by-dwroomimp-gates.md:91` 2. **再解决计时器 +0x138**：即便过了闸门 B，状态 1 仍需这个计时器启动。

## codol-static-full-clear-137.md  (5 处)

- `codol-static-full-clear-137.md:66` - 序号在字符串 VA 上**倒挂**；"为何在 10→11 换写法"**未定案**。
- `codol-static-full-clear-137.md:91` - 未闭合：V 语义、V≠02 的 K 式、M 语义、尾文法、`F1=K<<10` 的三种候选不可区分
- `codol-static-full-clear-137.md:99` 未定：记录条数、125 卷"1160 段"口径、ID 族语义、`[0,4)`/`[15000,15002)` 含义。
- `codol-static-full-clear-137.md:125` ### R3 `932` = svc4 请求字段 #0（角色闭合 / 语义名未定）
- `codol-static-full-clear-137.md:136` ①修正表未逐行核对全部 829 行；②`10→11` 换写法的原因未定案；③`0x4F2D70` 签名与两表上层语义归属为推断；④`0x15` 语义未验、消息号业务含义未定名；⑤V 语义/K 式/M 语义/尾文法/`F1=K<<10` 三候选不可区分；⑥8/3 记录条数只估、ID 族名未定；⑦`num37→id123` 为推断、服务端解释未知；⑧R1b 字段名不可得（已穷举证"这里没有"）；⑨`+0x14` 的"计数"是用法反推；⑩93…

## codol-svc-task-authoritative-table.md  (3 处)

- `codol-svc-task-authoritative-table.md:89` ## 4. 服务端缺口（可执行）
- `codol-svc-task-authoritative-table.md:129` ## 未闭合
- `codol-svc-task-authoritative-table.md:131` - `0x47/4` 的 16 字节是客户端上送还是下行（已证上行源 = `0xDB6B68`；下行去向未定）。

## codol-tconnd-protocalhandler.md  (1 处)

- `codol-tconnd-protocalhandler.md:54` ★ **两条限制**：（i）裸项判据**只判 NUL 分隔形态，不判 dir1/dir13/串区归属**；**（ii）`select` 这 8 个裸项自身的归属与 def-use 仍未定**（`peprobe.py imps/refs` 未跑）。

## codol-telemetry-envelope-and-macro-engine.md  (1 处)

- `codol-telemetry-envelope-and-macro-engine.md:23` - **未闭合**：`ClientLoadout`(5 vs 18) / `LoadoutChangeEvent`(5 vs 17) 完整模板（差的是配装明细，续接片段 `0x9B7B88` 未精确对上）。

## codol-telemetry-four-entries-65-sites.md  (3 处)

- `codol-telemetry-four-entries-65-sites.md:24` ## ★★ ClientLoadout / LoadoutChangeEvent = 运行时循环追加（127 卷"未闭合"的真相）
- `codol-telemetry-four-entries-65-sites.md:45` ## 旁证 / 未定
- `codol-telemetry-four-entries-65-sites.md:50` - ⚠️ A 入口 `[esi+0x14]=3` 语义未定（候选"来源=游戏内"）。

## codol-telemetry-template-table.md  (2 处)

- `codol-telemetry-template-table.md:24` **宏**：`${CODOID(%llu)}` `${ZONEID(...)}` `${TIMESTAMP}` `${TIMESTAMP_OFFSET(-N)}` ⇒ 客户端有**遥测宏替换引擎**（实现地址未定位）。
- `codol-telemetry-template-table.md:26` **诚实缺口**：`UIPage`(`0x9C7090`) / `UIClick`(`0x9C7088`) 只有裸名字串、**无 `|%s|…` 格式串**，且紧邻 `UIKeySetting`/`UIInitialGameMode`（这两条有模板）⇒ **运行时拼格式或走另一张表，未定位**；故 124 卷 `UIPage` 字段序列仍是"样本观察"非"客户端定义"。

## codol-typeid-always-zero-142.md  (1 处)

- `codol-typeid-always-zero-142.md:3` description: "142：srpc+4 类型号分配器全镜像唯一写点 0xB82179（置 0），此后无自增 ⇒ 类型号恒为 0（穷举证明）；首次取得 43 个 dwRoomMessage* RTTI 全名，与 138 表对账 36/38 印证并发现 6 个未定位类；关键澄清两个「类型号」同名不同义"

## codol-uipage-pageid-and-ui-dispatcher.md  (1 处)

- `codol-uipage-pageid-and-ui-dispatcher.md:60` 真身份：大厅作用域 **5 参动作记录器** `f(flag, v1, v2, str, str)`，flag 观测值 `{1,4,0x0E,0x10,0x12,0x13,0x17}` —— **稀疏、语义未定，别叫"类别枚举"**。落地目标（本地记录 vs 上报包）未证。

## codol-winpcap-and-onlinecheck.md  (2 处)

- `codol-winpcap-and-onlinecheck.md:44` 但**只有类名字符串，尚未做 def-use**。不要当成已确认。
- `codol-winpcap-and-onlinecheck.md:56` ⇒ 上述是**动态装载名单字面量**。**「游戏在抓包」尚未成立**，需 def-use（指针/`LoadLibrary` 调用点）。

