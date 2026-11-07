import sys, os, socket, struct, time, subprocess, hashlib, hmac

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOBBY_DIR = os.path.join(SCRIPT_DIR, 'REF_LOBBY_KIT')
sys.path.insert(0, LOBBY_DIR)
import battle_server as bs

SERVER_EXE = os.path.join(SCRIPT_DIR, 'CODOL-Combat-Server-v0.1', 'build', 'bin', 'CODOLCombatServer.exe')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'CODOL-Combat-Server-v0.1', 'config', 'firingrange_live.cfg')
WORKDIR = os.path.join(SCRIPT_DIR, 'CODOL-Combat-Server-v0.1')

cmd = [SERVER_EXE, "--config", CONFIG_FILE, "--run", "--max-seconds", "8"]
proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

time.sleep(1.0)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 0))
sock.settimeout(0.5)
local_ip, local_port = sock.getsockname()
server_addr = ("127.0.0.1", 28960)

seq_out = 0

try:
    # 1. NAT
    nat_probe = bytearray(bytes.fromhex("0d0200e50f34bf0c6b7f282c223021df5dc0a85501fb557f0000012071"))
    nat_probe[23:27] = socket.inet_aton(local_ip)
    nat_probe[27:29] = struct.pack("<H", server_addr[1])
    sock.sendto(nat_probe, server_addr)
    r_nat, _ = sock.recvfrom(4096)
    print("NAT replied:", r_nat.hex())

    # 2. DTLS init
    client_tag = 0x41D2
    dtls_init = bytearray(bytes.fromhex("010200000000d2410100000000000000"))
    sock.sendto(dtls_init, server_addr)
    r_cookie, _ = sock.recvfrom(4096)
    print("Cookie replied:", len(r_cookie))
    server_tag = struct.unpack_from("<H", r_cookie, 14)[0]

    # 3. ECDH Key Exchange
    client_priv, client_pub = bs.gen_keypair()
    kx_blob = bytearray(219)
    kx_blob[0] = 0x03
    kx_blob[1] = 0x02
    struct.pack_into("<H", kx_blob, 2, server_tag)
    kx_blob[6:6 + len(r_cookie)] = r_cookie
    struct.pack_into("<Q", kx_blob, 111, 1)
    kx_blob[119:219] = bs.export_pubkey(client_pub)
    sock.sendto(kx_blob, server_addr)
    r_keyack, _ = sock.recvfrom(4096)
    print("KeyAck replied:", len(r_keyack))

    from battle_server import _pt_mul, import_pubkey
    server_pub_point = import_pubkey(bytes(r_keyack[6:106]))
    shared = _pt_mul(client_priv, server_pub_point)
    shared_x = shared[0].to_bytes(28, "big")
    sec_key = bytes.fromhex("01" * 16)
    transport_key = hashlib.sha1(shared_x + sec_key).digest() + hashlib.sha1(sec_key + shared_x).digest()

    def send_data_frame(plain):
        global seq_out
        seq = seq_out
        seq_out = (seq_out + 1) & 0xFFFF
        pkt = bytearray(16 + len(plain))
        pkt[0] = 0x06
        pkt[1] = 0x02
        pkt[2] = r_cookie[14]
        pkt[3] = r_cookie[15]
        struct.pack_into("<H", pkt, 4, seq)
        struct.pack_into("<H", pkt, 14, len(plain))
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        pkt[16:16 + len(plain)] = bs._keystream_xor(transport_key[:16], seed, plain)
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        pkt[6:14] = hmac.new(transport_key[:24], auth, hashlib.sha1).digest()[:8]
        sock.sendto(pkt, server_addr)

    def read_data_frame(pkt):
        if len(pkt) < 16 or pkt[0] != 0x06 or pkt[1] != 0x02:
            return None
        seq = struct.unpack_from("<H", pkt, 4)[0]
        enc_len = struct.unpack_from("<H", pkt, 14)[0]
        auth = bytes(pkt[0:6]) + bytes(pkt[14:])
        mac = hmac.new(transport_key[:24], auth, hashlib.sha1).digest()[:8]
        if mac != bytes(pkt[6:14]):
            print("  MAC MISMATCH! received:", pkt[6:14].hex(), "computed:", mac.hex())
            return None
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        plain = bs._keystream_xor(transport_key[:16], seed, bytes(pkt[16:16 + enc_len]))
        return seq, plain

    # 4. getchallenge
    send_data_frame(b"\xff\xff\xff\xffgetchallenge 0 \"e7c8a98a6b4c2d0e\"\x00")
    r_chal, _ = sock.recvfrom(4096)
    d_chal = read_data_frame(r_chal)
    print("chal response:", d_chal[1][:30])

    # 5. connect
    send_data_frame(b"\xff\xff\xff\xffconnect e7c8a98a6b4c2d0e \"\\name\\Player\\xuid\\e7c8a98a6b4c2d0e\\natType\\1\"\x00")

    # 6. loop to read incoming
    t_end = time.time() + 4.0
    stage = 1
    sent_stage = 0
    while time.time() < t_end:
        try:
            r_pkt, _ = sock.recvfrom(4096)
            d = read_data_frame(r_pkt)
            if d:
                seq, plain = d
                if plain.startswith(b"\xff\xff\xff\xff"):
                    print(f"OOB RX: {plain[:50]}")
                elif len(plain) > 100 and sent_stage == 0:
                    print(f"GameState received! len={len(plain)}")
                    for s in range(1, 7):
                        send_data_frame(f"\xff\xff\xff\xffgamestateupdate {s}\x00".encode("latin1"))
                    sent_stage = 6
                    print("Sent gamestateupdate 1..6")
                    real14 = bytes.fromhex("0100000000000000000000000002")
                    send_data_frame(real14)
                    print("Sent 14B usercmd")
                else:
                    print(f"Snapshot RX: seq={seq} len={len(plain)} plain[:16]={plain[:16].hex()}")
            else:
                print(f"Raw packet (not data frame): len={len(r_pkt)} head={r_pkt[0]:02X}")
        except socket.timeout:
            pass

finally:
    sock.close()
    proc.terminate()
    stdout, _ = proc.communicate()
    print("--- Server Output ---")
    for l in stdout.splitlines()[-25:]:
        print("  ", l)
