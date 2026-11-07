# -*- coding: utf-8 -*-
"""battle_server.py —— 战斗服（UDP 127.0.0.1:28960）。

逐条移植三方 `success/codol/dist/launcher_src/tools/firingrange-test/src/`：
  · ``CodolLocalBattleServer.cs``  —— 握手 / netchan / 游戏状态 / 快照调度
  · ``CodolBattleKeyExchange.cs``  —— ECDH P-224 + 传输密钥派生

协议（实测 2026-10-04：客户端确实按这个顺序来，`battle_srv.log` 收到 type=1 的 16B 包）
------------------------------------------------------------------------------------
1) **NAT 遍历**   29B，首字节 13 → 回同包但首字节改 12
2) **DTLS init**  16B：``01 02 0000 0000 clientTag(2) 01 00 00 00 00 00 00 00``
                  → 回 **38B cookie**（含 serverTag / 本机 IP:port / u64 1）
3) **cookie+公钥** 219B：``03 02 serverTag(2) | cookie(38B) | ...(67B) | u64 1 | 公钥(100B)``
                  → 派生传输密钥 → 回 **114B key-exchange ack**（含服务端公钥 100B）
4) **数据帧**     ``06 02 serverTag(2) seq(2) hmac(8) len(2) cipher``（AES 流 + HMAC-SHA1 前 8B）

密钥派生：ECDH P-224 → 共享 x 坐标 **28B 大端** ‖ securityKey(16B) = 44B → **SHA1** → 20B
         → 补 4 个 0 成 24B（AES 用前 16B，HMAC 用全部 24B）。
★ securityKey = **16 个 0x01**（不是 0）：C# 注释 *"Build 1649370's live security-key map
  retained the 0x01 default for ID 1 despite the empty lobby blob (verified by v10 data MAC)"*。

用法:
  python battle_server.py                 # 127.0.0.1:28960
"""
import argparse
import hashlib
import hmac
import math
import os
import random
import socket
import struct
import sys
import time

import codol_crypto as cc

OUTDIR = os.path.dirname(os.path.abspath(__file__))
LOGF = os.path.join(OUTDIR, "battle_srv.log")
GAMESTATE_FILE = os.path.join(OUTDIR, "firingrange-gamestate.bin")
# ★ 客户端移动权威开关（2026-10-04）：存在时，非首帧快照**省略位置/速度**字段，
#   让客户端用它自己的预测+真实碰撞移动 —— 消除"服务端粗糙积分无碰撞"造成的橡皮筋。
CLIENT_MOVEMENT_FLAG = os.path.join(OUTDIR, "client_movement.on")
# ★ 出生点实验开关（2026-10-04）：存在时**连首帧也省略位置** → 客户端保留**地图自带的出生点**。
#   用途：验证"(48,-572,-116) 这个坐标是错的"（它只是三方未证实的 candidate），
#   并确认客户端到底用不用地图 spawn。见 HANDOFF §13.27。
SPAWN_FROM_MAP_FLAG = os.path.join(OUTDIR, "spawn_from_map.on")
# ★ idx 45 实验开关（2026-10-04）：默认**关**（文件不存在即不发）。见 `_build_motion_snapshot`。
#   背景：官方每帧下发 idx 45（原生 +0xB8），录像 trace 里它 = yaw。宽度已实测为 17 位
#   （1 位 presence + 2 字节），但把 yaw 写进去会让客户端**视角乱转/无法移动** → 语义仍不对。
#   故默认关，保持可用基线；要再做编码实验时 `New-Item idx45.on` 即可。
IDX45_FLAG = os.path.join(OUTDIR, "idx45.on")
# ★ 出生点指定文件（2026-10-04）：`spawn_at.txt` 写一行 "x y z" → **首帧**把位置发成这个坐标，
#   之后照常省略（其余仍走 omit）。用途：`spawn_from_map.on` 让客户端在**地图自带的几十个
#   mp_tdm_spawn 里自己挑**，会挑到几何体/屋顶里 → 卡住走不动。见 HANDOFF §13.35。
SPAWN_AT_FILE = os.path.join(OUTDIR, "spawn_at.txt")
# ★ v32 等价模式（2026-10-04）：`static_spawn.on` 存在时 —— **每帧**都把位置发成 `spawn_at.txt`
#   里的固定坐标（= 参考 launcher 的 `staticPosition=true`）。见 HANDOFF §13.38。
#   v32 的实测行为（Data\battle.log）：`TX_SPAWN_EXPERIMENT … bytes=36 staticPosition=true`、
#   且 `RX_USERCMD … position=48,-572,-116` → 它每帧都发同一个固定点，且**不做模拟**。
STATIC_SPAWN_FLAG = os.path.join(OUTDIR, "static_spawn.on")
# ★ 逐条输入日志（2026-10-04，诊断"移动延迟大"）：存在 `log_inputs.on` 时，把**每一条**解出来的
#   usercmd 都写日志（move 键位 / yaw / dt / 结果位置）——用来看"按住 W 之后，位置到底几百 ms 才动"。
LOG_INPUTS_FLAG = os.path.join(OUTDIR, "log_inputs.on")
_LOG_INPUTS = os.path.exists(LOG_INPUTS_FLAG)      # 启动时判一次即可
# ★ viewangles 省略开关（2026-10-04）：存在 `omit_viewangles.on` → 快照里**不下发 idx 18/19/29**
#   （yaw/pitch/roll），让客户端用自己的视角，消除"回声阻尼"（转 180° 只有 ~20°）。见 §13.43。
OMIT_VIEWANGLES_FLAG = os.path.join(OUTDIR, "omit_viewangles.on")
_OMIT_VIEWANGLES = os.path.exists(OMIT_VIEWANGLES_FLAG)
# ★ 方向诊断（2026-10-04）：`force_dir.txt` 写一个角度(度) → 移动方向**固定用它**、完全忽略 yaw。
#   用途：判断"我们的方向到底有没有传到画面上"。见 §13.44。
FORCE_DIR_FILE = os.path.join(OUTDIR, "force_dir.txt")


def read_force_dir():
    """读 `force_dir.txt`；不存在/格式错 → None（= 正常按 yaw 走）。两种写法：

        "<角度>"        固定方向（度）        —— 如 `0`
        "rot [度/秒]"   方向**缓慢旋转**（默认 20 度/秒）
                        —— 不需要任何参照物：方向若真受我们控制，按住 W 会走一个大圆圈
    """
    try:
        if not os.path.exists(FORCE_DIR_FILE):
            return None
        p = open(FORCE_DIR_FILE, "r", encoding="utf-8").read().replace(",", " ").split()
        if not p:
            return None
        if p[0].lower() in ("rot", "rotate"):
            return ("rot", float(p[1]) if len(p) > 1 else 20.0)
        return ("fix", float(p[0]))
    except Exception:
        return None


_FORCE_DIR = read_force_dir()      # 启动时判一次即可
# ★ 方向换算标定（2026-10-04）：`dir_bias.txt` 写 "<偏移度> [缩放]" → 移动方向 = yaw*缩放 + 偏移。
#   用来校正"视角坐标 ↔ 移动方向"之间的常数差/比例差（用户看到的"偏"）。见 §13.44。
DIR_BIAS_FILE = os.path.join(OUTDIR, "dir_bias.txt")


def read_dir_bias():
    """读 `dir_bias.txt`（"<偏移度> [缩放]"）；不存在/格式错 → None。"""
    try:
        if not os.path.exists(DIR_BIAS_FILE):
            return None
        p = open(DIR_BIAS_FILE, "r", encoding="utf-8").read().replace(",", " ").split()
        bias = float(p[0])
        scale = float(p[1]) if len(p) > 1 else 1.0
        return (bias, scale)
    except Exception:
        return None


_DIR_BIAS = read_dir_bias()
# ★ 镜像客户端预测态（2026-10-04，B 路线）：存在 `mirror_predicted.on` 时，战斗服改成**回发客户端
#   自己算的那份 predicted playerstate**（由 nt10 的 [PS] 探针 20ms 定点写 `predicted.bin`）。
#   实测：该结构与"回声我们快照"的权威态不同 —— z=-99.63(非-116)、带下落速度、pm_flags=0x2020。
#   ⇒ 方向(视角为前方)/碰撞/重力 全在它里面。见 HANDOFF §13.47。
MIRROR_PRED_FLAG = os.path.join(OUTDIR, "mirror_predicted.on")
_MIRROR_PRED = os.path.exists(MIRROR_PRED_FLAG)
PRED_FILE = os.path.join(OUTDIR, "predicted.bin")
# ★ 镜像前导补偿（2026-10-04）：镜像回发的是"20ms 前"的客户端预测值 ⇒ 客户端被往回拽(抖动/穿墙/延迟感)。
#   `pred_lead_ms.txt` 写毫秒数 → 回发时沿预测速度**外推**掉这段延迟。默认 50ms。
PRED_LEAD_FILE = os.path.join(OUTDIR, "pred_lead_ms.txt")


def read_pred_lead():
    """pred_lead_ms.txt：前导补偿毫秒数（默认 50ms）。"""
    try:
        if os.path.exists(PRED_LEAD_FILE):
            return float(open(PRED_LEAD_FILE, "r", encoding="utf-8").read()
                         .replace(",", " ").split()[0]) / 1000.0
    except Exception:
        pass
    return 0.05


_PRED_LEAD = read_pred_lead()
# ★ tick 率（2026-10-04）：快照下发间隔 = 1/tick_hz。默认 **128 tick ≈ 7.8ms**
#   （用户指定"采样 128tick"）—— 镜像链越快，客户端被往回拽的窗口越小。
TICK_HZ_FILE = os.path.join(OUTDIR, "tick_hz.txt")


def read_tick_hz():
    try:
        if os.path.exists(TICK_HZ_FILE):
            v = float(open(TICK_HZ_FILE, "r", encoding="utf-8").read()
                      .replace(",", " ").split()[0])
            if 1.0 <= v <= 1000.0:
                return v
    except Exception:
        pass
    return 128.0


_TICK_HZ = read_tick_hz()
# ★ 快照下发频率（可与探针 tick 分开）：`snap_hz.txt`（默认 = tick_hz）。
#   理由：位置纠正越频繁，"回声过期值→客户端重新播种预测"的打架越频繁；
#   参考 launcher v32 实测只有 ~3.3 Hz 且位置是对的。见 HANDOFF §13.52。
SNAP_HZ_FILE = os.path.join(OUTDIR, "snap_hz.txt")


def read_snap_hz():
    try:
        if os.path.exists(SNAP_HZ_FILE):
            v = float(open(SNAP_HZ_FILE, "r", encoding="utf-8").read()
                      .replace(",", " ").split()[0])
            if 1.0 <= v <= 1000.0:
                return v
    except Exception:
        pass
    return _TICK_HZ


_SNAP_HZ = read_snap_hz()
_SNAP_DT = 1.0 / _SNAP_HZ
_pred_state = {"seq": None, "t": 0.0}
_mirror_miss = {"n": 0}          # 镜像开启但 predicted.bin 不可用的连续帧数（用于告警）


def read_predicted():
    """读 nt10 写的 predicted.bin（<6f>x,y,z,vx,vy,vz + <I>seq）。

    ★ 过期判据（2026-10-04 事故修复）：**必须看文件自身的 mtime**。
      之前只看"seq 有没有变"，于是上一轮残留的文件在**本轮启动后会被当成新数据用满 1 秒**
      —— 而出生点正是那第一秒决定的，一旦用错就再也回不来
      （现象：出生点在别处、跳不起来、爬不上去、朝向乱）。见 HANDOFF §13.53。
    """
    try:
        if not os.path.exists(PRED_FILE):
            return None
        now = time.time()
        if now - os.path.getmtime(PRED_FILE) > 0.5:      # 文件本身是旧的 → 一律不采信
            return None
        raw = open(PRED_FILE, "rb").read()
        if len(raw) < 28:
            return None
        x, y, z, vx, vy, vz, seq = struct.unpack("<6fI", raw[:28])
        if seq != _pred_state["seq"]:
            _pred_state["seq"] = seq
            _pred_state["t"] = now
        elif now - _pred_state["t"] > 0.5:
            return None                       # 探针停了 → 别用陈旧值
        for v in (x, y, z, vx, vy, vz):
            if v != v or abs(v) > 100000.0:
                return None
        if x == 0.0 and y == 0.0 and z == 0.0:
            return None
        return (x, y, z, vx, vy, vz)
    except Exception:
        return None


def read_spawn_at():
    """读 `spawn_at.txt`（一行 "x y z"，空格或逗号分隔）；不存在/格式错 → None。"""
    try:
        if not os.path.exists(SPAWN_AT_FILE):
            return None
        parts = open(SPAWN_AT_FILE, "r", encoding="utf-8").read().replace(",", " ").split()
        if len(parts) < 3:
            return None
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception:
        return None

# ------------------------------------------------------------------ P-224 (secp224r1)
P224_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF000000000000000000000001
P224_A = P224_P - 3
P224_B = 0xB4050A850C04B3ABF54132565044B0B7D7BFD8BA270B39432355FFB4
P224_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF16A2E0B8F03E13DD29455C5C2A3D
P224_GX = 0xB70E0CBD6BB4BF7F321390B94A03C1D356C21122343280D6115C1D21
P224_GY = 0xBD376388B5F723FB4C22DFE6CD4375A05A07476444D5819985007E34
P224_G = (P224_GX, P224_GY)


def _pt_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P224_P == 0:
        return None
    if p1 == p2:
        if y1 == 0:
            return None
        lam = (3 * x1 * x1 + P224_A) * pow(2 * y1, P224_P - 2, P224_P) % P224_P
    else:
        lam = (y2 - y1) * pow((x2 - x1) % P224_P, P224_P - 2, P224_P) % P224_P
    x3 = (lam * lam - x1 - x2) % P224_P
    y3 = (lam * (x1 - x3) - y1) % P224_P
    return (x3, y3)


def _pt_mul(k, p):
    r = None
    while k:
        if k & 1:
            r = _pt_add(r, p)
        p = _pt_add(p, p)
        k >>= 1
    return r


def gen_keypair():
    d = random.randrange(1, P224_N)
    return d, _pt_mul(d, P224_G)


def _der_uint(raw28):
    """把 28B 大端坐标编成 DER INTEGER（去前导 0、必要时补 0x00）。"""
    i = 0
    while i < len(raw28) - 1 and raw28[i] == 0:
        i += 1
    v = raw28[i:]
    body = (b"\x00" if (v[0] & 0x80) else b"") + v
    return b"\x02" + bytes([len(body)]) + body


def export_pubkey(pub):
    """100 字节 libtomcrypt 公钥：``30 <len> 03 02 07 00 02 01 1C <X> <Y>``。"""
    dx = _der_uint(pub[0].to_bytes(28, "big"))
    dy = _der_uint(pub[1].to_bytes(28, "big"))
    out = bytearray(100)
    out[0] = 0x30
    out[1] = 7 + len(dx) + len(dy)
    out[2:9] = bytes([3, 2, 7, 0, 2, 1, 28])
    out[9:9 + len(dx)] = dx
    out[9 + len(dx):9 + len(dx) + len(dy)] = dy
    return bytes(out)


def import_pubkey(b):
    """解 100 字节公钥 → (x, y) 整数；失败抛 ValueError。"""
    if len(b) != 100 or b[0] != 0x30:
        raise ValueError("ECC input sizes")
    end = b[1] + 2
    if end > 100 or end < 9 or b[2:9] != bytes([3, 2, 7, 0, 2, 1, 28]):
        raise ValueError("ECC public key header")
    pos = 9

    def rd():
        nonlocal pos
        if pos + 2 > end or b[pos] != 2:
            raise ValueError("ECC integer tag")
        pos += 1
        ln = b[pos]
        pos += 1
        if ln < 1 or ln > 29 or pos + ln > end or (b[pos] & 0x80):
            raise ValueError("ECC coordinate length/sign")
        skip = 1 if ln == 29 else 0
        if skip and b[pos] != 0:
            raise ValueError("ECC coordinate exceeds P224")
        seg = b[pos + skip:pos + ln]
        pos += ln
        v = bytearray(28)
        v[28 - len(seg):] = seg
        return int.from_bytes(bytes(v), "big")

    x = rd()
    y = rd()
    if pos != end:
        raise ValueError("ECC trailing fields")
    return x, y


def derive_transport_key(peer_pub100, security_key16):
    """C# Courve: ECDH → 共享 x 28B 大端 ‖ securityKey(16B) → SHA1 → 24B（后 4B 为 0）。"""
    priv, _ = _SESSION_KEY
    px, py = import_pubkey(peer_pub100)
    shared = _pt_mul(priv, (px, py))
    if shared is None:
        raise ValueError("ECDH degenerate")
    raw = shared[0].to_bytes(28, "big")     # 等价 C# 的 Array.Reverse(CNG 小端)
    return hashlib.sha1(raw + security_key16).digest() + b"\x00" * 4


# ------------------------------------------------------------------ AES 流（CTR 计数 = SHA1(seed)）
def _keystream_xor(key16, seed6, data):
    w = cc._expand_key(key16)
    counter = bytearray(hashlib.sha1(seed6).digest())
    out = bytearray(data)
    for off in range(0, len(out), 16):
        blk = cc._encrypt_block(w, bytes(counter))
        for j in range(min(16, len(out) - off)):
            out[off + j] ^= blk[j]
        for j in range(16):
            counter[j] = (counter[j] + 1) & 0xFF
            if counter[j]:
                break
    return bytes(out)


# ------------------------------------------------------------------ 全局状态
_SESSION_KEY = (0, None)        # 本进程的 P-224 私钥/公钥（一次生成，所有会话共用）
_COOKIE_KEY = os.urandom(16)    # 只用于 cookie 里那 4B 签名（C#: 本地自校验，客户端不回验）
COOKIES = {}                    # peer -> 38B cookie
ASSOCS = {}                     # peer -> dict


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    # ★ 加固（2026-10-04 事故）：战斗服由 run_all 启动时 stdout 被重定向到文件，
    #   控制台代码页是 GBK —— 日志里只要出现一个 GBK 编不出的字符（如 U+26A0 ⚠），
    #   `print` 就会抛 UnicodeEncodeError **把整个战斗服打死**（表现为客户端"等待连接"）。
    #   这里两层兜底：先按 UTF-8 写 stdout（换掉 GBK 编解码器），再退到 errors="replace"。
    try:
        buf = getattr(sys.stdout, "buffer", None)
        if buf is not None:
            buf.write(line.encode("utf-8", "replace") + b"\n")
            buf.flush()
        else:
            print(line, flush=True)
    except Exception:
        try:
            print(line.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def read_security_key():
    """16B securityKey —— 三方实测客户端用的是 **全 0x01**（不是 0），见文件头说明。"""
    p = os.path.join(OUTDIR, "battle_security_key.txt")
    try:
        with open(p, encoding="utf-8") as f:
            h = f.read().strip()
        if len(h) == 32 and h != "00" * 16:
            return bytes.fromhex(h)
    except Exception:
        pass
    return b"\x01" * 16


# ------------------------------------------------------------------ ① NAT 遍历
def try_build_nat_reply(pkt):
    if len(pkt) != 29 or pkt[0] != 13 or pkt[1] != 2 or pkt[2] != 0:
        return None
    if pkt[23:29] != bytes([127, 0, 0, 1, 0x20, 0x71]):
        return None
    r = bytearray(pkt)
    r[0] = 12
    return bytes(r)


# ------------------------------------------------------------------ ② DTLS init → cookie(38B)
def try_build_init_ack(pkt, peer):
    if (len(pkt) != 16 or pkt[0] != 1 or pkt[1] != 2 or
            struct.unpack_from("<H", pkt, 2)[0] != 0 or
            struct.unpack_from("<H", pkt, 6)[0] == 0 or
            struct.unpack_from("<Q", pkt, 8)[0] != 1):
        return None
    key = "%s:%d" % peer
    client_tag = struct.unpack_from("<H", pkt, 6)[0]
    cached = COOKIES.get(key)
    if cached and cached[2] == pkt[6] and cached[3] == pkt[7]:
        return cached
    server_tag = random.randrange(1, 0x10000)
    out = bytearray()
    out += b"\x02\x02"
    out += struct.pack("<H", client_tag)
    out += struct.pack("<H", 0)
    out += struct.pack("<I", int(time.monotonic() * 1000) & 0xFFFFFFFF)
    out += b"\x00\x00\x00\x00"
    out += struct.pack("<H", server_tag)
    out += struct.pack("<H", server_tag)
    out += struct.pack("<H", client_tag)
    out += struct.pack("<H", 0)
    out += struct.pack("<H", 0)
    out += socket.inet_aton(peer[0])
    out += struct.pack("<H", peer[1])
    out += struct.pack("<Q", 1)
    assert len(out) == 38, len(out)
    signed = bytearray(28)
    signed[0:4] = out[6:10]
    signed[4:14] = out[14:24]
    signed[14:22] = out[30:38]
    signed[22:28] = out[24:30]
    out[10:14] = hmac.new(_COOKIE_KEY, bytes(signed), hashlib.sha1).digest()[:4]
    cookie = bytes(out)
    COOKIES[key] = cookie
    ASSOCS.pop(key, None)
    return cookie


# ------------------------------------------------------------------ ③ cookie+公钥 → 114B ack
def try_build_key_exchange_ack(pkt, peer, sec_key):
    if len(pkt) != 219 or pkt[0] != 3 or pkt[1] != 2:
        return None
    key = "%s:%d" % peer
    cookie = COOKIES.get(key)
    if cookie is None:
        return None
    if struct.unpack_from("<H", pkt, 2)[0] != struct.unpack_from("<H", cookie, 14)[0]:
        return None
    if bytes(pkt[6:6 + len(cookie)]) != cookie:
        log("REJECT_COOKIE peer=%s" % key)
        return None
    if struct.unpack_from("<Q", pkt, 111)[0] != 1:
        return None
    try:
        pub = export_pubkey(_SESSION_KEY[1])
        transport = derive_transport_key(bytes(pkt[119:219]), sec_key)
    except Exception as e:
        log("REJECT_KEY_EXCHANGE peer=%s reason=%r" % (key, e))
        return None
    ack = bytearray(114)
    ack[0] = 4
    ack[1] = 2
    ack[2] = cookie[2]
    ack[3] = cookie[3]
    ack[6:106] = pub
    ack[106] = 1
    ASSOCS[key] = {
        "key": transport, "cookie": cookie, "peer": peer,
        "send_seq": 0, "netchan_seq": 1, "ready": False,
        "gamestate_attempts": 0, "gamestate_due": 0.0, "gamestate_sent": False,
        "gamestate_loading": False, "cancelled": False,
        # 运动快照: stage 6 后开始，每 25ms 一帧（"等待玩家数据"等的就是它）
        "snapshot_due": 0.0, "snapshot_sent": False, "snapshot_epoch": 0.0,
        "snapshot_attempts": 0, "last_rx": 0.0,
        # 玩家状态（默认位置/朝向照抄三方 Association 的初值）
        "equipment": _Equipment(),
        "pos_x": 48.0, "pos_y": -572.0, "pos_z": -116.0,
        "pitch": 0, "yaw": 0, "roll": 0,
        "vel_x": 0.0, "vel_y": 0.0, "aim_fraction": 0.0, "aiming": False,
        "client_reliable_ack": 0, "client_reliable_command": "",
        "processed_input_time": 1000, "input_baselines": {},
    }
    log("KEY_EXCHANGE_OK peer=%s transport=%s" % (key, transport[:16].hex()))
    return bytes(ack)


# ------------------------------------------------------------------ ④ 数据帧
def send_data(s, assoc, plain):
    peer = assoc["peer"]
    pkt = bytearray(16 + len(plain))
    pkt[0] = 6
    pkt[1] = 2
    pkt[2] = assoc["cookie"][2]
    pkt[3] = assoc["cookie"][3]
    seq = assoc["send_seq"]
    assoc["send_seq"] = (seq + 1) & 0xFFFF
    struct.pack_into("<H", pkt, 4, seq)
    struct.pack_into("<H", pkt, 14, len(plain))
    seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
    pkt[16:16 + len(plain)] = _keystream_xor(assoc["key"][:16], seed, plain)
    auth = bytes(pkt[0:6]) + bytes(pkt[14:])
    pkt[6:14] = hmac.new(assoc["key"][:24], auth, hashlib.sha1).digest()[:8]
    s.sendto(bytes(pkt), peer)
    assoc["tx"] = assoc.get("tx", 0) + 1
    if assoc["tx"] <= 12 or assoc["tx"] % 100 == 0:
        log("TX_DATA peer=%s:%d seq=%d plain=%dB" % (peer[0], peer[1], seq, len(plain)))


def read_data(pkt, assoc):
    if len(pkt) < 16 or pkt[0] != 6 or pkt[1] != 2:
        return None
    cookie = assoc["cookie"]
    if pkt[2] != cookie[14] or pkt[3] != cookie[15]:
        return None
    enc_len = struct.unpack_from("<H", pkt, 14)[0]
    if enc_len > len(pkt) - 16:
        return None
    auth = bytes(pkt[0:6]) + bytes(pkt[14:])
    mac = hmac.new(assoc["key"][:24], auth, hashlib.sha1).digest()[:8]
    if mac != bytes(pkt[6:14]):
        log("REJECT_DATA_MAC peer=%s:%d" % assoc["peer"])
        return None
    seq = struct.unpack_from("<H", pkt, 4)[0]
    seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
    return seq, _keystream_xor(assoc["key"][:16], seed, bytes(pkt[16:16 + enc_len]))


def _handle_stats(s, assoc, plain):
    """客户端统计分块上传 —— 照抄三方 `stats\\0` 分支。

    真实包形(来自三方 battle.log 实测):
        FF FF FF FF | "stats\\0" | index(1B) | total(u16 LE) | <分块数据>
    服务端回 ``statResponse <missing 位掩码>``（位 i = 第 i 块还缺）。
    ★ 不应答的后果: 客户端**每毫秒重发一次**、永不推进 -> 界面停在"同步游戏设置"
      然后报"服务器连接超时"（2026-10-04 实测踩过）。
    """
    if len(plain) < 13:
        return
    index = plain[10]
    total = struct.unpack_from("<H", plain, 11)[0]
    if total < 1 or total > 32768:
        log("RX_STATS 参数非法 index=%d total=%d len=%d" % (index, total, len(plain)))
        return
    count = (total + 1237) // 1238
    want = 13 + min(1238, total - index * 1238)
    st = assoc.get("stats")
    if st is None or len(st) != total:
        st = bytearray(total)
        assoc["stats"] = st
        assoc["stats_chunks"] = set()
    if index >= count:
        log("RX_STATS index 越界 index=%d count=%d" % (index, count))
        return
    n = min(len(plain) - 13, 1238, total - index * 1238)
    if n > 0:
        st[index * 1238:index * 1238 + n] = plain[13:13 + n]
    assoc["stats_chunks"].add(index)
    missing = 0
    for i in range(count):
        if i not in assoc["stats_chunks"]:
            missing |= (1 << i)
    log("RX_STATS index=%d total=%d count=%d len=%d(期望 %d) 已收块=%s"
        % (index, total, count, len(plain), want, sorted(assoc["stats_chunks"])))
    send_data(s, assoc, b"\xff\xff\xff\xff" + ("statResponse %d\0" % missing).encode("ascii"))
    log("TX_STAT_RESPONSE chunks=%d/%d remaining=%d"
        % (len(assoc["stats_chunks"]), count, missing))
    if missing == 0 and not assoc.get("stats_saved"):
        try:
            with open(os.path.join(OUTDIR, "firingrange-clientstats-last.bin"), "wb") as f:
                f.write(bytes(st))
        except Exception:
            pass
        assoc["stats_saved"] = True
        log("STATS_COMPLETE total=%d 已存 firingrange-clientstats-last.bin" % total)


def handle_plain(s, assoc, plain):
    """OOB 命令（0xFFFFFFFF 前缀）与客户端 netchan 头。"""
    if len(plain) >= 4 and struct.unpack_from("<I", plain, 0)[0] == 0xFFFFFFFF:
        cmd = plain[4:].split(b"\x00")[0].decode("latin1", "replace")
        log("RX_OOB peer=%s:%d cmd=%r" % (assoc["peer"][0], assoc["peer"][1], cmd[:80]))
        if cmd == "stats":
            _handle_stats(s, assoc, plain)
            return
        resp = None
        if cmd.startswith("getchallenge "):
            resp = "challengeResponse 1"
        elif cmd.startswith("connect "):
            resp = "connectResponse"
        elif cmd == "heartbeat":
            resp = "heartbeatresponse"
        elif cmd.startswith("gamestateupdate "):
            try:
                stage = int(cmd.split(" ", 1)[1].strip())
            except Exception:
                stage = -1
            if assoc["gamestate_attempts"] > 0 and 1 <= stage <= 6:
                assoc["gamestate_loading"] = True
            if stage == 6 and not assoc["snapshot_sent"] and not assoc["snapshot_due"]:
                assoc["snapshot_due"] = time.time() + 0.5
            log("RX_GAMESTATE_PROGRESS stage=%d" % stage)
        elif cmd.startswith("cancelConnect"):
            assoc["cancelled"] = True
            log("RX_CANCEL_CONNECT")
        if resp:
            send_data(s, assoc, b"\xFF\xFF\xFF\xFF" + resp.encode("ascii") + b"\x00")
            log("TX_GAME_OOB cmd=%r" % resp)
        return
    if len(plain) >= 14:
        head = struct.unpack_from("<I", plain, 0)[0]
        ack = struct.unpack_from("<I", plain, 5)[0] & 0x1FFFFFFF
        log("RX_CLIENT_GAME_HEADER messageAck=%d bytes=%d" % (ack, len(plain)))
        # ---- 照抄三方 TryReadData 的 netchan 体处理 ----
        if (head & 0xE0000000) == 0:
            body = bytearray(plain[13:])
            input_mask = (ack ^ 1 ^ plain[4]) & 0xFF
            for i in range(len(body)):
                body[i] ^= input_mask
            # ① 可靠命令（如 "mr 1 1 custom2" 换背包）
            for seqk, text in read_reliable(bytes(body)):
                if (seqk <= assoc["client_reliable_ack"]
                        or seqk > assoc["client_reliable_ack"] + 512):
                    continue
                assoc["client_reliable_ack"] = seqk
                assoc["client_reliable_command"] = text
                log("RX_CLIENT_RELIABLE seq=%d command=%r" % (seqk, text))
                if assoc["equipment"].select_backpack(text):
                    log("BACKPACK_SELECTED backpack=%d weapon=%d"
                        % (assoc["equipment"].backpack, assoc["equipment"].selected.weapon))
            # ② 用户命令（位置/视角/按键/武器）
            try:
                baseline = assoc["input_baselines"].get(ack)
                if baseline is None and assoc["snapshot_sent"] and ack > 0:
                    raise _Trunc("Unknown snapshot baseline %d" % ack)
                inputs, _rel = read_input(bytes(body), ack, baseline)
                n = 0
                for inp in inputs:
                    if not assoc["snapshot_sent"] or inp.time <= assoc["processed_input_time"]:
                        continue
                    elapsed = int(min((inp.time - assoc["processed_input_time"]) & 0xFFFFFFFF, 200))
                    dt = elapsed * 0.001
                    assoc["processed_input_time"] = inp.time
                    if assoc["equipment"].step(inp, elapsed):
                        log("WEAPON_FIRE weapon=%d clip=%d event=%d"
                            % (assoc["equipment"].selected.weapon,
                               assoc["equipment"].selected.clip,
                               assoc["equipment"].event_sequence))
                    assoc["pitch"] = inp.pitch
                    assoc["yaw"] = inp.yaw
                    assoc["roll"] = inp.roll
                    forward = (1 if (inp.move & 1) else 0) - (1 if (inp.move & 2) else 0)
                    right = (1 if (inp.move & 4) else 0) - (1 if (inp.move & 8) else 0)
                    yaw_r = inp.yaw * (2.0 * math.pi / 65536.0)
                    # ★ 方向换算标定：yaw → 度 → ×缩放 + 偏移 → 弧度
                    if _DIR_BIAS is not None:
                        _b, _s = _DIR_BIAS
                        _yd = (inp.yaw - 65536 if inp.yaw >= 32768 else inp.yaw) * 360.0 / 65536.0
                        yaw_r = (_yd * _s + _b) * math.pi / 180.0
                    # ★ 方向诊断：force_dir.txt 存在时，方向只用固定角(或缓慢旋转)，忽略 yaw
                    if _FORCE_DIR is not None:
                        _kind, _val = _FORCE_DIR
                        if _kind == "fix":
                            yaw_r = _val * math.pi / 180.0
                        else:
                            _t = time.time() - assoc.get("snapshot_epoch", time.time())
                            yaw_r = (_val * _t) * math.pi / 180.0
                    norm = (math.sqrt(0.5) if (forward != 0 and right != 0) else 1.0)
                    assoc["vel_x"] = (math.cos(yaw_r) * forward + math.sin(yaw_r) * right) * 190 * norm
                    assoc["vel_y"] = (math.sin(yaw_r) * forward - math.cos(yaw_r) * right) * 190 * norm
                    assoc["pos_x"] += assoc["vel_x"] * dt
                    assoc["pos_y"] += assoc["vel_y"] * dt
                    # ★ 诊断：逐条输入日志（见 LOG_INPUTS_FLAG 注释）
                    if _LOG_INPUTS:
                        log("  IN time=%d dt=%d move=0x%X fwd=%d right=%d yaw=%d pos=%.2f,%.2f,%.2f vel=%.1f,%.1f"
                            % (inp.time, elapsed, inp.move, forward, right, inp.yaw,
                               assoc["pos_x"], assoc["pos_y"], assoc["pos_z"],
                               assoc["vel_x"], assoc["vel_y"]))
                    eq = assoc["equipment"]
                    assoc["aiming"] = ((inp.buttons & 0x800) != 0 and eq.weapon_state != 8
                                       and eq.selected.capacity > 0)
                    step = (1.0 if assoc["aiming"] else -1.0) * eq.selected.ads_per_sec * dt
                    assoc["aim_fraction"] = max(0.0, min(1.0, assoc["aim_fraction"] + step))
                    n += 1
                if n:
                    assoc["input_packets"] = assoc.get("input_packets", 0) + 1
                    if assoc["input_packets"] <= 5 or assoc["input_packets"] % 20 == 0:
                        log("RX_USERCMD count=%d processedTime=%d yaw=%d pos=%.1f,%.1f,%.1f"
                            % (n, assoc["processed_input_time"], assoc["yaw"],
                               assoc["pos_x"], assoc["pos_y"], assoc["pos_z"]))
            except _Trunc as e:
                log("REJECT_USERCMD reason=%s" % e)
        assoc["ready"] = True
        if not assoc["gamestate_sent"] and not assoc["gamestate_due"]:
            assoc["gamestate_due"] = time.time() + 0.2


def pump_gamestate(s, assoc):
    """照抄 SendPendingGameStates：把 firingrange-gamestate.bin 作为首个 game state 推下去。"""
    if (not assoc["ready"] or assoc["gamestate_sent"] or assoc["cancelled"] or
            assoc.get("gamestate_loading") or
            assoc["gamestate_attempts"] >= 5 or not assoc["gamestate_due"] or
            time.time() < assoc["gamestate_due"]):
        return
    assoc["gamestate_due"] = time.time() + 2.0
    if not os.path.exists(GAMESTATE_FILE):
        return
    state = open(GAMESTATE_FILE, "rb").read()
    if len(state) < 16 or len(state) > 1100:
        return
    assoc["gamestate_attempts"] += 1
    seq = assoc["netchan_seq"]
    assoc["netchan_seq"] = (seq + 1) & 0xFFFFFFFF
    payload = bytearray(4 + len(state))
    struct.pack_into("<I", payload, 0, seq)
    payload[4:4 + len(state)] = state
    mask = (seq ^ 1) & 0xFF
    for i in range(8, len(payload)):
        payload[i] ^= mask
    send_data(s, assoc, bytes(payload))
    assoc["gamestate_sent"] = True
    log("TX_GAMESTATE seq=%d state=%dB (attempt %d)"
        % (seq, len(state), assoc["gamestate_attempts"]))


# ---------------------------------------------- 客户端命令解析（CodolClientCommandReader）
class _Trunc(Exception):
    pass


class _UserCommand(object):
    """照抄三方 `CodolClientCommandReader.UserCommand`。"""
    __slots__ = ("time", "buttons", "pitch", "yaw", "roll", "weapon",
                 "word22", "word24", "word34", "packed_angle", "move",
                 "byte32", "extra")

    def __init__(self):
        self.time = 0
        self.buttons = 0
        self.pitch = 0
        self.yaw = 0
        self.roll = 0
        self.weapon = 0
        self.word22 = 0
        self.word24 = 0
        self.word34 = 0
        self.packed_angle = 0
        self.move = 0
        self.byte32 = 0
        self.extra = [0] * 5

    def copy(self):
        c = _UserCommand()
        for k in _UserCommand.__slots__:
            v = getattr(self, k)
            setattr(c, k, list(v) if isinstance(v, list) else v)
        return c


class _MixedReader(object):
    """混合读写器 —— 逐行照抄 `CodolClientCommandReader.MixedReader`。

    ★ 与位写入器同源的怪癖: `Bytes()` 从 `cursor` 取并推进 cursor **不动 bit**;
      `Bits()` 只在字节对齐时把 `bit` 重置到 `cursor*8` —— 两套游标是**交错**的。
    """

    def __init__(self, data):
        self.data = data
        self.cursor = 0
        self.bit = 0

    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                if self.cursor >= len(self.data):
                    raise _Trunc("Truncated bits")
                self.bit = self.cursor * 8
                self.cursor += 1
            v |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v

    def bytes(self, n):
        if self.cursor + n > len(self.data):
            raise _Trunc("Truncated bytes")
        v = 0
        for i in range(n):
            v |= self.data[self.cursor] << (8 * i)
            self.cursor += 1
        return v

    def text(self):
        out = []
        for _ in range(1024):
            b = self.bytes(1)
            if b == 0:
                return "".join(out)
            if b < 32 or b > 126:
                raise _Trunc("Invalid command")
            out.append(chr(b))
        raise _Trunc("Command too long")

    def delta(self, old, key, width, aligned=False):
        if self.bits(1) == 0:
            return old
        v = self.bytes(width // 8) if aligned else self.bits(width)
        mask = 0xFFFFFFFF if width == 32 else ((1 << width) - 1)
        return (v ^ key) & mask


def read_reliable(data):
    """`CodolClientCommandReader.Read` —— 只解可靠命令 (seq, text)，失败即停。"""
    result = []
    cursor = 0
    state = {"bit": 0, "cursor": 0}

    def bits(width):
        value = 0
        for i in range(width):
            if (state["bit"] & 7) == 0:
                if state["cursor"] >= len(data):
                    raise _Trunc()
                state["bit"] = state["cursor"] * 8
                state["cursor"] += 1
            value |= ((data[state["bit"] >> 3] >> (state["bit"] & 7)) & 1) << i
            state["bit"] += 1
        return value

    try:
        for _ in range(512):
            if bits(3) != 2:
                break
            cursor = state["cursor"]
            if cursor + 4 > len(data):
                break
            seq = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            start = cursor
            while cursor < len(data) and data[cursor] != 0 and cursor - start < 1024:
                if data[cursor] < 32 or data[cursor] > 126:
                    raise _Trunc()
                cursor += 1
            if cursor >= len(data) or data[cursor] != 0 or seq == 0 or seq > 1000000:
                break
            if result and seq != result[-1][0] + 1:
                break
            result.append((seq, data[start:cursor].decode("ascii", "replace")))
            cursor += 1
            state["cursor"] = cursor
    except _Trunc:
        pass
    return result


def read_input(data, key, baseline=None):
    """`CodolClientCommandReader.ReadInput` —— 返回 (用户命令列表, 可靠命令列表)。"""
    r = _MixedReader(data)
    reliable = []
    opcode = r.bits(3)
    while opcode == 2 and len(reliable) < 512:
        seq = r.bytes(4)
        text = r.text()
        if seq == 0 or seq > 1000000 or (reliable and seq != reliable[-1][0] + 1):
            raise _Trunc("Reliable sequence")
        reliable.append((seq, text))
        opcode = r.bits(3)
    result = []
    if opcode not in (0, 1):
        return result, reliable
    count = r.bytes(1)
    if count < 1 or count > 32:
        raise _Trunc("Input count")
    old = _UserCommand() if baseline is None else baseline.copy()
    for _ in range(count):
        c = old.copy()
        c.time = (old.time + r.bytes(1)) & 0xFFFFFFFF if r.bits(1) != 0 else r.bytes(4)
        if (r.bits(1) ^ (key & 1)) == 0:
            if r.bits(3) != 7:
                raise _Trunc("Idle terminator")
        else:
            full = (r.bits(1) ^ (key & 1)) != 0
            first_key = key if full else (key ^ c.time)
            c.buttons = (old.buttons & ~1) | (r.bits(1) ^ (first_key & 1))
            c.pitch = r.delta(old.pitch, first_key, 16, True) & 0xFFFF
            c.yaw = r.delta(old.yaw, first_key, 16, True) & 0xFFFF
            c.move = r.delta(old.move & 0xFFFFFFFF, first_key, 4) & 0xF
            if full:
                timed = (key ^ c.time) & 0xFFFFFFFF
                c.roll = r.delta(old.roll, timed, 16, True) & 0xFFFF
                c.buttons = ((c.buttons & 1) | ((r.delta(old.buttons >> 1, timed, 29) << 1)
                                                & 0xFFFFFFFF)) & 0xFFFFFFFF
                c.weapon = r.delta(old.weapon, timed, 11) & 0xFFFF
                c.word24 = r.delta(old.word24, timed, 11) & 0xFFFF
                c.word22 = r.delta(old.word22, timed, 11) & 0xFFFF
                if c.buttons & 0x20000:
                    for j in range(3):
                        c.extra[j] = r.delta(old.extra[j], timed, 8, True) & 0xFF
                if c.buttons & 0x200000:
                    for j in range(3, 5):
                        c.extra[j] = r.delta(old.extra[j], timed, 8, True) & 0xFF
                if c.buttons & 4:
                    c.packed_angle = r.delta(old.packed_angle, timed, 16, True) & 0xFFFF
                    c.byte32 = r.delta(old.byte32, timed, 8) & 0xFF
                    c.word34 = r.delta(old.word34, timed, 11) & 0xFFFF
            if r.bits(3) != (5 if full else 2):
                raise _Trunc("Input terminator")
        result.append(c)
        old = c
    return result, reliable


# ---------------------------------------------- 装备/武器状态（CodolRangeEquipment）
class _Slot(object):
    def __init__(self, weapon, ammo, capacity, fire, ads):
        self.weapon = weapon
        self.ammo_key = ammo
        self.capacity = capacity
        self.clip = capacity
        self.reserve = capacity * 3
        self.fire_ms = fire
        self.ads_per_sec = ads
        self.semi = (weapon == 1158)
        self.reload_ms = 2000 if weapon == 1157 else (1799 if weapon == 1158 else 2029)
        self.empty_reload_ms = 2609 if weapon == 1157 else (2000 if weapon == 1158 else 2799)
        self.reload_add_ms = 1299 if weapon == 1157 else (1350 if weapon == 1158 else 1399)
        self.empty_reload_add_ms = 1399


class _Equipment(object):
    """照抄三方 `CodolRangeEquipment`（默认背包 custom1：M4A1 1156）。"""

    def __init__(self):
        self.slots = [_Slot(1156, 585, 30, 71, 4)]
        self.selected_slot = 0
        self.weapon_time = 0
        self.weapon_delay = 0
        self.weapon_state = 0
        self.backpack = 1
        self.event_sequence = 0
        self.events = [0] * 4
        self.event_weapons = [0] * 4
        self.previous_buttons = 0
        self.reload_transfer = False

    @property
    def selected(self):
        return self.slots[self.selected_slot]

    def add_event(self, etype, parameter):
        i = self.event_sequence & 3
        self.events[i] = etype
        self.event_weapons[i] = parameter
        self.event_sequence = (self.event_sequence + 1) & 0xFF

    def select_backpack(self, command):
        """`mr 1 1 customN` —— 只有 custom1/custom2 有效。"""
        w = command.split()
        if len(w) != 4 or w[0] != "mr" or w[1] != "1" or w[2] != "1":
            return False
        number = 1 if w[3] == "custom1" else (2 if w[3] == "custom2" else 0)
        if number == 0:
            return False
        if number == self.backpack:
            return True
        self.backpack = number
        self.selected_slot = 0
        self.weapon_time = self.weapon_delay = self.weapon_state = 0
        self.reload_transfer = False
        if number == 2:
            self.slots = [_Slot(1157, 1112, 36, 59, 5), _Slot(1158, 646, 15, 90, 8),
                          _Slot(317, 317, 0, 800, 0)]
        else:
            self.slots = [_Slot(1156, 585, 30, 71, 4)]
        return True

    def step(self, inp, elapsed):
        """照抄 `CodolRangeEquipment.Step`；返回是否开火。"""
        for i, s in enumerate(self.slots):
            if s.weapon == inp.weapon and i != self.selected_slot:
                self.selected_slot = i
                self.weapon_time = self.weapon_delay = self.weapon_state = 0
                self.reload_transfer = False
                break
        self.weapon_time = max(0, self.weapon_time - elapsed)
        self.weapon_delay = max(0, self.weapon_delay - elapsed)
        if self.reload_transfer and self.weapon_delay == 0:
            sel = self.selected
            amount = min(sel.capacity - sel.clip, sel.reserve)
            sel.clip += amount
            sel.reserve -= amount
            self.reload_transfer = False
        if self.weapon_time == 0:
            self.weapon_state = 0
        fired = False
        sel = self.selected
        reload_pressed = (inp.buttons & 0x10) != 0
        if (self.weapon_time == 0 and sel.capacity > 0 and sel.clip < sel.capacity
                and sel.reserve > 0 and (reload_pressed or sel.clip == 0)):
            empty = (sel.clip == 0)
            self.weapon_time = sel.empty_reload_ms if empty else sel.reload_ms
            self.weapon_delay = sel.empty_reload_add_ms if empty else sel.reload_add_ms
            self.weapon_state = 8
            self.reload_transfer = True
            self.add_event(0x1A if empty else 0x19, 0)
        if ((inp.buttons & 1) and self.weapon_time == 0 and sel.clip > 0
                and (not sel.semi or (self.previous_buttons & 1) == 0)):
            sel.clip -= 1
            self.weapon_time = sel.fire_ms
            self.weapon_state = 6
            self.add_event(0x24, sel.weapon)
            fired = True
        self.previous_buttons = inp.buttons
        return fired


# ------------------------------------------------------- 运动快照（CodolMotionSnapshot）
class _BitWriter(object):
    """逐位写入器 —— 逐行照抄三方 `CodolMotionSnapshot.Writer`。

    ★ 反直觉但关键: `bytes_()` 直接追加在 **Data 末尾**, 而位流指针 `bit` 不动;
      位流只在"字节对齐"时才 `bit = len(Data)*8` —— 也就是**跳到末尾**(越过刚追加的原始字节)。
      结果: 位流占用的字节与原始字段是**交错**的, 必须逐字节复刻, 不能自行"对齐"重排。
    """

    def __init__(self):
        self.data = bytearray()
        self.bit = 0

    def bytes_(self, b):
        self.data += bytes(b)

    def bits(self, v, n):
        for i in range(n):
            if (self.bit & 7) == 0:
                self.bit = len(self.data) * 8
                self.data.append(0)
            self.data[self.bit >> 3] |= (((v >> i) & 1) << (self.bit & 7))
            self.bit += 1

    def index(self, index, prev):
        skip = index - prev[0] - 1
        prev[0] = index
        if skip == 0:
            self.bits(1, 1)
        else:
            self.bits(0, 1)
            while skip >= 15:
                self.bits(15, 4)
                skip -= 15
            self.bits(skip, 4)

    def scalar(self, value, width):
        self.bits(0 if value == 0 else 1, 1)
        if value != 0:
            self.bits(value & ((1 << (width & 7)) - 1), width & 7)
            for i in range(width & 7, width, 8):
                self.bytes_([(value >> i) & 0xFF])


# 默认装备见 `_Equipment`（custom1 背包：M4A1 1156 / 弹匣 30 / 备弹 90 / 弹键 585）。


def _build_motion_snapshot(ack, server_time, command_time, first,
                           x, y, z, pitch, yaw, roll,
                           vx, vy, aim_fraction, aiming, eq, omit_motion=False):
    """玩家状态快照 —— 逐行照抄三方 `CodolMotionSnapshot.Build`（参数与字段序一一对应）。

    ★ omit_motion=True（默认关，开关文件 client_movement.on）:
      在**非首帧**时**省略位置/速度**(字段 8/10/11/13/14)。这套编码是"增量"语义 ——
      不写的字段 = 客户端保持原值。于是**位置由客户端自己的预测/碰撞决定**，
      彻底消除"服务端粗糙积分(恒定速度、无碰撞) vs 客户端真实预测"造成的**橡皮筋**。
      （首帧必须照发，客户端要靠它建立基线。）
    """
    w = _BitWriter()
    prev = [-1]
    sel = eq.selected
    slots = eq.slots
    w.bytes_(struct.pack("<I", ack))
    w.bytes_(b"\x00")
    w.bytes_(struct.pack("<I", server_time))
    w.bytes_(bytes([0 if first else 1, 8 if first else 4]))
    w.bits(0, 1)
    w.bits(1, 1)
    w.bits(220, 8)
    w.index(0, prev); w.bits(1, 1); w.bytes_(struct.pack("<I", command_time))
    w.index(1, prev); w.bits(0, 1); w.bytes_([eq.event_sequence & 0xFF])
    w.index(3, prev); w.scalar(eq.weapon_time, 16)
    if not omit_motion:
        w.index(8, prev); w.bytes_(struct.pack("<f", x))
        w.index(10, prev); w.bytes_(struct.pack("<f", z))
        w.index(11, prev); w.bytes_(struct.pack("<f", y))
        w.index(13, prev); w.bytes_(struct.pack("<f", vy))
        w.index(14, prev); w.bytes_(struct.pack("<f", vx))
    w.index(17, prev); w.scalar(eq.weapon_state, 6)
    # ★ 实验（2026-10-04，开关 `omit_viewangles.on`，默认**关**）：不下发 viewangles（idx 18/19/29）。
    #   现象依据：实跑 + 逐条输入日志证明"移动方向严格等于当前 yaw"（横移/后退也对），
    #   但用户转 180° 只有约 20° 的实际转向 → **视角被我们回声的 viewangles 阻尼掉了**：
    #   鼠标转 → 客户端算 usercmd → 我们把它写回 idx 18/19 → 客户端拿它覆盖自己的视角 → 每帧被拽回。
    #   增量语义下"不写 = 客户端保持", 于是它就能用自己的（未阻尼的）视角。
    if not _OMIT_VIEWANGLES:
        w.index(18, prev); w.bytes_(struct.pack("<H", yaw & 0xFFFF))
        w.index(19, prev); w.bytes_(struct.pack("<H", pitch & 0xFFFF))
    w.index(20, prev); w.scalar(0x10 if aiming else 0, 32)
    for i in range(4):
        w.index(21 + i, prev)
        w.bits(1, 1)
        w.bytes_([eq.events[i] & 0xFF])
        if eq.events[i] not in (0x19, 0x1A):
            w.bits(1, 1)
            w.bits(eq.event_weapons[i] & 0x7FF, 11)
    if not _OMIT_VIEWANGLES:
        w.index(29, prev); w.bytes_(struct.pack("<H", roll & 0xFFFF))
    w.index(34, prev); w.bytes_(struct.pack("<f", 60.0))
    w.index(38, prev); w.scalar(60, 8)
    w.index(39, prev); w.scalar(sel.weapon, 11)
    w.index(41, prev); w.bytes_(struct.pack("<f", aim_fraction))
    w.index(44, prev); w.scalar(eq.weapon_delay, 16)
    # ★ 实验（2026-10-04，**默认关**，开关文件 `idx45.on`）：官方每帧下发、我们从没写过的 idx 45
    #   （原生 playerState **+0xB8**）。录像 trace 里它的值 = yaw；原生 +0xB4/+0xB8/+0xBC 是
    #   三个连续 float（idx 70/45/191）。
    #   实测结论：
    #     · 宽度 = **17 位**（1 位 presence + 2 字节）—— 裸 f32(32 位)/裸 short(16 位) 都会让客户端
    #       **解析错位、卡在"等待玩家数据"**；改成 17 位后客户端能**进图**了（可达 942 条 usercmd）；
    #     · 但把 yaw 填进去后：**出生在屋顶 / 无法移动 / 视角 360° 乱转可倾斜 / 武器跑到屏幕中间**
    #       → 说明它的**语义不是"移动基准角"**（更像是相机/自由视角一类的字段），值也给错了。
    #   故默认不发；留此开关供后续继续做编码实验。
    if os.path.exists(IDX45_FLAG):
        w.index(45, prev); w.bits(1, 1); w.bytes_(struct.pack("<H", yaw & 0xFFFF))
    w.index(54, prev); w.bits(1, 1); w.bits(0x1000, 31)
    w.index(56, prev); w.scalar(139, 10)
    w.index(60, prev); w.scalar(190, 16)
    w.index(61, prev); w.scalar(2047, 16)
    w.index(63, prev); w.scalar(800, 16)
    w.index(68, prev); w.scalar(2047, 11)
    w.index(219, prev); w.bits(1, 1); w.bits(1, 1)
    w.bytes_(struct.pack("<f", 1.0)); w.bits(0, 8)
    w.bits(1, 1); w.bits(5, 17)
    w.bytes_(struct.pack("<H", 100)); w.bytes_(struct.pack("<H", 100))
    guns = len(slots) - (1 if slots[-1].capacity == 0 else 0)
    w.bits(1 if guns > 0 else 0, 1)
    for i in range(guns):
        s = slots[i]
        w.bits(i, 4); w.bits(s.weapon, 11); w.bits(1, 1)
        w.bits(s.clip, 9); w.bits(0, 1)
        w.bits(1 if i + 1 < guns else 0, 1)
    w.bits(1, 1)                                    # 15 个已拥有槽位（空基线）
    for i in range(15):
        occupied = i < len(slots)
        w.bits(1 if occupied else 0, 1)
        if occupied:
            w.bits(1, 1); w.bits(slots[i].weapon, 11); w.bits(0, 5); w.bits(0, 12)
    w.bits(1 if guns > 0 else 0, 1)                 # 备弹
    for i in range(guns):
        s = slots[i]
        w.bits(i, 4); w.bits(s.ammo_key, 11); w.bits(s.reserve & 0xFFF, 12)
        w.bits(1 if i + 1 < guns else 0, 1)
    w.bits(0, 13)
    w.bits(0, 1); w.bits(0, 1); w.bits(0, 1); w.bits(1, 1); w.bits(2047, 11)
    w.bits(0, 1); w.bits(0, 1)
    w.bytes_(b"\x05")
    return bytes(w.data), w.bit


def pump_snapshot(s, assoc):
    """照抄 SendPendingSnapshots：stage 6 之后每 25ms 一推玩家状态（位置/视角/武器都取实时值）。"""
    now = time.time()
    if (assoc["cancelled"] or not assoc["snapshot_due"] or now < assoc["snapshot_due"]
            or now - assoc.get("last_rx", now) > 15):
        return
    assoc["snapshot_due"] = now + _SNAP_DT
    if not assoc["snapshot_sent"]:
        assoc["snapshot_epoch"] = now
    server_time = 1000 + int((now - assoc["snapshot_epoch"]) * 1000)
    # ★ 客户端移动权威：非首帧省略位置/速度（见 CLIENT_MOVEMENT_FLAG 注释）
    omit = bool(assoc["snapshot_sent"]) and os.path.exists(CLIENT_MOVEMENT_FLAG)
    # ★ 出生点实验：连首帧也省略位置 → 客户端保留地图自带 spawn
    omit = omit or os.path.exists(SPAWN_FROM_MAP_FLAG)
    # ★ 出生点指定（spawn_at.txt）：**首帧**改为发这个坐标（覆盖上面的 omit），之后仍省略
    px, py, pz = assoc["pos_x"], assoc["pos_y"], assoc["pos_z"]
    pvx, pvy = assoc["vel_x"], assoc["vel_y"]
    spawn_at = read_spawn_at()
    static_spawn = os.path.exists(STATIC_SPAWN_FLAG)
    if spawn_at is not None and static_spawn:
        # ★ v32 等价：**每帧**都发同一个固定坐标（参考 launcher 的 staticPosition=true）
        px, py, pz = spawn_at
        omit = False
    elif spawn_at is not None and not assoc["snapshot_sent"]:
        px, py, pz = spawn_at
        omit = False
    # ★ B 路线：镜像客户端自己的预测态（含重力/碰撞/视角前方），优先级最高。
    #   ★ 注意 `and not omit`：若省略开关（如 spawn_from_map.on）被打开，就连位置一起**不发** ——
    #   那样客户端的预测就完全自由（不再被我们回发的过期值重新播种）。见 HANDOFF §13.50。
    if _MIRROR_PRED and not omit:
        _mp = read_predicted()
        if _mp is not None:
            _mirror_miss["n"] = 0
            _lx, _ly, _lz = _mp[3] * _PRED_LEAD, _mp[4] * _PRED_LEAD, _mp[5] * _PRED_LEAD
            # 外推距离限幅（≤120 单位），避免速度异常时把人瞬移出去
            if (_lx * _lx + _ly * _ly + _lz * _lz) > 120.0 * 120.0:
                _k = 120.0 / math.sqrt(_lx * _lx + _ly * _ly + _lz * _lz)
                _lx *= _k; _ly *= _k; _lz *= _k
            px, py, pz = _mp[0] + _lx, _mp[1] + _ly, _mp[2] + _lz
            pvx, pvy = _mp[3], _mp[4]
            omit = False
            assoc["pos_x"], assoc["pos_y"], assoc["pos_z"] = px, py, pz
        else:
            # ★ 明确告警：镜像开着却拿不到数据（探针没命中 / predicted.bin 过期）
            #   此时**回落到服务端积分**，出生点/物理会变成"老一套"，别误判成镜像的效果。
            _mirror_miss["n"] += 1
            if _mirror_miss["n"] == 1 or _mirror_miss["n"] % 800 == 0:
                log("[!] mirror_predicted.on 但 predicted.bin 不可用 -> 已回落服务端积分 (连续 %d 帧)"
                    % _mirror_miss["n"])
    state, _bits = _build_motion_snapshot(
        assoc["client_reliable_ack"], server_time, assoc["processed_input_time"],
        not assoc["snapshot_sent"],
        px, py, pz,
        assoc["pitch"], assoc["yaw"], assoc["roll"],
        pvx, pvy, assoc["aim_fraction"], assoc["aiming"],
        assoc["equipment"], omit_motion=omit)
    seq = assoc["netchan_seq"]
    assoc["netchan_seq"] = (seq + 1) & 0xFFFFFFFF
    # ★ 我方作为"基线"下发：客户端后续 usercmd 会以它为 base（缺失会报 Unknown snapshot baseline）
    base = _UserCommand()
    base.pitch = assoc["pitch"]
    base.yaw = assoc["yaw"]
    base.weapon = assoc["equipment"].selected.weapon
    base.buttons = 0x800 if assoc["aim_fraction"] != 0 else 0
    base.word34 = 2047
    assoc["input_baselines"][seq] = base
    if seq > 512:
        assoc["input_baselines"].pop(seq - 512, None)
    payload = bytearray(4 + len(state))
    struct.pack_into("<I", payload, 0, seq)
    payload[4:] = state
    # 掩码：seq^1，且逐字节混入"已确认的可靠命令"(与三方 SendPendingSnapshots 一致)
    mask = (seq ^ 1) & 0xFF
    cmd = assoc.get("client_reliable_command", "").encode("ascii", "replace")
    for i in range(8, len(payload)):
        if cmd:
            mask = (mask ^ ((cmd[(i - 8) % len(cmd)] << ((i - 8) & 1)) & 0xFF)) & 0xFF
        payload[i] ^= mask
    send_data(s, assoc, bytes(payload))
    assoc["snapshot_sent"] = True
    assoc["snapshot_attempts"] = assoc.get("snapshot_attempts", 0) + 1
    if assoc["snapshot_attempts"] <= 5 or assoc["snapshot_attempts"] % 40 == 0:
        log("TX_SPAWN_EXPERIMENT seq=%d serverTime=%d bytes=%d (第 %d 帧, omit=%d staticPosition=%s pos=%.1f,%.1f,%.1f yaw=%d)"
            % (seq, server_time, len(state), assoc["snapshot_attempts"], int(omit),
               ("true" if (spawn_at is not None and static_spawn) else "false"),
               px, py, pz, assoc["yaw"]))


def main():
    # ★ 先把 stdout/stderr 换成 UTF-8（errors="replace"）—— run_all 会把输出重定向到文件，
    #   控制台默认是 GBK，不换的话日志里任何非 GBK 字符都会抛 UnicodeEncodeError 打死进程。
    #   这是 2026-10-04 那次"客户端卡在等待连接"的直接原因（日志里一个 U+26A0）。
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=28960)
    a = ap.parse_args()

    global _SESSION_KEY
    _SESSION_KEY = gen_keypair()
    sk = read_security_key()
    log("==== battle_server 启动 %s:%d (pid=%d) ====" % (a.bind, a.port, os.getpid()))
    log("  ECDH P-224 公钥(100B) = %s…" % export_pubkey(_SESSION_KEY[1])[:16].hex())
    log("  securityKey(16B) = %s" % sk.hex())
    log("  game state 文件: %s (%s)"
        % (os.path.basename(GAMESTATE_FILE),
           ("%d 字节" % os.path.getsize(GAMESTATE_FILE)) if os.path.exists(GAMESTATE_FILE) else "缺"))
    _sa = read_spawn_at()
    if _sa and os.path.exists(STATIC_SPAWN_FLAG):
        _spawn_desc = "每帧固定 %s (static_spawn.on = v32 staticPosition)" % (_sa,)
    elif _sa:
        _spawn_desc = "首帧指定 %s (spawn_at.txt)" % (_sa,)
    elif os.path.exists(SPAWN_FROM_MAP_FLAG):
        _spawn_desc = "客户端自选（spawn_from_map.on）"
    else:
        _spawn_desc = "服务端积分位置"
    log("  出生点: %s" % _spawn_desc)
    log("  idx45 实验: %s" % ("开" if os.path.exists(IDX45_FLAG) else "关"))
    log("  viewangles: %s" % ("省略(客户端自管)" if _OMIT_VIEWANGLES else "下发"))
    log("  方向: %s" % (("固定 %.1f 度 (force_dir.txt)" % _FORCE_DIR[1]) if (_FORCE_DIR and _FORCE_DIR[0] == "fix")
                        else (("缓慢旋转 %.1f 度/秒 (force_dir.txt rot)" % _FORCE_DIR[1]) if _FORCE_DIR
                              else (("yaw x%s + %s 度 (dir_bias.txt)" % (_DIR_BIAS[1], _DIR_BIAS[0]))
                                    if _DIR_BIAS is not None else "按 yaw 原样"))))
    log("  位置: %s" % (("★镜像客户端预测态 (mirror_predicted.on), 前导补偿 %.0f ms, 探针 %.0f Hz, 快照 %.0f Hz"
                         % (_PRED_LEAD * 1000.0, _TICK_HZ, _SNAP_HZ)) if _MIRROR_PRED
                        else "服务端积分 (快照 %.0f Hz)" % _SNAP_HZ)
        + ("  [注意: 与省略开关同时开启 -> 位置将完全不发，客户端预测自由]" if _MIRROR_PRED else ""))
    if _MIRROR_PRED:
        # ★ 启动就清掉上一轮的 predicted.bin：否则残留文件会在本轮头 1 秒被采信，
        #   而**出生点正是那 1 秒决定的**（§13.53 事故）。清不掉也没关系，mtime 判据兜底。
        try:
            os.remove(PRED_FILE)
            log("  镜像: 已清空残留 predicted.bin（避免用上一轮数据播种出生点）")
        except Exception:
            pass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # ★ 不设 SO_REUSEADDR —— 否则多个战斗服能同时"绑上"同一个 UDP 端口, 客户端的包会被
    #   最早那个(可能是旧版本)抢走, 表现为"战斗服 0 包 / 一直等待连接"。
    #   2026-10-04 实测踩过: run_all 的 KILL_RE 漏了 battle_server.py, 累积出 21 个僵尸
    #   全绑在 28960 —— 已把 battle_server\.py 加进 KILL_RE。这里再让重复绑定直接失败。
    try:
        s.bind((a.bind, a.port))
    except Exception as e:
        log("[!] 绑定 %s:%d 失败: %r —— 是否还有旧战斗服占着? 见 run_all.py 的 KILL_RE"
            % (a.bind, a.port, e))
        return
    s.settimeout(0.01)
    log("[*] 已监听 UDP %s:%d" % (a.bind, a.port))

    n_rx = n_nat = n_init = n_keyex = n_data = 0
    last_stat = time.time()
    while True:
        try:
            pkt, peer = s.recvfrom(4096)
        except socket.timeout:
            pkt = None
        except Exception as e:
            log("[!] recv 异常: %r" % (e,))
            break
        if pkt is not None:
            n_rx += 1
            key = "%s:%d" % peer
            if n_rx <= 40 or n_rx % 100 == 0:
                log("RX #%d peer=%s len=%d hex=%s"
                    % (n_rx, key, len(pkt), pkt[:128].hex(" ")))

            assoc = ASSOCS.get(key)
            handled = False
            if assoc is not None:
                r = read_data(pkt, assoc)
                if r is not None:
                    n_data += 1
                    assoc["last_rx"] = time.time()
                    handle_plain(s, assoc, r[1])
                    handled = True
            if not handled:
                rep = try_build_nat_reply(pkt)
                if rep:
                    s.sendto(rep, peer)
                    n_nat += 1
                    handled = True
                else:
                    rep = try_build_init_ack(pkt, peer)
                    if rep:
                        s.sendto(rep, peer)
                        n_init += 1
                        log("TX_DTLS_INIT_ACK peer=%s 38B clientTag=%d serverTag=%d"
                            % (key, struct.unpack_from("<H", pkt, 6)[0],
                               struct.unpack_from("<H", rep, 14)[0]))
                        handled = True
                    else:
                        rep = try_build_key_exchange_ack(pkt, peer, sk)
                        if rep:
                            s.sendto(rep, peer)
                            n_keyex += 1
                            log("TX_DTLS_KEY_EXCHANGE_ACK peer=%s 114B stage=transport-ready" % key)
                            handled = True
            if not handled and n_rx <= 40:
                log("    (未处理: type=%d len=%d)" % (pkt[0] if pkt else -1, len(pkt)))

        for assoc in list(ASSOCS.values()):
            pump_gamestate(s, assoc)
            pump_snapshot(s, assoc)

        if time.time() - last_stat >= 30:
            last_stat = time.time()
            log("[stat] 收包=%d NAT=%d init=%d keyex=%d data=%d 会话=%d"
                % (n_rx, n_nat, n_init, n_keyex, n_data, len(ASSOCS)))
    s.close()


if __name__ == "__main__":
    main()
