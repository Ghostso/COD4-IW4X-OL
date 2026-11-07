# 学习报告 005 — nt10.py 会话密钥快照链路（行 709-802）

**学习范围**：密钥地址链、XOR 还原表、`snapshot_client`、`secrets_snapshot_thread`
**这是整个包最核心的机制 —— 没有它，客户端进不了大厅**

---

## 一、为什么密钥必须从内存读（行 719）

> 为什么要写文件：**服务端进程读游戏内存会被拦**（三方实测），而 nt10 这条链读得到。

**这是根本约束**：
- `Alwaysoffline.Localnet32` 跑在**客户端进程内**，但它是插件，不能直接调 `ReadProcessMemory` 读**自己进程**的密钥结构（实际上可以，但那不是设计的选择）
- 更重要的是：`lobby_server.py` 这种**独立进程**要读游戏内存会被 ACE 拦
- `nt10.py` 有 `PROCESS_VM_READ` 权限，读得到

★ 所以设计的本质是：**用一个有权限的外部进程，把密钥搬运到文件，服务端再读文件。**

---

## 二、密钥地址链（行 712-718）

```
svc       = [0x08269774]                    ← 场景全局（硬编码绝对地址）
sub       = [svc + 1268 (0x4F4)]
state     = [sub + 1512 (0x5E8)]            ← 状态机
challenge = read(sub + 1532 (0x5FC), 8)     ← state >= 2
a         = [sub + 1540 (0x604)]            ← state == 3
b         = [sub + 1544 (0x608)]
blob      = read(sub + 1548 (0x60C), 40)
aes_out   = read(a + 156, 16)
aes_in    = read(b + 156, 16)
hmac_out  = XOR还原(blob[0:20], 表1)
hmac_in   = XOR还原(blob[20:40], 表2)
```

### 关键设计点

1. **`0x08269774` 是绝对地址**（ImageBase = `0x400000`，所以 RVA = `0x4269774`）
   —— 绑定这一个 build。

2. **两级指针**：`svc → sub`，说明 `svc` 是一个对象，`+0x4F4` 处是子对象。

3. **状态门控**：
   - `state >= 2` 才有 `challenge`
   - `state == 3` 才有 `aes/hmac`

4. **`a + 156` / `b + 156`**：`a` 和 `b` 是对象指针，`+0x9C` 处是 16 字节密钥。
   ★ `156 = 0x9C`，这个偏移在两个对象上**相同** —— 说明 `a`/`b` 是同类对象。

5. **`blob` 是 40 字节 = 两个 20 字节 HMAC**
   —— 但**必须先 XOR 还原**，说明内存里存的是加密形态。

---

## 三、XOR 还原表（行 721-724）

```python
_HK_W1 = (2919830337, 4089226047, 3169481240, 3423678985, 4099162642)
_HK_I1 = (7, 17, 14, 16, 9, 19, 13, 0, 2, 3, 4, 8, 1, 10, 11, 5, 18, 6, 12, 15)
_HK_W2 = (2866684544, 4095810571, 938409728, 3457192487, 557642922)
_HK_I2 = (19, 18, 9, 4, 17, 1, 10, 8, 13, 2, 15, 3, 12, 16, 5, 7, 0, 14, 6, 11)
```

**结构**：5 个 DWORD（20 字节）+ 20 个索引（0-19 的排列）。

### `_decode_key` 的工作方式（行 727-730）

```python
def _decode_key(src, start, words, indices):
    tab = b"".join(struct.pack("<I", w) for w in words)   # 5 个 DWORD 展开成 20 字节
    return bytes(src[start + j] ^ tab[indices[j]] for j in range(len(indices)))
```

**算法**：
```
out[j] = src[start + j] ^ tab[indices[j]]
```

- `tab` 是 20 字节（5 个 DWORD 小端展开）
- `indices` 是**置换**（打乱顺序）
- 每个字节用**不同位置**的 tab 字节异或

★ **`indices` 是 0-19 的排列**（每个数字恰好出现一次）—— 这是个**置换表**，
不是随机索引。验证：`_HK_I1` 排序后是 `0,1,2,...,19`。

### 为什么这样做

**简单的循环 XOR 容易被识别**（模式固定）。用**置换 + 5 个 DWORD 分散**，
增加静态分析的难度 —— 这是一个**轻量混淆**，不是强加密。

---

## 四、`snapshot_client` 的状态门控（行 733-760）

```python
svc = r32(0x08269774)
if not svc: return {}          # ← LSG 对象还没建立

sub = r32(svc + 1268)
if not sub: return {}          # ← 子对象还没建立

st = r32(sub + 1512)
out = {"state": st, "sub": sub}

if st >= 2:
    out["challenge"] = read(sub+1532, 8)

if st == 3:
    a, b = r32(sub+1540), r32(sub+1544)
    blob = read(sub+1548, 40)
    if a and b and len(blob) == 40:
        ao, ai = read(a+156,16), read(b+156,16)
        if len(ao)==16 and len(ai)==16:
            out["aes_out"] = ao
            out["aes_in"]  = ai
            out["hmac_out"] = _decode_key(blob, 0,  _HK_W1, _HK_I1)
            out["hmac_in"]  = _decode_key(blob, 20, _HK_W2, _HK_I2)
```

### 三级安全检查

1. `svc` 非零
2. `sub` 非零
3. `a`/`b` 非零 且 `blob` 长度 == 40
4. `ao`/`ai` 长度 == 16

★ **每一级失败就返回空/跳过** —— 而不是崩溃。因为这是**轮询**，
下一次可能就成功了。

### 状态语义

| state | 含义 | 可读内容 |
|---|---|---|
| 0/1 | 未开始 | 无 |
| 2 | challenge 已生成 | challenge |
| 3 | 密钥已派生 | challenge + aes + hmac |

★ **这是 LSG 握手的状态机**：客户端先生成 challenge，再算密钥。

---

## 五、写入线程的提速（行 763-802）

```python
def secrets_snapshot_thread(h, log, pid, seconds=600.0):
    last = None
    while ...:
        s = snapshot_client(h)
        cur = (s.get("challenge", b""), s.get("aes_out", b""), s.get("hmac_out", b""))
        if any(cur) and cur != last:
            last = cur
            lines = ["pid %d" % pid, "state %d" % s.get("state", 0)]
            for n in ("challenge","aes_out","aes_in","hmac_out","hmac_in"):
                if s.get(n): lines.append("%s %s" % (n, s[n].hex()))
            tmp = SECRETS_PATH + ".tmp"
            with open(tmp,"w") as f: f.write("\n".join(lines)+"\n")
            os.replace(tmp, SECRETS_PATH)      # ← 原子替换
        time.sleep(0.05)                       # ← 20 Hz
```

### 三个关键设计

**① 变化检测 `cur != last`**
只在 `(challenge, aes_out, hmac_out)` **变化时**才写，避免无意义 IO。

**② 原子写 `tmp` + `os.replace`**
`os.replace` 在 Windows 上是**原子**的（`MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`）。
服务端可能在任何时刻读这个文件，**不能让它读到写了一半的内容**。

**③ 20 Hz 轮询（0.05s）**

行 766-777 的注释解释了原因：

> 老外 backend 在 `LobbyProtocol::processClientAuth`（处理 0x82 帧）
> 就 `readLobbySecrets()` 一次，**之后不再重读**。
> 而 `secrets.txt` 由本线程写；客户端只有在算完 LSG 密钥后才让 state 到 3。
> ⇒ 原来 0.5s 的轮询 + 大厅改为**进程内直连**把
> 「客户端算完密钥 → 服务端处理 0x82」这个窗口压到可能小于一个轮询周期
> ⇒ 文件还是上一轮的旧值 ⇒ backend 用错密钥回 0x83
> ⇒ 客户端第一条 0x86 对不上 ⇒ **`[100]`**。

★★ **这就是 `[100]` 的另一个成因**：**时序竞争**。
不是密钥算错，是**文件里还是旧值**。

### 放宽写入条件

```python
if st >= 2:  # challenge 可读就写，不等 state==3
```

> 另外 state>=2 时 challenge 就已可读（backend 的 0x83 正文要用它），
> 所以不再要求 state==3 才写 —— **先写 challenge，密钥到齐后再覆盖一次**。

**这解决了两个问题**：
1. 服务端处理 `0x82` 时就需要 challenge（回 `0x83` 用）
2. 如果只等 state==3，challenge 可能已经过时

### 判据（行 775）

> `secrets.txt` 第一行 `pid` 必须等于当前客户端 pid。

★ **这是防"读到上一轮残留"的直接手段**。上一轮的 `secrets.txt` 还在磁盘上，
新客户端启动后如果服务端先读了旧文件，密钥就是错的。

---

## 六、这一块的结论

1. **密钥链路两级指针 + 状态门控**，硬编码 `0x08269774`。
2. **HMAC 是 XOR 混淆存储**，用 5 DWORD + 20 元素置换表还原。
3. **轮询 20 Hz + 原子写**，因为服务端只读一次，窗口极窄。
4. **`[100]` 的两个成因**：密钥算错（用 AuthSession 推导）**或**时序竞争（读到旧文件）。
5. **`pid` 行是防残留的关键判据**。

---

## 七、待验证

- [ ] `_HK_I1`/`_HK_I2` 是否真是置换（排序后是否 0-19 全出现）
- [ ] `a+156` / `b+156` 的对象类型是什么
- [ ] `blob` 的 40 字节在内存里为何是加密态（谁写的、什么算法）
- [ ] `state` 从 2 到 3 的触发点（哪个网络事件）
- [ ] `0.05s` 是否足够（实测最坏延迟是多少）
