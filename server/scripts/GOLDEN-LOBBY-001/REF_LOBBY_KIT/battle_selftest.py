# -*- coding: utf-8 -*-
"""battle_selftest.py —— 战斗服离线自测（不需要游戏）。

为什么需要它
------------
战斗服的每一次改动，目前都只能"起游戏跑一局"来验证 —— 一轮 3~5 分钟，
而且中间任何一步错了都看不出是哪一步。这个脚本用**实测抓到的真实字节**
复放一个客户端，把整条链在几秒内跑完，逐步断言。

数据来源（全部是实机抓包，不是构造）
------------------------------------
`battle_srv.log` 21:28:19~21:28:20 那一轮：真实客户端完成了
    NAT(29B) -> DTLS init(16B) -> cookie+pubkey(219B) -> 数据帧
    -> OOB getchallenge / connect / stats / heartbeat -> usercmd(14B)
全部与我们的实现逐字节对上。

用法
----
    python -X utf8 battle_selftest.py           # 全流程 + 断言
    python -X utf8 battle_selftest.py -v        # 打印每一步的字节

退出码：0 = 全绿；非 0 = 第几步失败。
"""
import argparse
import hashlib
import hmac
import os
import random
import socket
import struct
import sys
import threading
import time

import battle_server as bs

VERBOSE = False


def log(*a):
    print(*a, flush=True)


def vlog(*a):
    if VERBOSE:
        print("     ", *a, flush=True)


# ---------------------------------------------------------------- 真实抓包常量
# NAT 遍历探针（29B）—— 客户端发，服务端只把首字节 0x0D 改成 0x0C 回。
NAT_PROBE = bytes.fromhex("0d0200e50f34bf0c6b7f282c223021df5dc0a85501fb557f00000120 71".replace(" ", ""))

# DTLS init（16B）—— clientTag 在 [6:8]。
DTLS_INIT = bytes.fromhex("010200000000d2410100000000000000")

# 客户端 OOB 文本命令（实测原文）。
OOB_GETCHALLENGE = b'getchallenge 0 "e7c8a98a6b4c2d0e"'
OOB_CONNECT = (b'connect e7c8a98a6b4c2d0e "\\name\\TTctRThTNkNsaWVudA=='
               b'\\xuid\\e7c8a98a6b4c2d0e\\natType\\1"')


class FakeClient(object):
    """按实测顺序复放的客户端。只做协议，不做游戏逻辑。"""

    def __init__(self, port, verbose=False):
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("127.0.0.1", 0))
        self.s.settimeout(2.0)
        self.peer = ("127.0.0.1", port)
        self.seq = 0                    # 出站数据帧序号
        self.key = None                 # 传输密钥（24B）
        self.server_tag = None
        self.cookie = None
        self.client_tag = struct.unpack_from("<H", DTLS_INIT, 6)[0]
        self.oob_seen = []
        self.data_rx = []
        self.gamestate_seq = None

    # ------------------------------------------------------------ 收发原语
    def send(self, pkt):
        self.s.sendto(pkt, self.peer)

    def recv(self):
        try:
            return self.s.recvfrom(4096)[0]
        except socket.timeout:
            return None

    # ------------------------------------------------------------ ① NAT
    def step_nat(self):
        self.send(NAT_PROBE)
        r = self.recv()
        assert r is not None, "NAT 无应答"
        assert len(r) == 29, "NAT 应答长度 %d != 29" % len(r)
        assert r[0] == 0x0C and r[1] == 0x02, "NAT 应答首字节 %02x%02x != 0c02" % (r[0], r[1])
        assert r[2:] == NAT_PROBE[2:], "NAT 应答体与探针不一致"
        vlog("NAT ok len=%d first=%02x" % (len(r), r[0]))

    # ------------------------------------------------------------ ② DTLS init -> cookie
    def step_init(self):
        self.send(DTLS_INIT)
        r = self.recv()
        assert r is not None, "DTLS init 无应答"
        assert len(r) == 38, "cookie 长度 %d != 38" % len(r)
        assert r[0] == 0x02 and r[1] == 0x02, "cookie 首字节 %02x%02x" % (r[0], r[1])
        assert struct.unpack_from("<H", r, 2)[0] == self.client_tag, "cookie clientTag 不对"
        self.cookie = r
        self.server_tag = struct.unpack_from("<H", r, 14)[0]
        vlog("cookie ok len=38 serverTag=%d clientTag=%d" % (self.server_tag, self.client_tag))

    # ------------------------------------------------------------ ③ cookie+pubkey -> key ack
    def step_key_exchange(self):
        priv, pub = bs.gen_keypair()
        self._ecdh_priv = priv
        blob = bytearray(219)
        blob[0] = 0x03
        blob[1] = 0x02
        struct.pack_into("<H", blob, 2, self.server_tag)
        blob[6:6 + len(self.cookie)] = self.cookie       # cookie 落在 [6:44]
        struct.pack_into("<Q", blob, 111, 1)
        blob[119:219] = bs.export_pubkey(pub)
        self.send(bytes(blob))
        r = self.recv()
        assert r is not None, "key exchange 无应答"
        assert len(r) == 114, "key ack 长度 %d != 114" % len(r)
        assert r[0] == 0x04 and r[1] == 0x02, "key ack 首字节 %02x%02x" % (r[0], r[1])
        assert r[106] == 1, "key ack[106] != 1"
        from battle_server import _pt_mul, import_pubkey
        px, py = import_pubkey(bytes(r[6:106]))
        shared = _pt_mul(self._ecdh_priv, (px, py))
        assert shared is not None, "ECDH 退化"
        raw = shared[0].to_bytes(28, "big")
        self.key = hashlib.sha1(raw + b"\x01" * 16).digest() + b"\x00" * 4
        vlog("key ack ok len=114 transport=%s" % self.key[:16].hex())

    # ------------------------------------------------------------ ④ 数据帧
    def send_data(self, plain):
        seq = self.seq
        self.seq = (seq + 1) & 0xFFFF
        pkt = bytearray(16 + len(plain))
        pkt[0] = 0x06
        pkt[1] = 0x02
        # ★ 实测：客户端在数据帧 [2:4] 里回填的是**服务端 cookie 里的 serverTag**
        #   （= cookie[14:16]），不是 clientTag。抓包 RX#5 的 `06 02 c3 f2` 里
        #   `f2 c3` = 62147 = 我们刚发出去的 serverTag。服务端 read_data 也按
        #   cookie[14]/[15] 校验 —— 两边一致（早先这里写成 [2:4] 会静默丢包）。
        pkt[2] = self.cookie[14]
        pkt[3] = self.cookie[15]
        struct.pack_into("<H", pkt, 4, seq)
        struct.pack_into("<H", pkt, 14, len(plain))
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        pkt[16:16 + len(plain)] = bs._keystream_xor(self.key[:16], seed, plain)
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        pkt[6:14] = hmac.new(self.key[:24], auth, hashlib.sha1).digest()[:8]
        self.send(bytes(pkt))

    def read_data(self, pkt):
        """解一条服务端数据帧 -> (seq, plaintext)；失败返回 None。"""
        if len(pkt) < 16 or pkt[0] != 0x06 or pkt[1] != 0x02 or self.key is None:
            return None
        seq = struct.unpack_from("<H", pkt, 4)[0]
        enc_len = struct.unpack_from("<H", pkt, 14)[0]
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        mac = hmac.new(self.key[:24], auth, hashlib.sha1).digest()[:8]
        if mac != bytes(pkt[6:14]):
            return None
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        return seq, bs._keystream_xor(self.key[:16], seed, bytes(pkt[16:16 + enc_len]))

    def drain(self, seconds=1.0):
        """收一段时间；返回 (data_frames, oob_list)。"""
        t0 = time.time()
        data, oob = [], []
        while time.time() - t0 < seconds:
            r = self.recv()
            if r is None:
                continue
            d = self.read_data(r)
            if d is None:
                continue
            # ★ 关键：服务端的 OOB 应答是**包在数据帧里的**
            #   （外层 06 02 ...，解密后的明文才以 FF FF FF FF 开头）。
            #   抓包 TX_DATA(24B) 后紧跟 TX_GAME_OOB 就是这个结构。
            _seq, plain = d
            if plain[:4] == b"\xff\xff\xff\xff":
                cmd = plain[4:].split(b"\x00")[0].decode("latin1", "replace")
                oob.append(cmd)
                self.oob_seen.append(cmd)
                vlog("OOB <-", cmd[:60])
            else:
                data.append(d)
                vlog("DATA <- seq=%d len=%d" % (d[0], len(d[1])))
        return data, oob

    # ------------------------------------------------------------ ⑤ OOB 包裹
    def send_oob(self, text):
        self.send_data(b"\xff\xff\xff\xff" + text + b"\x00")

    def step_getchallenge(self):
        self.send_oob(OOB_GETCHALLENGE)
        _, oob = self.drain(1.5)
        assert any(c.startswith("challengeResponse") for c in oob), \
            "没收到 challengeResponse（收到 %r）" % oob
        vlog("challengeResponse ok")

    def step_connect(self):
        self.send_oob(OOB_CONNECT)
        # ★ 服务端在 connect 应答之后**紧接着**就推首个 game state（这是刚修的
        #   行为），所以这里必须把数据帧也留下来，不能只看 OOB。
        data, oob = self.drain(1.5)
        assert any(c.startswith("connectResponse") for c in oob), \
            "没收到 connectResponse（收到 %r）" % oob
        self.pending_gamestate = data
        vlog("connectResponse ok")

    def step_stats(self):
        total = 826
        chunk = 1238
        body = bytes(random.randrange(256) for _ in range(min(chunk, total)))
        pkt = (b"\xff\xff\xff\xff" + b"stats\x00" + bytes([0]) +
               struct.pack("<H", total) + body)
        self.send_data(pkt)
        _, oob = self.drain(1.5)
        assert any(c.startswith("statResponse") for c in oob), \
            "没收到 statResponse（收到 %r）" % oob
        vlog("statResponse ok")

    def step_heartbeat(self, n=2):
        for _ in range(n):
            self.send_oob(b"heartbeat")
            _, oob = self.drain(0.4)
            assert any(c.startswith("heartbeatresponse") for c in oob), \
                "没收到 heartbeatresponse（收到 %r）" % oob
        vlog("heartbeat x%d ok" % n)

    # ------------------------------------------------------------ ⑥ 等 game state
    def wait_gamestate(self, seconds=4.0):
        """连接建好后服务端应主动下发 game state。"""
        # 先在 step_connect 期间已经收到的那批里找
        for d in getattr(self, "pending_gamestate", []) or []:
            if len(d[1]) > 8:
                self.gamestate_seq = d[0]
                vlog("gamestate(early) seq=%d len=%d" % (d[0], len(d[1])))
                return d
        t0 = time.time()
        while time.time() - t0 < seconds:
            r = self.recv()
            if r is None:
                continue
            d = self.read_data(r)
            if d is None:
                continue
            seq, plain = d
            if len(plain) > 8:
                self.gamestate_seq = seq
                vlog("gamestate seq=%d len=%d head=%s" % (seq, len(plain), plain[:12].hex()))
                return seq, plain
        return None, None


def check_gamestate(plain):
    """核对 game state 明文里是否含预期的 configstring。"""
    txt = bytes(plain[4:])
    return b"g_gametype" in txt or b"mapname" in txt or b"coop" in txt


def main():
    global VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--port", type=int, default=28961)
    a = ap.parse_args()
    VERBOSE = a.verbose

    log("=" * 66)
    log("战斗服离线自测（复放真实抓包，不需要游戏）")
    log("=" * 66)

    from battle_server import (gen_keypair, read_security_key, try_build_nat_reply,
                               try_build_init_ack, try_build_key_exchange_ack,
                               read_data as bs_read_data, handle_plain,
                               pump_gamestate, pump_snapshot)
    import battle_server

    battle_server._SESSION_KEY = gen_keypair()
    sk = read_security_key()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", a.port))
    sock.settimeout(0.01)

    stop = {"v": False}

    def serve():
        while not stop["v"]:
            try:
                pkt, peer = sock.recvfrom(4096)
            except socket.timeout:
                pkt = None
            except OSError:
                break
            if pkt is not None:
                key = "%s:%d" % peer
                assoc = battle_server.ASSOCS.get(key)
                handled = False
                if assoc is not None:
                    r = bs_read_data(pkt, assoc)
                    if r is not None:
                        assoc["last_rx"] = time.time()
                        handle_plain(sock, assoc, r[1])
                        handled = True
                if not handled:
                    rep = try_build_nat_reply(pkt)
                    if rep:
                        sock.sendto(rep, peer)
                    else:
                        rep = try_build_init_ack(pkt, peer)
                        if rep:
                            sock.sendto(rep, peer)
                        else:
                            rep = try_build_key_exchange_ack(pkt, peer, sk)
                            if rep:
                                sock.sendto(rep, peer)
            for assoc in list(battle_server.ASSOCS.values()):
                pump_gamestate(sock, assoc)
                pump_snapshot(sock, assoc)

    th = threading.Thread(target=serve, daemon=True)
    th.start()

    c = FakeClient(a.port, VERBOSE)
    steps = [
        ("① NAT 遍历", c.step_nat),
        ("② DTLS init -> 38B cookie", c.step_init),
        ("③ cookie+公钥 -> 114B key ack", c.step_key_exchange),
        ("④ OOB getchallenge", c.step_getchallenge),
        ("⑤ OOB connect", c.step_connect),
        ("⑥ stats 分块", c.step_stats),
        ("⑦ heartbeat x2", c.step_heartbeat),
    ]
    rc = 0
    for name, fn in steps:
        try:
            fn()
            log("  [OK] %s" % name)
        except AssertionError as e:
            log("  [FAIL] %s: %s" % (name, e))
            rc = 1
            break

    if rc == 0:
        log("  ... 等 game state（服务端主动推）")
        seq, plain = c.wait_gamestate(4.0)
        if seq is None:
            log("  [FAIL] ⑧ 服务端没主动下发 game state")
            log("       → 检查 pump_gamestate 的 gate：ready / gamestate_due / gamestate_loading")
            rc = 1
        elif not check_gamestate(plain):
            log("  [FAIL] ⑧ game state 内容里没有 g_gametype/mapname/coop")
            rc = 1
        else:
            log("  [OK] ⑧ game state seq=%d len=%d" % (seq, len(plain)))

    if rc == 0:
        # ★ 用**真实抓包解出来的** 14B 明文，不是全零。
        #   实录（battle_srv.log 21:28:24 RX#17，用会话密钥 22d0fa68… 解出）：
        #       01 00 00 00 00 00 00 00 00 00 00 00 00 02
        #   head=1（高 3 位=0 → netchan 分支）、body=plain[13:]=0x02，
        #   read_reliable/read_input 都不抛异常。全零的假包反而会
        #   `REJECT_USERCMD reason=Truncated bytes`，不是客户端真实行为。
        #                head     ack[5:9]        ...            terminator 0x02
        #                01 00 00 00 | 00 00 00 00 | 00 00 00 00 | 00 02  (共 14B)
        c.send_data(bytes.fromhex("0100000000000000000000000002"))
        snaps, _ = c.drain(1.5)
        log("  [OK] ⑨ 快照/数据帧 %d 条" % len(snaps))

    # ⑩ 真实 usercmd 必须被解析器接受（不能 REJECT_USERCMD）
    if rc == 0:
        import struct as _s
        plain = bytes.fromhex("0100000000000000000000000002")
        head = _s.unpack_from("<I", plain, 0)[0]
        ack = _s.unpack_from("<I", plain, 5)[0] & 0x1FFFFFFF
        body = bytearray(plain[13:])
        mask = (ack ^ 1 ^ plain[4]) & 0xFF
        for i in range(len(body)):
            body[i] ^= mask
        assert (head & 0xE0000000) == 0, "真实 14B 包没进 netchan 分支"
        ok = True
        try:
            from battle_server import read_reliable, read_input
            read_reliable(bytes(body))
            read_input(bytes(body), ack, None)
        except Exception as e:
            ok = False
            log("  [FAIL] ⑩ 真实 14B usercmd 被拒: %r" % e)
        if ok:
            log("  [OK] ⑩ 真实 14B usercmd 解析通过（head=0x%08X）" % head)
        else:
            rc = 1

    # ⑪ 快照必须在 game state 之后**自动**开始（不能等客户端的 gamestateupdate）
    #    ★ 回归护栏：真实客户端从不发 `gamestateupdate 6`
    #      （抓包实录 0 次），所以快照绝不能只靠那条命令触发。
    if rc == 0:
        # 先让 game state 那 0.5s 的 snapshot_due 到期
        snaps, _ = c.drain(2.5)
        # 再喂一条真实 usercmd，逼服务端走完整输入处理
        for _ in range(3):
            c.send_data(bytes.fromhex("0100000000000000000000000002"))
            time.sleep(0.05)
        more, _ = c.drain(2.0)
        total = len(snaps) + len(more)
        if total == 0:
            log("  [FAIL] ⑪ 快照根本没开始（snapshot_due 没被置位）")
            log("       → 检查 pump_gamestate 里有没有启动 snapshot_due")
            rc = 1
        else:
            log("  [OK] ⑪ 快照自动开始，共 %d 条" % total)

    # ⑫ 快照字段序列必须覆盖真实客户端要求的 idx 21..24（武器槽）
    #    ★ 回归护栏（2026-10-07）：真实 playerstate-motion-trace 解出
    #      idx 21/22/23/24 是**武器槽**（值 1157/0/0/0），不是事件数组。
    #      旧代码往那里写 eq.events[i]，客户端会把事件号当武器 id —— 语义错位。
    #      静态检查源码即可（不依赖运行）：
    #        · 字面量形式      w.index(21, prev)
    #        · 循环形式        w.index(21 + i, prev)
    if rc == 0:
        try:
            import re as _re
            _src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "battle_server.py"), encoding="utf-8").read()
            _m = _re.search(
                r"def _build_motion_snapshot.*?return bytes\(w\.data\), w\.bit",
                _src, _re.S)
            _body = _m.group(0)
            _literals = {int(x) for x in _re.findall(r"w\.index\((\d+), prev\)", _body)}
            _loops = _re.findall(r"w\.index\((\d+)\s*\+\s*i,\s*prev\)", _body)
            for _base in _loops:
                _literals |= {int(_base) + i for i in range(4)}
            _missing = [i for i in (21, 22, 23, 24) if i not in _literals]
            if _missing:
                log("  [FAIL] ⑫ 快照缺武器槽字段 idx=%s" % _missing)
                rc = 1
            else:
                log("  [OK] ⑫ 快照含武器槽字段 idx=21..24（语义已对齐）")
        except Exception as e:
            log("  [FAIL] ⑫ 无法核对快照字段序列: %r" % e)
            rc = 1

    # ⑬ 快照字段序列必须与真实 trace **完全一致**（29/29）
    #    ★ 回归护栏（2026-10-07）：我们用 snapshot_diff 把序列对齐到实录，
    #      这里把它固化 —— 任何改动只要让序列偏离就会报 FAIL。
    #      实录（playerstate-motion-trace.json）:
    #        68 之后直接是 84（编码 1bit0 + 4bit15）；
    #        旧代码写内容但**漏了 w.index(84)**，会让整段错位。
    if rc == 0:
        try:
            import snapshot_diff as _sd
            _ours = _sd.our_index_order()
            _real = [0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
                     21, 22, 23, 24, 29, 34, 38, 39, 41, 44, 54, 56,
                     60, 61, 63, 68, 84]
            if _ours != _real:
                log("  [FAIL] ⑬ 快照字段序列与实录不一致")
                log("       我方: %s" % _ours)
                log("       实录: %s" % _real)
                rc = 1
            else:
                log("  [OK] ⑬ 快照字段序列与实录完全一致（29/29）")
        except Exception as e:
            log("  [FAIL] ⑬ 无法核对字段序列: %r" % e)
            rc = 1

    stop["v"] = True
    log("-" * 66)
    log("全绿。" if rc == 0 else "有失败项。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
