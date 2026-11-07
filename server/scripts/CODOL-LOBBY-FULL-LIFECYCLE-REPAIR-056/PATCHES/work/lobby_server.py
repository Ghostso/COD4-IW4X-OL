# -*- coding: utf-8 -*-
"""大厅服 LOBBY SERVER —— 127.0.0.2:3074 (明文 LSG, = formal-zone-lsg.codol.qq.com)。

================================================================================
组件定位(术语约定)
================================================================================
本文件 = **大厅服 (lobby server)**。只负责客户端进图**之前**的大厅阶段:
  · 握手 / 档案 / 钱包 / 商城
  · findSessions 会话对象 —— 决定给客户端哪张地图、什么模式(动态选单)
  · mmbook 预约确认

它与 **战斗服 (battle server)** 是两个独立组件:

  大厅服  lobby_server.py          (本文件, Python, TCP 3074)
  战斗服  codol_battle_server.exe  (唯一在用, C 原生, UDP 28960)

  ★「新 C 服 / 旧 C 服 / Python 服」这三个说法**全部指战斗服**, 不指大厅服:
      新 C 服   codol_battle_server.exe            唯一启用, 当前源码
      旧 C 服   codol_battle_server.legacy.exe     已废弃, 需显式开启
      Python 服 battle_server.py                   已废弃, 需显式开启

  ★ 区分要点: 战斗服源码(CODOL_SERVER_319_20261021\)里 **没有** playlist /
    findSessions / mmbook —— 客户端连上 UDP 28960 之前的一切都在本文件里完成。
    所以「进不了图」查大厅服, 「进图后异常」查战斗服。
================================================================================

协议(全部照抄三方 CodolLocalLobbyServer.cs / 其 lsg.log 真实帧):
  1) 客户端先发 28 字节 hello:
        C8 00 00 00 | C8 00 00 00 | D2 00 00 00 | DC 00 00 00 | 00 00 08 00 | <8B nonce>
  2) 服务端回 0x81:  u32 22 | 00 | 81 | u32 0xDC | 8B 随机 | 8B(=hello[20:28])
  3) 客户端发 0x82(stage1):  u32 len | AB | 82 | <...>
  4) 服务端回 0x83:  u32 10 | 00 | 83 | <8B challenge>(从客户端内存读; 有补丁4 时不校验)
  5) 之后客户端发 0x85 加密任务帧, 服务端解密 -> 回 0x85 应答
        frame = u32 len | AB | 85 | u32 seq | iv[16] | cipher | hmac8[8]
  另外 4 个 0x00 字节 = keepalive。

密钥来自 nt10.py 写出的 secrets.txt(服务端进程读游戏内存会被拦, 所以由 nt10 读)。

分派覆盖(照抄三方 + 本轮借鉴 ol-mod):
  - 10/21 发行方配置, 10/12 用户文件, 8/1,8/2 档案
  - 80/32,80/130,93/1 钱包(CP/GP)
  - 21/5,21/16 findSessions 会话对象(258B) —— 见 session_objects(), 移植自 ol-mod
  - 80/70,107,119,154,173,174,203,230,232 商城空应答(ol-mod 同款语义)

会话密钥: 默认仍由 nt10.py 读游戏内存写 secrets.txt(见下)。
  ★ 另有一条 KDF 派生分支(codol_crypto.derive_session_keys, 借鉴 ol-mod):
    它只在**与内存快照互证一致**时才被采信; 实测当前 build 对不上(kdf_probe.py),
    所以实际生效的仍是内存快照 —— 日志会打 `[kdf] ...` 供持续观察。

用法:
  python lobby_server.py                    # 127.0.0.2:3074
  python lobby_server.py --lobby-bind 0.0.0.0 --lobby-port 8446 --raw-ports 80,8081   # 调试
"""
import argparse
import glob
import hashlib
import json
import os
import re
import socket
import struct
import subprocess
import sys
import zlib


# ======================================================================
# 玩家档案(service=8) —— 逐字节照抄 C# SavePublicProfile(第 700-764 行)
# ======================================================================
def _profile_crc(buf, off, length):
    """照抄 C# ProfileCrc: CRC32(多边形 0xEDB88320) 取反。"""
    num = 0xFFFFFFFF
    for i in range(off, off + length):
        num ^= buf[i] & 0xFF
        for _ in range(8):
            num = (num >> 1) ^ (0xEDB88320 if (num & 1) else 0)
    return (~num) & 0xFFFFFFFF


def _inflate_profile(blob):
    """照抄 C# InflateProfile。C# 的 num3==1 表示压缩。"""
    return zlib.decompress(blob, 15)


# ★ 2026-10-06 实验开关: 往 public.result 尾部 125 个 0x07 槽里注入名片 itemID。
#   目的: 验证这 125 槽是不是"军牌定制可装备清单"。
#   名单在同目录 public-tail-items.txt(每行一个十进制 itemID)。
#   回滚: 删除 public-tail-inject.on
def _inject_public_tail(tail_bytes, n=125):
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(here, "public-tail-inject.on")):
        return tail_bytes
    try:
        ids = []
        with open(os.path.join(here, "public-tail-items.txt"),
                  "r", encoding="ascii") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    ids.append(int(ln.split()[0]))
    except Exception:
        return tail_bytes
    if len(tail_bytes) < n * 5:
        return tail_bytes
    vals = []
    for i in range(n):
        if tail_bytes[i * 5] != 0x07:
            return tail_bytes
        vals.append(struct.unpack_from("<i", tail_bytes, i * 5 + 1)[0])
    present = set(vals)
    added = 0
    for it in ids:
        if it in present:
            continue
        for i, v in enumerate(vals):
            if v == 0:
                vals[i] = it
                present.add(it)
                added += 1
                break
    if not added:
        return tail_bytes
    out = bytearray()
    for v in vals:
        out += bytes([0x07]) + struct.pack("<i", v)
    print("-- [profile-tail] 注入 %d 个名片 itemID 到可装备清单" % added)
    return bytes(out)


def save_public_profile(plain, outdir, owner=16701785630074219790):
    """处理 8/3 上传的 public profile, 落盘 public.result。

    plain 是**含 8 字节头**的完整明文(与 C# 一致)。
    返回 (ok, note)。
    """
    try:
        declared = struct.unpack_from("<I", plain, 0)[0]
        num = declared + 5
        n125 = 125
        if num > len(plain) or num < 35 + n125 * 5 or plain[num - 1] != 0:
            return False, "结构长度不符(declared=%d len=%d)" % (declared, len(plain))
        if not (plain[8] == 8 and plain[13] == 8 and plain[18] == 8
                and plain[23] == 8 and plain[28] == 19 and plain[29] == 8):
            return False, "结构标记不符"
        num3 = struct.unpack_from("<I", plain, 14)[0]      # 压缩标志
        num4 = struct.unpack_from("<I", plain, 19)[0]      # 必须 1
        num5 = struct.unpack_from("<I", plain, 24)[0]      # CRC
        num6 = struct.unpack_from("<i", plain, 30)[0]      # blob 长度
        if num4 != 1 or num6 < 0 or num6 > 32768:
            return False, "版本/长度不符(num4=%d num6=%d)" % (num4, num6)
        if num != 35 + num6 + n125 * 5:
            return False, "总长不符(num=%d 期望=%d)" % (num, 35 + num6 + 625)
        raw = bytes(plain[34:34 + num6])
        if num3 == 1:
            raw = _inflate_profile(raw)
        if len(raw) != 32768:
            return False, "解压后 %d != 32768" % len(raw)
        if (struct.unpack_from("<I", raw, 4)[0] != 233
                or struct.unpack_from("<I", raw, 8)[0] != 1248641861):
            return False, "档案魔数不符"
        if struct.unpack_from("<I", raw, 0)[0] != num5 or \
                _profile_crc(raw, 4, 32764) != num5:
            return False, "CRC 校验失败"
        for i in range(n125):
            if plain[34 + num6 + i * 5] != 7:
                return False, "尾部第 %d 项 tag != 07" % i

        # 重建 public.result(照抄第 730-737 行)
        out = bytearray(32803 + n125 * 5)
        out[0] = 10
        struct.pack_into("<Q", out, 1, owner)
        out[9:35] = plain[8:34]
        struct.pack_into("<I", out, 15, 0)
        struct.pack_into("<I", out, 31, 32768)
        out[35:35 + 32768] = raw
        out[32803:32803 + n125 * 5] = _inject_public_tail(
            plain[34 + num6:34 + num6 + n125 * 5], n125)

        d = os.path.join(outdir, "player_profiles")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, "public.result")
        tmp = dst + ".tmp"
        with open(tmp, "wb") as f:
            f.write(bytes(out))
        os.replace(tmp, dst)
        return True, ("public.result 已保存(%d 字节, 压缩=%d, blob=%d)"
                      % (len(out), num3, num6))
    except Exception as e:
        return False, "解析异常: %r" % (e,)


# ======================================================================
# 玩家档案(service=8) —— public.result 的打包/拆包
#   结构(实测):
#     0A <owner u64> | 08 <ver u32> | 08 <flags u32> | 08 <u32 1>
#     08 <crc u32>   | 13 08 <len u32> <裸档案 32768B>
#     07 <i32> x125  <- 可装备清单(军牌定制里能换什么)
# ======================================================================
def _read_profile_tail(path):
    """从已有 public.result 里读出尾部 0x07 清单。"""
    try:
        pub = open(path, "rb").read()
    except Exception:
        return []
    k = 0
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            k += 6 + ln
            break
        else:
            return []
    vals = []
    while k + 5 <= len(pub) and pub[k] == 0x07:
        vals.append(struct.unpack_from("<i", pub, k + 1)[0])
        k += 5
    return vals


def _pack_public_result(raw, tail=(), owner=16701785630074219790,
                        version=4, flags=0, one=1):
    """把 8/3 上传的裸档案重新包成 8/1 要回的 public.result。"""
    crc = struct.unpack_from("<I", raw, 0)[0]
    out = bytearray()
    out += bytes([0x0A]) + struct.pack("<Q", owner)
    out += bytes([0x08]) + struct.pack("<I", version)
    out += bytes([0x08]) + struct.pack("<I", flags)
    out += bytes([0x08]) + struct.pack("<I", one)
    out += bytes([0x08]) + struct.pack("<I", crc)
    out += bytes([0x13, 0x08]) + struct.pack("<I", len(raw)) + raw
    for v in tail:
        out += bytes([0x07]) + struct.pack("<i", v)
    return bytes(out)
import threading
import time

import codol_crypto as cc

CURRENT_LOBBY_ADDR = "-"
CURRENT_LOBBY_STATE = {"playlist": "unknown", "map": "unknown", "mode": "unknown", "room_id": "-"}

# 商城模块(独立文件, 移植自三方 v32 的 MarketplaceStore.cs)。目录缺 SKU 目录文件时降级为空应答。
try:
    import marketplace_store as ms
except Exception as _e:                                     # pragma: no cover
    ms = None
    print("-- [market] marketplace_store 不可用(%r) -> 商城回空应答" % (_e,))

# 把我们自己编的 SKU 目录页接进来(默认关, 见 market_skus.py)。
try:
    import market_skus
except Exception as _e:                                     # pragma: no cover
    market_skus = None
    print("-- [market] market_skus 不可用(%r) -> 商城目录仍回空页" % (_e,))

# 库存 Owner 必须与写入时一致(C# 里是玩家 CODOID; 三方本地实现用 1)。
# 可用同目录的 marketplace-owner.txt 覆盖。
def _market_owner():
    """库存 Owner 的取值优先级:
       ① marketplace-owner.txt (显式覆盖)  ② 现有 marketplace-inventory.json 里的 Owner
       ③ 默认 1。
    库存文件的 Owner 是权威(C# 的 Read 会严格校验 state.Owner != owner 并抛错),
    所以**必须**优先沿用它, 否则会出现 "Invalid marketplace inventory owner/version"。"""
    try:
        with open(os.path.join(OUTDIR, "marketplace-owner.txt"), "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        pass
    try:
        with open(os.path.join(OUTDIR, "marketplace-inventory.json"), "r", encoding="utf-8") as f:
            return int(json.load(f)["Owner"])
    except Exception:
        return 1


MARKET_OWNER = 1        # 真正的取值在 OUTDIR 定义之后(见下方 _market_owner())

OUTDIR = os.path.dirname(os.path.abspath(__file__))
MARKET_OWNER = _market_owner()
LOCK = threading.Lock()
SECRETS = os.path.join(OUTDIR, "secrets.txt")
# ★ nt10 的 KDF hook 直接派生出来的密钥(优先用, 见 read_secrets 注释)
SECRETS_KDF = os.path.join(OUTDIR, "secrets_kdf.txt")
# ★ 多客户端: nt10 每个会话追加一行「会话密钥 + 四把子密钥 + challenge」
#   (kdf_sessions.txt)。服务端靠它把"连接"与"该客户端的密钥"配对。
SESS_FILE = os.path.join(OUTDIR, "kdf_sessions.txt")

# 占位 challenge(补丁4 把客户端的 nonce 校验 NOP 掉了, 所以拿不到真值时也能过)
H8 = bytes.fromhex("1122334455667788")

# nt10.py 在客户端 [obj+0x5E8]==1 时写这个标志
READY_FLAG = os.path.join(OUTDIR, "lobby_ready.flag")

# ---- 靶场(firing range)开关文件(照抄三方 C# 的 File.Exists 判据; 都放在 OUTDIR) ----
# ★ 这三个开关**都不存在**时, 本文件行为与改造前**完全一致**(不破坏已跑通的大厅)。
FR_SESSION_FLAG = os.path.join(OUTDIR, "firingrange-session.enabled")        # 21/5 靶场会话对象
FR_BOOKING_FLAG = os.path.join(OUTDIR, "firingrange-booking-push.enabled")   # 6/* booking 推送
FR_BATTLE_FLAG = os.path.join(OUTDIR, "firingrange-battle.enabled")          # 战斗服(UDP)启动

# ★ 2026-10-07: 客户端 PvE 剧情任务实测请求 playlist=10, 随后 6/14 的完整
#   mmstart 明确携带 `g_gametype coop; map coop_training_mp_cargoship;`。
#   21/5 必须回同一套 map/gametype, 否则客户端不会进入加载、也就不会连 28960。
#   保留为集合是为了后续把其它 PvE playlist 逐个实测加入, 避免误伤靶场(playlist=1)。
PVE_PLAYLIST_IDS = {10}
PVE_ADDRESS67_FLAG = os.path.join(OUTDIR, "pve-address67.on")
# C# BuildFiringRangeBookingAccepted 的"裸"消息(含结尾 0x00, 长度 16)——
# 内层流是 typed-mode-disabled, 只写 u32 长度 + 这个消息字节。
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"
FR_BATTLE_BIND = "0.0.0.0"       # 战斗服 UDP —— 绑所有本地 IPv4,
                                 # 避免客户端按 localhost 解析到别的地址时收不到包
FR_BATTLE_PORT = 28960

# ------------------------------------------------------------- 官方选单动态解析器
LOCAL_AVAILABLE_MAPS = {
    "coop_train_mp_firingrange",
    "coop_training_mp_cargoship",
    "mp_cargoship",
    "mp_firingrange",
}

class _PlaylistResolver(object):
    def __init__(self, kit_dir):
        self.kit_dir = kit_dir
        self.playlists = {}
        self._load()

    def _load(self):
        info_path = os.path.join(self.kit_dir, "publisher_files", "mp_playlists_shipRetail_1.0.0.info")
        if not os.path.isfile(info_path):
            self.playlists[198] = [("coop_train_mp_firingrange", "coop")]
            self.playlists[10] = [("coop_training_mp_cargoship", "coop")]
            self.playlists[13] = [("mp_cargoship", "tdm"), ("mp_firingrange", "tdm")]
            return
        try:
            import zlib
            raw = open(info_path, "rb").read()
            text = zlib.decompress(raw).decode("latin1", "replace")
            cur_id = None
            for line in text.splitlines():
                m = re.match(r"^\s*playlist\s+(\d+)", line)
                if m:
                    cur_id = int(m.group(1))
                    self.playlists.setdefault(cur_id, [])
                    continue
                if cur_id is not None:
                    m2 = re.match(r"^\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*,\s*\d+", line)
                    if m2:
                        self.playlists[cur_id].append((m2.group(1), m2.group(2)))
        except Exception:
            pass

    def resolve(self, playlist_id, explicit_map=None):
        if explicit_map and explicit_map in LOCAL_AVAILABLE_MAPS:
            gt = "coop" if explicit_map.startswith("coop_") else "tdm"
            is_fr = (explicit_map == "coop_train_mp_firingrange")
            max_p = 1 if is_fr else (4 if explicit_map.startswith("coop_") else 18)
            return explicit_map, gt, is_fr, max_p
        pid = int(playlist_id) if playlist_id is not None else 198
        entries = self.playlists.get(pid, [])
        for map_name, gt in entries:
            if map_name in LOCAL_AVAILABLE_MAPS:
                is_fr = (map_name == "coop_train_mp_firingrange")
                max_p = 1 if is_fr else (4 if gt == "coop" else 18)
                return map_name, gt, is_fr, max_p
        mode = entries[0][1] if entries else ("coop" if pid in (10, 12, 198) else "tdm")
        if mode == "coop":
            if pid == 198:
                return "coop_train_mp_firingrange", "coop", True, 1
            return "coop_training_mp_cargoship", "coop", False, 4
        return "mp_cargoship", mode if mode != "coop" else "tdm", False, 18

_RESOLVER_INSTANCE = None

def get_playlist_resolver():
    global _RESOLVER_INSTANCE
    if _RESOLVER_INSTANCE is None:
        _RESOLVER_INSTANCE = _PlaylistResolver(OUTDIR)
    return _RESOLVER_INSTANCE


def log(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg)
    with LOCK:
        print(line, flush=True)
        try:
            with open(os.path.join(OUTDIR, "lobby_srv.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def hexd(d):
    return d.hex(" ")


def _read_hex_file(path):
    """把 `key value` 文本解析成 dict(pid/state 转 int, 其余按 hex 转 bytes)。"""
    d = {}
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 2:
                    continue
                if p[0] in ("pid", "state"):
                    try:
                        d[p[0]] = int(p[1])
                    except Exception:
                        pass
                else:
                    try:
                        d[p[0]] = bytes.fromhex(p[1])
                    except Exception:
                        pass
    except Exception:
        pass
    return d


def read_secrets():
    """读会话密钥。

    ★ 优先 `secrets_kdf.txt` —— 那是 nt10 挂住客户端的 HMAC(0xBA0D20) 后,
      **直接用抓到的两个入参派生**出来的(2026-10-03, 见 HANDOFF §10.8);
      已实测与内存快照逐字段一致(kdf_probe.py --inputs 全 OK)。
      好处: 不再依赖"读 auth 对象内存槽 [sub+0x604..0x60C]"以及 [sub+0x5E8]==3 的时序。
    没有该文件时回退 `secrets.txt`(老的 nt10 内存快照路径)。
    """
    d = _read_hex_file(SECRETS_KDF)
    if d.get("aes_out") and d.get("hmac_out"):
        d["src"] = "kdf"
        return d
    d = _read_hex_file(SECRETS)
    d["src"] = "mem"
    return d


def load_kdf_sessions():
    """读 nt10 写的「会话 → 密钥」表; 以**会话密钥 hex**为键。

    格式(nt10 每命中一次 KDF 追加一行):
        <session_key:24B> <transcript_hash:20B> <challenge:8B> <aes_out:16B>
        <aes_in:16B> <hmac_out:20B> <hmac_in:20B>
    """
    d = {}
    try:
        with open(SESS_FILE, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 7:
                    continue
                try:
                    d[p[0]] = {
                        "session_key": bytes.fromhex(p[0]),
                        "transcript_hash": bytes.fromhex(p[1]),
                        "challenge": bytes.fromhex(p[2]),
                        "aes_out": bytes.fromhex(p[3]),
                        "aes_in": bytes.fromhex(p[4]),
                        "hmac_out": bytes.fromhex(p[5]),
                        "hmac_in": bytes.fromhex(p[6]),
                        "src": "kdf-session",
                    }
                except Exception:
                    continue
    except Exception:
        pass
    return d


def load_kdf_sessions_all():
    """按文件顺序返回**全部**会话记录(允许同一会话密钥多行)。

    ★ 为什么需要它: 客户端 `/auth/` 只发一次(会话密钥不变), 但**每次重连大厅都会
      重新派生一套密钥**(transcriptHash 变) → 同一会话密钥会有多行。
      单用 dict(最后一行胜出) 会配错 —— 2026-10-03 实测就出现了 `hmac=BAD`。
      所以真正可靠的判据是"试解 + HMAC 校验"(见 pick_keyset)。
    """
    out = []
    try:
        with open(SESS_FILE, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 7:
                    continue
                try:
                    out.append({
                        "session_key": bytes.fromhex(p[0]),
                        "transcript_hash": bytes.fromhex(p[1]),
                        "challenge": bytes.fromhex(p[2]),
                        "aes_out": bytes.fromhex(p[3]),
                        "aes_in": bytes.fromhex(p[4]),
                        "hmac_out": bytes.fromhex(p[5]),
                        "hmac_in": bytes.fromhex(p[6]),
                        "src": "kdf-session",
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return out


def pick_keyset(frame, sk_hex=None):
    """**按 HMAC 校验**挑出这条连接该用的密钥组; 返回 (keys, 解密结果) 或 (None, None)。

    候选顺序: 同会话密钥的(新→旧) → 其余全部(新→旧) → 全局 secrets。
    HMAC-SHA1 截断 8 字节, 误判概率 2^-64 —— 足够当判据。
    """
    cands = load_kdf_sessions_all()
    same = [c for c in cands if sk_hex and c["session_key"].hex() == sk_hex]
    others = [c for c in cands if not (sk_hex and c["session_key"].hex() == sk_hex)]
    for k in list(reversed(same)) + list(reversed(others)):
        try:
            r = cc.decrypt_task_frame(frame, k["aes_out"], k["hmac_out"])
        except Exception:
            continue
        if r and r.get("hmac_ok"):
            return k, r
    g = read_secrets()
    if g.get("aes_out"):
        try:
            r = cc.decrypt_task_frame(frame, g["aes_out"], g["hmac_out"])
            if r and r.get("hmac_ok"):
                return g, r
        except Exception:
            pass
    return None, None


def requested_name(plain):
    """从 10/21、10/12 的请求明文里取文件名。
    实测形态: 10 00 10 <文件名字符串> 00 00
    这里取"含点号的可打印 ASCII 串", 足以覆盖 .info/.result 这些名字。"""
    m = re.search(rb"[0-9A-Za-z_\-\.]{3,}\.(?:info|json|dat|txt|cfg|result)",
                  plain or b"")
    return m.group(0).decode("ascii", "replace") if m else None


ACCOUNT = os.path.join(OUTDIR, "player-account.json")

# ---------------------------------------------------------------- 会话/对局参数
# 21/5 findSessions 的会话对象要用到的"权威服务器地址"。停服后我们本地没有真游戏服务,
# 先按配方里的既定值填 127.0.0.1:28960(与 SHARED.md 记的"21/5 含 127.0.0.1:28960"一致)。
GAME_IP = (127, 0, 0, 1)
GAME_PORT = 28960
SESSION_ID = 0x1122334455667788          # 非零即可; roomId 由它派生
MAP_NAME = "mp_crash_tropical"           # ol-mod 的缺省地图
SEC_KEY = b"\x00" * 16                   # 16B securityKey; 真游戏服要配对的另一半, 暂用全 0
# ★ 把它写给战斗服(battle_server.py) —— 战斗服的 ECDH 派生要用同一个 16B
SEC_KEY_FILE = os.path.join(OUTDIR, "battle_security_key.txt")

# ---- 房间/即时消息用到的身份与 id(照抄 ol-mod Unknown0B / InstantMessage) ----
PLAYER_UID = 0x1100001DEADC0DE           # 平台内部 id(与我们 docs 里记的一致)
ROOM_ID = SESSION_ID                     # createRoom 回的 roomId(非零即可)
ROOM_SECOND_ID = 0x1122334455667788 ^ 0x53525652564F4443   # ol-mod 用它区分合成会话


class BitWriter:
    """Demonware LSB-first 位流序列化器，用于构造 dwRoomMessage 系列消息。
    严格对齐客户端 0x00B77A70 (writeBitsCore) 与 0x00B777C0 (writeData)。"""
    def __init__(self, use_data_types=True):
        self.buf = bytearray()
        self.bit_len = 0
        self.use_data_types = use_data_types
        if use_data_types:
            # 必须在 bit 0 写出 1 位 m_useDataTypes 头（客户端 0x00B77A24 明确首读 1 bit）
            self.write_bits(1, 1)

    def write_bits(self, val, nbits=5):
        for i in range(nbits):
            byte_idx = self.bit_len // 8
            bit_idx = self.bit_len % 8
            if bit_idx == 0:
                self.buf.append(0)
            if (val >> i) & 1:
                self.buf[byte_idx] |= (1 << bit_idx)
            self.bit_len += 1

    def write_tag(self, tag):
        self.write_bits(tag, 5)

    def write_data(self, data_bytes, nbits=None):
        if nbits is None:
            nbits = len(data_bytes) * 8
        for i in range(nbits):
            byte_in = i // 8
            bit_in = i % 8
            bit = (data_bytes[byte_in] >> bit_in) & 1

            byte_out = self.bit_len // 8
            bit_out = self.bit_len % 8
            if bit_out == 0:
                self.buf.append(0)
            if bit:
                self.buf[byte_out] |= (1 << bit_out)
            self.bit_len += 1

    def write_blob(self, blob_bytes):
        self.write_tag(0x13)
        self.write_tag(8)
        length = len(blob_bytes)
        self.write_data(length.to_bytes(4, "little"), 32)
        self.write_data(blob_bytes, length * 8)

    def data(self):
        return bytes(self.buf)


def build_bd_common_addr_67(ip_tuple=(127, 0, 0, 1), port=28960, nat_type=1):
    """构造 Demonware 3.19 标准 67 字节 bdCommonAddr 地址块 (sub_B95C50 要求 0x43=67 字节)。
    slot 0 = 本端, 9个空槽(00 FF 00 FF 00 00), slot 10 = 发布地址, natType = 1。"""
    out = bytearray(67)
    out[0:4] = bytes(ip_tuple)
    struct.pack_into("<H", out, 4, port)
    empty_slot = bytes([0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00])
    for i in range(9):
        out[6 + i*6 : 12 + i*6] = empty_slot
    out[60:64] = bytes(ip_tuple)
    struct.pack_into("<H", out, 64, port)
    out[66] = nat_type & 0xFF
    return bytes(out)


def build_startgame_payload(addr_67, session_id_int, security_key_16=None):
    """构造 dwRoomMessageStartGame 位流载荷 (严格对齐 0x00625BE0 与 0x00625CE0)。
    包含: bit 0(m_useDataTypes=1) + 字段1(tag 3, val=3) +
    字段2(blob 67B addr) + 字段3(blob 8B sessionId) + 字段4(blob 16B securityKey)。
    总长度恰好 109 字节。"""
    if security_key_16 is None or len(security_key_16) != 16:
        security_key_16 = b"\x00" * 16
    w = BitWriter(True)
    w.write_tag(3)
    w.write_data(bytes([3]), 8)
    w.write_blob(addr_67)
    w.write_blob(struct.pack("<Q", session_id_int & 0xFFFFFFFFFFFFFFFF))
    w.write_blob(security_key_16)
    return w.data()


def build_room_push(sender_id, sender_name, room_id, payload):
    """构造 Demonware 房间信道广播推送体 (信封类型 8，带字段标签)。
    客户端接收后由 0x007F1060 -> 0x007E7C90 -> 0x006371F0 -> 0x00634870 处理。"""
    ob = cc.Buf(True)
    ob.u32(8)
    ob.u64(sender_id)
    ob.string(sender_name)
    ob.u64(room_id)
    ob.blob(payload)
    ob.u32(0)
    return ob.data()


def start_udp_port_relay(src_port=8305, dst_port=28960):
    """启动本地 UDP 端口转发器 (0.0.0.0:8305 -> 127.0.0.1:28960)。
    兼容客户端按大端网络字节序将 (20 71) 解释为端口 8305 的情况，确保 UDP 握手数据包直达战斗服。"""
    def _relay_loop():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", src_port))
            last_client = [None]
            log("  ★ 启动 UDP 端口转发器: 0.0.0.0:%d -> 127.0.0.1:%d" % (src_port, dst_port))
            while True:
                data, addr = sock.recvfrom(8192)
                if addr[0] == "127.0.0.1" and addr[1] == dst_port:
                    if last_client[0]:
                        sock.sendto(data, last_client[0])
                else:
                    last_client[0] = addr
                    sock.sendto(data, ("127.0.0.1", dst_port))
        except Exception as e:
            log("  UDP 端口转发器异常: %r" % (e,))
    t = threading.Thread(target=_relay_loop, daemon=True)
    t.start()


def player_name():
    return str(read_account().get("Name", "Player"))


def session_objects(query_kind):
    """21/5 findSessions 的结果对象 —— 移植 ol-mod MatchmakingService.findSessions。

    queryKind = 1(FIND_SERVERS, 实测我们客户端发的就是它):
        只回"权威服务器"这一条, maxPlayers=18 / currentPlayers=0(ol-mod 的合成候选);
    其它 queryKind:
        回本地房间一条, currentPlayers=1。

    ★ 三条"错了就崩"的门槛已在 cc.build_session_record 内保证
      (gate 字段=67 / roomId 非零十进制 / hostUid != 玩家 CODOID)。
    """
    cur = 0 if query_kind == 1 else 1
    return [cc.build_session_record(SESSION_ID, GAME_IP, GAME_PORT,
                                    game_type=0, max_players=18, current_players=cur,
                                    map_name=MAP_NAME, security_key=SEC_KEY)]


def keys_of(derived):
    """把 KDF 派生结果映射成我们的四把密钥名; 未派生时返回 {}。
    方向对照(ol-mod Crypto.cpp:209-215):
        decrypt -> aes_out(解客户端帧)   encrypt -> aes_in(加密我的应答)
        requestHmac -> hmac_out(验客户端帧)   responseHmac -> hmac_in(签我的应答)"""
    if derived.get("decrypt") and derived.get("encrypt"):
        return {"aes_out": derived["decrypt"], "aes_in": derived["encrypt"],
                "hmac_out": derived["request_hmac"], "hmac_in": derived["response_hmac"],
                "challenge": derived["response_id"]}
    return {}


def read_account():
    """读 player-account.json(三方 LocalPlayerAccount 的同款字段); 缺文件时给默认值。"""
    d = {"Name": "Player", "Level": 70, "Experience": 11056700,
         "Prestige": 4, "CodPoints": 999999, "Gold": 999999}
    try:
        with open(ACCOUNT, encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def balance_object(currency):
    """照抄 MarketplaceStore.BalanceObject: 03 <currency> 08 <u32 值>。
    currency=1 -> CP(CodPoints), 2 -> GP(Gold)。"""
    a = read_account()
    v = int(a.get("CodPoints", 0)) if currency == 1 else int(a.get("Gold", 0))
    return bytes([3, currency & 0xFF, 8]) + struct.pack("<I", v & 0xFFFFFFFF), v


def reply_objects(service, task, plain):
    """按任务类型准备应答对象(照抄三方的分派)。返回 (objects, 说明, pushes)。
    pushes = [(messageType, body)] —— 服务端主动推送(类型 2), 由调用方在应答之后发出。"""
    def ack(note):
        return [], note, []

    if service == 10 and task == 21:                     # 发行方配置
        nm = requested_name(plain)
        if not nm:
            return ack("名字没解析出来")
        p = os.path.join(OUTDIR, "publisher_files", os.path.basename(nm))
        # ★ 2026-10-05: 客户端在大厅初始化时请求 mp_playlists_shipRetail_1.0.0.info,
        #   而参考套件只带了 mp_playlists_shipRetail_release.info(同一份内容)。
        #   缺这个文件就是 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 的直接原因。
        #   这里做一个同义名回退, 免得重新拷贝套件后又要手工补文件。
        if not os.path.exists(p) and os.path.basename(nm) == "mp_playlists_shipRetail_1.0.0.info":
            p = os.path.join(OUTDIR, "publisher_files", "mp_playlists_shipRetail_release.info")
        if not os.path.exists(p):
            return ack("缺 %s" % nm)
        d = open(p, "rb").read()
        return [cc.serialize_file_data(d)], "publisher %s (%d 字节)" % (nm, len(d)), []
    if service == 10 and task == 12:                     # 用户文件
        nm = requested_name(plain)
        if not nm:
            return ack("名字没解析出来")
        p = os.path.join(OUTDIR, "user_files", os.path.basename(nm))
        if not os.path.exists(p):
            return ack("缺 %s (三方此处也是 missing)" % nm)
        d = open(p, "rb").read()
        return [cc.serialize_file_data(d)], "user_file %s (%d 字节)" % (nm, len(d)), []
    if service == 8 and task in (1, 2):                  # 档案 public / secure
        fn = "public.result" if task == 1 else "secure.result"
        p = os.path.join(OUTDIR, "player_profiles", fn)
        if not os.path.exists(p):
            return ack("缺 %s" % fn)
        d = open(p, "rb").read()
        return [d], "profile %s (%d 字节)" % (fn, len(d)), []
    if service == 8 and task == 3:
        # ★★ 2026-10-06: 客户端**上传**玩家档案(名片/装备/统计都在里面)。
        #    逐字节照抄 C# SavePublicProfile(第 700-764 行):
        #      头部 35 字节 + blob(可 zlib) + 125 项 07 <i32> 尾清单。
        #    之前一律回空 ACK -> 客户端发的档案被丢弃 -> 买的东西/装备不生效。
        #    reply_objects 收到的 plain 只是 payload, 必须补 8 字节头。
        try:
            declared = len(plain) + 3
            frame = (struct.pack("<I", declared)
                     + bytes([0x86, service, 0x03, task]) + plain)
            ok, note = save_public_profile(frame, OUTDIR)
            return ack("profile 8/3 %s" % note)
        except Exception as e:
            return ack("profile 8/3 处理失败: %r" % (e,))
    if (service == 80 and task in (32, 130)) or (service == 93 and task == 1):
        # 钱包 —— 对象 = writeU8(type) + writeU32(amount)。
        # ol-mod 实测: 客户端一次余额轮询发两个请求 —— Marketplace/130 取第 1 个钱包,
        # 93/1 取第 2 个(MarketplaceService.cpp:381-408 注释), 与我们的映射一致。
        cur = 1 if service == 80 else 2
        obj, val = balance_object(cur)
        return [obj], "balance %d/%d currency=%d 值=%d" % (service, task, cur, val), []
    if service in (0x15, 0x8A) and task in (5, 16):
        # 21/5 findSessions —— 会话对象(进房间/进对局的前置)。
        # ★ 2026-10-06: 把原始 payload 打出来 —— 用户选不同地图/模式时会带不同参数,
        #   我们要按它回的 session 才能对上; 之前无条件回靶场 session, 所以"剧情任务进不去"。
        log("       ★ findSessions 原始 payload(%d): %s"
            % (len(plain or b""), (plain or b"").hex(" ")))
        # ★ 靶场模式(2026-10-03): 存在开关文件 firingrange-session.enabled 时, 改用三方 C#
        #   权威的 BuildMissionSessionObject(67B 地址块 / GameType 0x1000007 / MaxPlayers=1),
        #   返回**单个**对象。这是"靶场进入路径"的第一步。
        #   ★ 无开关 → 完全保持既有行为(258B session 记录), 不破坏已跑通的大厅。
        if os.path.exists(FR_SESSION_FLAG):
            # ★ 从请求里取 playlist(第 3 个 u32)
            _vals = []
            _i = 0
            while _i < len(plain or b""):
                _t = plain[_i]
                _i += 1
                if _t == 0x08 and _i + 4 <= len(plain):
                    _vals.append(struct.unpack_from("<I", plain, _i)[0]); _i += 4
                elif _t == 0x07 and _i + 4 <= len(plain):
                    _vals.append(struct.unpack_from("<i", plain, _i)[0]); _i += 4
                elif _t == 0x01 and _i + 1 <= len(plain):
                    _i += 1
                else:
                    break
            _pl = _vals[2] if len(_vals) >= 3 else None
            log("       ★ findSessions 解析值=%s -> 选单 playlist=%s"
                % (_vals, _pl))
            log("LOBBY_FIND_SESSIONS request_id=%s playlist=%s map=unknown mode=unknown room_id=- client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), _pl, CURRENT_LOBBY_ADDR))

            # 动态解析官方选单并匹配本地可用地图
            _resolver = get_playlist_resolver()
            _exp_map = cc._coop_map_override() if _pl in PVE_PLAYLIST_IDS else None
            _map_name, _gt, _is_fr, _max_p = _resolver.resolve(_pl, explicit_map=_exp_map)

            # 写入房间状态供战斗服动态组装 Gamestate
            import json
            _room_info = {
                "map": _map_name,
                "game_type": _gt,
                "playlist": _pl,
                "is_firing_range": _is_fr,
                "max_players": _max_p,
                "timestamp": time.time(),
            }
            try:
                with open(os.path.join(OUTDIR, "active_room.json"), "w", encoding="utf-8") as _rf:
                    json.dump(_room_info, _rf, indent=2)
            except Exception as _e:
                log("       (写入 active_room.json 失败: %r)" % (_e,))

            _gt_id = 0x1000007 if _is_fr else (0x1000003 if _gt == "coop" else 0x1000001)
            log("LOBBY_BATTLE_ENDPOINT_ASSIGNED request_id=%s playlist=%s map=%s mode=%s room_id=- client=%s session_id=0x1122334455667788 endpoint=127.0.0.1:28960" % (CURRENT_LOBBY_STATE.get("request_id"), _pl, _map_name, _gt, CURRENT_LOBBY_ADDR))
            CURRENT_LOBBY_STATE.update({"playlist": _pl, "map": _map_name, "mode": _gt})
            log("LOBBY_MODE_SELECTED request_id=%s playlist=%s map=%s mode=%s room_id=- client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), _pl, _map_name, _gt, CURRENT_LOBBY_ADDR))
            objs = [cc.build_mission_session_object(
                _is_fr, playlist=_pl,
                map_override=_map_name,
                game_type_override=_gt_id,
                address67=True)]
            return objs, ("findSessions -> ★ 单人/本地Host模式房间: playlist=%s map=%s gametype=%s (对象 %d 字节, maxPlayers=1)"
                          % (_pl, _map_name, _gt, len(objs[0]))), []
        qk, _ = cc.parse_u32_tagged(plain or b"", 0)
        objs = session_objects(qk)
        return objs, ("findSessions queryKind=%s -> %d 条 session 对象, 每条 %d 字节"
                      % (qk, len(objs), len(objs[0]) if objs else 0)), []
    if service in (0x15, 0x8A) and task == 1:
        # ★ 21/1 createSession —— 2026-10-03 实测: 客户端进出房间时会发它(x1),
        #   我们原先没实现 → 回空对象 → 客户端拿不到 sessionId, 走不到战斗服。
        #   照抄 ol-mod MatchmakingService.cpp:404-438: 对象 = [blob 8B processSessionId]。
        ob = cc.Buf()
        ob.blob(struct.pack("<Q", SESSION_ID & 0xFFFFFFFFFFFFFFFF))
        return [ob.data()], ("createSession -> sessionId=0x%X (对象 %d 字节)"
                             % (SESSION_ID, len(ob.data()))), []
    if service in (0x15, 0x8A) and task in (2, 3, 9, 12):
        # updateSession / deleteSession / submitPerformance / updatePlayers —— 照抄 ol-mod 均为空 ACK
        return ack("matchmaking %d/%d 空应答(payload=%d)" % (service, task, len(plain or b"")))
    if service in (0x15, 0x8A) and task == 10:
        # getPerformanceValues: 对象 = [u64 userId][i64 value]; 我们还没有性能数据 -> 空
        return ack("matchmaking %d/10 getPerformanceValues 空(无数据)" % service)
    if service == 0x47 and task == 2:
        # Tencent/2: (string username) → [bool false][string username]  (ol-mod TencentService.cpp)
        nm = b""
        m = re.search(rb"[0-9A-Za-z_\-\.\[\]]{2,32}", plain or b"")
        if m:
            nm = m.group(0)
        ob = cc.Buf(); ob.bool_(False); ob.string(nm)
        return [ob.data()], ("Tencent/2 -> bool false + username %r" % nm.decode("latin1", "replace")), []
    if (service == 80 and task in (70, 107, 119, 154, 173, 174, 203, 230, 232)) or (service == 93 and task == 131):
        # 商城 —— 语义与字节布局照抄三方 v32 的 MarketplaceStore.cs
        #   154 purchaseSkus / 93-131: 购买(真实扣款 + 写入库存)
        #   203: 库存列表    230: 玩家资产(PlayerData)
        #   70 getSkusPaginated: 刻意回"空页"。源码注释写明: 格式正确的空应答能让商店保持
        #      可浏览; 而客户端反序列化不了的应答会让**整个 marketplace 服务死掉**
        #      (STORE/INVENTORY 变灰且本次会话不再恢复) —— 这是实测过的失败。
        #      CODOL 的 SKU 记录不是 MW19 的 bdMarketplaceSku(多两个字段), 照抄兄弟作品的
        #      字段序就会触发那次失败, 所以这里坚持回空页。107/173/174/232 同理。
        cur = 1 if service == 80 else 2
        if ms is not None:
            try:
                if task in (154, 131):
                    # ★★ C# 的 ParsePurchase(frame, declared, ...) 里 frame 是**含 8 字节头的完整明文**
                    #    (它按 frame[8+i] 取 payload[i]); 而 reply_objects 收到的 plain 只是 payload,
                    #    必须把 8 字节头补回去, 否则整体错位 8 字节 -> 模板校验必然失败。
                    #    2026-10-03 实测: 硬证据是客户端发的 93/131 payload(58B) 与三方日志里的
                    #    逐字节相同, declared=61, 仅因缺头而报 Unsupported purchase parameters。
                    declared = len(plain) + 3
                    frame = struct.pack("<I", declared) + bytes([0x86, service, 0x03, task]) + plain
                    sku, qty = ms.parse_purchase(frame, declared, cur)
                    tx = hashlib.sha1(bytes(plain)).hexdigest()   # 同一购买帧重发天然幂等
                    # ★ 2026-10-05: 实测客户端购买帧里的 sku 大多**不在** exe 内嵌目录里
                    #   (点 6 次: 241/242/31774/31816 全部查无此 SKU, 只有 32223 命中)。
                    #   => 客户端用的是"服务端目录"的编号, 与 exe 内嵌那份不同。
                    #   把未知 SKU 记下来(供后续建映射), 但仍按原语义失败 —— 不做"假成功不发货"。
                    try:
                        ms.purchase(OUTDIR, MARKET_OWNER, tx, cur, [sku], [qty])
                    except Exception as e:
                        try:
                            with open(os.path.join(OUTDIR, "unknown_skus.txt"), "a",
                                      encoding="ascii") as f:
                                f.write("%d\t%s\n" % (sku, e))
                        except Exception:
                            pass
                        # ★ 2026-10-06: 失败时把 SKU 也写进主日志, 便于分类。
                        log("       ★ 购买失败 sku=%d currency=%d qty=%d 原因=%s"
                            % (sku, cur, qty, e))
                        raise
                    # ★★ 2026-10-06 更正: C# 参考实现购买成功后回的是
                    #    BuildTaskReply(..., resultObject=**null**, status=purchaseStatus)
                    #    —— **不携带任何结果对象**(第 1343 行)。
                    #    我们之前回了一个"余额对象", 客户端会把它当成别的东西解析,
                    #    于是判定购买失败(游戏内表现为"点了没反应")。
                    #    现在改为与参考实现一致: 空对象 + status=0。
                    return [], \
                           ("marketplace 80/%d 购买成功 sku=%d qty=%d (空对象+status=0)"
                            % (task, sku, qty)), []
                if task == 203:
                    objs = ms.inventory_results(OUTDIR, MARKET_OWNER)
                    return objs, ("marketplace 80/203 库存 %d 件" % len(objs)), []
                if task == 230:
                    d = ms.marketplace_player_data(OUTDIR, MARKET_OWNER)
                    return ([d] if d else []), \
                           ("marketplace 80/230 玩家资产 %d 字节" % len(d or b"")), []
                # ★ 2026-10-05: 目录页(70/107/119/173/174/232)——
                #   默认仍回空页(空页是安全的, 客户端不炸); 打开 marketplace-skus.on
                #   后才回我们自己编的 SKU 页(字段表见 _sku_schema_as.py)。
                #   ★ 先发少量(marketplace-skus-count.txt), 确认客户端不再抛 #1009 再放量。
                if task in (70, 107, 119, 173, 174, 232):
                    # ★ 哨兵探针(默认关): 用唯一常量编 1 条 SKU, 让客户端解析;
                    #   成功则哨兵会存活在客户端内存里。见 market_sku_probe.py。
                    try:
                        import market_sku_probe as msp
                    except Exception:
                        msp = None
                    if msp is not None and msp.probe_enabled():
                        objs = msp.build_objects()
                        return objs, ("marketplace 80/%d ★ 哨兵探针 variant=%d "
                                      "count=%d 对象=%s"
                                      % (task, msp.variant(), msp.count(),
                                         [len(o) for o in objs])), []
                    # ★ 2026-10-07: "按 item 分组、组内多档" 的实验路径。
                    #   只发**含 ground-truth SKU 的 item 组**(当前仅 5 组),
                    #   每个 SKU 档用 _sku_obj 编。默认关; 打开
                    #   marketplace-skus-itemgroup.on 才生效, 单条可控、随时回滚。
                    if market_skus is not None \
                            and market_skus.itemgroup_enabled():
                        try:
                            n = market_skus.page_size(default=1)
                        except Exception:
                            n = 1
                        groups = market_skus.build_item_sku_page(limit=n)
                        objs = []
                        for _item, tier_objs in groups:
                            objs.extend(tier_objs)
                        if not objs:
                            return ack("marketplace 80/%d itemgroup: 无可信 item 组"
                                       % task)
                        return objs, ("marketplace 80/%d ★ item 分组 SKU 页: "
                                      "%d 个 item / %d 档 SKU (ground-truth 组)"
                                      % (task, len(groups), len(objs))), []
                    if ms is not None and market_skus is not None \
                            and market_skus.sku_page_enabled():
                        # ★★ 2026-10-05 实测失败, 默认禁用 ★★
                        #   只发 3 条自编 SKU 就把**整个 marketplace 服务**打挂:
                        #   仓库/商城全变红色叹号、角色被锁、所有按钮点不动。
                        #   这正是三方注释警告过的"格式错的 SKU 页会让服务死掉"。
                        #   结论: 我们编的字段集/顺序**不对**, 不能就这么发。
                        #   要再试必须先拿到**真实 SKU 页的字节**(官方响应样本),
                        #   或把客户端反序列化器逆到字段级, 不能再靠猜。
                        #   保留代码与开关, 但这里强制回退到空页。
                        if os.path.exists(os.path.join(OUTDIR, "marketplace-skus-allow-unsafe.on")):
                            entries = market_skus.catalog_entries(limit=2000)
                            objs = market_skus.build_sku_page(entries)
                            return objs, ("marketplace 80/%d ★ SKU 页 %d 条"
                                          % (task, len(objs))), []
                        return ack("marketplace 80/%d SKU 页已禁用(上次自编格式打挂服务)"
                                   % task)
            except Exception as e:
                # 失败时**不回半成品对象**(照抄 C# 的 status=1 语义), 退回空 ACK
                return ack("marketplace 80/%d 失败(%s) -> 空 ACK" % (task, e))
        return ack("marketplace 80/%d 空应答(ol-mod 同款语义)" % task)

    # ---------------- 房间服务 0x0B(=11) —— 照抄 ol-mod Unknown0BService ----------------
    if service == 11:
        if task == 13:                                   # createRoom(请求无参)
            CURRENT_LOBBY_STATE["room_id"] = "0x%X" % ROOM_ID
            # 对象 = [u64 roomId][u32 memberCount=1][u32 18][u64 secondId][bool false][bool false][u32 1]
            # ★★★ 2026-10-27 实测定案：memberCount 必须是 1，不能是 0。
            #   依据（本地 A/B，run ONCE_20261027_132700 + 转储 EARLIEST2_20261027_132645）：
            #     · memberCount=0 时，客户端**从不创建** dwRoomMatchUber 对象
            #       （[0x82E1518]=0，MyEventHandler 零实例，从未有过任何建房尝试）；
            #     · 改成 1 后，同一进程内 [0x82E1518] 从 0 变成有效指针 0x3ACA0CD8
            #       （vtable 0x00DC795C / +0x68=0x63C5E0 校验通过），
            #       "已请求开局"标志 [0x849B61C] 由 0 变 1。
            #   线索来源：_LEARN_TESTOL_DELIVERY2\reports\112 —— 该记录写
            #     "dest1yo DLL 用成员数 0 / C# OLfinal 用 1，两个都能进大厅，故都不算被证伪"。
            #   本 build(3.19/1649370) 上我们实测：**0 无效、1 有效**，补上了该空缺。
            ob = cc.Buf()
            ob.u64(ROOM_ID); ob.u32(1); ob.u32(1); ob.u64(ROOM_SECOND_ID)
            ob.bool_(False); ob.bool_(False); ob.u32(1)
            return [ob.data()], ("createRoom -> roomId=0x%X secondId=0x%X (%d 字节)"
                                 % (ROOM_ID, ROOM_SECOND_ID, len(ob.data()))), []
        if task in (1, 9, 11):
            return ack("0B/%d consumeUserPair(u64,u64) 空应答" % task)
        if task == 2:
            CURRENT_LOBBY_STATE["room_id"] = "-"
            return ack("0B/2 leaveRoom 空应答")
        if task == 4:
            # setRoomData(channelId u64, batch blob, type u32) —— 房间 ready 就走这里。
            # ★ 2026-10-03 实测: 客户端确实发了 4 次, 其中一次 payload 就是那个 16B ready 批次。
            #   ol-mod 的注释(cpp:87-127)说明它在这里把 ready 消息**广播回频道** ——
            #   我们之前只回空 ACK, 客户端可能因此在等"房间成员都 ready"的回执。
            ch, batch, tp = _parse_set_room_data(plain)
            # ★ 2026-10-04 更正 ready 判据：**不是** `payload[11]==0x15`。
            #   · ol-mod(第三个独立来源)在 Unknown0BService.cpp:96-105 用逐字节比较那 16 字节
            #     `CapturedReadyMessage` 来识别"准备"，其注释明确:
            #       "Task 4 — every room message the client sends, as (u64 roomId, blob batch, u32).
            #        ... Unlike task 13 it binds no result buffer ... so a bare acknowledgement
            #        is correct for this one."  → **11/4 只回裸 ACK 就是对的**(我们已如此)。
            #   · 三方的 `pushData[11]==0x15` 是**误读**：那个字节其实是 blob 长度的低字节
            #     (0x15=21)，不是子类型 —— 见 HANDOFF §13.8.1 的 payload[11] 序列
            #     (0x8F/0x15/0x10/0x14 = 各自 blob 的长度)。
            #   实测本客户端**确实发过**这条 16B ready 批次(01:09:54, batch=16)。
            # ★ 2026-10-07 实机更正: 客户端 PvE 剧情任务发来的 ready 批次是
            #   21B, 其中 plain[11] == 0x15; 参考 C# 的自动开局判据正是这一条
            #   (`pushData[11] == 0x15`)。旧代码只认 16B ROOM_READY_BATCH,
            #   所以从不推 game start, 客户端一直停在“战斗开始”且不连 28960。
            #   保留 16B 常量作为兼容路径, 新增 0x15 这条参考实现判据。
            has_ready = (bytes(batch or b"") == cc.ROOM_READY_BATCH
                         or (len(plain or b"") > 11 and plain[11] == 0x15))
            pushes = []
            # ★ 2026-10-04 重做(照抄三方 CodolLocalLobbyServer.cs:1399-1412 的 SendChannelMessage 分支):
            #   ① 空 ACK(BuildTaskReply(..., null)) —— 我们已有;
            #   ② **把客户端这条频道消息原样回显**成频道广播:
            #        BuildPushFrameWithSender(seq, service=11, pushData=客户端 payload,
            #                                 senderId=1, senderName="Player")
            #      其信封 = cc.instant_push_body(1, "Player", <payload>, kind=11)(已逐字节核对)。
            #   旧代码推的是无关的 16B ROOM_READY_BATCH 常量 → 客户端收到一条它没发过的消息,
            #   同秒 reset(lobby_srv.log 00:50:14 / 00:50:27 / 00:52:05 / 00:53:45 四次复现)。
            #   ③ ★"准备"批次(batch == 16B ROOM_READY_BATCH，ol-mod 的 CapturedReadyMessage) →
            #      再推一条 **game start**(照抄三方 1414-1434)。**注意**：这条路两个来源都不太站得住 ——
            #      ol-mod 根本不从大厅推开局(它把 RoomEvent::Ready 交给独立的 sharedRoomClient_/
            #      DedicatedBookingDispatcher 子系统)；三方的 gameStartData 是不透明抓包常量、
            #      且从未在 11/4 场景验证过(其 lsg.log 里没有 service=11)。见 HANDOFF §13.9。
            sub = plain[11] if (plain and len(plain) > 11) else None
            if ch and os.path.exists(os.path.join(OUTDIR, "ready_push.on")):
                pushes.append((2, cc.instant_push_body(1, "Player", bytes(plain or b""), kind=11)))
                if has_ready:
                    pushes.append((2, cc.instant_push_body(0, "Server",
                                                           cc.GAME_START_PAYLOAD, kind=11)))
                    try:
                        _addr67 = build_bd_common_addr_67(GAME_IP, GAME_PORT)
                        _sg_payload = build_startgame_payload(_addr67, SESSION_ID, SEC_KEY)
                        _r_push = build_room_push(1, "HostUser", ROOM_ID, _sg_payload)
                        pushes.append((2, _r_push))
                        log("       ★ 11/4 触发 ready -> 追加推送 dwRoomMessageStartGame (%d 字节)" % len(_sg_payload))
                    except Exception as _e:
                        log("       (11/4 构建 dwRoomMessageStartGame 失败: %r)" % (_e,))
            return ack("0B/4 setRoomData 空应答(channel=0x%X type=%s batch=%d%s len[11]=%s%s)%s"
                       % (ch, tp, len(batch or b""),
                          " ★就是那条 16B ready 批次" if has_ready else "",
                          ("0x%02X" % sub) if sub is not None else "-",
                          "(=blob 长度低字节)" if sub is not None else "",
                          ", 已回显频道推送+game start" if len(pushes) > 1
                          else (", 已回显频道推送(三方同款)" if pushes else "")))[:2] + (pushes,)
        if task == 5:
            return ack("0B/5 publishChannelMessage 空应答")
        if task == 10:
            return ack("0B/10 空应答")
        return ack("0B/%d 空应答(payload=%d)" % (task, len(plain or b"")))

    # ---------------- 即时消息 0x06(=6) —— 照抄 ol-mod InstantMessageService ----------------
    if service == 6:
        if task in (5, 14, 18):
            body = plain or b""
            # ★★ 实测(2026-10-03): 真实客户端发的是 "mmbook 1 <base64> 0", **不是** "mmstart <token>"。
            #    三方成功日志同形: seq=49 `6/14 size=46` payload 以 0A 01 00..00 13 08 1B 00 00 00
            #    17 00 00 00 6D 6D 62 6F 6F 6B ...("mmbook 1 AQAAAAAAAAA= 0") 开头,
            #    服务端收到后**立刻**推 "mmbook accepted" -> 客户端这才去连战斗服 28960。
            #    (他们: RAW_FIRINGRANGE_BOOKING_PUSH bytes=98 data=20)
            if re.search(rb"mmbook[^\x00]{0,120}", body):
                log("LOBBY_MMBOOK_RECEIVED request_id=%s playlist=%s map=%s mode=%s room_id=%s client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), CURRENT_LOBBY_STATE.get("playlist", "unknown"), CURRENT_LOBBY_STATE.get("map", "unknown"), CURRENT_LOBBY_STATE.get("mode", "unknown"), CURRENT_LOBBY_STATE.get("room_id", "-"), CURRENT_LOBBY_ADDR))
                pushes = []
                if os.path.exists(FR_BOOKING_FLAG) or os.path.exists(FR_SESSION_FLAG):
                    accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
                    pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
                    log("LOBBY_MMBOOK_RESPONDED request_id=%s playlist=%s map=%s mode=%s room_id=%s client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), CURRENT_LOBBY_STATE.get("playlist", "unknown"), CURRENT_LOBBY_STATE.get("map", "unknown"), CURRENT_LOBBY_STATE.get("mode", "unknown"), CURRENT_LOBBY_STATE.get("room_id", "-"), CURRENT_LOBBY_ADDR))
                    return ack("6/%d 命中 'mmbook' -> push 'mmbook accepted'(data=%d)"
                               % (task, len(accepted)))[:2] + (pushes,)
                return ack("6/%d 命中 'mmbook' (booking 开关未开, 仅空应答)" % task)[:2] + ([],)
            # 兼容 ol-mod 的写法: "mmstart <token>"; token 的 FNV-1a == 0xDEC30B2A 才推送。
            m = re.search(rb"mmstart[^\x00]{0,512}", body)
            if m:
                full_cmd = m.group(0)
                tok = full_cmd.split()
                token = tok[1] if len(tok) > 1 else b""
                fnv = _fnv1a(token)
                # ★ 2026-10-07: 这条命令里带着客户端实际选择的 gametype/map。
                #   之前只记 token, 无法看出 PvE 选的是 coop_training_mp_cargoship,
                #   导致 21/5 一直回 mp_firingrange。现在完整记录, 便于逐项对齐。
                _cmd_txt = full_cmd.decode("latin1", "replace")
                _map = re.search(r"\bmap\s+([^;\s]+)", _cmd_txt)
                _gt = re.search(r"\bg_gametype\s+([^;\s]+)", _cmd_txt)
                log("       ★ mmstart 完整命令: %s" % _cmd_txt)
                log("LOBBY_MMSTART_RECEIVED request_id=%s playlist=%s map=%s mode=%s room_id=%s client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), CURRENT_LOBBY_STATE.get("playlist", "unknown"), _map.group(1) if _map else "unknown", _gt.group(1) if _gt else "unknown", re.search(r"\broomChatChannelID\s+(\d+)", _cmd_txt).group(1) if re.search(r"\broomChatChannelID\s+(\d+)", _cmd_txt) else "unknown", CURRENT_LOBBY_ADDR))
                log("LOBBY_MMSTART_PARSED request_id=%s playlist=%s map=%s mode=%s room_id=%s client=%s session_id=0x1122334455667788" % (CURRENT_LOBBY_STATE.get("request_id"), CURRENT_LOBBY_STATE.get("playlist", "unknown"), _map.group(1) if _map else "unknown", _gt.group(1) if _gt else "unknown", re.search(r"\broomChatChannelID\s+(\d+)", _cmd_txt).group(1) if re.search(r"\broomChatChannelID\s+(\d+)", _cmd_txt) else "unknown", CURRENT_LOBBY_ADDR))
                log("       ★ mmstart 选择: gametype=%s map=%s"
                    % (_gt.group(1) if _gt else "?",
                       _map.group(1) if _map else "?"))
                # ★★★ 2026-10-07 关键：**记下客户端实际选的地图**。
                #   实测两轮客户端选的是不同的剧情关
                #   （coop_take_mp_fav_tropical / coop_chopper_mp_suburbs），
                #   而 21/5 findSessions 是在这**之前**回答的 —— 我们当时只能猜，
                #   猜错（回 coop_training_mp_cargoship）客户端就不去连战斗服。
                #   做法：把 mmstart 里的 map 落盘成 coop_map.txt；
                #   下一次 21/5 就会回**与客户端所选取一致**的那张图，
                #   形成"选哪关就回哪关"的自校正闭环。
                if _map and _gt:
                    _m_name = _map.group(1)
                    _gt_name = _gt.group(1)
                    try:
                        _p = os.path.join(OUTDIR, "coop_map.txt")
                        _prev = ""
                        if os.path.exists(_p):
                            _prev = open(_p, encoding="utf-8").read().strip()
                        if _prev != _m_name:
                            with open(_p, "w", encoding="utf-8") as _f:
                                _f.write(_m_name + "\n")
                            log("       ★ 已记住剧情地图 -> coop_map.txt = %s"
                                % _m_name)
                        # 更新当前房间状态
                        _is_fr = (_m_name == "coop_train_mp_firingrange")
                        _room_info = {
                            "map": _m_name,
                            "game_type": _gt_name,
                            "is_firing_range": _is_fr,
                            "timestamp": time.time(),
                        }
                        with open(os.path.join(OUTDIR, "active_room.json"), "w", encoding="utf-8") as _rf:
                            import json
                            json.dump(_room_info, _rf, indent=2)
                        log("       ★ mmstart 更新 active_room.json: map=%s gametype=%s"
                            % (_m_name, _gt_name))
                    except Exception as _e:
                        log("       (更新 active_room.json 失败: %r)" % (_e,))
                pushes = []
                try:
                    _addr67 = build_bd_common_addr_67(GAME_IP, GAME_PORT)
                    _sg_payload = build_startgame_payload(_addr67, SESSION_ID, SEC_KEY)
                    _r_push = build_room_push(1, "HostUser", ROOM_ID, _sg_payload)
                    pushes.append((2, _r_push))
                    log("       ★ mmstart 触发 -> 推送 dwRoomMessageStartGame (%d 字节) 击发开局" % len(_sg_payload))
                except Exception as _e:
                    log("       (mmstart 构建 dwRoomMessageStartGame 失败: %r)" % (_e,))
                note = ("6/%d 命中 'mmstart' (token=%r fnv=0x%08X) -> push 'dwRoomMessageStartGame'(%d B)"
                        % (task, token.decode("latin1", "replace"), fnv, len(_sg_payload) if pushes else 0))
                return ([], note, pushes)
            return ack("6/%d 空应答(payload=%d)" % (task, len(body)))
        return ack("6/%d 空应答" % task)
    # ★ 2026-10-05: 走到这里 = 我们**没有映射**这个 service/task。
    #   大厅里"点了没反应/页面空白"的功能大多落在这里, 所以显式记一条,
    #   方便逐项补齐(见 HANDOFF: 大厅待办清单)。
    # ★★ 2026-10-07: `28/1` 特别标注 —— 它是"任务参数"，实测在
    #   `mmstart` **之前**到达，很可能带着"玩家选了哪一关"的线索。
    #   如果能在这一步就拿到关卡/地图，就能让 21/5 一次回对图，
    #   不用靠"上一轮记住、这一轮才对上"的自校正。
    #   这里把它单独记一条便于逐轮对比 payload（不同关卡 = 哪些字节在变）。
    if service == 28 and task == 1:
        log("       ★★ 28/1 任务参数 payload(%d): %s"
            % (len(plain or b""), hexd(plain or b"")))
        try:
            with open(os.path.join(OUTDIR, "task_params.txt"), "a",
                      encoding="utf-8") as _f:
                _f.write("%s\t%s\n" % (time.strftime("%H:%M:%S"),
                                       (plain or b"").hex()))
        except Exception:
            pass
    # ---------------- storage / playerdata 0x66(=102) ----------------
    # 客户端请求 playerdata 字段。字段表来自
    #   _e1_regression\ol-mod-olfinal\tests\game_server\Fixtures\
    #     mp_playerdata.def.1649370.bin    (build 号 1649370 = 我们的目标版本)
    # 实测请求结构:
    #   102/7  08 <count> 然后重复 count 次: 03 01 0A <idx u32>
    #          → 批量读 count 个字段 (索引 0..count-1)
    #   102/1  08 00 00 00 00 | 08 <base> 00 00 00 | 03 xx 0A <idx>
    #          → 读一段字段
    #   102/2  00
    #   102/5  08 02 00 00 00 03 01 03 02 00
    #
    # ★ 关键: 字段表索引 [44..49] 正是
    #     currentMatchSelectPVEDifficulty / PVEMap / PVEMode /
    #     PVPMatch / PVPMode / RootIndex
    #   而 102/7 请求的正好是 0..49 —— 包含 PvE 关卡选择状态。
    #   之前一律回空 ACK ⇒ 客户端读不到"自己选了哪一关" ⇒ 卡在"战斗开始"。
    if service == 0x66:
        if task == 7:
            # 实测请求格式 (556B):
            #   08 <count u32 LE>            ← 5 字节头 (不是 varint!)
            #   重复 count 次:
            #     03 01 0A <idx u32 LE> <val u32 LE>   ← 11 字节/项
            # 应答: 同样的结构, 但 <val> 填当前值。
            try:
                p = plain or b""
                if len(p) < 5 or p[0] != 0x08:
                    return [], "102/7 请求格式不认识 %dB (%s)" % (
                        len(p), (p[:12].hex() if p else "-")), []
                cnt = struct.unpack_from("<I", p, 1)[0]
                if cnt > 512:
                    return [], "102/7 count=%d 太大" % cnt, []
                out = bytearray([0x08])
                out += struct.pack("<I", cnt)
                off = 5
                n = 0
                while n < cnt and off + 7 <= len(p):
                    if p[off] != 0x03 or p[off + 1] != 0x01 or p[off + 2] != 0x0A:
                        break
                    idx = struct.unpack_from("<I", p, off + 3)[0]
                    out += bytes([0x03, 0x01, 0x0A])
                    out += struct.pack("<I", idx)
                    out += struct.pack("<I", 0)      # 值 = 0
                    # 请求里若有原值就跳过它
                    off += 11 if (off + 7 < len(p) and
                                  len(p) - off >= 11) else 7
                    n += 1
                return [bytes(out)], ("storage 102/7 ★ 回显 %d/%d 个字段(值=0) %dB"
                                      % (n, cnt, len(out))), []
            except Exception as e:
                return [], "102/7 构造失败: %r" % (e,), []
        if task == 1:
            # 102/1 是频道订阅。客户端 0x00B8F495 强校验必须返回至少 1 个对象，
            # 内部反序列化器 0x00B8FD60 严格读取 (u32, u8)。回空会导致客户端标记
            # ChannelSubscriptionFail 并拒收后续全部房间信道消息。
            ob = cc.Buf(True)
            ob.u32(0)
            ob.u8(0)
            return [ob.data()], "storage 102/1 订阅成功应答(对象 7B)", []
        if task == 5:
            return [], "storage 102/5 空应答", []
        return [], "storage 102/%d 空应答(payload=%d)" % (task, len(plain or b"")), []
    return [], "UNMAPPED service=%d task=%d payload=%dB -> 空 ACK (功能未实现)" \
                % (service, task, len(plain or b"")), []


def _fnv1a(data):
    """FNV-1a 32 位 —— ol-mod InstantMessageService.cpp:135-139 用的就是它。"""
    h = 0x811C9DC5
    for b in (data or b""):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def _parse_set_room_data(payload):
    """尽量解开 0B/4 setRoomData 的 (u64 channelId, blob batch, u32 type)。

    带 tag 的形式: 0A <u64> | 13 08 <u32 len> <batch...> | 08 <u32 type>
    解不出就返回 (0, b"", None) —— 调用方按无频道处理, 不影响应答。
    """
    d = payload or b""
    ch, batch, tp = 0, b"", None
    off = 0
    try:
        if off + 9 <= len(d) and d[off] == 0x0A:
            ch = struct.unpack_from("<Q", d, off + 1)[0]
            off += 9
        elif off + 8 <= len(d):
            ch = struct.unpack_from("<Q", d, off)[0]      # 无 tag 兜底
            off += 8
        if off + 6 <= len(d) and d[off] == 0x13 and d[off + 1] == 0x08:
            ln = struct.unpack_from("<I", d, off + 2)[0]
            batch = d[off + 6:off + 6 + ln]
            off += 6 + ln
        if off + 5 <= len(d) and d[off] == 0x08:
            tp = struct.unpack_from("<I", d, off + 1)[0]
    except Exception:
        pass
    return ch, batch, tp


def wait_ready(limit=30.0):
    """等客户端的"大厅就绪"信号(客户端分发器只在 [obj+0x5E8]==1 时才受理 0x81)。

    ★ 多客户端: nt10 现在同时写 `lobby_ready.flag` 与 `lobby_ready_<pid>.flag`。
      这里**只要有任一存在**就放行并消费掉全局那个(带 pid 的留给 nt10 自己管)。
      ⚠️ 局限: "哪条连接属于哪个 pid"在 0x82 之前无法判定(身份只在 0x82 的票据里),
      所以这里是"至少有一个客户端就绪即放行"; 尚未就绪的那条会被客户端复位后重连
      (实测客户端本来就会重连 2~3 次, 自愈)。
    """
    t0 = time.time()
    while time.time() - t0 < limit:
        if os.path.exists(READY_FLAG):
            try:
                os.remove(READY_FLAG)
            except Exception:
                pass
            return time.time() - t0
        try:
            if glob.glob(os.path.join(OUTDIR, "lobby_ready_*.flag")):
                return time.time() - t0
        except Exception:
            pass
        time.sleep(0.02)
    return None


def handle_lobby(conn, addr):
    global CURRENT_LOBBY_ADDR, CURRENT_LOBBY_STATE
    CURRENT_LOBBY_ADDR = "%s:%s" % addr
    CURRENT_LOBBY_STATE = {"playlist": "unknown", "map": "unknown", "mode": "unknown", "room_id": "-"}
    log("=== 大厅连接建立 %s ===" % (addr,))
    w = wait_ready(30.0)
    log("  客户端就绪等待: %s" % ("%.2fs" % w if w is not None else "超时(继续)"))
    conn.settimeout(1.0)

    # 1) 等客户端的 28 字节 hello
    hello = b""
    t0 = time.time()
    while time.time() - t0 < 5.0 and len(hello) < 28:
        try:
            d = conn.recv(28 - len(hello))
        except socket.timeout:
            continue
        except Exception as e:
            log("  hello 读取异常: %r" % (e,))
            break
        if not d:
            break
        hello += d
    if hello:
        log("  <- 客户端 hello (%d 字节): %s" % (len(hello), hexd(hello)))
        try:
            open(os.path.join(OUTDIR, "lobby_rx.bin"), "ab").write(hello)
        except Exception:
            pass

    # 2) 发 0x81(回显 hello[20:28]); ★ 保存下来 —— 它要参与 transcript 的密钥派生
    try:
        f = cc.build_handshake_reply(hello)
        sent81 = f
        log("  -> 0x81 (%d 字节) = %s" % (len(f), hexd(f)))
        conn.sendall(f)
    except Exception as e:
        log("  发 0x81 失败: %r" % (e,))
        try:
            conn.close()
        except Exception:
            pass
        return

    # ★★ 每连接的**出站 0x85 帧序号计数器** —— 照抄三方 CodolLocalLobbyServer.cs:1144
    #    `uint num8 = 1u;`：它给**所有**出站 0x85 帧(应答 **和** 推送)共用同一个序号，
    #    每发一帧 +1，与客户端请求的 seq 解耦。
    #    2026-10-04 实测教训: 我们此前让推送"回显请求 seq"，于是应答(seq=N)与推送(seq=N)
    #    **重复**，客户端立刻 ConnectionReset(10054) —— 见 lobby_srv.log 00:50:14。
    #    懒初始化为首帧的请求 seq：无推送时与旧的"回显"行为**逐字节等价**(零回归)，
    #    一旦插入推送，后续帧仍严格 +1(不再重复)，这正是三方 num8 的语义。
    out_seq = None
    # ★★ 2026-10-07: 独立的"应答 id 计数器" —— 对应三方参考的 `++num9`。
    #   参考代码里 **帧 seq 与 replyId 是两个独立计数器**：
    #       BuildTaskReply(secrets, task, num8++, ++num9, ...)
    #   我方旧代码把 replyId 直接**回显请求 seq**（`r["seq"]`）。
    #   在 1:1 应答（请求 seq 与出站 seq 同步递增）时两者同值，看不出差别；
    #   但一旦**在应答之间插入推送**（如 6/14 的 booking push），
    #   出站帧 seq 会比请求 seq 多走一格 → 回显值就与客户端期望的
    #   replyId 错位 → 客户端匹配不上 → ClientException / "服务器繁忙"。
    #   所以这里改成独立递增，与参考一致。
    reply_id = 0
    sent83 = False
    buf = b""
    ntasks = 0
    pending = []          # ★ 密钥快照还没就绪时先把 0x85 攒着, 一旦有 key 再解
    keys_logged = False
    # ★ 2026-10-07: "候选密钥组都没过 HMAC"只提示一次, 避免刷屏；
    #   命中后置回 False（见下面 conn_keys 命中处）。
    pending_waited = False
    sent81 = b""          # 我们实际发出的 0x81(要进 transcript, 必须原样保存)
    derived = {}          # ★ KDF 派生出来的会话密钥
    conn_keys = {}        # ★ 多客户端: 本条连接专属的密钥(由 HMAC 试解确定)
    conn_sk = ""          # 本条连接从 0x82 票据[97:121] 读出的会话密钥 hex
    t0 = time.time()
    while time.time() - t0 < 600:
        # ---- ① 先把攒着的 0x85 处理掉(密钥可能刚被 nt10 写出来) ----
        if pending:
            # ★ 密钥组还没定: 用首个待解帧 **按 HMAC 试解**挑一组(唯一可靠判据)。
            if not conn_keys.get("_ok"):
                k, _r = pick_keyset(pending[0], conn_sk or None)
                if k is not None:
                    k["_ok"] = True
                    conn_keys = k
                    log("  [keys] ★ 试解命中: 密钥组 src=%s aes_out=%s challenge=%s"
                        % (k.get("src"), k["aes_out"].hex(),
                           (k.get("challenge") or b"").hex() or "(无)"))
                elif keys_logged is False:
                    if not read_secrets().get("aes_out") and not load_kdf_sessions_all():
                        log("  [keys] 还没有任何可用密钥组, 继续攒帧")
                    keys_logged = None      # 只提示一次
            # ★★★ 2026-10-07 关键修复：**候选密钥组没过 HMAC 时，绝不"硬解"**。
            #   实机实录（15:29~15:30 连续 3 次断连）：
            #     同一会话密钥 96149686… 在 kdf_sessions.txt 里累积到 2/3/4 组
            #     （每次重连 nt10 都会追加一组新的派生结果）。此时 pick_keyset
            #     **试解失败**，旧代码就回落到 `keys_of(derived)` 里"猜的一组"硬解
            #     客户端首帧，解出满屏乱码：
            #         hmac=BAD marker=0x4F service=133 ver=0x48 declared=79273349
            #     （正常帧永远是 marker=0x86 / ver=0x03 / declared 几十）。
            #     该帧随后被 `pending = []` 丢掉、**永不回应** →
            #     客户端超时 → 重连 → nt10 又追加一组 → 再失败 → 死循环，
            #     最终 ConnectionResetError(10054)。
            #   正确做法：**没通过 HMAC 就什么都不做** —— 帧留在 pending，
            #   等 nt10 把正确的那组写进 kdf_sessions.txt 后自然命中。
            if conn_keys.get("_ok"):
                sec = conn_keys
            else:
                sec = None
                if not pending_waited:
                    log("  [keys] 现有 %d 组候选都没通过 HMAC —— 暂不解码, "
                        "保留待解帧等 nt10 写入正确密钥后重试"
                        % sum(1 for _ in load_kdf_sessions_all()))
                    pending_waited = True
            if sec is not None and sec.get("aes_out") and sec.get("hmac_out"):
                if not keys_logged:
                    log("  [keys] 拿到会话密钥 来源=%s pid=%s state=%s challenge=%s"
                        % (sec.get("src"), sec.get("pid"), sec.get("state"),
                           (sec.get("challenge") or b"").hex()))
                    keys_logged = True
                for fr in list(pending):
                    CURRENT_LOBBY_STATE["request_id"] = None
                    try:
                        r = cc.decrypt_task_frame(fr, sec["aes_out"], sec["hmac_out"])
                    except Exception as e:
                        log("  !! 解密异常: %r" % (e,))
                        continue
                    if not r:
                        log("  !! 0x85 解密失败 (%d 字节)" % len(fr))
                        continue
                    ntasks += 1
                    log("  ★ 解密成功 #%d seq=%d hmac=%s marker=0x%02X service=%d ver=0x%02X task=%d declared=%d"
                        % (ntasks, r["seq"], "OK" if r["hmac_ok"] else "BAD",
                           r["marker"], r["service"], r["ver"], r["task"], r["declared"]))
                    if not r["hmac_ok"]:
                        # ★★ 绝不回 BAD 帧(2026-10-03 实测教训, 见 HANDOFF §13.8):
                        #    重连时首帧常在密钥就绪前到达, 用旧/错密钥硬解就得到 hmac=BAD 的乱码。
                        #    若照旧回一条应答, 客户端发现应答与自己的请求对不上 -> 立刻断连 ->
                        #    再重连 -> **无限死循环**。游戏内表现就是:
                        #      "大厅服务遇到了一个服务中断, 连接已经被重新建立,
                        #       但是所有在重连中运行的任务已经被取消"
                        #    而靶场因为 booking 任务被取消, 提示"服务器繁忙"。
                        #    正确做法: **不回**, 把原始帧塞回 pending, 等下一轮密钥刷新后重解。
                        log("       (hmac=BAD -> 不回, 塞回 pending 待密钥刷新后重解)")
                        pending.append(fr)
                        continue
                    if r["payload"]:
                        CURRENT_LOBBY_STATE["request_id"] = r["seq"]
                        log("       payload(%d): %s" % (len(r["payload"]), hexd(r["payload"][:96])))
                        try:
                            open(os.path.join(OUTDIR, "lobby_tasks.bin"), "ab").write(
                                bytes([r["service"], r["task"]])
                                + struct.pack("<I", len(r["payload"])) + r["payload"])
                        except Exception:
                            pass
                    objs, note, pushes = reply_objects(r["service"], r["task"], r["payload"])
                    if note:
                        log("       -> %s" % note)
                    try:
                        # ★ 应答的 seq = 本连接的出站帧计数器(首帧懒初始化为请求 seq);
                        #   replyId 仍回显请求 seq(三方 num9 在 1:1 时与请求 seq 同值)。
                        #   2026-10-03 教训(§13.6): 曾经拿全局计数器 srv_seq 当 replyId —— 推送一旦
                        #   插进来占掉一格, 后续应答的 replyId 就整体错位, 客户端匹配不上 ->
                        #   卡死 -> ClientException(service=71 task=7) -> ConnectionAborted(10053)。
                        if out_seq is None:
                            out_seq = r["seq"]
                        # ★ 2026-10-07: 曾试过"replyId 用独立计数器（= 参考 ++num9）"，
                        #   实测**没有解决问题**（客户端仍闪退）→ 已回退，
                        #   继续用"回显请求 seq"（1:1 时与参考同值，且是干净大厅的既有行为）。
                        reply_id = r["seq"]
                        rep = cc.build_task_reply_objects(sec["aes_in"], sec["hmac_in"], out_seq,
                                                          r["task"], reply_id, objs, 0)
                        out_seq += 1
                        conn.sendall(rep)
                        log("  -> 0x85 应答 seq=%d(replyId=%d) service=%d task=%d 对象=%d (%d 字节)"
                            % (out_seq - 1, reply_id, r["service"], r["task"], len(objs), len(rep)))
                        # ★★ 2026-10-04 已验证的修法(HANDOFF §13.8): 出站帧 seq 必须严格 +1,
                        #   应答与推送共用同一个 out_seq 计数器, 每发一帧都 +1。
                        #   曾尝试的 push_seq=请求seq+1000 会因序号跳跃导致客户端直接断开(10054)。
                        for _mt, _body in (pushes or []):
                            _pseq = out_seq
                            out_seq += 1
                            pf = cc.build_push(sec["aes_in"], sec["hmac_in"], _pseq, _body, _mt)
                            conn.sendall(pf)
                            log("  -> 0x85 推送 type=%d seq=%d(出站计数器) (%d 字节 body=%d)"
                                % (_mt, _pseq, len(pf), len(_body)))
                    except Exception as e:
                        log("  回 0x85 失败: %r" % (e,))
                        break
                pending = []
        # ---- ② 收数据 ----
        try:
            d = conn.recv(16384)
        except socket.timeout:
            continue
        except Exception as e:
            log("  recv 异常: %r" % (e,))
            break
        if not d:
            log("  对端关闭")
            break
        try:
            open(os.path.join(OUTDIR, "lobby_rx.bin"), "ab").write(d)
        except Exception:
            pass
        buf += d
        frames, buf = cc.parse_frames(buf)
        for fr, kind in frames:
            if kind == "keepalive":
                log("  <- keepalive")
                continue
            if len(fr) < 6:
                continue
            op = fr[5]
            if op == cc.KIND_STAGE1 and not sent83:
                log("  <- 0x82 stage1 (%d 字节): %s" % (len(fr), hexd(fr[:40])))
                # ★ 会话密钥现在有两条来源(按优先级):
                #   ① 本条连接专属(多客户端): 用 0x82 里的票据[97:121] 到
                #      kdf_sessions.txt 里配对 —— 见下面;
                #   ② 全局回退: secrets_kdf.txt(KDF 派生) / secrets.txt(内存快照)。
                derived = {}
                chal, src, waited = None, "内存快照", 0.0
                # ---- ★ 多客户端配对: 0x82 里转发的票据[97:121] 就是该客户端的会话密钥,
                #      而 fake_auth_tls 现在给每个 /auth/ 请求发**唯一的 24B**,
                #      所以它能当"连接 ↔ 密钥"的配对键。 ----
                tk = cc.ticket_from_client_auth(fr)
                session_hit = None
                if tk:
                    # ★ 只用票据[97:121] 定位"是哪个客户端"; **不直接采信**同一会话密钥的第一条
                    #   记录 —— 客户端每次重连都会重新派生一套密钥(同一会话密钥多行),
                    #   真正的挑选放到首个 0x85 上用 HMAC 试解做(见 pick_keyset)。
                    conn_sk = cc.session_key_from_ticket(tk).hex()
                    # ★ 固定启动链竞态(2026-10-05): 0x82 可能比 nt10 的 KDF hook 落盘早
                    #   1~2 秒。此时若先用旧 secrets.txt 的 challenge 回 0x83, 客户端会
                    #   立刻断开(16:01:52/61556 都复现)。这里按会话密钥等本会话的记录,
                    #   拿到后优先用它的 challenge; 等不到才走下面的全局回退。
                    t_key = time.time()
                    while time.time() - t_key < 5.0:
                        hits = [e for e in load_kdf_sessions_all()
                                if e["session_key"].hex() == conn_sk]
                        if hits:
                            session_hit = hits[-1]
                            break
                        time.sleep(0.15)
                    n_cand = len([e for e in load_kdf_sessions_all()
                                  if e["session_key"].hex() == conn_sk])
                    log("  [multi] 本连接会话密钥=%s; kdf_sessions.txt 里有 %d 个候选密钥组"
                        " (等待 %.2fs) -> 稍后按 HMAC 试解挑正确那组"
                        % (conn_sk, n_cand, time.time() - t_key))
                    if session_hit:
                        chal = session_hit["challenge"]
                        src = "kdf-session"
                        waited = time.time() - t_key
                        log("  [keys] 本会话 KDF challenge=%s aes_out=%s"
                            % (chal.hex(), session_hit["aes_out"].hex()))
                else:
                    log("  [multi] 0x82 里取不到票据 -> 只能靠全局密钥")
                if not chal:
                    # 照抄三方 ReadLocalClientChallenge: 轮询等快照里的真 challenge(最多 ~3s)
                    t_wait = time.time()
                    while time.time() - t_wait < 3.0:
                        sec = read_secrets()
                        if sec.get("challenge"):
                            chal = sec["challenge"]
                            break
                        time.sleep(0.15)
                    waited = time.time() - t_wait
                    if not chal:
                        chal, src = H8, "占位"
                f2 = cc.build_stage2(chal)
                log("  -> 0x83 (%d 字节) = %s   [challenge 来源: %s%s]"
                    % (len(f2), hexd(f2), src, (", 等待 %.2fs" % waited) if waited else ""))
                try:
                    conn.sendall(f2)
                    sent83 = True
                except Exception as e:
                    log("  发 0x83 失败: %r" % (e,))
                    break
                continue
            if op == cc.KIND_TASK:
                if not (keys_of(derived) or read_secrets()).get("aes_out"):
                    log("  <- 0x85 (%d 字节) 会话密钥还没就绪, 先攒着" % len(fr))
                pending.append(fr)
                continue
            log("  <- 其它帧 opcode=0x%02X (%d 字节): %s" % (op, len(fr), hexd(fr[:40])))
    try:
        conn.close()
    except Exception:
        pass
    log("=== 大厅连接结束 %s (解出任务 %d 条) ===" % (addr, ntasks))


def handle_raw(conn, addr, tag):
    log("[raw:%s] 连接来自 %s" % (tag, addr))
    conn.settimeout(60)
    try:
        d = conn.recv(4096)
        if d:
            if d[:1] == b"\x16" and len(d) >= 3 and d[1] == 0x03:
                kind = "TLS ClientHello(版本 %02X%02X)" % (d[1], d[2])
            elif len(d) >= 6:
                kind = "疑似明文帧 len=%d type=0x%02X opcode=0x%02X" % (
                    struct.unpack("<I", d[:4])[0], d[4], d[5])
            else:
                kind = "短包"
            log("[raw:%s] 首包 %d 字节 [%s]: %s" % (tag, len(d), kind, hexd(d[:256])))
            try:
                open(os.path.join(OUTDIR, "raw_%s.bin" % tag), "ab").write(d)
            except Exception:
                pass
    except Exception as e:
        log("[raw:%s] 异常 %r" % (tag, e))
    try:
        conn.close()
    except Exception:
        pass


def listen(bind, port, fn, *a):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((bind, port))
        s.listen(16)
    except Exception as e:
        log("[!] %s:%d 监听失败: %r" % (bind, port, e))
        return
    log("[*] 监听 %s:%d" % (bind, port))

    def loop():
        while True:
            try:
                c, ad = s.accept()
            except Exception:
                continue
            threading.Thread(target=fn, args=(c, ad) + a, daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()


def maybe_start_battle_server(bind, port, lobby_bind):
    """★ 靶场战斗服启动条件 —— 逐条照抄 C# CodolLocalLobbyServer.cs:900-940:
         `listenAddress == "127.0.0.2"` **且** 存在 `firingrange-battle.enabled`
         → 起战斗服(CodolLocalBattleServer → 我们这里是 battle_server.py, UDP 127.0.0.1:28960)。

    ★ 本任务只做"按开关决定起/不起 + 记日志", **不动 battle_server.py 内部协议**(另有任务)。
    ⚠️ 注意: run_all.py 默认也会起一份战斗服; 若两处同时起会抢 28960 端口 —— 这里只在
       开关文件存在时才起, 平时(无开关)完全不碰, 因此不影响既有默认流程。
    """
    if lobby_bind != "127.0.0.2":
        log("  战斗服: 未启动 (listen=%s != 127.0.0.2)" % lobby_bind)
        return None
    if not os.path.exists(FR_BATTLE_FLAG):
        log("  战斗服: 未启动 (无开关文件 %s)" % os.path.basename(FR_BATTLE_FLAG))
        return None
    script = os.path.join(OUTDIR, "codol_battle_server.exe")
    if not os.path.exists(script):
        log("  战斗服: 开关在, 但找不到 %s" % script)
        return None
    try:
        out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w")
        err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w")
        p = subprocess.Popen([script, "--bind", bind, "--port", str(port)],
                             cwd=OUTDIR,
                             stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                             creationflags=0x08000000)
        log("  ★ 战斗服已启动: codol_battle_server.exe (C 原生) --bind %s --port %d (pid=%s, UDP)"
            % (bind, port, p.pid))
        return p
    except Exception as e:
        log("  战斗服启动失败: %r" % (e,))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lobby-bind", default="127.0.0.2",
                    help="大厅(lsg)监听地址 —— 三方用 127.0.0.2(formal-zone-lsg)")
    ap.add_argument("--lobby-port", type=int, default=3074)
    ap.add_argument("--raw-ports", default="",
                    help="可选的原始抓包端口(逗号分隔)。默认空 —— 443/80/8081 应交还真实网络")
    a = ap.parse_args()
    log("==== lobby_server 启动 lobby=%s:%d raw=[%s] ===="
        % (a.lobby_bind, a.lobby_port, a.raw_ports))
    # ★ 把 16B securityKey 写给战斗服(它的 ECDH 派生要用同一个; 见 battle_server.py)
    try:
        with open(SEC_KEY_FILE, "w", encoding="ascii") as f:
            f.write(SEC_KEY.hex())
        log("  已写出 battle_security_key.txt = %s (战斗服共用)" % SEC_KEY.hex())
    except Exception as e:
        log("  写 battle_security_key.txt 失败: %r" % (e,))
    listen(a.lobby_bind, a.lobby_port, handle_lobby)
    # ★ 靶场开关状态 + 战斗服启动(照抄 C# 900-940: 仅 127.0.0.2 + 开关文件)
    log("  靶场开关: session=%s booking=%s battle=%s"
        % (os.path.exists(FR_SESSION_FLAG), os.path.exists(FR_BOOKING_FLAG),
           os.path.exists(FR_BATTLE_FLAG)))
    maybe_start_battle_server(FR_BATTLE_BIND, FR_BATTLE_PORT, a.lobby_bind)
    for p in a.raw_ports.split(","):
        p = p.strip()
        if p.isdigit():
            listen("0.0.0.0", int(p), handle_raw, p)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
