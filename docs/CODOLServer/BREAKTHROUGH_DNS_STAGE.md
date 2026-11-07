# 🎯 突破：dwLobby 状态机被成功推进（DW_DNS_ERROR → DW_ACCOUNT_ERROR）

日期：2026-09-25  阶段：**B 阶段重大进展**

---

## 一、成果

**通过运行期向 `0x81A76A8` 写入主机名，`DW_DNS_ERROR` 被消除，状态机推进到 `DW_ACCOUNT_ERROR`。**

```
注入前:  cur = "DW_DNS_ERROR"      (弹窗根因)
注入后:  cur = "DW_ACCOUNT_ERROR"  ← ✅ 进入下一阶段（账号）
```

这是本项目**第一次成功推动 dwLobby 状态机前进**。

---

## 二、完整机制（现已全部拆解）

### 2.1 dwLobby 状态机 `0x7F26C0`（跳转表 `0x7F2850`）

| 状态 | 调用 | 结果分支 |
|---|---|---|
| 1 | `0x7F3600` DNS检查 | `[0x84ABA78]==0` → **DW_DNS_ERROR**；`==2` → DW_DNS_COMPLETE |
| 2 | `0x7F28F0` 账号检查 | `0` → 看 `[0x84ABA5C]==0x22C7` → DW_DUPLICATE_LOGIN / DW_ACCOUNT_ERROR；`9` → DW_ACCOUNT_LOGIN_COMPLETE |
| 3 | `0x7F3800` 大厅检查 | `0` → DW_LOBBY_ERROR；`2` → DW_LOBBY_CONNECTED |
| 4 | `0x4A6470` | `==2` → DWLOGON_REGISTERCODOID_COMPLETE |
| 5 | `0x7F2680` 收尾 | — |

### 2.2 写状态函数 `0x7F2580`

```asm
007F2583  mov ecx,[0x84ABA50]      ; 旧状态
007F258D  mov [0x84ABA50],eax      ; 新状态
007F2592  mov eax,[ebp+8]          ; 状态名指针
007F259B  mov [0xE4EA3C],eax       ; 写"当前状态名"
```
约定：`eax` = 新状态号，`[ebp+8]` = 状态名指针（字符串 VA）

### 2.3 DNS 检查 `0x7F3600`

```asm
007F3618  cmp [0x84ABA78],0 / jne 0x7F3644    ; 已有结果则轮询
007F3620  call 0x7F34E0                        ; 创建解析器对象 A/B
007F362D  mov [0x84ABA78],0                    ; 失败 → DW_DNS_ERROR
; 轮询路径
007F364A  call 0x83B730   ; 查 A 状态
007F3674  call 0x83B730   ; 查 B 状态
007F3694  cmp esi,2 / cmp eax,esi              ; 都完成?
007F36AB  mov [0x84ABA78],esi                  ; 成功 → 2 → DW_DNS_COMPLETE
007F374D  mov [0x84ABA78],0                    ; 否则 → 0
```

### 2.4 解析器创建 `0x7F34E0`（★关键）

```asm
007F34E3  mov eax,[0x84ABA70]      ; 槽 A
007F34F6  push 0x238 / call new    ; 分配 0x238 字节
007F3533  push 0x81A76A8           ; ⭐ 主机名槽（本次为空 → 失败）
007F3538  call 0xBAEAB0            ; 建对象
; 同法建槽 B @0x84ABA74，用 [0x81A76A8] 的对应值
```

### 2.5 配置来源（`0x641980` 函数）

```asm
00641945  mov ecx,[0x82E1580]      ; 配置管理器对象（运行期实测有效 0x17576D18）
0064194D  mov eax,[eax+0x30]       ; vtable+0x30
0064195F  push 8                   ; ⭐ 键 ID = 8
00641961  call eax                 ; 取值 → [ebp-0x418]
; 用 ';'(0x3B) 和 ':'(0x3A) 分割
006419C3  mov al,[ebp+ecx-0x418] / cmp al,0x3b / cmp al,0x3a
00641A07  cmp edx,9                ; 共 9 段
00641A10  mov edx,0x81A76A8        ; ← 段1 → host1
00641A27  mov edx,0xE51184         ; ← 段2 → host2
00641A56  mov [0xE513D4],ax        ; 段3 → 端口
00641A62  mov edx,0x81A7F34        ; ← 段4
00641A92  mov edx,0x81A9784        ; ← 段6
00641AB6  ...
```

**配置格式**：`host1:port1;host2:port2;...`（9 段）

---

## 三、运行期实测数据

### 3.1 配置槽状态（注入前）
```
0x81A76A8 = 全 0（空）           ← ⭐ host1 缺失 → 本次失败根因
0xE51184  = "211.147.81.116"     ← exe 内硬编码初值（VA 0xE51184）
0x81A7F34 = 全 0
0x81A9784 = 全 0
0x81A9780 = 全 0
0xE513D4  = ""http://127.0.0.1/"" ← 被沙箱 iips.ini 覆盖
[0x82E1580] = 0x17576D18         ← 配置对象有效
```

### 3.2 全局时间线
```
t=0.000   cur=0xDAE091(空)   objA=0 objB=0 res=0  state=0
t=15.684  cur=0xDAE091        objA=0 objB=0 res=0  u874=0x8105EE0  ← 模块初始化
t=19.901  cur="DW_DNS_ERROR"  objA=0 objB=0 res=0                ← 失败
--- 注入 host1=host4=host6="tqos.gamesafe.qq.com", port=8081 ---
t=20.02   cur="DW_ACCOUNT_ERROR"                                  ← ✅ 推进!
```

**注意**：`objA/objB/res` 始终为 0 —— 说明走的是**另一条判定路径**（`0x7F373E` 分支，非 `0x7F3620` 创建路径）。

---

## 四、写入能力已验证

```python
k32.VirtualProtectEx(h, va, len(data), 0x40, &old)   # PAGE_EXECUTE_READWRITE
k32.WriteProcessMemory(h, va, data, len, &written)
k32.VirtualProtectEx(h, va, len, old, &old)
```
实测：对 `0x81A76A8` / `0x81A7F34` / `0x81A9784` / `0x81A9780` / `0xE513D4` **全部写入成功**。

**⇒ 我们现在能读+写游戏内存（在挂起抢句柄模式下），且不触发 ACE 蓝屏。**

---

## 五、下一步

1. **查 `0x81A76A8` 该被填什么**（配置键 ID 8 → 配置对象 vtable+0x30 的完整逻辑）
2. **推进 `DW_ACCOUNT_ERROR`**（状态2：`0x7F28F0` 账号检查）
3. 确认[配置键 ID 8 的取值来源]（dvar / TCLS 下发 / cfg / 注册表）

---

## 六、产物

```
CODOLServer\_mainline\_poke.py / _poke_out\poke.jsonl     ★ 注入实验（DW_DNS_ERROR→DW_ACCOUNT_ERROR）
CODOLServer\_mainline\_cfg2.py / _cfg2_out\               ★ 配置槽实测
CODOLServer\_mainline\_glob.py / _glob_out\               ★ 全局时间线
CODOLServer\_mainline\_statemach.py / _f7f2580.py / _f7f3600.py   状态机反汇编
CODOLServer\_mainline\_b2.py / _b2b.py / _b2c.py / _b2d.py / _ip211.py   引用与配置链追踪
```
