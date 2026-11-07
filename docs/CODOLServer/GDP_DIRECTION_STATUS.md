# GDP / TQoS 服务器方向 —— 阶段结论（A 完成 / C 失败 / B 进行中）

日期：2026-09-25
方法：**GDPLoader.dll 静态反汇编（明文可读）+ 运行期只读内存采样（挂起抢句柄，未碰 ACE）**

---

## A. 反编译 GDPLoader.dll —— 完成

### A.1 组件画像

```
GDPLoader.dll   291,832 B  ImageBase 0x10000000  导出只有 1 个: InitGdp @0x100193A0
  .text ent 6.44  .rdata 5.35  .data 6.16  .tvm0 仅 0x1000(4KB)   ⇒ 基本明文
  PDB: d:\Jenkins\workspace\gdp_loader_build\Output\Release_x32\GDPLoader.pdb
  IMPORTS: WINHTTP(10) + WS2_32(9) + KERNEL32(100)

GameDataPlatformServer.dll  354,808 B  无 .tvm0
  GDP_HANDSHAKE_CHANNEL_REQUEST / _MUTEX / _EVENT_REQUESTCOMPLETE / _EVENT_RESPONSECOMPLETE / _WRITE_MUTEX
  GDPPkg / GDPOpenProtocol.tdr
  PDB: gdpcommunication_components_build
```

### A.2 服务器发现逻辑（InitGdp 内，0x10019920 段）

```asm
10019939  push 0x202 / call WSAStartup
10019971  mov esi,[0x10033200]        ; = gethostbyname
10019977  push 0x10037438             ; "tqos.gamesafe.qq.com"
1001997C  call esi                    ; gethostbyname(...)
1001997E  je  -> 返回 0xFFFFFFFE(-2)
10019984  call 0x10019830             ; 处理结果1
100199B8  push 0x10037438 / call esi  ; 再解析一次
100199C5  call 0x100197C0             ; 处理结果2
```

### A.3 端口（两个 sockaddr）

```asm
处理函数1 (0x10019830)
  10019864 div esi                    ; 地址数取模 → 随机选 IP
  1001986C push 0x1F90                ; 端口 8080
  1001987B mov [0x10047F6C],edx       ; IP
  10019881 mov word [0x10047F68],2    ; AF_INET
  10019887 call htons
  1001988D mov [0x10047F6A],ax        ; 端口(网络序)

处理函数2 (0x100197C0)
  100197FC push 0x1F91                ; 端口 8081
  1001980B mov [0x10047F5C],edx       ; IP
  10019811 mov word [0x10047F58],2    ; AF_INET
```

**⇒ `tqos.gamesafe.qq.com:8080` 与 `:8081`（UDP，`socket`+`sendto`，无 recv）**

### A.4 协议结构（TssQosPkg）

```
TssQosPkgHead : wLength | wCommand | wVersion
TssQosPkgBody : stUnit_log_upload → TssQosUnitLogUpload
                   dwUser_id | dwLog_type | dwGame_id | szLog_comment
                   wChar_count | aszChar_array | wInt_count | int_array
TssQosPkg     : stHead + stBody
命令常量      : TSS_QOS_UNIT_LOG_UPLOAD / TSS_QOS_PKG_COMMAND
其它          : 183.60.58.99（硬编码 IP，紧邻域名）
返回码        : -2(预处理失败) / -3(编码失败) / -4(发送失败)
```

---

## C. 假 GDP 服务器测试 —— **失败**

### C.1 做了什么
```
1. 备份 backups\GDP_PATCH_20260925_200049\GDPLoader.dll.orig
2. 打补丁（沙箱 DLL）：tqos.gamesafe.qq.com → 127.0.0.1 ；183.60.58.99 → 127.0.0.1
3. 起本地 HTTP 服务 127.0.0.1:8080 与 :8081
4. 跑游戏，采样状态
5. 恢复原始 DLL（sha 4a6e09b8… 已核验）
```

### C.2 结果
```
HTTP 请求数 = 0                 ← 服务器完全没收到请求
t=22.58 cur='DW_DNS_ERROR'      ← 弹窗根因依旧
```

### C.3 原因（已查明）
- **游戏 exe / Base.dll 都不引用 `GDPLoader`/`InitGdp`**（全盘搜只有 GDPLoader.dll 自己含该串）
- ⇒ **`GDPLoader.dll` 很可能是死代码**，或只在更晚的大厅阶段加载
- ⇒ **`DW_DNS_ERROR` 发生在 GDP 之前**，补丁路径不对

---

## B. 追 `DW_DNS_ERROR` 真源 —— 进行中

### B.1 已确定
```
GDPLoader 只用 gethostbyname + socket + sendto（UDP，发完不管）
网络导入仅 6 个：gethostbyname / socket / sendto / closesocket / WSAStartup / WSAGetLastError
```

### B.2 运行期实测（挂起抢句柄，0.2s 采样）
```
t=0.000   cur=0xDAE091(空)  objA=0 objB=0 res=0  u874=0        u8AC=0
t=15.684  cur=0xDAE091      objA=0 objB=0 res=0  u874=0x8105EE0 u8AC=0x810F760
t=19.901  cur=0xDE08D8 "DW_DNS_ERROR"  objA=0 objB=0 res=0  t2=1
```

### B.3 关键推论
- `objA(0x84ABA70)/objB/res` **全程 0** ⇒ `0x7F34E0`（创建解析器对象）**从未执行**
- ⇒ `DW_DNS_ERROR` 由**上游**设置，不是解析器失败
- `0x81A76A8` 处 `protect=0x4, dword=0` ⇒ 是**空指针槽**，不是主机名
- 状态机 `0x7F26C0` 的 state 采样一直是 0（0.2s 粒度太粗，漏掉了中间态）

### B.4 尚未解决
1. `0x7F2580` 的**全部调用者**（谁把 `DW_DNS_ERROR` 写进 `[0xE4EA3C]`）
2. `0x7F34E0` 到底被谁调用、`0xBAEAB0`（用 `push 0x81A76A8`）的语义
3. game 自己 DNS 全成功，为何仍判 DNS 失败

---

## 方法与红线（复用）

```
✅ 挂起抢句柄可穿透 ACE：
   CREATE_SUSPENDED → OpenProcess(QUERY|VM_READ) → ResumeThread
   ctypes 必须声明 restype/argtypes（否则 64 位句柄截断 → ReadProcessMemory 挂起）
✅ 游戏可执行文件字符串 VA = 文件偏移 + 0x714000
✅ 运行期 dump（0x400000..0xE65000）覆盖到主模块；更大地段须实时读
❌ 严禁 sc stop/config ACE 驱动（蓝屏 0x01010002）
❌ 游戏 exe/.tp3、ACE 多数组件是加密/虚拟化的，磁盘反汇编不可信
   —— 但 GDPLoader / GameDataPlatformServer / GDPImpl 基本明文，可直接反汇编
```

## 产物

```
backups\GDP_REVERSE_20260925\          GDPLoader/GameDataPlatformServer/GDPImpl/GDPCODOTrail/.tdr 副本
backups\GDP_PATCH_20260925_200049\     补丁前 GDPLoader.dll.orig（已用于还原）
CODOLServer\_mainline\_initgdp_full.py / _gdp_http2.py / _gdp_tss.py / _gdp_ws2.py   反汇编
CODOLServer\_mainline\_glob.py / _glob_out\globals.jsonl      ★ 全局状态时间线
CODOLServer\_mainline\_gdp_c_test.py / _gdp_c_out\            ★ C 测试（http_requests=0）
CODOLServer\_mainline\_vq_probe.py / _vq_out\vq.jsonl         ★ 内存属性查询
CODOLServer\_mainline\_gdp_patch.py                          补丁工具
```
