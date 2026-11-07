# 272 · 战斗服 securityKey 修复：大厅发 0x00、战斗服发 0x01，两边从未一致

> 卷次：272（2026-11-03，接 271）
> 触发：用户指示「先修，修完了再去实机」
> 产出：`battle.c` 补丁 + 重编 `codol_battle_server.exe` + 链上防脱钩断言

---

## §0 结论

1. **★★★★★ `security_key` 的真源是大厅**：`lobby_server.py:488 build_session_record(..., security_key=SEC_KEY)`
   → 经 `21/5 findSessions` 的会话记录**第 6 个记录尾字段**下发客户端。
2. **★★★★★ 两边取值不一致**：大厅 `SEC_KEY = b"\x00"*16`，战斗服 `memset(0x01,16)`，且战斗服
   **从不读** `battle_security_key.txt` ⇒ 派生出的 `transport_key` 必然不同 ⇒ 帧解密 / HMAC 全失败。
3. **★★★★ 已修**：`battle.c` 改为读该文件（读不到才回退 0x01 并打日志）；重编 exe 并装入统一链。
4. **★★★★ 已加防脱钩断言**：链上 `verify_kit_matches_protected()` 在 kit 与受保护镜像分叉时
   **以 exit=3 失败**（两个方向都实测过）。
5. **★★★ 更正我上一轮的判断**：我说「163 卷那条 KDF 对齐可纯静态做」是**过度自信**。深挖后发现
   163 卷的前提很可能站错了（见 §4）。

---

## §1 证据链（全部本项目自证）

```
lobby_server.py:460   SEC_KEY = b"\x00" * 16    # 注释: 真游戏服要配对的另一半, 暂用全 0
lobby_server.py:488   build_session_record(..., security_key=SEC_KEY)
codol_crypto.py:381   ob.blob((security_key or b"")[:16].ljust(16, b"\x00"))   # 6 16B 安全密钥
codol_crypto.py:364   「可变项只有 3 个: roomId / map 名 / 16B securityKey」
lobby_server.py:1400  写 battle_security_key.txt = SEC_KEY.hex()
battle.c:43           memset(b->security_key, 0x01, sizeof(...))    # ← 硬编码，从不读文件
battle.c:155          codol_derive_transport_key(shared, b->security_key, a->transport_key)
```

**`battle_service.c` 的全部 4 处 `fopen`**（`0x` 为行号）：

| 行 | 读什么 |
|---|---|
| 196 | `predicted.bin`（nt10 探针写的位姿） |
| 235 | flag 文件存在性 |
| 319 | `active_room.json` |
| 385 | `svc->gamestate_path` |

**⇒ 没有一处读 `battle_security_key.txt`。**（162 卷「写了没人读」成立，本卷补上了取值不一致这一半。）

### 1.1 ★ 为什么「客户端确实用它」

会话记录里那个字段是**从 CoD4X/IW4X 谱系的参考实现移植**来的
（`codol_crypto.py:354-356` 注明出处 `ol-mod MatchmakingService.cpp:614-629` +
C# `LobbyServer/Services/MatchMaking.cs BuildSessionRecord()`），
且 `codol_crypto.py:364` 明确写「可变项只有 3 个: roomId / map 名 / **16B securityKey**」——
**一个专门的、逐次会话可变的字段**，只可能是给客户端消费的。

★ 反向澄清：`battle.c` 里旧注释「客户端 build 1649370 的 live 映射对 ID 1 保留 0x01 默认值」
是**过时假设**。客户端拿到的是会话记录里的那 16B，不是内置常量表。

---

## §2 修复

`CODOL_SERVER_319_20261021/src/battle/battle.c`：

```c
static int hexval(int c) { ... }
static bool load_security_key(uint8_t out16[16])
{
    FILE *fp = fopen("battle_security_key.txt", "rb");
    ... 读 32 字符十六进制 -> 16 字节 ...
}
void codol_battle_init(codol_battle_t *b)
{
    memset(b, 0, sizeof(*b));
    if (load_security_key(b->security_key))
        fprintf(stderr, "[battle] securityKey <- battle_security_key.txt (%02X%02X...) 与大厅下发客户端的 16B 一致\n", ...);
    else
        memset(b->security_key, 0x01, ...), fprintf(stderr, "[battle] ... 回退默认\n");
    b->nonce = mono_ms() | 1u;
    codol_p224_gen_keypair(b->priv, &b->pub);
}
```

**保留回退**：单独起战斗服调试时文件不存在 ⇒ 仍用 0x01 并**打日志**（不再静默）。

### 2.1 构建

| | 旧 | 新 |
|---|---|---|
| `codol_battle_server.exe` | 314368 B / `275B165F0A79` | **315904 B / `6B14823AD2D1F5FF`** |
| 工具链 | `E:\BuildTools\...\cmake.exe`（VS17 2022 生成器，Debug） | 同 |
| 编译 | — | **成功**；新二进制内已含串 `battle_security_key.txt` |
| 装入 | — | `CHAIN_UNIFIED_20261103\CODOL_VERIFIED_GOLDEN_20261019\` |

★ 链里的旧 exe 与 `build\Debug\` 里那份**同哈希**（`275B165F0A79`）⇒ 源码与运行体对应，改动有效。

---

## §3 防「校验对象 ≠ 执行对象」（271 卷遗留）

给统一链的入口 `run_frozen_chain_once.py` 加：

```python
LAUNCH_CORE = ("run_all.py","nt10.py","lobby_server.py","fake_auth_tls.py","codol_crypto.py","make_local_ca.ps1")
def verify_kit_matches_protected(kit): ...   # 逐文件比 sha，不一致 => "kit!=protected(校验一套/跑另一套)"
...
mirror_bad = verify_kit_matches_protected(kit)
if mirror_bad: print("kit != protected mirror: ...", file=sys.stderr); return 3
```

**实测两向**：

| 场景 | 结果 |
|---|---|
| 正常 | `protected baseline: OK` / `kit == protected mirror: OK`，exit=0 |
| 改坏 **受保护镜像** | `protected baseline changed: codol_crypto.py:size`，**exit=2**（旧清单检查先拦） |
| 改坏 **kit 侧** | `kit != protected mirror: codol_crypto.py:kit!=protected(校验一套/跑另一套)`，**exit=3** |

---

## §4 ★★★ 更正：163 卷的前提很可能站错了

271/272 之前，我按 163 卷的说法准备「把战斗服的 `SHA1(shared28‖key16)` 换成客户端的带标签 KDF」。
深挖后认为**这个方向可疑**：

1. **`0xBA1E96` / `0xBA13D0` 那条链是「DW 大厅握手」，不是战斗服 UDP 通道。**
   它先算 24 字节会话密钥（`0xBA1E7A call 0xBA0750`）、20 字节 transcript hash（`0xBA1E5B call 0xC73D20`），
   再做 `secret = HMAC(transcriptHash20, sessionKey24)`（`0xBA1E96 call 0xBA0D20`），
   然后**连续两次** `expand_key(secret, "CLIENTCHAL", 16)` / `expand_key(secret, "BDDATA", 72)`。
   —— 这正是 `codol_crypto.py` 给**大厅**用的那套 `derive_session_keys`。
   而战斗服的 `codol_derive_transport_key` 是 **DTLS 味儿的 ECDH**（162 卷记的 NAT29B→DTLS16B→38B cookie→ECDH），
   **是另一条通道**。拿大厅的 KDF 去否定战斗服的公式，可能是**范畴错误**。
2. **163 卷把 `0xBA0D20` 记作「EC 秘密计算」很可能错**：本卷反汇编其函数体，
   **全是字符串/缓冲操作**（`0xC73800` 构造、`0xC73760` 赋值、`0xC737A0` 取 20 字节），**没有一处 EC 域运算**。
3. **Python 侧那份 KDF 明确写着「照抄 ol-mod」**（`codol_crypto.py:571-573`），
   这违反 AGENTS.md 的权威分级；而且它自己的 **2026-10-03 实测注记**记录：
   「用票据的全部 24B 窗口 × 12 种 transcript × 2 种 HMAC 参数序 × 2 种 label 序 = **5040 组穷举，
   与真实内存密钥全部不命中**」⇒ **该配方在我们的 build 上从未被验证过**。

**⇒ 所以本卷**没有**去改战斗服的 transport_key 公式。** 依据不足时不动手，是本项目用三次
「照抄/试一把 ⇒ 整服务死」换来的纪律。

---

## §5 边界总账

| # | 项 | 状态 |
|---|---|---|
| 1 | 战斗服读 `battle_security_key.txt` | ✅ 已改 + 编译 + 装入链 |
| 2 | 该修复的**运行期效果** | ❌ **未验证**（需实机） |
| 3 | 链上防脱钩断言 | ✅ 两向实测 |
| 4 | 战斗服 transport_key 公式是否与客户端一致 | ❌ **未定**（见 §4；不猜着改） |
| 5 | `SEC_KEY = 0x00*16` 是否该换成非零值 | ❌ 未动。全 0 在密码学上可用（只要两侧一致），换成非零需要先知道客户端期望什么 |
| 6 | `COOP_PLAYLIST_MAP` / R22 | ❌ 需真实抓包 |
| 7 | 实机 | 按用户指示「修完再去」 |

---

## §6 复现

```powershell
E:\BuildTools\CommonLibs\...\cmake.exe --build CODOL_SERVER_319_20261021\build --config Debug --target codol_battle_server
python -I CHAIN_UNIFIED_20261103\run_codol_001\run_frozen_chain_once.py --verify-only --game-root "<本体>\COD OL"
python -I _rev_analysis/_p253/f2_kdf_find.py     # 标签串定位 (BDDATA 0xD5A4E0 / CLIENTCHAL 0xD5A4E8)
python -I _rev_analysis/_p253/f4_kdf.py          # expand_key 调用点
```

---

## §7 方法论

1. **★★★★★ 「占位值必须追到落实」的下一层：两侧占位值必须**先彼此一致**。**
   162 卷查到「写了没人读」；本卷再进一步——**即使读了也没用**，因为两边填的是不同常量。
   查这类缺陷要问两个问题：**谁写、谁读**，以及**两边填的值是否相同**。
2. **★★★★ 「A 与 B 的公式不同」之前，先确认 A 与 B 处理的是不是同一条链。**
   163 卷的比较对象很可能分属「DW 大厅握手」与「战斗服 DTLS 通道」两条不同的链。
3. **★★★ 被标为「照抄第三方」的代码段，其正确性存疑**；本例中 Python 那份 KDF 的
   自附实测注记已经写明「5040 组全不命中」，却在后续卷里仍被当作权威引用。
