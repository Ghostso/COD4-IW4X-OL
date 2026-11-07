# -*- coding: utf-8 -*-
import csv
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
def A(s): return s
C = []
def add(*r): C.append(r)

# ---- A. 传输层与消息边界 ----
add("C-001","传输层","CODOL 游戏通道使用 UDP（非 TCP/TLS）承载 netchan 消息",
 "SRC-OLD: codol_wire.h + codol_netchan.c（源码级）；codol_network.c:304 CODOL_NetworkReceive 优先于 SV_PacketEvent",
 "2697 服务端：11 loopback 守卫包装 WS2_32；C-2697 有独立 recv/recvfrom/send/sendto 调用点（E17/E18 已归属）",
 "C-2697 9 个收包原语，8/9 已归属（错误日志/HTTP更新/ICMP/Demonware/libcurl），1/9(0x788133)未闭合",
 "2697 二进制与 OLD 同族 WS2_32 导入",
 "CoD4x sys_net.c / netchan.c（同族 UDP）",
 "一致（服务端与客户端均为 UDP 栈）","PROVEN","I4（互通前提）",
 "无需新增；仅需注意 libcurl/TLS 属更新模块，不构成游戏通道反例")
add("C-002","传输层","CODOL 战斗握手/记录层为自研（cookie+ECDH P-224 + DATA 记录），不等同标准 DTLS",
 "SRC-OLD: codol_handshake.c / codol_ecdh.c / codol_crypto.c（源码）；atlas 04 §5",
 "C-2697 内联 OpenSSL 0.9.8p 字符串（E14 §3.2）；CONFLICT-03 已把'使用 DTLS'降级",
 "客户端含 P-224/OpenSSL 字符串，但无证据表明标准 DTLS 记录层",
 "2697 同族握手常量",
 "CoD4x/IW4x 均无 cookie+ECDH → 属 CODOL 自研",
 "一致（自研，非标准 DTLS）","PROVEN","I4",
 "对 C-2697 抓包以固定 189 vs 219 长度（见 C-006）")
add("C-003","传输层","CODOL netchan 分片参数：分片体 1162B、最多 128 片、序列掩码 0x1fffffff、FRAGMENT_BIT 0x80000000",
 "SRC-OLD: codol_wire.h（宏，活体读取 V-05）",
 "2697 服务端指令级常量：0x489(=1161)、0x24500(=1162×128)、0x1fffffff、0x70cc729=ceil(2^37/1162)（R-17）",
 "客户端**未**发现同族分片常量（E14 §4）",
 "2697 _CODOL_NetchanTransmit RVA 0x999B6 cmp 0x489；_NetchanTransmitNextFragment 0x998D8",
 "CoD4x netchan：PACKET_HEADER 10、MAX_MSGLEN 0x20000（**不同**）",
 "一致（OLD 源码 ↔ 2697 指令，常量级双证）","PROVEN","I4",
 "核对 2697 分片上限 128（0x24500/1162）是否被客户端接受——需抓包或客户端常量定位")
add("C-004","传输层","body 经对称 XOR（CODOL_Xor）后再分片/发送",
 "SRC-OLD: codol_wire.c CODOL_Xor（源码）",
 "2697 同族（未独立反汇编确认）",
 "无客户端直接证据",
 "2697 存在同族调用（未独立验证）",
 "CoD4x 无此 XOR（KEY 不同实现）",
 "部分一致（源码级，2697 未逐指令复核）","INFERRED","I3",
 "反汇编 2697 CODOL_Xor 调用点，确认密钥来源（BQ-12）")
add("C-005","传输层","客户端最大消息长度/缓冲区边界未由本地证据确定",
 "-","-","C-2697 Msg 核心 0x1AC1D0（按调用者给长复制），无独立上限常量证据","2697 上限 0x24500（服务端侧）",
 "CoD4x MAX_MSGLEN 0x20000（不适用）","无独立佐证（客户端）","BLOCKED","I3",
 "在 C-2697 收包路径定位长度上限校验")
add("C-006","传输层/握手","COOKIE_ECHO 长度：源码 189B vs C#/PVE 契约 219B（版本/阶段相关，未裁决）",
 "SRC-OLD: codol_handshake.c:47 n==189",
 "DEV-BOOKING\\PVE-BATTLE-CONTRACT-LINEAGE-021 §8 与 C# CodolProtocol 219B",
 "无（需抓包）","2697 握手同族，未取长",
 "无","冲突（SOURCE-CONFLICT）","BLOCKED","I3",
 "对 C-2697 抓包确定 COOKIE_ECHO 长度")

# ---- B. Reliable Command ----
add("C-007","Reliable Command","2697 reliable 有两形态：ret<0→Com_Error；ret==0→0x01+long+NUL串；ret>0→0x02+long+short(len)+data",
 "2697 服务端 _SV_WriteReliableCommand RVA 0x8612E（指令级，写点 0x8616B/0x8617D/0x86189/0x8619F 与 0x861D0/0x861E2/0x861EE）",
 "2697_SA 04 §2.3；12_CODEC_MVP 05 §1",
 "C-2697 0xA2E50 读 long+short+payload，上限 0x3FC（形状匹配）",
 "同左（服务端为唯一 writer 证据源）",
 "CoD4x 无 2697 形态（NOT_APPLICABLE）",
 "服务端与客户端**字段形状**一致；**机制来源单一**","PROVEN（服务端格式）/ 单源（客户端形状）","I4",
 "在客户端定位 0x02 读取点→分派→0xA2E50（Q-04）")
add("C-008","Reliable Command","客户端 0xA2E50 的字段布局 = long(4)+short(2)+payload，长度上限 0x3FC",
 "E-13/E-14 客户端反汇编",
 "12_CODEC_MVP 05 §1（同源结论，**非独立**）",
 "C-2697 0xA2E50（指令级）","0x86189 short 与 0x3FC 上限（服务端）",
 "无","部分一致（与 C-007 共享同一字段定义，独立性弱）","PROVEN（形状）","I4",
 "同上")
add("C-009","Reliable Command","opcode 0x02 → 客户端 0xA2E50 的**绑定与分派**未由本地证据建立",
 "E-13/E-14：E8/绝对VA/裸RVA/跳转表全 0 命中",
 "E-19：0x6ABBC0 闭包内不含 0xA2E50",
 "无调用者；.data 99.86% 缺失 + .tvm0 未解码 → 搜索空间不完备",
 "服务端 writer 已证（单侧）",
 "无","无独立佐证（负向）","BLOCKED","I4",
 "定位客户端 0x02 读取点与分派表（静态，优先）")

# ---- C. Gamestate / Configstring ----
add("C-010","Gamestate","2697 gamestate 字段序 = <0x03> <long ver> <map\\0> <\"mp\"\\0> <long field4> <configstrings:0x04..> <long fieldC> <long field8> <0x06>",
 "2697 _CODOL2697_WriteGamestate RVA 0xA21B8（指令级，写点 0xA224C/0xA225A/0xA2269/0xA2279/0xA2288/0xA22C1/0xA22F8）",
 "atlas 07 §1.2；2697_SA 04 §2.1",
 "客户端 0x03 仅 demo 消费者 0x34FD80(1)，字段序与服务端**冲突**（E12/E14）",
 "同左","CoD4x svc_gamestate 常量（不同实现）",
 "服务端单一来源；客户端无关证据","PROVEN（服务端）/ 客户端 BLOCKED","I4",
 "定位客户端**实时** 0x03 consumer（Q-05）")
add("C-011","Gamestate","2697 gamestate 顶层尾字节 = 0x06（旧通道为 0x05）",
 "2697 _CODOL2697_WriteGamestate 0xA22F8 = WriteByte(6)",
 "2697_SA 04 §2.1（同源）",
 "客户端未见读取该字节","同左","无",
 "服务端单源","PROVEN（服务端）","I4","客户端 0x06 读取点（Q-08）")
add("C-012","Gamestate","客户端已定位的 0x03 消费者与 2697 服务端字段序**不匹配**（REFUTED）",
 "E-12/E-14：0x34FD80(1) 读 {i32,cstring,cstring,i32} 与服务端 {long,cstr,\"mp\",long} 不一致",
 "E-14 04 §1（同源）",
 "0x350170 表项 3 → 0x34FD80(1)（归属 demo，强推断）","2697 字段序（见 C-010）",
 "无","冲突已裁定为 demo 路径不适用；实时路径无证据","REFUTED（demo 消费者）/ BLOCKED（实时）","I4",
 "定位实时消费者，或证明实时与 demo 共用同一消费者")
add("C-013","Configstring","2697 configstring 起始 0x04、count1=2 字节（16 位 LE）、终止 0x06",
 "2697 _CODOL2697_WriteConfigstrings RVA 0xA0468（0xA07F8 写 4；0xA0807 WriteShort；0xA0997 写 6）",
 "E-09 03（count1 裁定）；E-14 04 §2；本任务 V-03/V-04 独立复核",
 "C-2697 0xA2660：push 2 + MSG_ReadData + movsx word（count1）；0x352FA1 +1 字节",
 "同左","无","一致（服务端 ↔ 客户端，指令级）","PROVEN","I3",
 "无（待外层框架）")
add("C-014","Configstring","索引编码：连续→1 bit '1'；否则→1 bit '0'+13 bit 绝对值；首索引 lastIdx=-1 故 0 走连续",
 "2697 WriteIndexDelta RVA 0xA0400（指令级）",
 "E-08 04；E-09；本任务 V-04 复核客户端 push 0xD",
 "C-2697 0xA26E2/0xA26F0/0xA26F4（call 0x44C8C0；否则 push 0xD）","同左",
 "无","一致（两侧指令级）","PROVEN","I3","无")
add("C-015","Configstring","索引上限 0x1DD6，0x1DD7 为 sentinel/跳过；合法区间 0..0x13（跳过 0x12）",
 "2697 _WriteConfigstrings cmp 0x1DD6 / 区间校验",
 "E-08 03 §2.1；本任务 V-04 客户端 cmp 0x1DD7 / cmp 0x14 / cmp 0x12",
 "C-2697 0xA2702/0xA2728","同左","无",
 "一致","PROVEN","I3","无")
add("C-016","Configstring","A1 字符串块：strlen+1 字节（含 NUL），长度上限 0x1FFF，拒绝 0x25('%')/0x92",
 "2697 0x99651（strlen+1 WriteData）；上限 cmp 0x1FFF；黑名单 0x25/0x92",
 "E-08 03 §2.1；E-09",
 "C-2697 0xA25F0 NUL 扫描（0xA2751 调用）","同左","无",
 "一致","PROVEN","I3","无")
add("C-017","Configstring","A2 块：段计数 11 bit；每条 = 索引增量 + 10 bit 值",
 "2697 0xA084D mov [esp+8],0xB / 0xA088A mov 0xA（**E-08 曾误记 10 bit 计数，E-14 更正**）",
 "E-14 04 §3；**本任务 V-03 独立复核服务端=0xB**",
 "C-2697 0xA2765 push 0xB（计数）/ 0xA27D7 push 0xA（值）——**本任务 V-04 独立复核**",
 "同左","无","一致（两侧，指令级双复核）","PROVEN","I3",
 "无（E-08 旧记录已在冲突登记保留为历史）")
add("C-018","Configstring","A3 块：段计数 10 bit；每条 = 索引增量 + 10 bit + 7 bit + 4 bit n + n×12 bit 扩展",
 "2697 0xA08AD(0xA)/0xA090B(0xA)/0xA0922(7)/0xA0939(4)/0xA0950(12)（本任务 V-03 复核 0xA/7）",
 "E-08 03 §2.3；E-14 04 §2",
 "C-2697 子过程 0xA2480 push 0xA/7/4","同左","无","一致","PROVEN","I3","无")
add("C-019","Configstring","字符串写入不更新位游标，位写入与字节写入可交错；0x06 不保证字节对齐",
 "2697 0x99651 无 [msg+0x10] 访问；MSG_WriteBits 增长块 0x9960A 强制 bitpos=used*8",
 "E-09 04 §（累计位 44/53/61/72/129）",
 "客户端读取端**无**独立对齐证据（0xA2660 循环结束即 ret）","同左","无",
 "服务端单侧闭合；客户端缺","PROVEN（服务端）/ BLOCKED（客户端对齐）","I3",
 "客户端 0x06 读取与对齐判定（Q-08）")
add("C-020","Configstring","count1=8 bit 的假设被驳回（唯一来源为内联 snprintf 串 \"* %u\"，非线格式）",
 "E-08 06 C-01（旧冲突）",
 "E-09 03 §3/§5（驳回）；本任务 V-03/V-04（两侧均 2 字节）",
 "C-2697 push 2 + movsx word","同左","无",
 "旧冲突已裁决；双方记录保留","REFUTED（8 bit）","I2","无")

# ---- D. Snapshot ----
add("C-021","Snapshot","2697 snapshot 调用序列（Reached→entities/clients/glass/HUD/第二遍/区域复制）已由指令级确定",
 "2697 _CODOL2697_WriteSnapshotReached RVA 0xA4860（0xA495D/0xA496E/.../0xA4EBB..0xA4F7D）",
 "atlas 07 §3.2；2697_SA 04 §2.2（同源）",
 "无客户端对应解析路径被定位","同左","无",
 "服务端单源","PROVEN（服务端调用序列）","I3","定位客户端 snapshot 解析（Q-05）")
add("C-022","Snapshot","快照外层终止符 = 0x05（archives 未激活）或 0x06（激活），由 _SV_EndClientSnapshot 0x87104 选择",
 "2697 _SV_EndClientSnapshot RVA 0x86F7D 0x87104（指令级）",
 "atlas 07 §3.2；2697_SA 04 §2.1（同源）",
 "客户端未见选择逻辑","同左","无","服务端单源","PROVEN（服务端）","I3",
 "客户端 0x05/0x06 语义（Q-08）")
add("C-023","Snapshot","快照内部 0x06（0xA4CAF）之后 writer 仍继续写入 → 是内部子记录标记，**不是**整条消息 EOF",
 "2697 _CODOL2697_WriteSnapshotReached 0xA4CAF 后续仍有 HUD/第二遍写入",
 "atlas 07 §3.3；2697_SA 04 §2.1",
 "无","同左","无","服务端单源（强结构证据）","PROVEN（服务端）","I2",
 "客户端对内部 0x06 的处理（Q-08）")
add("C-024","Snapshot","客户端 snapshot delta 解码与完整帧边界仍 BLOCKED（候选 0x6E060/0x6D340 未闭合）",
 "atlas 07 §4；E-12/E-14",
 "12_CODEC_MVP 05 §5（同源）",
 "候选解析器未闭合；0x6D340 附近有与 5/6 比较","2697 帧边界未闭合","CoD4x sv_snapshot.c（仅骨架）",
 "两端均未闭合","BLOCKED","I3","定位客户端 delta 解码闭环")

# ---- E. 会话认证 / Demonware ----
add("C-025","会话/Demonware","客户端存在 4 字节长度前缀分帧器 0x6ABBC0 与 4 状态接收状态机 0x6ABE80（类型码 1/2）",
 "E-19（单一来源；本轮未独立复核）",
 "无第二独立来源",
 "C-2697 0x6ABBC0（累 4 字节到 [esi+0xA0]）/0x6ABE80（jmp [ebx*4+0xAAC090]）/0x6A9920（cmp al,1/2）",
 "无（服务端侧无对应）","无",
 "**单一来源**（E-19 内部）","INFERRED（E-19 内为 PROVEN，跨来源为单源）","I3",
 "独立复核 0x6ABBC0；并判定类型码是否映射游戏 opcode（Q-32）")
add("C-026","会话/Demonware","该 0x6ABBC0 状态机**承载游戏会话消息**：未证明（类型码 1/2 与游戏 opcode 0x01..0x04 非同一编码空间）",
 "E-19 §2/§5（REFUTED 限定范围）",
 "E-17/E-18（Demonware 栈未承载游戏路径，未通过）",
 "0x6ABBC0 闭包内不含 0xA2660/0xA2E50/0x350170/0x3547D0/0x354100","无","无",
 "一致（多轮均为'未承载'的负向）","BLOCKED（否定性多源）","I4",
 "展开 0x6A9920 分支目标（Q-32）")
add("C-027","会话/认证","后端（Demonware/平台/TCLS/IIPS/TenProtect）通信与游戏实时消息路径**是两套东西**",
 "atlas 06 §5、atlas 09 §4；EV-Lobby-Battle 边界",
 "E-15（TLS=libcurl 更新模块）/E-17/E-18/E-19",
 "客户端平台组件存在但未接入游戏 socket 调用点（8/9 已归属为非游戏）","2697 平台导入与游戏 socket 分离",
 "无","一致（多来源）","PROVEN","I4",
 "无；在报告中强制分层")
add("C-028","会话/认证","认证成功（进大厅）**不**构成进入战斗/可玩的充分条件",
 "atlas 06 §5：进大厅=REF_LOBBY_KIT；战斗端点由 21/5 findSessions 下发；监听 28960 时 BATTLE_RX=0",
 "EV-Battle-RX0（动态）；`_combat_next011` accepted_present=false",
 "客户端未走到拨号战斗端点阶段","无","无","一致（动态证据）","PROVEN（否定性）","I4",
 "先解决战斗端点握手而非先写战斗服（见 FINAL_RECOMMENDATION）")

# ---- F. 开源血统 / 可迁移 ----
add("C-029","开源血统","OLD/1113 服务端是 CoD4x 的 fork（IW4OL），非原始 IW/Infinity Ward 源码",
 "SRC-OLD q_shared.h 字面 'IW4OL, a fork of CoD4x'；Jaccard 93-99%",
 "atlas 13；E-14 01/03（同源）",
 "—（服务端源码结论）","OLD/1113/2697 共享引擎骨架符号（RVA 各异）","CoD4x_Server @ddd65fce",
 "一致（字面 + 定量）","PROVEN","I2","无")
add("C-030","开源血统","CoD4x 与 IW4x 共享 Quake3 netchan 结构（netchan_t 1:1）",
 "atlas 13；E-14",
 "CoD4x netchan.c / IW4x netchan",
 "—","2697 与 OLD 的 netchan 常量为 CODOL 专属（见 C-003）","CoD4x @ddd65fce / IW4x @d1b175da",
 "一致（外部参考）","PROVEN","I1","无")
add("C-031","开源可迁移","CODOL netchan **不是** CoD4x/IW4x netchan 同一实现（头长/分片/上限均不同）",
 "C-003 常量对比（1162×128 vs 0x20000；头 4/6 vs 10B）",
 "atlas 04 §4.3；E-14 03（同源）",
 "客户端未见同族常量（E-14 §4）","2697/OLD 常量（C-003）","CoD4x/IW4x（不适用）",
 "一致（不兼容为结论）","PROVEN（差异）/ REFUTED（兼容假设）","I3",
 "不可直接复用netchan 实现；仅骨架")
add("C-032","开源可迁移","客户端网络栈可直接映射到 IW4X/CoD4x：**不成立**（CODOL 客户端为虚表分派 + 内联 OpenSSL）",
 "E-14 03/§4（客户端虚表分派 + OpenSSL 0.9.8p）",
 "E-15/E-18（libcurl/OpenSSL 归属）",
 "C-2697 虚表分派；内联 OpenSSL 0.9.8p；libcurl 7.38.0","—","IW4x/CoD4x（无 TLS）",
 "一致（否定）","REFUTED（映射假设）","I3",
 "不可移植客户端网络栈")
add("C-033","开源可迁移","服务端引擎层（msg/huffman/cvar/cmd/sv_init）可复用 CoD4x",
 "E-14 09（Jaccard 81.9-100%）",
 "atlas 13",
 "—","OLD/1113 源码含同名实现","CoD4x**同一仓库**",
 "一致","PROVEN","I2","注意 AGPL/GPL 许可义务")
add("C-034","开源可迁移","ol-mod 是 CODOL 3.3.3.3 专有链路源码重建，**不基于** IW4x；不能用于 2.6.9.7",
 "CODOL_OLMOD_AUDIT_AUDIT.md（EV-R-OlMod-NoIW4x）",
 "E-14 01 §3",
 "—","—","ol-mod-olfinal @2a75bdd8",
 "一致","PROVEN","I2","不可迁移到 2.6.9.7")
add("C-035","开源可迁移","IW4x 无专用服务器源码（仅客户端 DLL）",
 "E-14 01 §4；EV-R-IW4x-NoServer",
 "两份克隆差异未建清（CONFLICT-06）",
 "—","—","iw4x-client @d1b175da / @0699a7e5",
 "一致（缺口）","PROVEN（缺口）","I2","不可作为服务器方案")
add("C-036","开源可迁移","2697 传输层与 OLD 源码常量为**同一来源**（fork 延续 + 2697 层叠加），非重写",
 "R-17 常量精确匹配（本任务 V-05 复核 OLD 侧）",
 "atlas 12/13 更新",
 "—","2697 常量 0x489/0x24500/0x1fffffff/0x70cc729","CoD4x（共同祖先）",
 "一致（常量级双证）","PROVEN","I3","无")

# ---- G. 恢复镜像限制 / 方法学 ----
add("C-037","方法学/证据限制","客户端恢复镜像 .data 99.86% 缺失、末节 .tp3 未恢复、.tvm0 未解码 → 客户端搜索空间不完备",
 "E-06；atlas 15 UPDATE-2；EV-C2697-DataGap",
 "本任务 V-02 独立复核 .data VSize 0x0D05C420 vs RawSize 0x00049600",
 "C-2697-REC 区段表（活体）","—","无",
 "一致（多来源 + 本任务复核）","PROVEN（限制）/ BLOCKED（影响）","I4",
 "还原 .data 初始化来源（.rimp）；先解码 .tvm0 再搜索")
add("C-038","方法学/证据限制", "'客户端分派未找到' 是**弱否定**，不得据此断言'客户端不支持'",
 "任务书 §五/§六硬要求；E-12/E-15/E-16 负搜索限定表述",
 "E-13（REFUTED 限定范围）/E-15（REFUTED 限定范围）",
 "缺失 .data/.tp3/.tvm0","—","无",
 "一致","PROVEN（方法学）","I3","无")

# ---- H. 运行时证据分层 ----
add("C-039","运行时证据","`_combat_next011` 的 44 帧为**平台/预订层**（service 21/5、6/14），非游戏战斗 opcode 域",
 "\\_combat_next011\\frame_inventory.json（本任务读取）",
 "\\_combat_next011\\accepted_check.json（accepted_present=false）；DEV-BOOKING",
 "偏移来自 C-3333 平台客户端（非 C-2697）","—","无",
 "一致（抓包自证层）","PROVEN（分层）","I3","勿把平台帧当游戏协议证据")
add("C-040","运行时证据","唯一第一手'进入大厅'实机证据为 REF_LOBBY_KIT ↔ C-3333（2026-10-05）",
 "GOLDEN-LOBBY-001（RT-06）",
 "atlas 06 §5",
 "C-3333（非 C-2697）","—","REF_LOBBY_KIT",
 "一致","PROVEN","I2","不进战斗；与 2697 客户端无关")

COLS = ["Claim_ID","Protocol_Topic","Specific_Claim","Source_A","Source_B","Local_Client_Evidence","Server_Evidence","OpenSource_Reference","Consistency","Evidence_Grade","Impact_Level","Next_Action"]
OUT = rf"{ROOT}\XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION\XVAL01_PROTOCOL_CLAIM_MATRIX.csv"
with open(OUT,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(COLS)
    for r in C:
        assert len(r)==len(COLS), (len(r), r[0])
        w.writerow(r)
print("wrote",OUT,"claims",len(C))
from collections import Counter
print("grades:", dict(Counter(r[9] for r in C)))
