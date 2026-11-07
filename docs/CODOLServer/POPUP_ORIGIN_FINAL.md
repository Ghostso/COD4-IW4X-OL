# 游戏内弹窗「[100]无法连接大厅服务!」完整溯源（动态取证）

日期：2026-09-25
方法：**挂起创建 + 抢在 ACE 之前拿句柄** → 全运行期只读内存采样（**未碰 ACE 驱动**）
产物：`CODOLServer\_mainline\_dyn_game_out3\state.jsonl`（220 采样点 / 109.7s）

---

## 一、弹窗从哪里来（完整调用链，逐条 VA 级验证）

### 1.1 状态机入口

```asm
007F26C0  push ecx
007F26C1  mov  eax, [0x84ABA50]        ; dw 状态 (0..5)
007F26C6  cmp  eax, 5
007F26C9  je   0x7F284E
007F26CF  dec  eax
007F26D3  ja   0x7F2824
007F26D9  jmp  dword [eax*4 + 0x7F2850] ; 状态跳转表
```

### 1.2 状态 1 = **DNS 检查**（就是它失败）

```asm
007F26E0  call 0x7F3600               ; DNS 检查函数
007F26E5  mov  eax, [0x84ABA78]       ; 结果
007F26EC  jne  0x7F2700
007F26EE  push 0x00DE08D8             ; "DW_DNS_ERROR"     <<<<<< 弹窗根因
007F26F3  call 0x7F2580               ; 写当前状态
007F2700  cmp  eax, 2
007F2709  push 0x00DE08E8             ; "DW_DNS_COMPLETE"
```

`0x7F3600` 内部：

```asm
007F3618  cmp  [0x84ABA78], 0
007F3620  call 0x7F34E0               ; 最内层判定
007F3625  test al, al
007F362D  mov  [0x84ABA78], 0         ; 失败 → 结果 0
```

`0x7F34E0` 内部：

```asm
007F34E3  mov  eax, [0x84ABA70]       ; 解析器对象 A
007F34F6  push 0x238 / call 0xB74220  ; new(0x238)
007F3533  push 0x081A76A8             ; <<< 目标主机名（运行时初始化）
007F3538  call 0xBAEAB0               ; 解析/比较
...
007F354C  push 0x238 / new            ; 解析器对象 B [0x84ABA74]
```

### 1.3 状态 2 = 账号检查

```asm
007F271B  call 0x7F28F0               ; 账号检查
007F2724  cmp  [0x84ABA5C], 0x22C7    ; 错误码 8903
007F272E  mov  eax, 0x00DE0610        ; "DW_DUPLICATE_LOGIN"
007F2735  mov  eax, 0x00DE08F8        ; "DW_ACCOUNT_ERROR"
007F2753  push 0x00DE090C             ; "DW_ACCOUNT_LOGIN_COMPLETE"
```

### 1.4 状态 3 = 大厅检查

```asm
007F276A  call 0x7F3800               ; 大厅检查
                          → "DW_LOBBY_ERROR" / "DW_LOBBY_CONNECTED"
```

### 1.5 状态 4 = 弹窗触发点（与子代理结论一致，我已复核）

```asm
007EF210  cmp  esi, 4
007EF219  mov  eax, [0xE4EA3C]        ; <<< 当前 DW 状态名指针
007EF21E  push 0x00DE0610             ; "DW_DUPLICATE_LOGIN"
007EF22E  call 0x774710
007EF23E  jne  0x7EF253
007EF253  push 0x00DE0640             ; "@SF_UI_DW_LIVE_CONNECTING_FAILED"
007EF258  call 0x771240               ; Scaleform 面板投递
```

---

## 二、为什么来（动态实测证据）

| 时刻 | `dwLobby_state`(0x84ABA50) | 当前状态名 `[0xE4EA3C]` | `code@0x7EF210` |
|---|---|---|---|
| t=0.00 | 0 | `0xDAE091`（空） | `0c56578b...` **加密态** |
| **t=18.54** | 2 | **`0xDE08D8` = "DW_DNS_ERROR"** | **`83fe040f...` 现场解密** |
| t=19.04 | 10 | 同上 | 同上 |

**⇒ 弹窗的根本原因 = `DW_DNS_ERROR`（DNS 阶段判定失败）**

---

## 三、对应的静态文件（明确答案）

| 内容 | 静态文件 | 位置 |
|---|---|---|
| 全部状态机代码 + 跳转表 | **`COD OL\codoMP_client_shipRetail.exe`** | VA 0x7EF210 / 0x7F2580 / 0x7F2600 / 0x7F26C0 / 0x7F34E0 / 0x7F3600 |
| DW 状态名字符串表（连续块） | **同上** | VA 0x00DE08C8 ~ 0x00DE09BC |
| 弹窗文案 key | **同上** | VA 0x00DE0640 `@SF_UI_DW_LIVE_CONNECTING_FAILED` |
| **中文文案** | **`COD OL\localization.txt`** | offset **0x950** → 「无法连接大厅服务!」 |
| 域名（stun/master） | `COD OL\codoMP_client_shipRetail.exe` | VA 0xD5A9CC/0xD5A9E4/0xD5A9FC/0xDC6610/0xDBD558 |

**DW 状态名字符串表（exe 内连续块）**
```
0x00DE08C8  dwLogonStart
0x00DE08D8  DW_DNS_ERROR          ← 本次弹窗
0x00DE08E8  DW_DNS_COMPLETE
0x00DE08F8  DW_ACCOUNT_ERROR
0x00DE090C  DW_ACCOUNT_LOGIN_COMPLETE
0x00DE0928  DW_LOBBY_ERROR
0x00DE0938  DW_LOBBY_CONNECTED
0x00DE094C  DWLOGON_REGISTERCODOID_ERROR
0x00DE096C  DWLOGON_REGISTERCODOID_COMPLETE
0x00DE098C  DW_LOGON_ERROR
```

---

## 四、DNS 追踪（同轮，ETW Microsoft-Windows-DNS-Client）

**按 PID 分类**（游戏 pid=16408）：

```
PID 0x0BC0 (3008)  410 次  ← 含 socket.hipcapi.com x129  【非游戏】
PID 0x11B0 (4528)   92 次  ← 全是 socket.hipcapi.com     【非游戏】
PID 0x4018 (16408)  68 次  ← ⭐ 游戏进程
       down.qq.com / intldlgs.qq.com / tqos.gamesafe.qq.com
       dump.gamesafe.qq.com / stat.iips.qq.com
       stun1/2/3-tub.codol.qq.com / ied-tqos.qq.com
       xxx.dlied1.cdntips.net (CDN)
```

**⇒ `socket.hipcapi.com` 不是游戏查的**（我先前误判，已更正）

**游戏进程所有 DNS 查询均解析成功**（逐一复验）：
```
down.qq.com            -> 116.131.225.198 ✅
intldlgs.qq.com        -> 218.69.49.90   ✅
tqos.gamesafe.qq.com   -> 182.50.14.56   ✅
dump.gamesafe.qq.com   -> 61.241.53.221  ✅
stat.iips.qq.com       -> 42.187.183.162 ✅
stun1/2/3-tub.codol.qq.com -> 121.51.232.x ✅
ied-tqos.qq.com        -> 116.130.224.66 ✅
```
（唯一失败的 `tqm.gamebaby.qq.com` 是 **PID 3756 非游戏进程** 在查）

---

## 五、尚存的未知（必须诚实标注）

1. **`0x081A76A8` 上的主机名是什么** —— 该地址在 exe 的 230MB 虚拟段（BSS），
   **运行期才初始化**，且我的读取返回越界/失败。**未能抓到具体主机名**。
2. `0x7F34E0` 内 `0xBAEAB0` / `0xBAEDF0` / `0xB74220` 的**具体语义**（解析器 API）未展开。
3. 既然游戏自己的 DNS 查询全部成功，`DW_DNS_ERROR` 究竟是
   「某个未出现在 DNS trace 里的内部名字解析失败」还是「解析成功但结果不可用」——**未定论**。

---

## 六、工具与产物

```
CODOLServer\_mainline\_dyn_game2.py       运行期状态采样（挂起抢句柄，已验证可用）
CODOLServer\_mainline\_dns_trace.py       ETW DNS 追踪 + 游戏启动
CODOLServer\_mainline\_dns_str.py         读 DNS 检查相关全局
CODOLServer\_mainline\_min_probe.py       最小验证（已证挂起抢句柄可读）
CODOLServer\_mainline\_dwtable.py/_dwpush.py/_dnscheck.py/_dns_core.py   反汇编
CODOLServer\_mainline\_dyn_game_out3\state.jsonl    ★ 220 采样点状态轨迹
CODOLServer\_mainline\_dns_out\dns.csv             ★ DNS ETW 原始事件(651行)
CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin   ★ 全主模块镜像(解密后)
```

**方法要点（下次直接复用）**
- **必须** `CREATE_SUSPENDED` → 先 `OpenProcess(QUERY|VM_READ)` → 再 `ResumeThread`
- ctypes **必须声明 restype/argtypes**，否则 64 位句柄被截断 → 读操作**挂起**
- 脚本纯 ASCII，中文路径走参数或从脚本位置推导
