# -*- coding: utf-8 -*-
"""CODOL 大厅 0x85 帧的加解密(零依赖: 纯 Python AES-128-CBC + HMAC-SHA1)。

依据: 三方 CodolLocalLobbyServer.cs(AesTransform / Hmac8 / BuildTaskReplyObjects
      / BuildPushFrameWithSender / 0x85 解密分支) —— 逐字段照抄。

本机没有任何 AES 库(Crypto/Cryptodome/cryptography 全无), 所以自带一份 AES。

帧结构(两端一致):
    u32 total_len(= 整帧长度 - 4)
    u8  0xAB
    u8  0x85
    u32 seq
    u8  iv[16]
    u8  cipher[n]      (n 是 16 的倍数)
    u8  hmac8[8]       (= HMAC-SHA1(key, frame[:-8])[:8])

明文(解密后):
    u32 payload_len
    u8  marker         (0x01 = 任务应答, 0x02 = 服务端推送)
    u8  payload[payload_len]

任务应答 payload 的 TLV(照抄 BuildTaskReplyObjects):
    tag 10 + u64 replyId
    tag 8  + u32 status
    tag 3  + u8 task
    tag 8  + u32 对象个数
    (若个数 != 0) tag 8 + u32 个数, 然后逐个对象的原始字节

客户端任务帧的明文(照抄解密分支):
    u32 declared | 0x86 | service | 0x03 | task | payload(declared-3)

自测: python codol_crypto.py    (跑 FIPS-197 向量 + CBC 往返 + 帧往返)
"""
import hashlib
import hmac
import os
import struct

# ★ 可选加速: PyCryptodome 的 AES-128-CBC 与下面的纯 Python 实现逐字节一致。
#   大应答(全量道具 80/230 ≈ 830KB)纯 Python 要 ~19s, 客户端会 reset;
#   有它则毫秒级返回, 没有则自动回退纯 Python(功能完全不变)。
try:
    from Crypto.Cipher import AES as _AES
except Exception:
    _AES = None


# ------------------------------------------------------------------ AES 表
def _rotl8(x, s):
    return ((x << s) | (x >> (8 - s))) & 0xFF


def _build_sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = (p ^ ((p << 1) & 0xFF) ^ (0x1B if (p & 0x80) else 0)) & 0xFF
        q = (q ^ ((q << 1) & 0xFF)) & 0xFF
        q = (q ^ ((q << 2) & 0xFF)) & 0xFF
        q = (q ^ ((q << 4) & 0xFF)) & 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q
        for s in (1, 2, 3, 4):
            x ^= _rotl8(q, s)
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i
    return sbox, inv


SBOX, INV_SBOX = _build_sbox()
RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xt(a):
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xt(a)
        b >>= 1
    return r & 0xFF


def _expand_key(key):
    w = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return w


def _add_rk(s, w, rnd):
    for c in range(4):
        for r in range(4):
            s[r][c] ^= w[rnd * 4 + c][r]


def _encrypt_block(w, blk):
    s = [[blk[r + 4 * c] for c in range(4)] for r in range(4)]
    _add_rk(s, w, 0)
    for rnd in range(1, 10):
        for r in range(4):
            for c in range(4):
                s[r][c] = SBOX[s[r][c]]
        for r in range(1, 4):
            s[r] = s[r][r:] + s[r][:r]
        for c in range(4):
            a0, a1, a2, a3 = s[0][c], s[1][c], s[2][c], s[3][c]
            s[0][c] = _mul(a0, 2) ^ _mul(a1, 3) ^ a2 ^ a3
            s[1][c] = a0 ^ _mul(a1, 2) ^ _mul(a2, 3) ^ a3
            s[2][c] = a0 ^ a1 ^ _mul(a2, 2) ^ _mul(a3, 3)
            s[3][c] = _mul(a0, 3) ^ a1 ^ a2 ^ _mul(a3, 2)
        _add_rk(s, w, rnd)
    for r in range(4):
        for c in range(4):
            s[r][c] = SBOX[s[r][c]]
    for r in range(1, 4):
        s[r] = s[r][r:] + s[r][:r]
    _add_rk(s, w, 10)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def _decrypt_block(w, blk):
    s = [[blk[r + 4 * c] for c in range(4)] for r in range(4)]
    _add_rk(s, w, 10)
    for rnd in range(9, 0, -1):
        for r in range(1, 4):
            s[r] = s[r][-r:] + s[r][:-r]
        for r in range(4):
            for c in range(4):
                s[r][c] = INV_SBOX[s[r][c]]
        _add_rk(s, w, rnd)
        for c in range(4):
            a0, a1, a2, a3 = s[0][c], s[1][c], s[2][c], s[3][c]
            s[0][c] = _mul(a0, 14) ^ _mul(a1, 11) ^ _mul(a2, 13) ^ _mul(a3, 9)
            s[1][c] = _mul(a0, 9) ^ _mul(a1, 14) ^ _mul(a2, 11) ^ _mul(a3, 13)
            s[2][c] = _mul(a0, 13) ^ _mul(a1, 9) ^ _mul(a2, 14) ^ _mul(a3, 11)
            s[3][c] = _mul(a0, 11) ^ _mul(a1, 13) ^ _mul(a2, 9) ^ _mul(a3, 14)
    for r in range(1, 4):
        s[r] = s[r][-r:] + s[r][:-r]
    for r in range(4):
        for c in range(4):
            s[r][c] = INV_SBOX[s[r][c]]
    _add_rk(s, w, 0)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def cbc_encrypt(key, iv, data):
    """AES-128-CBC 加密(不做填充, data 长度必须是 16 的倍数)。"""
    # ★ 2026-10-05: 大应答(如全量道具 80/230 ≈ 830KB)用纯 Python AES 要 ~19s,
    #   客户端等不到就 reset。PyCryptodome 的输出与 _encrypt_block 逐字节一致
    #   (已自测), 用它把 830KB 压到毫秒级。没装则回退纯 Python, 行为不变。
    if _AES is not None:
        return _AES.new(key, _AES.MODE_CBC, iv).encrypt(bytes(data))
    w = _expand_key(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = bytes(x ^ y for x, y in zip(data[i:i + 16], prev))
        c = _encrypt_block(w, blk)
        out += c
        prev = c
    return bytes(out)


def cbc_decrypt(key, iv, data):
    """AES-128-CBC 解密(不做去填充)。"""
    if _AES is not None:
        return _AES.new(key, _AES.MODE_CBC, iv).decrypt(bytes(data))
    w = _expand_key(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        p = _decrypt_block(w, blk)
        out += bytes(x ^ y for x, y in zip(p, prev))
        prev = blk
    return bytes(out)


# --------------------------------------------------------------- 帧 处 理
MARK = 0xAB
KIND_TASK = 0x85
KIND_STAGE1 = 0x82


def hmac8(key, data):
    return hmac.new(key, data, hashlib.sha1).digest()[:8]


def parse_frames(buf):
    """从缓冲区里切出完整帧; 返回 (帧列表, 剩余缓冲)。u32 长度字段 == 0 视为 keepalive。"""
    frames = []
    off = 0
    while len(buf) - off >= 4:
        ln = struct.unpack_from("<I", buf, off)[0]
        if ln == 0:
            frames.append((b"\x00\x00\x00\x00", "keepalive"))
            off += 4
            continue
        if ln > 0x100000:
            return frames, buf[off:]      # 长度异常, 保留余下让上层处理
        if len(buf) - off - 4 < ln:
            break
        frames.append((buf[off:off + 4 + ln], "frame"))
        off += 4 + ln
    return frames, buf[off:]


def decrypt_task_frame(frame, aes_out, hmac_out):
    """解一条客户端 0x85 任务帧。返回 dict 或 None。"""
    if not aes_out or not hmac_out or len(frame) < 34:
        return None
    total = struct.unpack_from("<I", frame, 0)[0]
    body = frame[:total + 4]
    if len(body) < 34 or body[4] != MARK or body[5] != KIND_TASK:
        return None
    seq = struct.unpack_from("<I", body, 6)[0]
    mac_ok = (hmac8(hmac_out, body[:-8]) == body[-8:])
    iv, ct = body[10:26], body[26:-8]
    if len(ct) % 16 or not ct:
        return None
    pt = cbc_decrypt(aes_out, iv, ct)
    if len(pt) < 8:
        return None
    declared = struct.unpack_from("<I", pt, 0)[0]
    d = {
        "total": total, "seq": seq, "hmac_ok": mac_ok, "plain": pt,
        "declared": declared, "marker": pt[4], "service": pt[5],
        "ver": pt[6], "task": pt[7],
        "payload": pt[8:8 + max(0, declared - 3)] if declared >= 3 else b"",
    }
    return d


def serialize_file_data(data):
    """照抄三方 SerializeFileData: tag 0x13 + tag 0x08 + u32 长度 + 原始字节。"""
    return bytes([19, 8]) + struct.pack("<I", len(data)) + data


# ------------------------------------------- Demonware 类型化写入器(借鉴 ol-mod)
# 出处: ol-mod src/backend/Demonware/ByteBuffer.cpp:8-21(类型表) / 195-281(写侧)。
# 默认 useDataTypes=true, 每个值前写 1 字节类型标签。
# ★ 关键: matchmaking 的 query-criterion 字段是 SIGNED, 必须用 I32(0x07);
#         写成 U32(0x08) 会被客户端逐值类型检查拒绝(源码 ByteBuffer.cpp:11-16 明确标注)。
T_BOOL, T_U8, T_U16, T_I32 = 0x01, 0x03, 0x06, 0x07
T_U32, T_I64, T_U64 = 0x08, 0x09, 0x0A
T_STRING, T_BLOB, T_ARRAY = 0x10, 0x13, 0x6C


class Buf(object):
    """Demonware ByteBuffer 写侧(逐字段照抄 ByteBuffer.cpp 的 writeXxx)。

    `use_types=False` 对应 ol-mod 的 `useDataTypes(false)` —— 只写值、**不写类型标签**。
    ★ 2026-10-03 实测教训: 频道推送(marker=2)的 body 用带 tag 的写法**会让客户端立刻断连**
      (见 HANDOFF §13.4), 所以 push 路径改用无 tag 模式(ol-mod 处理本地即时消息时也正是
      关掉标签的)。任务应答(0x01)仍用带 tag —— 那条已被实机验证。
    """

    def __init__(self, use_types=True):
        self.b = bytearray()
        self.ut = use_types

    def _t(self, tag):
        if self.ut:
            self.b += bytes([tag])

    def u8(self, v):
        self._t(T_U8); self.b += bytes([v & 0xFF]); return self

    def bool_(self, v):
        self._t(T_BOOL); self.b += bytes([1 if v else 0]); return self

    def u16(self, v):
        self._t(T_U16); self.b += struct.pack("<H", v & 0xFFFF); return self

    def u32(self, v):
        self._t(T_U32); self.b += struct.pack("<I", v & 0xFFFFFFFF); return self

    def i32(self, v):
        self._t(T_I32); self.b += struct.pack("<i", int(v)); return self

    def u64(self, v):
        self._t(T_U64); self.b += struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF); return self

    def i64(self, v):
        self._t(T_I64); self.b += struct.pack("<q", int(v)); return self

    def string(self, s):
        if isinstance(s, str):
            s = s.encode("utf-8")
        self._t(T_STRING)
        self.b += s + b"\x00"; return self

    def blob(self, d):
        """带 tag: 13 08 <u32 len> data; 无 tag: <u32 len> data。"""
        if self.ut:
            self.b += bytes([T_BLOB, T_U32]) + struct.pack("<I", len(d) & 0xFFFFFFFF) + d
        else:
            self.b += struct.pack("<I", len(d) & 0xFFFFFFFF) + d
        return self

    def u32array(self, xs):
        if self.ut:
            self.b += bytes([T_ARRAY, T_U32]) + struct.pack("<II", len(xs) * 4, len(xs))
        else:
            self.b += struct.pack("<II", len(xs) * 4, len(xs))
        for x in xs:
            self.b += struct.pack("<I", x & 0xFFFFFFFF)
        return self

    def data(self):
        return bytes(self.b)


def bd_common_addr(ipv4_be, port):
    """37 字节 bdCommonAddr —— 照抄 ol-mod MatchmakingService.cpp:284-310 commonAddress()。
        [ipv4 4B 大端][port 2B 小端] | [00 FF 00 FF 00 00]×4 | 同上 6B | [01]"""
    ep = bytes(ipv4_be) + struct.pack("<H", port & 0xFFFF)
    return ep + bytes([0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00]) * 4 + ep + b"\x01"


# 房间 host uid: 常量 1000001 —— 照抄 ol-mod MatchmakingService.cpp:146。
# ★ 绝不能等于玩家自己的 CODOID, 否则客户端把"加入房间"的消息发给自己并丢弃回包
#   → 表现为"房间无响应"(源码注释 142-145)。
ROOM_HOST_UID = 1000001

# mp_playlists_shipRetail_release.info 的版本号, 照抄 ol-mod MatchmakingService.cpp:544。
PLAYLIST_VERSION = 796


def build_session_record(session_id, host_ipv4, host_port,
                         game_type=0, max_players=18, current_players=1,
                         map_name="mp_crash_tropical", security_key=b"\x00" * 16,
                         room_host_uid=ROOM_HOST_UID):
    """构造 1 条 matchmaking session 对象(完整 258 字节对象)。

    出处: ol-mod MatchmakingService.cpp:614-629(5 个前置字段 + 记录尾)
          + :514-558(writeSessionRecordTail 逐字段) —— 移植自 C# 参考
          LobbyServer/Services/MatchMaking.cs BuildSessionRecord()。

    ★ 三个"错了就崩"的门槛(源码 485-513 的实测注释):
      1. MatchMakingInfo+70 必须 == 67(由"逐字段构造"保证; 贴不透明描述符会填成 37
         → sub_B95C50 把 out 指针留 0 → sub_8071F0 读 *(0+0x10) 访问违例);
      2. roomId 必须是**非零十进制字符串**(否则 MatchController.as 的
         _strtoui64(room.id) == last_kick_room_id(未设置=0) → 每次加入都被判"被踢");
      3. host uid 不能等于玩家自己的 CODOID(见上面 ROOM_HOST_UID 注释)。
    可变项只有 3 个: roomId / map 名 / 16B securityKey。
    """
    room_id = (int(session_id) & 0x7FFFFFFF) | 1        # 强制非零
    ob = Buf()
    # ---- 5 个前置字段 ----
    ob.blob(bd_common_addr(host_ipv4, host_port))                       # ① Hostaddress
    ob.blob(struct.pack("<Q", int(session_id) & 0xFFFFFFFFFFFFFFFF))    # ② SessionId
    ob.u32(game_type)                                                   # ③ GameType
    ob.u32(max_players)                                                 # ④ MaxPlayers
    ob.u32(current_players)                                             # ⑤ CurrentPlayers
    # ---- 记录尾 ----
    ob.string(str(room_id))            # 1 roomId(非零十进制串)
    ob.u64(room_host_uid)              # 2 host uid
    ob.string(map_name)                # 3 地图名
    ob.i32(-695030357)                 # 4 query criterion, 0xD692ADAB
    for _ in range(6):
        ob.i32(0)                      # 5
    ob.blob((security_key or b"")[:16].ljust(16, b"\x00"))   # 6 16B 安全密钥
    ob.i32(19); ob.i32(0); ob.i32(0)   # 7/8
    ob.i32(8); ob.i32(-1)              # 9/10
    ob.i32(PLAYLIST_VERSION); ob.i32(30)   # 11/12
    ob.i32(0); ob.i32(7); ob.i32(0)        # 13
    ob.i32(0x0C0DE001)                 # 14 room id(刻意非零)
    ob.u64(room_host_uid)              # 15 demonwareID / room id
    ob.i32(0); ob.i32(0); ob.i32(0); ob.i32(1); ob.i32(0)   # 16
    return ob.data()


# ---------------------------------------------------- 21/5 会话对象(靶场/普通)
# 逐字段照抄三方 C# BuildMissionSessionObject(CodolLocalLobbyServer.cs:420-488)。
# ★ 与上面的 build_session_record(ol-mod 的 258B 记录)是**两种不同实现**: 这里按 C# 权威
#   形状 —— 33 个字段; 靶场用 67B 地址块, 普通用 24B 地址块。
# ★ 2026-10-05: 三方 C# 用的是 "mp_shootingrange", 但本机 CODOL 资源里只有
#   COD OL\IIPS\IIPSDownload\*_mp_firingrange_V*.ifs —— 没有 shootingrange。
#   地图名必须和客户端已安装资源一致, 否则进图时会找不到地图。
MISSION_MAP_FIRING = "mp_firingrange"
# ★★ 2026-10-07 实机更正：剧情任务的地图**不是固定的**。
#   实测两轮，客户端 mmstart 里报的 map 分别是：
#       第 1 轮: coop_take_mp_fav_tropical
#       第 2 轮: coop_chopper_mp_suburbs
#   —— 它取决于玩家在剧情列表里**选的哪一关**。
#   所以这里只作为"没有 playlist 信息时的兜底"，真正取值走
#   COOP_PLAYLIST_MAP / coop_map.txt（见 build_mission_session_object）。
MISSION_MAP_NORMAL = "coop_training_mp_cargoship"
MISSION_SESSION_ID_BLOB = bytes([1, 0, 0, 0, 0, 0, 0, 0])   # field 2: 8B sessionId

# ★ 2026-10-07: coop/PvE playlist id -> 该 playlist 的默认地图。
#   客户端在 21/5 请求里用第 3 个 u32 报告它想进哪个 playlist(实测剧情任务 = 10);
#   21/5 的 session 必须回**同一张地图**, 否则客户端过滤不过就不连战斗服。
#   地图名取自客户端内置 coop 任务注册表(mem_linear 里的 `coop_*` 串表), 本地已安装。
#   这里只登记已实测/已确认的条目; 未登记的 playlist 退回 MISSION_MAP_NORMAL。
# ★★ 2026-10-07 实机更正：playlist=10 对应的剧情任务地图**不是**写死的那张。
#   实测（用户手动进剧情那一轮，lobby_srv.log 17:02:56）客户端随后发来的
#   mmstart 明确写着：
#       g_gametype coop; map coop_take_mp_fav_tropical;
#   而我们 findSessions 回的是 coop_training_mp_cargoship —— **两张不同的图**。
#   素材侧确认 coop_take_mp_fav_tropical 存在：
#       ff_init_coop_take_mp_fav_tropical_V53.ifs        (30 MB)
#       lf_init_coop_take_mp_fav_tropical_V4.ifs         (25 MB)
#       lf_hi_init_coop_take_mp_fav_tropical_V3.ifs      (42 MB)
#   ⇒ session 里的 map 必须与客户端实际要加载的一致，否则它拿到的
#     "要去哪张图"与"要下哪张图"对不上，就不会去连战斗服。
#   这里留一个可覆盖文件 `coop_map.txt`（写一行地图名），默认按实测值。
COOP_PLAYLIST_MAP = {
    10: "coop_take_mp_fav_tropical",
}


def _coop_map_override():
    """读 `coop_map.txt`（一行地图名）；不存在/为空则返回 None。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coop_map.txt")
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read().strip().split()
            if t:
                return t[0]
    except Exception:
        pass
    return None


def coop_map_for(playlist):
    """解析某个 playlist 最终会用哪张地图（供日志/排查使用）。

    优先级：coop_map.txt 覆盖 > COOP_PLAYLIST_MAP 登记 > MISSION_MAP_NORMAL 兜底。
    必须与 build_mission_session_object 的取值逻辑保持一致。
    """
    ov = _coop_map_override()
    if ov:
        return ov
    try:
        return COOP_PLAYLIST_MAP.get(int(playlist), MISSION_MAP_NORMAL)
    except Exception:
        return MISSION_MAP_NORMAL


def build_mission_session_object(firing_range=False, playlist=None,
                                 game_type_override=None, map_override=None,
                                 address67=False):
    """21/5 findSessions 的**单个** session 对象 —— 逐字段照抄 BuildMissionSessionObject。

    字段序(全部带 tag; 数字 = C# 注释里的 field 序号):
      1  地址 blob          19 08 <u32 len> <addr>   (普通 24B / 靶场 67B)
      2  SessionId blob     19 08 08 01 00 00 00 00 00 00 00
      3  u32 0              08 00000000
      4  u32 0              08 00000000
      5  u32 1 (Players)    08 01000000
      6  map 字符串         10 <ASCII> 00
      7  u64 1              0A 01 00 00 00 00 00 00 00
      8  hostname           10 "localhost" 00
      9  i32 GameType       07 <靶场 0x1000007 / 普通 0x1000003>
      10 i32 Playlist       07 01 00 00 00
      11 i32 0              07 00 00 00 00
      12 u32 LicenseType    08 FF FF FF FF
      13 i32 0              07 00 00 00 00
      14 i32 0              07 00 00 00 00
      15 i32 0              07 00 00 00 00
      16 空 blob            19 08 00 00 00 00
      17 i32 MaxPlayers     07 <靶场 1 / 普通 4>
      18..27 i32 0 ×10      07 00 00 00 00 ×10
      28 u64 1              0A 01 00 00 00 00 00 00 00
      29..33 i32 0 ×5       07 00 00 00 00 ×5

    ⚠️ 有符号 int32 必须用 tag **7**; tag 8 是 uint32 —— 客户端运行时读取器 0xB76910
       会逐值检查类型(C# 注释 466-467 明确)。混用会被判非法。

    长度: 靶场 270B(= 6+67 + 14 + 15 + 18 + 9 + 11 + 15 + 5 + 15 + 6 + 55 + 9 + 25);
          普通 237B(= 6+24 + 14 + 15 + 28 + 9 + 11 + 15 + 5 + 15 + 6 + 55 + 9 + 25)。
    """
    if firing_range or address67:
        # 0xB95C50 要求地址块长度 0x43(=67); 0xB750B0 读 10 个 6B 本地槽 + 1 个公网槽 + NAT 字节
        addr = bytearray(67)
        addr[0] = 127; addr[3] = 1
        addr[4] = 0x20; addr[5] = 0x71             # 127.0.0.1:28960(小端)
        addr[60] = 127; addr[63] = 1
        addr[64] = 0x20; addr[65] = 0x71
        addr[66] = 1                               # 实验性本地 NAT 分类
        if firing_range:
            game_type, map_name, max_players = 0x1000007, MISSION_MAP_FIRING, 1
        else:
            # ★ 2026-10-07 对照实验(已否证): PvE 也使用 67B 地址块,
            #   但保留 mmstart 实测的 coop map/gametype。实测客户端仍停在
            #   “战斗开始”, battle_server 仍 0 收包 → 地址块长度不是根因。
            #   保留此开关仅用于后续对照, 默认关闭。
            game_type, map_name, max_players = 0x1000003, MISSION_MAP_NORMAL, 4
    else:
        # 24B: 内网 127.0.0.1:28960 + 外网 127.0.0.1:28960
        addr = bytearray(24)
        addr[0] = 127; addr[3] = 1
        addr[4] = 0x20; addr[5] = 0x71
        addr[18] = 127; addr[19] = 0; addr[20] = 0; addr[21] = 1
        addr[22] = 0x20; addr[23] = 0x71
        game_type, map_name, max_players = 0x1000003, MISSION_MAP_NORMAL, 4
    # ★ 2026-10-07: 允许按客户端 findSessions 请求回填 Playlist / GameType / map,
    #   否则客户端选剧情任务时拿到的是靶场那条(Playlist=1), 过滤不过就不连战斗服。
    if playlist is not None:
        try:
            playlist = int(playlist)
        except Exception:
            playlist = None
    # ★ 2026-10-07: coop/PvE —— 已登记的 playlist 用它自己的地图,
    #   让 21/5 回的地图与客户端所选任务一致(而不是恒为训练关)。
    if not firing_range and playlist is not None and playlist in COOP_PLAYLIST_MAP:
        map_name = COOP_PLAYLIST_MAP[playlist]
    # ★ 2026-10-07: 允许用 coop_map.txt 覆盖（不影响靶场分支）
    if not firing_range:
        _ov = _coop_map_override()
        if _ov:
            map_name = _ov
    if game_type_override is not None:
        game_type = int(game_type_override)
    if map_override:
        map_name = str(map_override)
    ob = Buf()
    ob.blob(bytes(addr))                            # 1 地址 blob
    ob.blob(MISSION_SESSION_ID_BLOB)                # 2 SessionId
    ob.u32(0); ob.u32(0); ob.u32(1)                 # 3-5 Players = 1
    ob.string(map_name)                             # 6 map
    ob.u64(1)                                       # 7
    ob.string("localhost")                          # 8 hostname
    pl_val = playlist if playlist is not None else (1 if firing_range else 1)
    ob.i32(game_type); ob.i32(pl_val); ob.i32(0)
    ob.u32(0xFFFFFFFF)                              # 12 LicenseType
    ob.i32(0); ob.i32(0); ob.i32(0)                 # 13-15
    ob.blob(b"")                                    # 16 空 blob
    ob.i32(max_players)                             # 17 MaxPlayers
    for _ in range(10):                             # 18-27
        ob.i32(0)
    ob.u64(1)                                       # 28
    for _ in range(5):                              # 29-33
        ob.i32(0)
    return ob.data()


def build_balance_object(currency, amount):
    """钱包对象 —— 照抄 ol-mod MarketplaceService.cpp:448-451 / :428-431:
        writeU8(type) + writeU32(amount) = 03 <type> 08 <u32 amount>。"""
    return bytes([T_U8, currency & 0xFF, T_U32]) + struct.pack("<I", amount & 0xFFFFFFFF)


def parse_u32_tagged(d, off=0):
    """读一个带 tag 的 u32(0x08); 返回 (值, 新偏移) 或 (None, off)。"""
    if off + 5 > len(d) or d[off] != T_U32:
        return None, off
    return struct.unpack_from("<I", d, off + 1)[0], off + 5


# ============================================================ 会话密钥派生(KDF)
# ★ 本轮借鉴 ol-mod 的核心: 逆出密钥派生, 从此不必读游戏内存(nt10 快照)。
#
# 出处: ol-mod src/backend/Demonware/Crypto.cpp:153-216(expandKey / deriveSessionKeys)
#       + LobbyProtocol.cpp:58-114(authInfo 位布局 / sessionKey 来源)
#       + LobbyProtocol.cpp:330-378(transcript 组装)
#
# 一句话: 会话根密钥**来自客户端自己的 0x82 帧**(authInfoData[0..24]) ——
#   auth3 下发的 128B server ticket 前 24B 就是 key, 客户端原样转发。
#   两个客户端会拿到不同密钥, 所以任何"单一共享值"都不可能工作(对方源码 65-70 行注释).
#
# transcript = clientHello[8:28] + ServerHeaderAck(26B) + clientAuth[0:-8]
#   注意: ServerHeaderAck 用的是**服务端实际发出的那 26 字节**(对方用固定常量,
#         我们用自己的 0x81 应答 —— 客户端拿到什么就哈希什么)。
# secret   = HMAC-SHA1(key=transcriptHash, data=sessionKey)
#   ★ 对方 hmacSha1(data, key) 的参数序是 (data, key); 调用 hmacSha1(sessionKey, transcriptHash)
#     等价于 key=transcriptHash / data=sessionKey。已用其已知答案向量验证。
# challenge = expandKey(secret, "CLIENTCHAL", 16)
# data      = expandKey(secret, "BDDATA",     72)
#   responseId   = challenge[8:16]     -> 0x83 里那 8 字节(不用再读内存!)
#   requestHmac  = data[0:20]          -> 校验客户端帧(= 我们的 hmac_out)
#   responseHmac = data[20:40]         -> 签我们的应答(= hmac_in)
#   decrypt      = data[40:56]         -> 解客户端帧(= aes_out)
#   encrypt      = data[56:72]         -> 加密我们的应答(= aes_in)
#
# ⚠️ 实测结论(2026-10-03, 用 kdf_probe.py 复盘真实会话):
#   1. 算法本身**正确** —— 逐字段复现对方的已知答案向量(DemonwareTests.cpp:2455-2478);
#   2. `session_key_from_client_auth()` 的位布局**正确** —— 从我们自己的会话里解出的
#      sessionKey 正是我方 /auth/ 伪造票据的前 24 字节(`DE AD BD EF` + 公式);
#   3. 字符串 `CLIENTCHAL`/`BDDATA` 在**我们 build 的代码里确实存在**
#      (运行时解壳段 0xD5A4E0 / 0xD5A4E8, 见 n10*_exe_d5a.bin);
#   4. **但这个配方的输入与我们的 build 不同**: 用票据的全部 24B 窗口 × 12 种 transcript
#      × 2 种 HMAC 参数序 × 2 种 label 序 = 5040 组穷举, 与真实内存密钥**全部不命中**。
#   => 所以本文件提供的派生函数目前只用于**诊断/互校**; 生效的密钥来源仍是 nt10 内存快照。
#      一旦某天对上, lobby_server 的日志会打 "★ 与内存快照完全一致"。

AUTH_INFO_BYTES = 139          # 客户端 0x82 帧里 authInfo 的长度(定长)
SERVER_HEADER_ACK = bytes.fromhex(
    "16000000" "AB81" "D2000000" "70E2FDC0" "B66A3492" "7179FCB0" "85931651")
# = u32 22 | AB 81 | D2 00 00 00 | 8B | 8B | 8B   —— 真机(ol-mod)的服务端 0x81 常量


def sha1(data):
    return hashlib.sha1(data).digest()


def hmac_sha1(key, data):
    return hmac.new(key, data, hashlib.sha1).digest()


def expand_key(secret, label, size):
    """照抄 ol-mod Crypto.cpp:153-173 expandKey:
        block_i = HMAC-SHA1(key=secret, data=prev || label || counter), counter 从 1 递增, 拼接后截断。"""
    if isinstance(label, str):
        label = label.encode("ascii")
    out = bytearray()
    prev = b""
    counter = 1
    while len(out) < size:
        prev = hmac_sha1(secret, prev + label + bytes([counter & 0xFF]))
        counter += 1
        out += prev
    return bytes(out[:size])


def derive_session_keys(session_key, transcript):
    """照抄 ol-mod Crypto.cpp:197-216 deriveSessionKeys。返回 dict。"""
    if len(session_key) != 24:
        raise ValueError("DW session key 必须是 24 字节, 实际 %d" % len(session_key))
    transcript_hash = sha1(transcript)
    secret = hmac_sha1(transcript_hash, session_key)   # key=transcriptHash, data=sessionKey
    challenge = expand_key(secret, b"CLIENTCHAL", 16)
    data = expand_key(secret, b"BDDATA", 72)
    return {
        "secret": secret,
        "challenge": challenge,
        "response_id": challenge[8:16],       # 0x83 的 8 字节
        "request_hmac": data[0:20],           # = hmac_out
        "response_hmac": data[20:40],         # = hmac_in
        "decrypt": data[40:56],               # = aes_out
        "encrypt": data[56:72],               # = aes_in
    }


def ticket_from_client_auth(frame):
    """从客户端 0x82 帧里取出**被转发的 128B 票据**(跳过 83 bit, LSB-first 读 128B)。

    authInfo 位布局(同 ol-mod LobbyProtocol.cpp:89-114):
        serviceId 8 | unknown 1 | titleId 5+32 | ivSeed 5+32 | authInfoData 1024(128B)
    → 数据起点 = bit 83(不是字节对齐)。
    """
    off = 6
    if len(frame) < off + AUTH_INFO_BYTES:
        return None
    ai = frame[off:off + AUTH_INFO_BYTES]
    pos = 8 + 1 + (5 + 32) + (5 + 32)
    out = bytearray()
    for _ in range(128):
        v = 0
        for i in range(8):
            v |= ((ai[(pos + i) // 8] >> ((pos + i) % 8)) & 1) << i
        pos += 8
        out.append(v)
    return bytes(out)


def session_key_from_ticket(ticket):
    """会话密钥 = 票据偏移 **97..121**（24B）。

    ★ 2026-10-03 实测（HANDOFF §10.9）：客户端 HMAC(0xBA0D20) 的 data 就是这 24 字节,
      **不是**票据开头的 `DE AD BD EF`（那只是魔数）。
      这也正好对上 ol-mod 自己 `makeTicket()` 的布局（会话密钥写在 97..120）。
    """
    return bytes(ticket[97:121]) if ticket and len(ticket) >= 121 else b""


def session_key_from_client_auth(frame):
    """从 0x82 帧取会话密钥(= 票据[97:121])。"""
    t = ticket_from_client_auth(frame)
    return session_key_from_ticket(t) if t else None


def build_transcript(hello28, server_ack26, client_auth_frame):
    """transcript = hello[8:28] + 服务端实际发出的 0x81(26B) + clientAuth[:-8]。"""
    return bytes(hello28[8:28]) + bytes(server_ack26) + bytes(client_auth_frame[:-8])


def build_task_reply_objects(aes_in, hmac_in, seq_out, task, reply_id,
                             objects=(), status=0):
    """构造 0x85 任务应答(照抄 BuildTaskReplyObjects)。
    objects 是一串"结果对象"的原始字节(可为空)。"""
    inner = bytearray()
    inner += bytes([10]) + struct.pack("<Q", reply_id)
    inner += bytes([8]) + struct.pack("<I", status)
    inner += bytes([3, task & 0xFF])
    inner += bytes([8]) + struct.pack("<I", len(objects))
    if objects:
        inner += bytes([8]) + struct.pack("<I", len(objects))
        for o in objects:
            inner += o
    n = (5 + len(inner) + 15) // 16 * 16
    plain = bytearray(n)
    struct.pack_into("<I", plain, 0, len(inner))
    plain[4] = 1
    plain[5:5 + len(inner)] = inner
    iv = os.urandom(16)
    enc = cbc_encrypt(aes_in, iv, bytes(plain))
    fr = bytearray(26 + len(enc) + 8)
    struct.pack_into("<I", fr, 0, len(fr) - 4)
    fr[4] = MARK
    fr[5] = KIND_TASK
    struct.pack_into("<I", fr, 6, seq_out)
    fr[10:26] = iv
    fr[26:26 + len(enc)] = enc
    fr[-8:] = hmac8(hmac_in, bytes(fr[:-8]))
    return bytes(fr)


def build_task_reply(aes_in, hmac_in, seq_out, task, reply_id, status=0, objects=()):
    """单对象/空对象的便捷版。"""
    return build_task_reply_objects(aes_in, hmac_in, seq_out, task, reply_id,
                                    objects, status)


# --------------------------------------------------- 服务端主动推送(类型 2)
# 出处: ol-mod LobbyProtocol.cpp queuePush / InstantMessageService.cpp:179-184
#       / Unknown0BService.cpp:212-219。壳与任务应答完全一样(0x85), 只有明文里的
#       marker 从 0x01(应答) 变成 0x02(推送) —— 客户端据此走 push 分发。
def build_push(aes_in, hmac_in, seq_out, body, message_type=2):
    """构造一条服务端推送帧(同 0x85 壳, 明文 marker = message_type)。"""
    n = (5 + len(body) + 15) // 16 * 16
    plain = bytearray(n)
    struct.pack_into("<I", plain, 0, len(body))
    plain[4] = message_type & 0xFF
    plain[5:5 + len(body)] = body
    iv = os.urandom(16)
    enc = cbc_encrypt(aes_in, iv, bytes(plain))
    fr = bytearray(26 + len(enc) + 8)
    struct.pack_into("<I", fr, 0, len(fr) - 4)
    fr[4] = MARK
    fr[5] = KIND_TASK
    struct.pack_into("<I", fr, 6, seq_out)
    fr[10:26] = iv
    fr[26:26 + len(enc)] = enc
    fr[-8:] = hmac8(hmac_in, bytes(fr[:-8]))
    return bytes(fr)


def instant_push_body(sender_id, sender_name, message, kind=21, use_types=True):
    """即时消息推送**信封** —— 与 C# BuildPushFrameWithSender **逐字节一致**。

    C# 权威格式(CodolLocalLobbyServer.cs:503-517):
        08 <u32 service> | 0A <u64 senderId> | 10 <senderName 的 ASCII> 00
        | 13 08 <u32 len> <data>
    ——即**信封带 tag**, 只有最内层 data 由调用方决定是否带 tag。

    ol-mod decodeInstantPush 的 `[u32 21][u64 senderId][string name][blob message]`
    与之等价: 这里的 `kind` 就是 C# 的第一个字段 `service`(它同时是 type 21 = InstantMessage),
    `Buf(use_types=True)` 会写出 08/0A/10/13 08 这些 tag, 与 C# 完全对齐(已核对, 无需改)。

    ⚠️ 它输出的就是 `build_push(..., body)` 的 `body`(marker=2 由 build_push 补)。
    """
    ob = Buf(use_types)
    ob.u32(kind)                    # = C# 的 service(21)
    ob.u64(sender_id)
    ob.string(sender_name)
    ob.blob(message if isinstance(message, bytes) else message.encode("utf-8"))
    return ob.data()


def channel_push_body(sender_id, sender_name, channel_id, message,
                      whisper=False, msg_type=0, use_types=False):
    """频道推送体 —— 照抄 ol-mod Unknown0BService.cpp:212-219

    ⚠️★ **已废弃, 勿用(不再用于任何新路径)** —— 2026-10-03 实测: 这条推送体一发,
       客户端**立刻断连**(带 tag 时同秒 reset; 改无 tag 也只是多活几秒, 见 HANDOFF §13.4-13.7)。
       保留此函数仅为留存实验记录 / 可能的历史调用(仅 `ready_push.on` 那条默认关闭的老路径),
       新的推送一律走 `instant_push_body`(其信封 = C# BuildPushFrameWithSender)。
       若将来要再碰频道推送, 不要靠猜字段序, 应从 `decodeChannelPush` 严格反推。

    字段: [u32 (whisper?7:8)][u64 senderId][string senderName][u64 channelId][blob message][u32 msg_type]
    """
    ob = Buf(use_types)
    ob.u32(7 if whisper else 8)
    ob.u64(sender_id)
    ob.string(sender_name)
    ob.u64(channel_id)
    ob.blob(message if isinstance(message, bytes) else message.encode("utf-8"))
    ob.u32(msg_type)
    return ob.data()


# 房间 ready 批次的 16 字节常量 —— 照抄 ol-mod Unknown0BService.cpp:98-101。
ROOM_READY_BATCH = bytes.fromhex("0C00000002020000 0008000000800800".replace(" ", ""))

# ★★ 开局(game start)推送体 —— 逐字节照抄三方 CodolLocalLobbyServer.cs:1419-1430
#   的 `gameStartData`(162 字节)。触发条件: 客户端 `0B/4 setRoomData` 的 payload[11]==0x15
#   (即"点准备"), 三方在此**紧接着频道回显**再推这一条, 客户端才会进入加载/连战斗服。
#   推送封装 = BuildPushFrame(seq, service=11, data) → 即 instant_push_body(0, "Server", data, kind=11)。
#
#   ⚠️ 2026-10-07: 这条 162B 是三方从 firingrange 抓到的常量。实机确认
#   `plain[11]==0x15` 触发 + 推送都成功, 但 PvE coop 客户端仍停在“战斗开始”,
#   战斗服 0 收包。因此它**不是已验证的 coop 开局数据**; 下一步要么桥接 mmstart
#   到 battle_server, 要么替换成真实 coop gameStartData。
GAME_START_PAYLOAD = bytes.fromhex(
    "0A011000000000000013088500000081"
    "0000000204000000A4010000181802000000"
    "467D09D8AF02F807F8070000F807F807"
    "0000F807F8070000F807F8070000F807"
    "F8070000F807F8070000F807F8070000"
    "F807F8070000F807F8070000F807F807"
    "00E84BFA9A138B1740000000187A237A"
    "72634B73830000001848107828384800"
    "08485020304068580050000000706100"
    "00000000000000000000080100000000"
)
assert len(GAME_START_PAYLOAD) == 162, len(GAME_START_PAYLOAD)


def build_handshake_reply(hello28):
    """服务端 0x81 应答(照抄三方): u32 22 | 00 | 81 | u32 0xDC | 8B 随机 | 8B(=hello[20:28])。"""
    fr = bytearray(26)
    struct.pack_into("<I", fr, 0, 22)
    fr[4] = 0x00
    fr[5] = 0x81
    struct.pack_into("<I", fr, 6, 0xDC)
    fr[10:18] = os.urandom(8)
    fr[18:26] = hello28[20:28] if len(hello28) >= 28 else os.urandom(8)
    return bytes(fr)


def build_stage2(challenge8):
    """服务端 0x83(照抄三方): u32 10 | 00 | 83 | 8B challenge。"""
    fr = bytearray(14)
    struct.pack_into("<I", fr, 0, 10)
    fr[4] = 0x00
    fr[5] = 0x83
    fr[6:14] = challenge8[:8]
    return bytes(fr)


# ------------------------------------------------------------------ 自 测
if __name__ == "__main__":
    key = bytes(range(16))
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    want = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    got = _encrypt_block(_expand_key(key), pt)
    print("FIPS-197 AES-128 加密 : %s  %s" % (got.hex(), "OK" if got == want else "!! 失败"))
    back = _decrypt_block(_expand_key(key), got)
    print("FIPS-197 AES-128 解密 : %s  %s" % (back.hex(), "OK" if back == pt else "!! 失败"))

    iv = bytes(range(16, 32))
    data = bytes(range(32))
    c = cbc_encrypt(key, iv, data)
    print("CBC 往返              : %s" % ("OK" if cbc_decrypt(key, iv, c) == data else "!! 失败"))

    k1, k2 = os.urandom(16), os.urandom(20)
    fr = build_task_reply(k1, k2, 7, 0x04, 0x1122334455667788)
    d = decrypt_task_frame(fr, k1, k2)
    print("帧往返                : hmac_ok=%s seq=%s service=%s task=%s declared=%s"
          % (d["hmac_ok"], d["seq"], d["service"], d["task"], d["declared"]) if d
          else "帧往返                : !! 失败")
    frames, rest = parse_frames(fr + b"\x00\x00\x00\x00" + fr[:10])
    print("分帧                  : %d 帧, 剩余 %d 字节" % (len(frames), len(rest)))

    # --- 借鉴 ol-mod: session 记录必须逐字节对齐其导出样本(FULL A, 258 字节) ---
    FULL_A = (
        "1308250000007F000001207100FF00FF000000FF00FF000000FF00FF000000FF00FF00007F0000012071"
        "01130808000000887766554433221108000000000812000000080100000010"
        "31343332373738363333000A41420F0000000000106D705F63726173685F74726F706963616C00"
        "07ABAD92D6070000000007000000000700000000070000000007000000000700000000"
        "130810000000000102030405060708090A0B0C0D0E0F"
        "071300000007000000000700000000070800000007FFFFFFFF071C030000071E000000"
        "070000000007070000000700000000"
        "0701E00D0C0A41420F000000000007000000000700000000070000000007010000000700000000"
    )
    got = build_session_record(0x1122334455667788, (127, 0, 0, 1), 28960,
                               game_type=0, max_players=18, current_players=1,
                               map_name="mp_crash_tropical",
                               security_key=bytes(range(16)))
    want = bytes.fromhex(FULL_A)
    print("session 记录(258B)    : 长度=%d 期望=%d  %s"
          % (len(got), len(want), "OK" if got == want else "!! 不一致"))
    if got != want:
        for i in range(min(len(got), len(want))):
            if got[i] != want[i]:
                print("  首个差异 @0x%02X: got=%02X want=%02X" % (i, got[i], want[i]))
                break
    # 门槛自检: roomId 非零十进制 / host uid != 玩家 CODOID
    rid = (0x1122334455667788 & 0x7FFFFFFF) | 1
    print("  门槛: roomId=%s(非零十进制=%s) hostUid=%d"
          % (rid, str(rid).isdigit() and rid != 0, ROOM_HOST_UID))
    print("commonAddr 长度       : %d (应 37)" % len(bd_common_addr((127, 0, 0, 1), 28960)))
    print("钱包对象 03/08        : %s" % build_balance_object(1, 985699).hex(" "))

    # --- 21/5 mission session 对象: 靶场 / 普通(C# BuildMissionSessionObject) ---
    fr_obj = build_mission_session_object(True)
    nm_obj = build_mission_session_object(False)
    print("21/5 靶场 session 对象: 长度=%d 头48B=%s" % (len(fr_obj), fr_obj[:48].hex(" ")))
    print("21/5 普通 session 对象: 长度=%d 头48B=%s" % (len(nm_obj), nm_obj[:48].hex(" ")))
    print("  field1 头(靶场/普通) : %s / %s   (应 '13 08 43' / '13 08 18'; 0x13=tagblob)"
          % (fr_obj[:3].hex(" "), nm_obj[:3].hex(" ")))
    print("  靶场 GameType(07 07 00 00 01) 在流里 : %s"
          % ("07 07 00 00 01" in fr_obj.hex(" ")))
    print("  普通 GameType(07 03 00 00 01) 在流里 : %s"
          % ("07 03 00 00 01" in nm_obj.hex(" ")))
    print("  靶场 MaxPlayers(1) / 普通(4) 字段     : %s / %s"
          % ("07 01 00 00 00" in fr_obj.hex(" "), "07 04 00 00 00" in nm_obj.hex(" ")))

    # --- booking 推送帧: C# BuildFiringRangeBookingAccepted + BuildPushFrameWithSender ---
    accepted = struct.pack("<I", len(b"mmbook accepted\x00")) + b"mmbook accepted\x00"
    bk_body = instant_push_body(1, "localhost", accepted)          # service=21, sender=1
    bk_frame = build_push(k1, k2, 1000, bk_body, 2)
    bd = decrypt_task_frame(bk_frame, k1, k2)
    # 推送明文的布局是 u32 len | 0x02 | body(与客户端任务帧 0x86 布局不同),
    # 所以手工按明文核对: body = plain[5 : 5+declared]
    inner = bd["plain"][5:5 + bd["declared"]] if bd else b""
    ok = bool(bd) and bd["hmac_ok"] and bd["marker"] == 2 and inner == bk_body
    print("booking 推送帧        : %s  marker=%s declared=%s hmac=%s body(手工解)==信封:%s"
          % ("OK" if ok else "!! 失败", bd and bd["marker"], bd and bd["declared"],
             bd and bd["hmac_ok"], inner == bk_body))
    print("  信封(前32B)         : %s" % bk_body[:32].hex(" "))
    print("  内层 data(裸 20B)   : %s" % accepted.hex(" "))

    # --- 借鉴 ol-mod: deriveSessionKeys 的已知答案向量(KAT) ---
    # 出处 ol-mod tests/backend/DemonwareTests.cpp:2455-2478
    SK = b"Shippo fuute, mofu-mofu!"          # 24B
    TR = bytes(range(64))
    exp = {
        "response_id": "ea09fd53518d4361",
        "request_hmac": "96548bb09f4bd93996465628b618c9d3ec09ddd5",
        "response_hmac": "4395bd6340aa21bc95d9b77db1c04afc67061382",
        "decrypt": "71120733ba54e6ff13ded72c69deca7f",
        "encrypt": "b1adf0f2663cde670df4f20fbe37fc2e",
    }
    try:
        k = derive_session_keys(SK, TR)
        ok = all(k[n].hex() == v for n, v in exp.items())
        print("deriveSessionKeys KAT : %s" % ("OK" if ok else "!! 不一致"))
        for n, v in exp.items():
            if k[n].hex() != v:
                print("    %-13s got=%s want=%s" % (n, k[n].hex(), v))
        if not ok:
            # 参数序存疑时给出另一种解释的结果, 便于定位
            alt = hmac_sha1(SK, sha1(TR))
            c2 = expand_key(alt, b"CLIENTCHAL", 16)
            d2 = expand_key(alt, b"BDDATA", 72)
            print("    [备选 key=sessionKey] responseId=%s decrypt=%s"
                  % (c2[8:16].hex(), d2[40:56].hex()))
    except Exception as e:
        print("deriveSessionKeys KAT : !! 异常 %r" % (e,))
    print("SERVER_HEADER_ACK     : %d 字节 %s" % (len(SERVER_HEADER_ACK), SERVER_HEADER_ACK.hex(" ")))
