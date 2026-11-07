# CODOL 交接块逆向结果（TCLS_SHAREDMEMEMORY）

日期：2026-09-25
方法：Frida 动态探针 + 崩溃现场捕获 + 逐字节二分定位（非静态反汇编）
结论：**已能让客户端读取并接受我们的交接块而不崩溃**

---

## 一、三个决定性发现

### 1. 客户端真正打开的对象名

动态观测 `OpenFileMappingW`（Frida）：

```
OpenFileMappingW name="TCLS_SHAREDMEMEMORY<pid>"  access=0xF001F  -> handle 有效
```

注意：

- **没有下划线**（不是 `TCLS_SHAREDMEMEMORY_<pid>`）
- **`MEMEMORY`** —— 原程序自身的拼写错误，必须照抄
- `<pid>` 十进制直接拼接

我们此前一直创建 `TCLS_TASMEMORY_<pid>` / `TCLS_SHELLMEMORY_<pid>`，
所以客户端从未读过它（`handoff_recovery.md` 里"映射从未出现在游戏句柄表"的真实原因）。

字符串位置（`codoMP_client_shipRetailBase.dll`）：

```
off 0x88EFFC  va 0x1088FFFC   "TCLS_SHAREDMEMEMORY"
off 0x88F010  va 0x10890010   "TAS-3AAC03A5-7D57-4c80-A175-0E4BEA43EE41-%u"
off 0x88F13C  va 0x1089013C   "TCLS_TASMEMORY_" (UTF-16LE)
```

所在区段全部落在 `.rdata`，且**没有任何 `push imm32` / `mov r32,imm32` 交叉引用，
重定位表也没有指向该 VA 的 HIGHLOW 项**（153482 项中 0 命中）——
说明引用被 VMProtect 虚拟化（`.tvm0`，rva 0x19DD000，size 0x1F5E000）。

### 2. 同时创建三个映射会导致必崩

| 创建的映射 | 结果 |
|---|---|
| `TASMEMORY_` + `SHELLMEMORY_` + `SHAREDMEMEMORY` | ❌ `0xC0000005` 秒崩 |
| **只建 `SHAREDMEMEMORY`** | ✅ 稳定运行 |
| 不建任何映射 | ✅ 稳定运行 |

结论：`TCLS_TASMEMORY_` / `TCLS_SHELLMEMORY_` 是 **TCLS 写入端**使用的名字；
客户端看到它们会进入另一条路径并崩溃。**必须只创建这一个对象。**

### 3. 崩溃字段的精确偏移

二分定位（每轮只把一个区域填 `0x01010101`，其余清零）：

| 区域 | 偏移 | 结果 |
|---|---|---|
| 头部 | 0x000–0x010 | ✅ 存活 |
| block1 | 0x010–0x410 | ❌ `0xC0000005` |
| block2 | 0x410–0x490 | `0xFFFFFFFF` |
| tail | 0x490–0x7AC | `0xFFFFFFFF` |

继续细分 block1：

| 子区域 | 结果 |
|---|---|
| 0x010–0x050 | ✅ |
| **0x050–0x090** | ❌ |
| 0x090–0x0D0 | ✅ |
| 0x0D0–0x110 | ✅ |
| 0x110–0x210 | ✅ |
| 0x210–0x310 | ✅ |
| 0x310–0x410 | ✅ |

再细分到 dword：

| 偏移 | 结果 |
|---|---|
| 0x050 | ✅ 存活 |
| **0x054** | ❌ **`0xC0000005`** |
| 0x058 | ✅ 存活 |
| 0x05C | ✅ 存活 |

**唯一崩溃字段：块内偏移 `0x054` 的 dword，被当作指针/偏移解引用。**

### 3.1 更精确的读取端结论（2026-09-25 补测）

用 `ready=1, len1=0, len2=0`、其余全零的**明文**块复测：

```
OpenFileMappingW  TCLS_SHAREDMEMEMORY9640 -> success
MapViewOfFile     base=0x12f80000
shm_access        read @ offset 0x0   (只读 ready 字段)
survived 20s      （未崩溃，未解引用 block1）
```

说明读取端的实际分支是：

```
读 +0x000 (ready)
  ready==0 -> 不做后续解析
  ready!=0 -> 读 +0x008 (len1) / +0x00C (len2)
              len1/len2 为 0 -> 不进入 block1 解析
              len1/len2 非 0 -> 进入 block1，把其中字段当指针/长度
```

而 `build_tas_payload()` 会把 `+0x004` 起的整段（含 `+0x008/+0x00C`）
一起加密；客户端按**明文**去读这两个长度字段，于是拿到随机值 → 越界。

**这才是 `full` 崩溃的真实原因，而不是 `+0x054` 本身。**
`+0x054` 只是随机长度值触发解析后，第一个被解引用的字段。

---

## 二、崩溃现场（Frida ExceptionHandler 捕获）

```
type      : access-violation (read)
pc        : 0x7AD08ACC   -> codoMP_client_shipRetailBase.dll + 0x2B18ACC  (.tvm0)
read addr : 0xD97DF688
edx       : 0xD97DF688      <- 就是它
ecx       : 0xC4DAF688
esi       : 0x7AC16F9F
edi       : 0xA0000
eax       : 0xA0020
ebx       : 0x7AC42981
```

崩溃指令（文件偏移 `0x2B0D8CC + (0x2B18ACC - 0x19DD000)`）：

```
7AD08AC6  8B 16              mov edx, [esi]
7AD08AC8  03 17              add edx, [edi]
7AD08ACA  81 C2 98 0D 56 2C  add edx, 0x2C560D98
7AD08ACC  8B 0A              mov ecx, [edx]     <-- 崩在这里
```

`esi` 落在 `.tvm0` 内，是 VMProtect 的间接寻址链。
**静态逆向此处的成本极高，因此改用二分法直接定位数据字段，结果如上。**

---

## 三、可用的安全块

实测通过（客户端稳定运行 20–30 秒、16 个 connect、ACE 正常加载）：

```python
def build_safe_shared_payload():
    buf = bytearray(0x7AC)
    struct.pack_into('<I', buf, 0x004, 0x7AC)  # size
    struct.pack_into('<I', buf, 0x000, 1)      # ready = 1
    struct.pack_into('<I', buf, 0x008, 0)      # len1 = 0
    struct.pack_into('<I', buf, 0x00C, 0)      # len2 = 0
    return bytes(buf)

```

要点：

- **头部必须明文**，不能像 TAS 写入端那样整段加密
- `len1/len2` 必须为 0，客户端才不会去解引用 block1
- `+0x054` 保留为 0 即可（它只在 block1 被解析时才重要）
```

要点：

- 大小 `0x7AC`（1964）
- `+0x004` 写 `0x7AC`
- `+0x000`（ready）写 0 —— 写 1 也不崩（已验证），但 0 更保守
- **`+0x054` 必须为 0**，否则必崩
- 其余区域填 0 是安全的（block2 / tail 非零只会让客户端走 `0xFFFFFFFF` 退出路径，不越界）

`COD OL\scripts\codol_launch.py` 已加入此函数（`build_safe_shared_payload`）。

---

## 四、安全块下观测到的客户端行为

一次 30 秒完整运行（PID 21256）：

```
17:02:56  MapViewOfFile (CEF)
17:02:57  connect 116.131.225.20:80    TenProtect/BugTrace 配置下载
17:02:59  LoadLibrary ACE-DRV32.dll
17:02:59  connect 127.0.0.1:55888,55890   CEF 回环
17:02:59  connect 123.234.2.103:443      TLS（9 字节长度前缀握手）
17:03:00  LoadLibrary tersafe.dll
17:03:03  LoadLibrary ACE-MMS32.dll
17:03:04  OpenFileMappingW TCLS_SHAREDMEMEMORY21256  -> success, handle 0x8ec
17:03:04  MapViewOfFile 同对象   -> base 0x12e50000
17:03:04  shm_access  read  @ base+0   （读取 ready 字段）
17:03:06  connect 61.241.53.221:80    /cgi-bin/susup/infocheck + upload
          exit 0xFFFFFFFF
```

关键：**客户端确实打开并映射了我们的块，并读取了它**。

---

## 五、下一步

1. **让 `ready=1` 且 `+0x054=0`，看客户端是否继续推进**（当前用 ready=0，等价于"无数据"）。
2. `123.234.2.103:443` 的 TLS 握手值得单独抓——它的载荷形状（9 字节 ASCII 前缀 +
   517 字节 ClientHello）不像普通 HTTPS，可能是 TAS/登录认证。
3. `61.241.53.221:80` 的 `infocheck`/`upload` 是 ACE 退出前的最后一步，
   重定向到本机并返回成功响应，可能就能让客户端不再以 `0xFFFFFFFF` 退出。

---

## 六、工具

| 文件 | 作用 |
|---|---|
| `CODOLServer\crash_probe.js` | Frida ExceptionHandler，抓崩溃现场（pc/寄存器/模块偏移） |
| `CODOLServer\_shm_bisect.py` | 逐区域/逐 dword 二分定位崩溃字段 |
| `CODOLServer\_shm_variants.py` | 载荷变体矩阵（zero/ready/noready/full） |
| `CODOLServer\game_net_probe.js` | 网络 + 映射 + 内存访问监控 |
| `CODOLServer\game_launch_probe.py` | 挂起创建 → 注入 → 建映射 → 放行 |
| `CODOLServer\_find_shm_reader.py` / `_find_shm_reader2.py` | 静态 xref 搜索（确认被 VM 化） |
| `CODOLServer\tasdata_sample.bin` | `C:\ProgramData\Tencent\TAS\TASData.dat` 副本（240B） |
