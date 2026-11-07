# 学习报告 043（重开）— `nt10.py` 最终导出与清理（文件结束）

**学习范围**：第 2564–2661 行（主循环存活判定 + 最终导出 + finally 清理）
**性质**：全实测
**★★★ `nt10.py` 全文（2,661 行 / 146,765 字节）已逐段学完**

---

## 一、★★★ 主循环的存活判定（第 2564–2575 行）

```python
while time.time() - t0 < a.secs:
    time.sleep(2)
    if _inject:
        # 注入式下没有 Popen 句柄(p=None)，改用进程名判断存活
        if not _game_pids(a.exe):
            log("game 已退出 (注入式) t=%.1f" % (time.time() - t0))
            break
    else:
        if p.poll() is not None:
            log("game 退出 rc=%d t=%.1f" % (p.poll(), time.time() - t0))
            break
else:
    log("game 仍在运行 (%.0fs)" % a.secs)
```

★★★ **⇒ 两个分支的存活判定（与报告 035 一致）：**
```
注入式：  not _game_pids(a.exe)     ← ★ 按进程名
非注入：  p.poll() is not None      ← Popen 对象
```

★ **⇒ `while ... else` 语法：**循环正常结束（不 break）时执行 `else`。**

★★ **⇒ 即：**跑满 `a.secs` 秒 ⇒ 打印 "game 仍在运行"。**

---

## 二、★★★★ `own()` —— 把 VA 转成 `模块+偏移`（第 2577–2583 行）

```python
ml2 = mods_any(pid, h)[0]

def own(v):
    for n2, b2, s2 in ml2:
        if b2 <= v < b2 + s2:
            return "%s+0x%X" % (n2, v - b2)
    return "0x%08X" % v
```

★★★ **⇒ 把绝对地址转成 `模块名+0x偏移`（更可读）。**

★ **⇒ 找不到所属模块时退回 `0x%08X`。**

★★ **⇒ 这是**日志可读性的关键改进**（地址有了语义）。**

---

## 三、★★★★★ 最终导出：每条命中记录的**完整解码**（第 2585–2646 行）

### 3.1 ★★★ 数据来源优先落盘文件（第 2587–2595 行）

```python
raw = b""
sp = snap + ".slot%d" % i
if os.path.exists(sp):
    raw = open(sp, "rb").read()          # ★ 优先读落盘文件
if len(raw) < 4:
    raw = rpm(h, cnt, BUF_LEN)           # ★ 回退到读内存
if len(raw) < 4:
    log("\n=== %s 无数据 ===" % nm)
    continue
```

★★★ **⇒ 优先读 `timeline` 线程落盘的 `.slotN` 文件（报告 038），**
**⇒ 因为此时游戏可能已退出，内存读不到。**

★ **⇒ 这是**重要的健壮性设计**。**

### 3.2 ★★★ 每条记录的完整字段（第 2599–2606 行）

```python
for k in range(min(c, RING)):
    rec = 4 + k * REC
    if rec + REC > len(raw):
        break
    caller = struct.unpack_from("<I", raw, rec)[0]        # +0  调用者
    argp   = struct.unpack_from("<I", raw, rec + 4)[0]    # +4  参数
    cont   = raw[rec + 8:rec + 24]                        # +8  16 字节内容
    sc     = raw[rec + CODE_OFF:rec + CODE_OFF + CODE_LEN] # +24 48 字节机器码
```

★★★ **⇒ 与 `REC = 72` 的布局**完全一致**（报告 020）：**
```
+0   4   调用者
+4   4   参数
+8  16   内容
+24 48   调用点机器码
```

### 3.3 ★★★ 四种解码分支（第 2607–2636 行）

#### ① socket 类（第 2607–2611 行）

```python
if nm in SOCK_APIS:
    s = "raw=" + cont[:8].hex(" ")
    sa = describe_sockaddr(raw, rec)
    if sa:
        s += "  ->  " + sa
```

★ **⇒ 同时显示原始 8 字节和解码后的 `IP:端口`。**

#### ② `args` / `decl` 模式（第 2612–2624 行）

```python
elif mode in ("args", "decl"):
    a1, a2, a3, a4 = struct.unpack("<4I", cont)
    if nm.startswith("tp+"):
        if a2 == 0:
            s = "tag=0x%X(%d) 查询长度模式 dst=NULL pLen=0x%X" % (a1, a1, a3)
        elif mode == "decl":
            s = ("tag=0x%X(%d) dst=0x%X pLen=0x%X 声明容量=%d"
                 % (a1, a1, a2, a3, a4))
        else:
            s = "tag=0x%X(%d) dst=0x%X" % (a1, a1, a2)
    else:
        s = "a1=0x%X a2=0x%X a3=0x%X a4=0x%X" % (a1, a2, a3, a4)
```

★★★★★ **⇒ `tp+` 的三个分支（极其关键）：**

| 条件 | 输出 |
|---|---|
| **`a2 == 0`** | **`tag=0x%X(%d) 查询长度模式 dst=NULL pLen=0x%X`** |
| `mode == "decl"` | **`tag=0x%X(%d) dst=0x%X pLen=0x%X 声明容量=%d`** |
| 其他 | `tag=0x%X(%d) dst=0x%X` |

★★★ **⇒ 第 2 分支的"声明容量=%d"就是 `a4` ——**
**即报告 022 的 `mode="decl"` 抢在函数执行前读到的 `*pLen`。**

★★ **⇒ 而第 1 分支（`a2 == 0`）明确标注 **"查询长度模式"**（`dst=NULL`）。**

★ **⇒ 与报告 022 的 `dst==0` 是"查询长度模式"**完全一致**。**

#### ③ 字符串类（第 2625–2631 行）

```python
else:
    s = cont.decode("utf-16le" if wide else "gbk", "replace").split("\x00")[0]
    if nm in STR_HOOKS:
        full = follow_str(h, raw, rec, wide)
        if full and full != s:
            s = full
```

★ **⇒ 先用 16 字节内容解码，再用 `follow_str` 取完整串（如果不同则替换）。**

#### ④ WinHttp 类（第 2632–2636 行）

```python
if nm in WHTTP_APIS:
    # WinHttpConnect: a2=pswzServerName(上面的字符串), a3=nServerPort
    _a1, _a2, _a3, _a4 = struct.unpack("<4I", cont)
    s = "%s  [a1=0x%X a2=0x%X a3=0x%X(端口=%d) a4=0x%X]" % (
        s, _a1, _a2, _a3, _a3, _a4)
```

★★★ **⇒ 注释精确说明了参数位置（逐字）：**
```
WinHttpConnect: a2 = pswzServerName（上面的字符串）, a3 = nServerPort
```

★★ **⇒ 输出 `a3=0x%X(端口=%d)` —— 直接把 `a3` 解释为端口。**

★ **⇒ 这正是报告 020 说的"记下 (serverName, port) 就能拼出完整 URL"。**

### 3.4 ★★★ 反汇编调用点（第 2639–2644 行）

```python
if shown <= a.show:
    base = max(0, caller - 0x20)              # ★ 往前 0x20 字节
    for ins in MD.disasm(sc, base):
        mk = "  <<< 返回地址" if ins.address <= caller < ins.address + ins.size else ""
        log("         %08X  %-10s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mk))
```

★★★ **⇒ 用 capstone 反汇编调用点的 48 字节机器码，并**标记返回地址**。**

★★ **⇒ `base = max(0, caller - 0x20)` —— 从返回地址往前 0x20 字节开始反汇编。**

★ **⇒ `a.show` 默认 **6**（`--show` 参数），控制显示多少条。**

★★★ **⇒ 这是**最有价值的输出**：能看到**调用点的实际指令**。**

---

## 四、★★★★ `finally` 的清理（第 2647–2656 行）

```python
except Exception as e:
    import traceback
    log("EXC: %r" % (e,))
    log(traceback.format_exc())
finally:
    stop.set()                                              # ★ 通知所有线程停止
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "TP3Helper.exe"], capture_output=True)
    log("\n结果已写入 %s" % a.out)
    fh.close()
```

### ★★★★★ 五个清理动作

| # | 动作 | 说明 |
|---|---|---|
| **1** | **`stop.set()`** | ★ 通知所有 daemon 线程停止 |
| **2** | **`taskkill /F /PID <pid>`** | 杀游戏进程（★ 按 PID） |
| **3** | **`taskkill /F /IM TP3Helper.exe`** | ★ 杀 TP3 辅助进程 |
| **4** | 打印结果文件路径 | |
| **5** | `fh.close()` | 关闭日志文件 |

★★★ **⇒ 第 3 条与报告 033 的"每次启动前杀两个进程"**对称**。**

★★ **⇒ `traceback.format_exc()` —— 完整堆栈（不只是 `repr(e)`）。**

---

## 五、★★★★★ `nt10.py` 全文结构总览（2,661 行）

| 行范围 | 内容 |
|---|---|
| **1–23** | docstring（四条关键设计） |
| **24–124** | 导入 + 常量 + `TRAMP_APIS`（33 个 API） |
| **127–133** | `MODULEENTRY32` |
| **135–147** | `rpm` / `wpm` |
| **149–211** | `mods_toolhelp` / `mods_peb` / `mods_any` |
| **214–223** | `export_rva` |
| **226–237** | `pick_stolen` |
| **240–314** | **`build_tramp`**（手写 x86 机器码，三种模式） |
| **317–328** | `describe_sockaddr` |
| **331–345** | `follow_str` |
| **348–363** | `decode_cmdline` |
| **366–488** | **`build_tas_image`**（TCLS 镜像，三套命名空间） |
| **491–545** | `parse_patches` / `apply_patches`（读-写-读） |
| **546–707** | **四个兼容补丁 + latch** |
| **710–802** | **会话密钥快照**（地址链 + XOR 还原） |
| **805–850** | `scan_dword`（只扫 MEM_PRIVATE） |
| **853–885** | `probe_auth_object` |
| **888–944** | `watch_dialogs`（零风险探针） |
| **950–1014** | `scan_playerstate_bases`（含误收事故） |
| **1017–1046** | `read_playerstate`（14 字段） |
| **1049–1116** | tick_hz / 预测态判据 |
| **1118–1316** | `playerstate_probe_thread`（三阶段状态机） |
| **1319–2661** | **`main()`**（约 1,340 行，含大量实测记录） |

★★★ **⇒ `main()` 占了**一半以上**（1,340 / 2,661 = 50.4%）——**
**其中绝大部分是**实测记录注释**。**

---

## 六、★★★★★ `nt10.py` 学到的**十项核心成果**

| # | 成果 | 报告 |
|---|---|---|
| **1** | **`.tp3` 加密**：磁盘加密，必须运行时解壳（5 次独立确认） | 025/035/040/041 |
| **2** | **三个精确时序**：t≈0.2s ACE 封枚举 / t≈2s TP3 检查 / t≈2.5s 拒 VirtualAllocEx | 020/036 |
| **3** | **四个兼容补丁 + latch**（补丁 3 改 E8→E9 会破坏补丁 2 的模式） | 025 |
| **4** | **会话密钥七层地址链**（svc→sub→state→challenge/a/b/blob） | 026 |
| **5** | **`secrets.txt` 七行格式 + 原子写 + 0.05s 轮询** | 026/027 |
| **6** | **TCLS 镜像三套命名空间**（全局/服务器/嵌套） | 023/024 |
| **7** | **`[obj+0x5E8]==1` 才受理 0x81**（否则 ConnectionReset 10054） | 042 |
| **8** | **`TenProxy 基址 = 调用者 - 0x61E8`**（或直接读堆上 vtable） | 038/041 |
| **9** | **80/230 只要回非空就卡**（不是"回得太大"） | 034/035 |
| **10** | **unlock-all 是唯一拥有权来源**（8/1 校验时 203 还没来） | 034 |

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 主循环间隔 | **2 秒** |
| 2 | ★ 存活判定 | 注入式按进程名 / 非注入按 `p.poll()` |
| 3 | ★★ `own()` | VA → **`模块名+0x偏移`** |
| 4 | ★★★ 数据来源 | **优先 `.slotN` 落盘文件**（游戏可能已退出） |
| 5 | 记录布局 | `+0` 调用者 / `+4` 参数 / `+8` 内容 16B / `+24` 机器码 48B |
| 6 | ★★★★★ **`tp+` 三分支** | **`a2==0`⇒查询长度 / `decl`⇒声明容量 / 其他 |
| 7 | ★★★ WinHttp | `a2`=服务器名 / **`a3`=端口** |
| 8 | ★★★ 反汇编 | 调用点 48 字节，**标记返回地址**，往前 `0x20` |
| 9 | `--show` 默认 | **6** |
| 10 | ★★★ finally | **`stop.set()` + 杀 pid + 杀 `TP3Helper.exe`** |
| 11 | 异常 | **`traceback.format_exc()`**（完整堆栈） |
| 12 | ★★ 文件规模 | **2,661 行 / 146,765 字节**，`main()` 占 **50.4%** |

---

## 八、结论

### 1. ★★★★★ `nt10.py` 全文已学完（43 份报告中的 20 份）

★ **⇒ 从常量表到机器码生成，从 TCLS 镜像到主循环，全部覆盖。**

### 2. ★★★★★ **`tp+` 的三分支输出是"观测设计"的最终体现**

```
a2 == 0      ⇒ 查询长度模式（dst=NULL）
mode=decl    ⇒ ★ 声明容量 = *pLen（抢在函数执行前读到）
其他         ⇒ 简单两参
```

### 3. ★★★ **优先读落盘文件**是关键的健壮性设计

### 4. ★★★ **反汇编调用点并标记返回地址**是最有价值的诊断输出

### 5. ★★ **`finally` 里杀 `TP3Helper.exe`** 与启动前的清理对称

---

## 九、下一步

`bundle\` 还剩 **4 个脚本**：
- `fake_auth_tls.py`（17,600 B）
- `stun_local.py`（7,618 B）
- `force_display_name.py`（19,288 B）
- （`launch_chain.py` 已完成）

然后：
- `bundle\` **5 个证书文件**逐字节
- `payload\` **4 个插件 PE** + **4 个 loader 二进制**
- `payload\` **18 个小 map lua** + `cha.lua`/`zm.lua` 剩余
- `source\` 结构与关键文档
