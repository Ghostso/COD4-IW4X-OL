"""Synthetic encrypted UDP peer for an isolated native sh1x server.

Requires the trusted alpha0022 crypto reference and a separate test key file.
Never reads the reference's live securitykey.bin or edits its lobby state.
This verifies transport/connect acceptance, not a playable C1 match.
"""
import argparse
import json
from pathlib import Path
import secrets
import socket
import struct
import sys
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--key-file', type=Path, required=True)
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--request-gamestate', action='store_true', help='Also report encrypted packets after a native in-band request')
    ap.add_argument('--configstrings-output', type=Path, help='Save decoded native gamestate overrides; requires --request-gamestate')
    ap.add_argument('--upload-stats', action='store_true', help='Upload a synthetic 32768-byte profile and verify all missing-chunk masks')
    ap.add_argument('--class-perk-fixture', action='store_true', help='Upload a schema-valid synthetic class-perk profile for codol_class_vm callback checks')
    ap.add_argument('--profile-rcon-password', help='Isolated server test RCON password: verify mounted public-profile acestreak after fixture upload')
    ap.add_argument('--bind-secure-profile', type=Path, help='Use test RCON to bind synthetic secure profile UID 1 to client 0')
    ap.add_argument('--ack-gamestate', action='store_true', help='Decode CS 3 and verify a reliable client command is acknowledged using that server ID')
    ap.add_argument('--pure-catalog', type=Path, help='Send cp from verified C1 archive checksum records; requires --ack-gamestate; server log must confirm validation')
    ap.add_argument('--move', action='store_true', help='Send a native usermove after cp and inspect the first gameplay snapshot')
    ap.add_argument('--delta', action='store_true', help='Acknowledge the baseline, send another usermove, and decode its delta snapshot')
    ap.add_argument('--matchdata-fixture', action='store_true', help='Require the codol_matchdata_vm native GSC record in a gameplay snapshot')
    ap.add_argument('--matchdata-ack', action='store_true', help='Observe a retry, send matchdatadone, and require continued snapshots without match data')
    ap.add_argument('--snapshot-output', type=Path, help='Save the synthetic plaintext snapshot for offline decoding; requires --move')
    args = ap.parse_args()
    if args.configstrings_output and not args.request_gamestate:
        ap.error('--configstrings-output requires --request-gamestate')
    if args.class_perk_fixture and not args.upload_stats:
        ap.error('--class-perk-fixture requires --upload-stats')
    if args.profile_rcon_password and (not args.class_perk_fixture or
            any(c.isspace() or c=='\0' for c in args.profile_rcon_password)):
        ap.error('--profile-rcon-password requires --class-perk-fixture and a password without whitespace/NUL')
    if args.delta and not args.move:
        ap.error('--delta requires --move')
    if args.bind_secure_profile and (not args.profile_rcon_password or
            any(c in str(args.bind_secure_profile) for c in '\0\r\n";')):
        ap.error('--bind-secure-profile requires test RCON and a directory without command delimiters')
    if args.matchdata_fixture and not args.move:
        ap.error('--matchdata-fixture requires --move')
    if args.matchdata_ack and (not args.matchdata_fixture or args.delta):
        ap.error('--matchdata-ack requires --matchdata-fixture without --delta')
    if args.ack_gamestate and not (args.upload_stats and args.request_gamestate):
        ap.error('--ack-gamestate requires --upload-stats --request-gamestate')
    if args.pure_catalog and not args.ack_gamestate:
        ap.error('--pure-catalog requires --ack-gamestate')
    if args.move and not args.pure_catalog:
        ap.error('--move requires --pure-catalog')
    if args.snapshot_output and not args.move:
        ap.error('--snapshot-output requires --move')
    if args.key_file.resolve() == (args.reference / 'securitykey.bin').resolve():
        ap.error('Use a separate test key file, not the active lobby key')
    security = args.key_file.read_bytes()
    if len(security) != 16:
        ap.error('Test key must contain exactly 16 bytes')
    sys.path.insert(0, str(args.reference.resolve()))
    import dtls_crypto as crypto
    from Crypto.PublicKey import ECC

    endpoint = ('127.0.0.1', args.port)
    sid = bytes([70, 0, 0, 0, 0, 0, 0, 0])
    peer_tag = secrets.randbelow(65535) + 1
    private = int(ECC.generate(curve='P-224').d)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('127.0.0.1', 0))
    s.settimeout(1)
    init = struct.pack('<BBHHH', 1, 2, 0, 0, peer_tag) + sid
    deadline = time.monotonic() + 30
    while True:
        s.sendto(init, endpoint)
        try:
            ack, address = s.recvfrom(65535)
            if address == endpoint and len(ack) == 38 and ack[:2] == b'\x02\x02':
                break
        except socket.timeout:
            if time.monotonic() >= deadline:
                raise AssertionError('INIT_ACK timeout')
    assert int.from_bytes(ack[2:4], 'little') == peer_tag
    assert ack[24:28] == socket.inet_aton('127.0.0.1')
    assert int.from_bytes(ack[28:30], 'little') == s.getsockname()[1]
    assert ack[30:38] == sid
    local_tag = int.from_bytes(ack[16:18], 'little')
    echo = struct.pack('<BBHH', 3, 2, local_tag, 0) + ack + bytes(37) + sid + crypto.export_pubkey(private)
    s.sendto(echo, endpoint)
    deadline = time.monotonic() + 5
    while True:
        cookie, address = s.recvfrom(65535)
        assert address == endpoint
        if cookie != ack:
            break
        # INIT retries queued during map startup can produce identical ACKs.
        assert time.monotonic() < deadline, 'COOKIE_ACK timeout after duplicate INIT_ACKs'
    assert address == endpoint and len(cookie) == 114
    assert cookie[:6] == struct.pack('<BBHH', 4, 2, peer_tag, 0)
    assert cookie[106:] == sid
    key, _ = crypto.shared_key20(cookie[6:106], security, private)
    last_receive = 0

    def expect_silent(packet):
        s.sendto(packet, endpoint)
        s.settimeout(0.25)
        try:
            s.recvfrom(65535)
        except socket.timeout:
            pass
        else:
            raise AssertionError('Rejected packet unexpectedly produced a reply')
        finally:
            s.settimeout(1)

    def receive_oob(prefix, require_nul=True):
        nonlocal last_receive
        end = time.monotonic() + 5
        while time.monotonic() < end:
            packet, address = s.recvfrom(65535)
            assert address == endpoint and packet[:2] == b'\x06\x02', 'plaintext response in encrypted mode'
            count, tag, plain, valid = crypto.decrypt_data(packet, key, last_receive)
            assert valid and tag == peer_tag
            assert count > last_receive, 'server reused a DATA counter'
            last_receive = count
            if plain.startswith(b'\xff' * 4 + prefix):
                if not require_nul:
                    return plain[4:]
                assert plain.endswith(b'\0')
                return plain[4:-1]
        raise AssertionError('OOB response timeout')

    request = b'\xff' * 4 + b'getchallenge 0123456789abcdef\0'
    expect_silent(request)  # No plaintext client fallback when transport is enabled.
    first_record = crypto.build_data(request, 1, local_tag, key)
    s.sendto(first_record, endpoint)
    challenge = int(receive_oob(b'challengeResponse ').split()[1])
    expect_silent(first_record)  # DATA replay must not dispatch the challenge twice.
    # Retransmit COOKIE_ECHO after DATA; ACK must be identical and the next
    # encrypted response must retain its original counter progression.
    s.sendto(echo, endpoint)
    repeated, _ = s.recvfrom(65535)
    assert repeated == cookie
    uid = '0123456789abcdef'
    info = (f'\\name\\EncryptedProbe\\xuid\\{uid}\\2490\\-1157214325'
            f'\\challenge\\{challenge}\\qport\\{s.getsockname()[1]}\\rate\\25000\\snaps\\20')
    request = b'\xff' * 4 + f'connect {uid} "{info}"'.encode() + b'\0'
    connect_record = crypto.build_data(request, 2, local_tag, key)
    bad = bytearray(connect_record)
    bad[6] ^= 1
    expect_silent(bad)
    s.sendto(connect_record, endpoint)  # Bad MAC must not consume receive counter 2.
    response = receive_oob(b'connectResponse ').decode('ascii')
    assert '\\protocol\\1\\shortversion\\1.1.1.13' in response
    next_send = 3
    stats_complete = False
    if args.upload_stats:
        profile = bytes((i * 17 + i // 1240) & 255 for i in range(32768))
        if args.class_perk_fixture:
            import zlib
            profile = bytearray(32768)
            struct.pack_into('<II', profile, 4, 220, 0xe4fd5218)
            # Public playerdata root acestreak: record offset 8, upload +4.
            struct.pack_into('<h', profile, 12, 1234)
            struct.pack_into('<h', profile, 0x1511 + 92 + 14, 3002)
            struct.pack_into('<h', profile, 0x1511 + 92 + 16, -1)
            struct.pack_into('<I', profile, 0, zlib.crc32(profile[4:]))
            profile = bytes(profile)
        missing = (1 << 27) - 1
        for index in reversed(range(27)):
            chunk = profile[index * 1240:(index + 1) * 1240]
            request = b'\xff' * 4 + b'stats\0' + struct.pack('<HB', s.getsockname()[1], index) + chunk
            s.sendto(crypto.build_data(request, next_send, local_tag, key), endpoint)
            next_send += 1
            missing &= ~(1 << index)
            assert int(receive_oob(b'statResponse ').split()[1]) == missing
        stats_complete = missing == 0
        request = b'\xff' * 4 + b'heartbeat\0'
        s.sendto(crypto.build_data(request, next_send, local_tag, key), endpoint)
        next_send += 1
        assert receive_oob(b'heartbeatresponse') == b'heartbeatresponse'
        if args.profile_rcon_password:
            request = (b'\xff'*4 + b'rcon ' + args.profile_rcon_password.encode('ascii') +
                       b' codol_checkprofile 0 mp/playerdata.def acestreak\0')
            s.sendto(crypto.build_data(request, next_send, local_tag, key), endpoint)
            next_send += 1
            reply = receive_oob(b'print', require_nul=False)
            assert b'CoDOL profile client 0 field acestreak bits 1234' in reply, reply
            if args.bind_secure_profile:
                request = (b'\xff'*4 + b'rcon ' + args.profile_rcon_password.encode('ascii') +
                    (' codol_bindprofile 0 "' + str(args.bind_secure_profile) + '" 1\0').encode('ascii'))
                s.sendto(crypto.build_data(request, next_send, local_tag, key), endpoint)
                next_send += 1
                reply = receive_oob(b'print\n', require_nul=False)
                assert b'CoDOL secure profile binding client 0: ready' in reply, reply
    post_connect = []
    gamestate = None
    command_texts = {}
    server_command_sequence = 0
    if args.request_gamestate:
        # A mismatched serverId asks the retained handler for gamestate. EOF is
        # encoded with the empty reliable-command key (no client commands yet).
        body = bytes([3 ^ ((challenge ^ 255) & 255)])
        request = struct.pack('<IHBII', 1, s.getsockname()[1], 255, 0, 0) + body
        s.sendto(crypto.build_data(request, next_send, local_tag, key), endpoint)
        next_send += 1
        end = time.monotonic() + 5
        fragments = {}
        while time.monotonic() < end:
            try:
                packet, _ = s.recvfrom(65535)
            except socket.timeout:
                break
            assert packet[:2] == b'\x06\x02'
            count, tag, plain, valid = crypto.decrypt_data(packet, key, last_receive)
            assert valid and tag == peer_tag and count > last_receive
            last_receive = count
            post_connect.append({'length': len(plain), 'header': hex(int.from_bytes(plain[:4], 'little'))})
            sequence = int.from_bytes(plain[:4], 'little')
            if sequence == 0xfffffff0:
                raise AssertionError('Native CoDOL server emitted a IW4OL binary reliable packet')
            if sequence & 0x80000000:
                assert len(plain) >= 10
                index, last, stride, size = struct.unpack_from('<BBHH', plain, 4)
                assert index <= last and stride == 1162 and size == len(plain) - 10
                sequence &= 0x1fffffff
                group = fragments.setdefault(sequence, {'last': last, 'chunks': {}})
                assert group['last'] == last
                group['chunks'][index] = plain[10:]
                if len(group['chunks']) != last + 1:
                    continue
                message = b''.join(group['chunks'][i] for i in range(last + 1))
            else:
                message = plain[4:]
            if len(message) < 5:
                continue
            # No reliable client commands were sent, so the XOR key string is
            # empty. Decode only after complete netchan reassembly.
            message = message[:4] + bytes(v ^ ((challenge ^ sequence) & 255) for v in message[4:])
            cursor = 4
            while cursor < len(message) and message[cursor] == 1:
                cmdseq = int.from_bytes(message[cursor+1:cursor+5], 'little')
                stop = message.index(b'\0', cursor + 5)
                command_texts[cmdseq] = message[cursor+5:stop]
                cursor = stop + 1
            if cursor < len(message) and message[cursor] == 2:
                server_command_sequence = int.from_bytes(message[cursor+1:cursor+5], 'little')
                cursor += 5
                stop = message.index(b'\0', cursor)
                mapname = message[cursor:stop].decode('ascii')
                cursor = stop + 1
                stop = message.index(b'\0', cursor)
                zone = message[cursor:stop].decode('ascii')
                cursor = stop + 5  # NUL plus constant-configstring checksum.
                assert message[cursor] == 3
                entries = int.from_bytes(message[cursor+1:cursor+3], 'little')
                cursor += 3
                bit_cursor = 0

                def bits(count):
                    nonlocal cursor, bit_cursor
                    value = 0
                    for bit in range(count):
                        if bit_cursor % 8 == 0:
                            bit_cursor = cursor * 8
                            cursor += 1
                        value |= ((message[bit_cursor // 8] >> (bit_cursor % 8)) & 1) << bit
                        bit_cursor += 1
                    return value

                configstrings = {}
                previous = -1
                for _ in range(entries):
                    index = previous + 1 if bits(1) else bits(13)
                    assert 0 <= index < 6519 and index not in configstrings
                    stop = message.index(b'\0', cursor)
                    configstrings[index] = message[cursor:stop].decode('latin1')
                    cursor = stop + 1
                    previous = index
                assert message[cursor] == 5
                clientnum, checksum_feed = struct.unpack_from('<II', message, cursor + 1)
                assert message[cursor+9:] == b'\x05'
                if args.configstrings_output:
                    args.configstrings_output.write_text(json.dumps(configstrings, indent=2)+'\n', encoding='utf-8')
                gamestate = {'sequence': sequence, 'bytes': len(message), 'map': mapname, 'zone': zone,
                             'configstrings': entries, 'server_id': int(configstrings[3]), 'client': clientnum,
                             'checksum_feed': checksum_feed}
                break
        if args.upload_stats:
            assert gamestate is not None, 'Complete stats did not lead to a reassembled gamestate'
    command_acknowledged = False
    pure_command_acknowledged = False
    gameplay_snapshot = None
    delta_snapshot = None
    matchdata_ack = None
    first_match_record = None
    first_match_time = None
    done_sent = False
    done_first_time = None
    done_snapshots = 0
    if args.ack_gamestate:
        from netchan_ack import netchan_xor
        # A legacy binary-channel marker must be discarded without touching
        # an unallocated IW4OL channel or poisoning the following netchan ACK.
        legacy = struct.pack('<IH', 0xfffffff0, s.getsockname()[1])
        s.sendto(crypto.build_data(legacy, next_send, local_tag, key), endpoint)
        next_send += 1
        def send_command(command, command_sequence):
            nonlocal next_send, last_receive
            body = bytes([2 | (3 << 3)]) + struct.pack('<I', command_sequence) + command + b'\0'
            body = netchan_xor(body, (challenge ^ gamestate['server_id'] ^ gamestate['sequence']) & 255,
                               command_texts.get(server_command_sequence, b''))
            packet = struct.pack('<IHBII', command_sequence + 1, s.getsockname()[1], gamestate['server_id'] & 255,
                                 gamestate['sequence'], server_command_sequence) + body
            s.sendto(crypto.build_data(packet, next_send, local_tag, key), endpoint)
            next_send += 1
            end = time.monotonic() + 5
            while time.monotonic() < end:
                record, _ = s.recvfrom(65535)
                count, tag, plain, valid = crypto.decrypt_data(record, key, last_receive)
                assert valid and tag == peer_tag and count > last_receive
                last_receive = count
                assert int.from_bytes(plain[:4], 'little') != 0xfffffff0, 'Unexpected IW4OL binary channel response'
                if len(plain) >= 8 and int.from_bytes(plain[:4], 'little') < 0x20000000:
                    if int.from_bytes(plain[4:8], 'little') == command_sequence:
                        return True
            return False
        # Interleaved bit pool: clientCommand (2) then EOF (3), three bits each.
        command_acknowledged = send_command(f'userinfo "{info}"'.encode('ascii'), 1)
        assert command_acknowledged, 'Native server did not acknowledge the command using published CS 3'
        if args.pure_catalog:
            import zlib
            catalog = json.loads(args.pure_catalog.read_text())
            feed = gamestate['checksum_feed']
            checksums = []
            for row in catalog['archives']:
                if row['archive'].startswith('localized_'):
                    continue
                # CRC32 seed adjustment is linear for a fixed byte length.
                # These verified C1 records have no empty ZIP entries.
                zeros = bytes(4 * row['entry_count'])
                checksums.append(row['client_checksum'] ^ zlib.crc32(zeros, feed) ^ zlib.crc32(zeros))
            aggregate = feed ^ len(checksums)
            for checksum in checksums:
                aggregate ^= checksum
            def signed(value):
                return str(value if value < 0x80000000 else value - 0x100000000)
            command = ('cp @ ' + ' '.join(map(signed, checksums + [aggregate]))).encode('ascii')
            pure_command_acknowledged = send_command(command, 2)
            assert pure_command_acknowledged, 'Native server did not acknowledge cp'
            if args.move:
                import usercmd_codec as uc
                wire_command = dict(uc._NULLCMD, serverTime=100)
                userkey = uc.usercmd_key(gamestate['sequence'],
                    command_texts.get(server_command_sequence, b'').decode('latin1'), feed)
                body = uc.build_client_message(userkey, [], [(wire_command, 'A')],
                    origin=(0, 0, 0), pred=100, move_op=uc.CLC_OP_MOVENODELTA)
                body = netchan_xor(body, (challenge ^ gamestate['server_id'] ^ gamestate['sequence']) & 255,
                    command_texts.get(server_command_sequence, b''))
                header = struct.pack('<IHBII', 4, s.getsockname()[1], gamestate['server_id'] & 255,
                    gamestate['sequence'], server_command_sequence)
                s.sendto(crypto.build_data(header + body, next_send, local_tag, key), endpoint)
                next_send += 1
                end = time.monotonic() + 5
                groups = {}
                while time.monotonic() < end:
                    try:
                        record, _ = s.recvfrom(65535)
                    except socket.timeout:
                        continue
                    count, tag, plain, valid = crypto.decrypt_data(record, key, last_receive)
                    assert valid and tag == peer_tag and count > last_receive
                    last_receive = count
                    sequence = int.from_bytes(plain[:4], 'little')
                    assert sequence != 0xfffffff0
                    if sequence & 0x80000000:
                        index, last, stride, size = struct.unpack_from('<BBHH', plain, 4)
                        assert index <= last and stride == 1162 and size == len(plain) - 10
                        sequence &= 0x1fffffff
                        group = groups.setdefault(sequence, {'last': last, 'chunks': {}})
                        assert group['last'] == last
                        group['chunks'][index] = plain[10:]
                        if len(group['chunks']) != last + 1:
                            continue
                        message = b''.join(group['chunks'][i] for i in range(last + 1))
                    else:
                        message = plain[4:]
                    ack = int.from_bytes(message[:4], 'little')
                    if ack not in ((2, 3) if done_sent else (2,)):
                        continue
                    message = message[:4] + netchan_xor(message[4:], (challenge ^ sequence) & 255,
                                                       b'matchdatadone' if ack == 3 else command)
                    cursor = 4
                    while cursor < len(message) and message[cursor] == 1:
                        cmdseq = int.from_bytes(message[cursor+1:cursor+5], 'little')
                        stop = message.index(b'\0', cursor + 5)
                        command_texts[cmdseq] = message[cursor+5:stop]
                        server_command_sequence = max(server_command_sequence, cmdseq)
                        cursor = stop + 1
                    if cursor + 7 < len(message) and message[cursor] == 0:
                        from codol_snapshot_decode import decode_snapshot
                        payload = message[cursor:]
                        if args.matchdata_ack:
                            decoded, state = decode_snapshot(payload, sequence)
                            match = state['matchdata']
                            now = decoded['server_time']
                            if done_sent:
                                if ack != 3:
                                    continue
                                assert match is None, 'Match data retransmitted after matchdatadone acknowledgement'
                                if done_first_time is None:
                                    done_first_time = now
                                done_snapshots += 1
                                if now - done_first_time >= 1500:
                                    matchdata_ack = {'retry_observed': True, 'command_acknowledged': True,
                                        'snapshots_after_ack': done_snapshots,
                                        'server_time_without_matchdata_ms': now - done_first_time}
                                    break
                                continue
                            if match is None:
                                continue
                            if first_match_record is not None:
                                assert match['record'] == first_match_record
                                assert now - first_match_time >= 1000, 'Match data retried too early'
                                # Keep the gamestate ACK so subsequent snapshots remain full;
                                # packet sequence 5 follows the initial move (4), while this
                                # reliable command follows cp (command sequence 2).
                                body = bytes([2 | (3 << 3)]) + struct.pack('<I', 3) + b'matchdatadone\0'
                                body = netchan_xor(body,
                                    (challenge ^ gamestate['server_id'] ^ gamestate['sequence']) & 255,
                                    command_texts.get(server_command_sequence, b''))
                                header = struct.pack('<IHBII', 5, s.getsockname()[1],
                                    gamestate['server_id'] & 255, gamestate['sequence'], server_command_sequence)
                                s.sendto(crypto.build_data(header + body, next_send, local_tag, key), endpoint)
                                next_send += 1
                                done_sent = True
                                end = time.monotonic() + 5
                                continue
                            first_match_record = match['record']
                            first_match_time = now
                        if gameplay_snapshot is not None:
                            if not payload[5]:
                                continue
                            decoded, _ = decode_snapshot(payload, sequence, baseline_state)
                            delta_snapshot = {'sequence': sequence, 'bytes': len(message), 'decoded': decoded}
                            if args.snapshot_output:
                                args.snapshot_output.with_suffix('.delta.bin').write_bytes(payload)
                                args.snapshot_output.with_suffix('.sequences.json').write_text(json.dumps({
                                    'baseline': gameplay_snapshot['sequence'], 'delta': sequence}) + '\n')
                            break
                        decoded, baseline_state = decode_snapshot(payload, sequence)
                        if args.matchdata_fixture:
                            match = baseline_state['matchdata']
                            if match is None:
                                continue
                            assert match['name'] == 'mp/clientmatchdata.def'
                            record = match['record']
                            assert struct.unpack_from('<II', record) == (16, 0x3fd7bbad)
                            assert record[654] == 2
                            assert struct.unpack_from('<i', record, 642)[0] == -12345
                            assert b'native-matchdata\0' in record
                            decoded['matchdata']['fixture_verified'] = True
                        if args.snapshot_output:
                            args.snapshot_output.write_bytes(payload)
                        gameplay_snapshot = {'sequence': sequence, 'bytes': len(message),
                            'server_time': int.from_bytes(message[cursor+1:cursor+5], 'little'),
                            'decoded': decoded}
                        if args.matchdata_ack:
                            end = time.monotonic() + 5
                            continue
                        if not args.delta:
                            break
                        command_time = gameplay_snapshot['server_time'] + 50
                        wire_command = dict(uc._NULLCMD, serverTime=command_time)
                        server_text = command_texts.get(server_command_sequence, b'')
                        userkey = uc.usercmd_key(sequence, server_text.decode('latin1'), feed)
                        body = uc.build_client_message(userkey, [], [(wire_command, 'A')],
                            origin=(0, 0, 0), pred=command_time, move_op=uc.CLC_OP_MOVE)
                        body = netchan_xor(body, (challenge ^ gamestate['server_id'] ^ sequence) & 255, server_text)
                        header = struct.pack('<IHBII', 5, s.getsockname()[1], gamestate['server_id'] & 255,
                            sequence, server_command_sequence)
                        s.sendto(crypto.build_data(header + body, next_send, local_tag, key), endpoint)
                        next_send += 1
                        end = time.monotonic() + 5
                assert gameplay_snapshot is not None, 'No gameplay snapshot after the first native usermove'
                if args.delta:
                    assert delta_snapshot is not None, 'No delta snapshot after acknowledging the baseline'
                if args.matchdata_ack:
                    assert matchdata_ack is not None, 'No verified retry/acknowledgement/continued-snapshot sequence'
    print(json.dumps({'encrypted_handshake': True, 'cookie_retransmission': True,
                      'encrypted_challenge': True, 'plaintext_replay_bad_mac_rejected': True,
                      'connect_response': response,
                      'last_server_counter': last_receive,
                      'stats_complete': stats_complete, 'gamestate': gamestate,
                      'client_command_acknowledged': command_acknowledged,
                      'pure_command_acknowledged': pure_command_acknowledged,
                      'gameplay_snapshot': gameplay_snapshot,
                      'delta_snapshot': delta_snapshot,
                      'matchdata_ack': matchdata_ack,
                      'post_connect_summary': {
                          'packets': len(post_connect),
                          'iw4ol_reliable_packets': sum(p['header'] == '0xfffffff0' for p in post_connect),
                          'fragment_packets': sum(bool(int(p['header'], 16) & 0x80000000) and
                                                  p['header'] != '0xfffffff0' for p in post_connect)}}))
    s.close()


if __name__ == '__main__':
    main()
