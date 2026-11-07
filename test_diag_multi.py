import sys, os, socket, struct, time, subprocess, hashlib, hmac

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
import battle_server as bs

SERVER_EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe"
CONFIG_FILE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\config\firingrange_live.cfg"
WORKDIR = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1"

cmd = [SERVER_EXE, "--config", CONFIG_FILE, "--run", "--max-seconds", "10", "+set", "sv_maxclients", "2"]
proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
time.sleep(1.0)
server_addr = ("127.0.0.1", 28960)

class WireClient:
    def __init__(self, name, ctag):
        self.name = name
        self.ctag = ctag
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.5)
        self.local_ip, self.local_port = self.sock.getsockname()
        self.seq_out = 0
        self.cookie = None
        self.server_tag = None
        self.transport_key = None

    def do_handshake(self):
        # NAT
        probe = bytearray(bytes.fromhex("0d0200e50f34bf0c6b7f282c223021df5dc0a85501fb557f0000012071"))
        probe[23:27] = socket.inet_aton(self.local_ip)
        probe[27:29] = struct.pack("<H", self.local_port)
        self.sock.sendto(probe, server_addr)
        r, _ = self.sock.recvfrom(4096)
        assert r[0] == 0x0C

        # DTLS init
        dtls_init = bytearray(bytes.fromhex("01020000000000000100000000000000"))
        struct.pack_into("<H", dtls_init, 6, self.ctag)
        self.sock.sendto(dtls_init, server_addr)
        r, _ = self.sock.recvfrom(4096)
        self.cookie = r
        self.server_tag = struct.unpack_from("<H", r, 14)[0]

        # Key Exchange
        client_priv, client_pub = bs.gen_keypair()
        kx_blob = bytearray(219)
        kx_blob[0] = 0x03; kx_blob[1] = 0x02
        struct.pack_into("<H", kx_blob, 2, self.server_tag)
        kx_blob[6:6 + len(self.cookie)] = self.cookie
        struct.pack_into("<Q", kx_blob, 111, 1)
        kx_blob[119:219] = bs.export_pubkey(client_pub)
        self.sock.sendto(kx_blob, server_addr)
        r, _ = self.sock.recvfrom(4096)
        assert r[0] == 0x04

        from battle_server import _pt_mul, import_pubkey
        server_pub_point = import_pubkey(bytes(r[6:106]))
        shared = _pt_mul(client_priv, server_pub_point)
        shared_x = shared[0].to_bytes(28, "big")
        self.transport_key = hashlib.sha1(shared_x + b"\x01" * 16).digest() + b"\x00" * 4

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

    def read_packet(self):
        try:
            pkt, _ = self.sock.recvfrom(4096)
        except socket.timeout:
            return None
        if len(pkt) < 16 or pkt[0] != 0x06 or pkt[1] != 0x02:
            return ("RAW", pkt)
        seq = struct.unpack_from("<H", pkt, 4)[0]
        enc_len = struct.unpack_from("<H", pkt, 14)[0]
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        mac = hmac.new(self.transport_key[:24], auth, hashlib.sha1).digest()[:8]
        if mac != bytes(pkt[6:14]):
            return ("BAD_HMAC", pkt)
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        plain = bs._keystream_xor(self.transport_key[:16], seed, bytes(pkt[16:16 + enc_len]))
        return (seq, plain)

try:
    c1 = WireClient("C1", 0x1111)
    c2 = WireClient("C2", 0x2222)
    c1.do_handshake()
    c2.do_handshake()
    print("Both handshakes complete!")

    c1.send_data(b"\xff\xff\xff\xffgetchallenge 0 \"c1\"\x00")
    c2.send_data(b"\xff\xff\xff\xffgetchallenge 0 \"c2\"\x00")

    # Read challenge responses
    p1 = c1.read_packet()
    p2 = c2.read_packet()
    print("C1 challenge resp:", p1[0] if p1 else None)
    print("C2 challenge resp:", p2[0] if p2 else None)

    c1.send_data(b"\xff\xff\xff\xffconnect c1 \"\\name\\P1\\xuid\\1001\\natType\\1\"\x00")
    c2.send_data(b"\xff\xff\xff\xffconnect c2 \"\\name\\P2\\xuid\\1002\\natType\\1\"\x00")

    # Read incoming packets for 3 seconds
    t0 = time.time()
    while time.time() - t0 < 3.0:
        p1 = c1.read_packet()
        if p1:
            if isinstance(p1[0], int):
                plain = p1[1]
                if plain[:4] == b"\xff\xff\xff\xff":
                    cmd = plain[4:].split(b"\x00")[0]
                    print(f"C1 OOB: {cmd}")
                else:
                    print(f"C1 DATA seq={p1[0]} len={len(plain)}")
            else:
                print(f"C1 {p1[0]}")
        p2 = c2.read_packet()
        if p2:
            if isinstance(p2[0], int):
                plain = p2[1]
                if plain[:4] == b"\xff\xff\xff\xff":
                    cmd = plain[4:].split(b"\x00")[0]
                    print(f"C2 OOB: {cmd}")
                else:
                    print(f"C2 DATA seq={p2[0]} len={len(plain)}")
            else:
                print(f"C2 {p2[0]}")
        time.sleep(0.01)

finally:
    c1.sock.close()
    c2.sock.close()
    proc.terminate()
    stdout, _ = proc.communicate()
    print("\n--- Server Process Tail ---")
    for l in stdout.strip().splitlines()[-15:]:
        print("  ", l)
