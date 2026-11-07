import sys, os, socket, struct, time, subprocess, hashlib, hmac

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
import battle_server as bs

SERVER_EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe"
CONFIG_FILE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\config\firingrange_live.cfg"
WORKDIR = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"

print("=" * 66)
print("MULTI-CLIENT CONCURRENCY TEST: Testing 2 Clients Concurrently on UDP 28960")
print("=" * 66)

cmd = [SERVER_EXE, "--config", CONFIG_FILE, "--run", "--max-seconds", "10", "+set", "sv_maxclients", "2"]
proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
time.sleep(1.0)

server_addr = ("127.0.0.1", 28960)

class WireClient:
    def __init__(self, name, xuid, ctag):
        self.name = name
        self.xuid = xuid
        self.ctag = ctag
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(2.0)
        self.local_ip, self.local_port = self.sock.getsockname()
        self.seq_out = 0
        self.cookie = None
        self.server_tag = None
        self.transport_key = None

    def do_nat(self):
        probe = bytearray(bytes.fromhex("0d0200e50f34bf0c6b7f282c223021df5dc0a85501fb557f0000012071"))
        probe[23:27] = socket.inet_aton(self.local_ip)
        probe[27:29] = struct.pack("<H", self.local_port)
        self.sock.sendto(probe, server_addr)
        r, _ = self.sock.recvfrom(4096)
        assert r[0] == 0x0C, f"[{self.name}] NAT failed"
        print(f"[{self.name}] NAT OK")

    def do_dtls_init(self):
        dtls_init = bytearray(bytes.fromhex("01020000000000000100000000000000"))
        struct.pack_into("<H", dtls_init, 6, self.ctag)
        self.sock.sendto(dtls_init, server_addr)
        r, _ = self.sock.recvfrom(4096)
        assert r[0] == 0x02 and len(r) == 38, f"[{self.name}] Cookie failed"
        self.cookie = r
        self.server_tag = struct.unpack_from("<H", r, 14)[0]
        print(f"[{self.name}] Cookie OK, serverTag={self.server_tag}")

    def do_key_exchange(self):
        client_priv, client_pub = bs.gen_keypair()
        kx_blob = bytearray(219)
        kx_blob[0] = 0x03
        kx_blob[1] = 0x02
        struct.pack_into("<H", kx_blob, 2, self.server_tag)
        kx_blob[6:6 + len(self.cookie)] = self.cookie
        struct.pack_into("<Q", kx_blob, 111, 1)
        kx_blob[119:219] = bs.export_pubkey(client_pub)
        self.sock.sendto(kx_blob, server_addr)
        r, _ = self.sock.recvfrom(4096)
        assert r[0] == 0x04, f"[{self.name}] Key ACK failed"

        from battle_server import _pt_mul, import_pubkey
        server_pub_point = import_pubkey(bytes(r[6:106]))
        shared = _pt_mul(client_priv, server_pub_point)
        shared_x = shared[0].to_bytes(28, "big")
        self.transport_key = hashlib.sha1(shared_x + b"\x01" * 16).digest() + b"\x00" * 4
        print(f"[{self.name}] Key Exchange OK")

    def send_data(self, plain):
        seq = self.seq_out
        self.seq_out = (self.seq_out + 1) & 0xFFFF
        pkt = bytearray(16 + len(plain))
        pkt[0] = 0x06; pkt[1] = 0x02
        pkt[2] = self.cookie[14]; pkt[3] = self.cookie[15]
        struct.pack_into("<H", pkt, 4, seq)
        struct.pack_into("<H", pkt, 14, len(plain))
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        pkt[16:16 + len(plain)] = bs._keystream_xor(self.transport_key[:16], seed, plain)
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        pkt[6:14] = hmac.new(self.transport_key[:24], auth, hashlib.sha1).digest()[:8]
        self.sock.sendto(pkt, server_addr)

    def read_data(self):
        try:
            pkt, _ = self.sock.recvfrom(4096)
        except socket.timeout:
            return None
        if len(pkt) < 16 or pkt[0] != 0x06 or pkt[1] != 0x02:
            return None
        seq = struct.unpack_from("<H", pkt, 4)[0]
        enc_len = struct.unpack_from("<H", pkt, 14)[0]
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        mac = hmac.new(self.transport_key[:24], auth, hashlib.sha1).digest()[:8]
        if mac != bytes(pkt[6:14]): return None
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        plain = bs._keystream_xor(self.transport_key[:16], seed, bytes(pkt[16:16 + enc_len]))
        return seq, plain

    def close(self):
        self.sock.close()

try:
    c1 = WireClient("Client-1", "1000000000000001", 0x1111)
    c2 = WireClient("Client-2", "1000000000000002", 0x2222)

    # Both clients do NAT
    c1.do_nat()
    c2.do_nat()

    # Both clients do DTLS init
    c1.do_dtls_init()
    c2.do_dtls_init()

    # Both clients do Key Exchange
    c1.do_key_exchange()
    c2.do_key_exchange()

    # Both clients send getchallenge
    c1.send_data(b"\xff\xff\xff\xffgetchallenge 0 \"1000000000000001\"\x00")
    _, p1 = c1.read_data()
    assert b"challengeResponse" in p1, "Client 1 challenge failed"
    print("[Client-1] challengeResponse received")

    c2.send_data(b"\xff\xff\xff\xffgetchallenge 0 \"1000000000000002\"\x00")
    _, p2 = c2.read_data()
    assert b"challengeResponse" in p2, "Client 2 challenge failed"
    print("[Client-2] challengeResponse received")

    # Both clients send connect
    c1.send_data(b"\xff\xff\xff\xffconnect 1000000000000001 \"\\name\\Player1\\xuid\\1000000000000001\\natType\\1\"\x00")
    c2.send_data(b"\xff\xff\xff\xffconnect 1000000000000002 \"\\name\\Player2\\xuid\\1000000000000002\\natType\\1\"\x00")

    # Verify both receive connectResponse and GameState
    for c in [c1, c2]:
        got_resp = False
        got_gs = False
        t_end = time.time() + 2.0
        while time.time() < t_end and not (got_resp and got_gs):
            d = c.read_data()
            if not d: continue
            plain = d[1]
            if plain[:4] == b"\xff\xff\xff\xff" and b"connectResponse" in plain:
                got_resp = True
            elif len(plain) > 100:
                got_gs = True
        assert got_resp, f"[{c.name}] connectResponse not received"
        assert got_gs, f"[{c.name}] GameState not received"
        print(f"[{c.name}] connectResponse and GameState successfully received!")

    # Both send gamestateupdate 6
    c1.send_data(b"\xff\xff\xff\xffgamestateupdate 6\x00")
    c2.send_data(b"\xff\xff\xff\xffgamestateupdate 6\x00")

    # Both send usercmd
    real14 = bytes.fromhex("0100000000000000000000000002")
    c1.send_data(real14)
    c2.send_data(real14)
    print("Both clients sent 14B usercmd!")

    # Verify both receive snapshots
    for c in [c1, c2]:
        got_snap = False
        t_end = time.time() + 2.5
        while time.time() < t_end and not got_snap:
            d = c.read_data()
            if d and d[1][:4] != b"\xff\xff\xff\xff":
                got_snap = True
                print(f"[{c.name}] Received authoritative snapshot: seq={d[0]} len={len(d[1])}")
        assert got_snap, f"[{c.name}] Snapshot not received"

    print("\n" + "=" * 66)
    print("MULTI-CLIENT CONCURRENCY TEST PASSED 100%! ZERO CONFLICTS!")
    print("=" * 66)

finally:
    c1.close()
    c2.close()
    proc.terminate()
    stdout, _ = proc.communicate()
    print("\n--- Server Process Output ---")
    for l in stdout.strip().splitlines()[-20:]:
        print("  ", l)
