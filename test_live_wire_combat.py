import sys, os, socket, struct, time, subprocess, hashlib, hmac

# Add REF_LOBBY_KIT to sys.path for crypto functions
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REF_LOBBY_KIT'))
import battle_server as bs

SERVER_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'build', 'bin', 'CODOLCombatServer.exe')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1', 'config', 'firingrange_live.cfg')
WORKDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CODOL-Combat-Server-v0.1')

print("=" * 60)
print("LIVE WIRE TEST: Testing CODOLCombatServer.exe over Real UDP 28960")
print("=" * 60)

# 1. Start server process
cmd = [SERVER_EXE, "--config", CONFIG_FILE, "--run", "--max-seconds", "8"]
print(f"Launching server: {' '.join(cmd)}")
proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

time.sleep(1.0) # give server 1s to bind socket and init

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 0))
sock.settimeout(2.0)
local_ip, local_port = sock.getsockname()
server_addr = ("127.0.0.1", 28960)
print(f"Client UDP socket bound to {local_ip}:{local_port}")

seq_out = 0

try:
    # --- Step 1: NAT Probe ---
    print("\n[Step 1] Sending NAT probe (29B)...")
    nat_probe = bytearray(bytes.fromhex("0d0200e50f34bf0c6b7f282c223021df5dc0a85501fb557f0000012071"))
    # Patch tail with client's actual IP and port
    nat_probe[23:27] = socket.inet_aton(local_ip)
    nat_probe[27:29] = struct.pack("<H", server_addr[1])
    sock.sendto(nat_probe, server_addr)

    r_nat, _ = sock.recvfrom(4096)
    print(f"  Received NAT reply: len={len(r_nat)} head=0x{r_nat[0]:02X}")
    assert len(r_nat) == 29 and r_nat[0] == 0x0C, f"NAT failed: {r_nat.hex()}"
    print("  [PASS] NAT traversal probe verified!")

    # --- Step 2: DTLS Init ---
    print("\n[Step 2] Sending DTLS init (16B)...")
    client_tag = 0x41D2 # 16850
    dtls_init = bytearray(bytes.fromhex("010200000000d2410100000000000000"))
    sock.sendto(dtls_init, server_addr)

    r_cookie, _ = sock.recvfrom(4096)
    print(f"  Received Cookie: len={len(r_cookie)} type=0x{r_cookie[0]:02X}")
    assert len(r_cookie) == 38 and r_cookie[0] == 0x02, f"DTLS init failed: {r_cookie.hex()}"
    recv_ctag = struct.unpack_from("<H", r_cookie, 2)[0]
    server_tag = struct.unpack_from("<H", r_cookie, 14)[0]
    print(f"  Cookie verified: clientTag={recv_ctag} serverTag={server_tag}")
    assert recv_ctag == client_tag, f"ClientTag mismatch: {recv_ctag} vs {client_tag}"
    print("  [PASS] DTLS init and Cookie verified!")

    # --- Step 3: ECDH Key Exchange ---
    print("\n[Step 3] Performing ECDH Key Exchange (219B -> 114B)...")
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
    print(f"  Received Key Ack: len={len(r_keyack)} type=0x{r_keyack[0]:02X}")
    assert len(r_keyack) == 114 and r_keyack[0] == 0x04, f"Key exchange failed: {r_keyack.hex()}"

    # Derive transport key
    from battle_server import _pt_mul, import_pubkey
    server_pub_point = import_pubkey(bytes(r_keyack[6:106]))
    shared = _pt_mul(client_priv, server_pub_point)
    assert shared is not None, "ECDH scalar multiplication returned None!"
    shared_x = shared[0].to_bytes(28, "big")
    sec_key = b"\x01" * 16 # live retail securityKey
    transport_key = hashlib.sha1(shared_x + sec_key).digest() + b"\x00" * 4
    print(f"  Derived Transport Key (24B): {transport_key.hex()}")
    print("  [PASS] ECDH P-224 Key Exchange verified!")

    # Helper functions for encrypted data frames
    def send_data_frame(plain):
        global seq_out
        seq = seq_out
        seq_out = (seq_out + 1) & 0xFFFF
        pkt = bytearray(16 + len(plain))
        pkt[0] = 0x06
        pkt[1] = 0x02
        pkt[2] = r_cookie[14] # serverTag low
        pkt[3] = r_cookie[15] # serverTag high
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

    # --- Step 4: OOB getchallenge ---
    print("\n[Step 4] Sending OOB getchallenge...")
    send_data_frame(b"\xff\xff\xff\xffgetchallenge 0 \"e7c8a98a6b4c2d0e\"\x00")
    r_chal, _ = sock.recvfrom(4096)
    d_chal = read_data_frame(r_chal)
    assert d_chal is not None, "Failed to decrypt challenge response frame"
    cmd_chal = d_chal[1][4:].split(b"\x00")[0].decode("latin1")
    print(f"  Server response: '{cmd_chal}'")
    assert cmd_chal.startswith("challengeResponse"), f"Unexpected response: {cmd_chal}"
    print("  [PASS] getchallenge -> challengeResponse verified!")

    # --- Step 5: OOB connect ---
    print("\n[Step 5] Sending OOB connect...")
    send_data_frame(b"\xff\xff\xff\xffconnect e7c8a98a6b4c2d0e \"\\name\\Player\\xuid\\e7c8a98a6b4c2d0e\\natType\\1\"\x00")
    
    # Wait for connectResponse and GameState
    got_connect_resp = False
    got_gamestate = False
    t_end = time.time() + 2.0
    while time.time() < t_end:
        try:
            r_pkt, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue
        d_frame = read_data_frame(r_pkt)
        if not d_frame:
            continue
        plain = d_frame[1]
        if plain[:4] == b"\xff\xff\xff\xff":
            cmd = plain[4:].split(b"\x00")[0].decode("latin1")
            print(f"  Server OOB: '{cmd}'")
            if "connectResponse" in cmd:
                got_connect_resp = True
        else:
            print(f"  Server Game Data Frame: seq={d_frame[0]} len={len(plain)}")
            if len(plain) > 100:
                got_gamestate = True
                print("  [PASS] GameState delivered by server!")
                break

    assert got_connect_resp, "Did not receive connectResponse!"
    print("  [PASS] connect -> connectResponse verified!")

    print("\n" + "=" * 60)
    print("ALL LIVE NETWORK HANDSHAKE STEPS PASSED ON REAL UDP 28960!")
    print("=" * 60)

finally:
    sock.close()
    proc.terminate()
    stdout, _ = proc.communicate()
    print("\n--- Server Process Output ---")
    print(stdout)
