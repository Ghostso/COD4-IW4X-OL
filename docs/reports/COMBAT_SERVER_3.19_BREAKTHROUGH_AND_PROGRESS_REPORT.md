# CODOL 3.19 战斗服务器端构建突破与全量推进报告

> **目标版本**：使命召唤OL (CODOL) **3.19 零售版**  
> **核心二进制**：`COD OL\codoMP_client_shipRetail.exe`（`3.19.26.22`, build `1649370`, `SizeOfImage: 0x0E659000`）  
> **参考版本说明**：2.6.9.7 (2697) / 1.1.1.13 / Antia 早期源码等版本仅供架构与只读协议参考，不混入 3.19 构建目标。  
> **日期**：2026-10-14  

---

## 一、 本轮推进核心成果速览

| 维度 | 推进前状态 | 本轮推进后状态 | 验证结论 |
|---|---|---|---|
| **大厅→战斗服交接门禁** | 客户端在 `0x632680` 静默 `ret 0x14`，RX#1 恒为 0 | **彻底闭合**：动态提取 A/B，正确构造 `sender_id` 与 accepted 推送 | ✅ `test_offline_replay.py` 100% 通过 |
| **推送断连与序号漂移** | 开启推送引发 9/9 闪退 / 序号跳跃 1000 导致断连 | **彻底解决**：修正 S2C 单调递增序号，双端协议无缝吻合 | ✅ 离线与网络解密验证通过 |
| **地址块长度契约 (0xB95C50)** | 默认 24B 会话地址块导致 `0xB95C50` 强校验拒绝 | **彻底闭合**：启用 67B 地址块 (`0x43`)，内嵌 `127.0.0.1:28960` | ✅ `0xB95C8C` 汇编指令级对齐 |
| **密钥派生一致性** | 大厅与战斗服 `SEC_KEY` 存在 0x00 vs 0x01 不一致 | **统一闭环**：大厅与战斗服完全对齐 `16 * 0x01`（实机 1649370 证据） | ✅ P-224 ECDH 传输密钥推导一致 |
| **真实 UDP 28960 网络链路** | 从未在真实网络收发活体数据包 | **全链路实通**：NAT -> DTLS Cookie -> ECDH -> Challenge -> Connect -> GameState -> Usercmd -> 128Hz 快照 | ✅ `test_full_wire_inmatch.py` 真实网络全绿 |
| **多客户端并发承载** | 单人限制 / 槽位管理未经网络多路复用验证 | **双客户端并发实通**：Slot 0 与 Slot 1 独立握手、独立状态、独立 128Hz 快照下发 | ✅ `test_diag_multi.py` 真实网络全绿 |
| **地图资源自动登记** | 无法定位工作区地图资产，告警缺少地图 | **已修复**：`ServerHost.cs` 正确挂载 `_map_extract` 下 7 个 fastfile | ✅ `mp_crash_tropical.ff` 自动解析挂载 |
| **权威战斗伤害系统** | 缺少生命值、扣血、击杀、死亡与重生逻辑 | **已实现并编译入库**：100 HP、3D 视线相交判定、武器开火伤害结算、阵亡 3 秒自动重生 | ✅ `test_combat_physics.py` 100% 通过 |

---

## 二、 客户端 3.19 "从不连接战斗服" 底层根因逆向突破

本轮通过只读反汇编逆向分析 `codoMP_client_shipRetail.exe`（`image_best.bin`），在指令级彻底查明了客户端静默拒绝连接战斗服的根本原因：

### 1. 即时消息分发器（RVA 0x7F1400）
`0x7F1400` 是 Demonware 针对 Service 6（即时消息/推送）的统一虚方法分发器（位于 `vtable 0xDE07A4 + 0x68`）：
```assembly
007F153C  push 6
007F153E  push ebx                         ; 接收到的推送消息体
007F153F  push 0xdc6724                    ; "mmbook"
007F1544  call 0xc3c678                    ; strncmp(ebx, "mmbook", 6)
007F154C  test eax, eax
007F154E  jne 0x7f1576                     ; 非 mmbook 分支
; 命中 mmbook!
007F1554  mov ecx, dword ptr [0x82e13fc]   ; 全局匹配单例
007F155A  mov eax, dword ptr [ecx]         ; vtable
007F155C  mov eax, dword ptr [eax + 0x13c] ; 0x632680 (accepted handler)
007F1562  push [esp + 0x14]                ; Arg 5
007F1563  push ebx                         ; Arg 4: 消息正文 ("mmbook accepted\0")
007F1566  push edi                         ; Arg 3
007F1567  mov edx, [ebp + 0xc]             ; Arg 2: sender_id 高 32 位 (B)
007F156A  push edx
007F156B  mov edx, [ebp + 8]               ; Arg 1: sender_id 低 32 位 (A)
007F156E  push edx
007F156F  call eax                         ; 调用 0x632680
```

### 2. 预约接受处理函数（RVA 0x632680）的 5 道致命门禁
`0x632680` 是战斗服发起连接的唯一入口，其内部存在 5 道严格校验：
```assembly
0063268D  cmp byte ptr [esi + 0x278], 0         ; 闸门 1: 匹配中状态
00632694  je 0x6328eb                           ; 失败静默退出
0063269A  cmp dword ptr [0x76446b0], 3          ; 闸门 2: 尚未进入战斗连接 (state < 3)
006326A1  jge 0x6328eb                          ; 失败静默退出
006326AA  cmp dword ptr [esi + 0xe360], 0       ; 闸门 3: 预约槽位有效 (slot >= 0)
006326B0  jl 0x6328ed                           ; 失败静默退出
006326B6  mov eax, [ebp + 8]                    ; 闸门 4: sender_id 低 32 位
006326B9  cmp eax, [esi + 0x3a048]              ; 必须严格等于本地预约记录 A (796)!
006326BF  jne 0x632916                          ; 不等立即 ret 0x14 静默返回！
006326C5  mov ebx, [ebp + 0xc]                  ; 闸门 5: sender_id 高 32 位
006326C8  cmp ebx, [esi + 0x3a04c]              ; 必须严格等于本地预约记录 B (0)!
006326CE  jne 0x632916                          ; 不等立即 ret 0x14 静默返回！
```
* **历史缺陷**：大厅旧代码将 `sender_id` 写死为 `1`。客户端发送的 `mmbook 796 AQAAAAAAAAA= 0` 记录了 `A=796, B=0`。闸门 4 判定 `1 != 796`，直接执行 `ret 0x14` 静默丢弃，导致客户端永远不触发后续连接代码！

### 3. 连接触发与地址块长度要求（RVA 0x6293B0 -> 0xB95C50）
当上述 5 道门禁全部 PASS 后：
* `0x63285A call 0x6293B0`：进入战斗桥接；
* `0x62942B call 0xB95C50`：解析会话地址块，在 `00B95C8C cmp dword ptr [ebx + 0x118], 0x43` 处**严格要求地址块长度必须为 67 字节（0x43）**，否则跳转至 `0xB95D20` 报错中断；
* `0x6294AF call 0x470360`：写入 netchan 地址 `127.0.0.1:28960`，并将连接状态置为 `3`；
* 客户端下一帧（`0x5C2A80`）检测到 `state == 3`，立即向 UDP 28960 发送 `getchallenge 0 "%s"`！

---

## 三、 本轮代码修复与工程落地明细

### 1. `REF_LOBBY_KIT/lobby_server.py` 修复
* **动态解析与构造 `sender_id`**：
  从客户端发来的 `mmbook <A> <token> <B>` 中正则提取 `A` 与 `B`，计算 `sender_id = (A & 0xFFFFFFFF) | ((B & 0xFFFFFFFF) << 32)`（例如 `796`），确保客户端 `0x632680` 的闸门 4 与闸门 5 绝对通过。
* **推送报文序号单调性修复**：
  移除原代码中导致序号越界的 `seq + 1000` 偏移量，使用服务端的严格单调递增 `out_seq`，彻底解决 TCP 通道去同步断连。
* **地址块与密钥对齐**：
  创建并启用 `REF_LOBBY_KIT\pve-address67.on`，使 21/5 会话对象输出符合 `0xB95C50` 要求的 67 字节地址块；对齐 `SEC_KEY` 为 `01010101010101010101010101010101`。
* **自动托管 C# 战斗服务器**：
  修改 `maybe_start_battle_server()`，优先拉起高性能独立 `CODOLCombatServer.exe`，并将其与大厅生命周期自动绑定。

### 2. `CODOL-Combat-Server-v0.1` 战斗服引擎升级
* **地图资产发现与挂载**：
  修改 `ServerHost.cs` 中的 `FindMapAssetDir()`，使其支持直接解析根目录 `_map_extract`，成功自动加载并登记 `mp_crash_tropical.ff`（32.6 MB）与 `mp_nuked.ff`。
* **权威生命值与伤害系统实现（`GameWorld.cs`）**：
  * 在 `PlayerState` 中实现 `Health (100)`、`MaxHealth`、`IsDead`、`Kills`、`Deaths`、`RespawnTimer`、`TakeDamage(damage, attacker)` 与 `Respawn(spawn)`。
  * 在 `GameWorld` 中实现 `RayIntersectsPlayer` 3D 射线与碰撞圆柱体（半径 15.0，站姿高度 72.0）相交算法，由 (Yaw, Pitch) 视线向量计算弹道碰撞；
  * 实现 `ProcessWeaponFire` 开火命中扣血与击杀判定；
  * 在 128Hz `Frame(dt)` 循环中实现阵亡倒计时，倒计时结束后自动在出生点满血复活。
* **重新编译与清单固化**：
  执行 `build.ps1` 确定性编译，产物通过校验，指纹与 `BUILD_MANIFEST.txt` 保持完全一致。

---

## 四、 自动化验证结果汇总

工作区已建立并执行了完整的自动化测试矩阵，所有测试均 100% 通过：

```
[1/3] test_offline_replay.py: 100% PASS
      · 21/5 findSessions: 地址块 67 字节 (0x43) 严格通过
      · 6/14 mmbook: 动态提取 A=796, B=0, sender_id=796 严格通过
      · Push 消息体: 加解密、HMAC 签名、TLV 信封结构严格通过

[2/3] test_full_wire_inmatch.py: 100% PASS (真实 UDP 28960 网络套接字)
      · Step 1: NAT 探针 (29B) -> 0x0C 回复通过
      · Step 2: DTLS init (16B) -> Cookie (38B) 获取通过
      · Step 3: ECDH P-224 密钥交换 (219B -> 114B ACK) 通过
      · Step 4: OOB getchallenge -> challengeResponse 1 接收通过
      · Step 5: OOB connect -> connectResponse 接收通过
      · Step 6: 服务端主动 GameState 下发 (259B) 接收通过
      · Step 7: gamestateupdate 1..6 进度上报通过
      · Step 8: 真实 14B usercmd 发送与服务端接收通过
      · Step 9: 128Hz 权威 Motion Snapshot 位级快照持续推送验证通过

[3/3] test_combat_physics.py: 100% PASS
      · 伤害衰减与生命值扣减验证通过
      · 致死伤害判定与 K/D 统计更新验证通过
      · 3D 射线正向命中 / 背向未命中 / 侧向未命中严格对齐
      · 阵亡状态与满血重生流程验证通过
```

---

## 五、 操作使用指南

### 1. 运行全链路自检验证
在工作区根目录下直接运行：
```powershell
python run_combat_pipeline.py --verify
```
输出全绿即代表战斗服务器的握手、网络、协议和战斗物理逻辑处于完全就绪状态。

### 2. 独立运行 3.19 战斗服务器
```powershell
python run_combat_pipeline.py --combat
```
服务器将在后台绑定 `UDP 127.0.0.1:28960`，自动加载会话描述符与地图资源，并以 128Hz 频率运行权威主循环。

### 3. 与游戏客户端进行端到端联调
1. 启动大厅与战斗服务器服务栈；
2. 启动 3.19 游戏客户端（`COD OL\codoMP_client_shipRetail.exe`）；
3. 客户端进入游戏大厅后，点击对局匹配/靶场训练；
4. 大厅服务将自动回复包含 `sender_id = 796` 的 `mmbook accepted` 帧；
5. 客户端通过 `0x632680` 门禁，直接向 `UDP 28960` 发送首包连接；
6. 战斗服务器自动完成 DTLS、P-224 ECDH 握手并下发游戏状态与权威运动快照！
