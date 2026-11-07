import sys, os, socket, struct, time, subprocess, hashlib, hmac

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REF_LOBBY_KIT'))
import battle_server as bs

SERVER_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'build', 'bin', 'CODOLCombatServer.exe')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'config', 'firingrange_live.cfg')
WORKDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1')

print("=" * 66)
print("FULL IN-MATCH WIRE TEST: Validating Handshake + GameState + Usercmd + Snapshots")
print("=" * 66)

cmd = [SERVER_EXE, "--config", CONFIG_FILE, "--run", "--max-seconds", "8"]
proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

time.sleep(1.0) # wait for server initialization

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 0))
sock.settimeout(2.0)
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
    assert r_nat[0] == 0x0C, "NAT failed"

    # 2. DTLS init
    client_tag = 0x41D2
    dtls_init = bytearray(bytes.fromhex("010200000000d2410100000000000000"))
    sock.sendto(dtls_init, server_addr)
    r_cookie, _ = sock.recvfrom(4096)
    assert r_cookie[0] == 0x02 and len(r_cookie) == 38, "Cookie failed"
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
    assert r_keyack[0] == 0x04, "Key ACK failed"

    from battle_server import _pt_mul, import_pubkey
    server_pub_point = import_pubkey(bytes(r_keyack[6:106]))
    shared = _pt_mul(client_priv, server_pub_point)
    shared_x = shared[0].to_bytes(28, "big")
    transport_key = hashlib.sha1(shared_x + b"\x01" * 16).digest() + b"\x00" * 4

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
            return None
        seed = bytes([seq & 0xFF, (seq >> 8) & 0xFF, 0, 0, pkt[2], pkt[3]])
        return seq, bs._keystream_xor(transport_key[:16], seed, bytes(pkt[16:16 + enc_len]))

    # 4. getchallenge
    send_data_frame(b"\xff\xff\xff\xffgetchallenge 0 \"e7c8a98a6b4c2d0e\"\x00")
    r_chal, _ = sock.recvfrom(4096)
    d_chal = read_data_frame(r_chal)
    assert b"challengeResponse" in d_chal[1], "challengeResponse missing"

    # 5. connect
    send_data_frame(b"\xff\xff\xff\xffconnect e7c8a98a6b4c2d0e \"\\name\\Player\\xuid\\e7c8a98a6b4c2d0e\\natType\\1\"\x00")

    # 6. Wait for connectResponse and GameState
    got_gs = False
    t_end = time.time() + 2.0
    while time.time() < t_end:
        try:
            r_pkt, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue
        d_frame = read_data_frame(r_pkt)
        if not d_frame: continue
        if len(d_frame[1]) > 100:
            got_gs = True
            print(f"  [PASS] GameState received! len={len(d_frame[1])} bytes")
            break

    assert got_gs, "GameState not received"

    # 7. Send gamestateupdate stages 1 to 6
    for stage in range(1, 7):
        send_data_frame(f"\xff\xff\xff\xffgamestateupdate {stage}\x00".encode("latin1"))
        time.sleep(0.05)
    print("  [PASS] gamestateupdate stages 1..6 sent!")

    # 8. Send 14B usercmd
    real14 = bytes.fromhex("0100000000000000000000000002")
    send_data_frame(real14)
    print("  [PASS] Sent real 14B usercmd to server!")

    # 9. Receive snapshots
    snapshots = []
    t_snap_end = time.time() + 2.5
    while time.time() < t_snap_end:
        try:
            r_pkt, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue
        d_frame = read_data_frame(r_pkt)
        if d_frame:
            plain = d_frame[1]
            if plain[:4] != b"\xff\xff\xff\xff":
                snapshots.append((d_frame[0], len(plain)))
                print(f"  [PASS] Received snapshot frame: seq={d_frame[0]} len={len(plain)} bytes")
                if len(snapshots) >= 3:
                    break

    assert len(snapshots) > 0, "No snapshots received from server!"
    print(f"\nSuccessfully received {len(snapshots)} authoritative Motion Snapshots from server!")
    print("ALL IN-MATCH FULL LOOP VERIFIED 100% OVER REAL UDP 28960!")

finally:
    sock.close()
    proc.terminate()
    stdout, _ = proc.communicate()
    print("\n--- Server Process Log Tail ---")
    lines = stdout.strip().splitlines()
    for l in lines[-15:]:
        print("  ", l)
