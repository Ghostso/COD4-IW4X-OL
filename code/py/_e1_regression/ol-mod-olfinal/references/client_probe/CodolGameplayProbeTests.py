#!/usr/bin/env python3
"""Unit tests for the controlled CODOL gameplay endpoint probe."""

from __future__ import annotations

import base64
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec

from CodolGameplayProbe import (
    CODOL_DEFAULT_CONFIGSTRINGS,
    DTLS_COOKIE_ACK,
    DTLS_DATA,
    DTLS_INIT_ACK,
    EMPTY_IPV4_ENDPOINT,
    NAT_INTRO_REPLY,
    OOB_PREFIX,
    DescriptorWatcher,
    DTLSCookieEchoPacket,
    DTLSDataPacket,
    DTLSECCKeyPair,
    DTLSInitPacket,
    DTLSSessionKeys,
    NATTraversalPacket,
    PROFILE_CHUNK_SIZE,
    ProfileStatsChunk,
    ProfileStatsUpload,
    ClientNetchanPacket,
    CLIENT_COMMAND_EOF,
    CLIENT_COMMAND_RELIABLE,
    SERVER_COMMAND_EOF,
    SERVER_COMMAND_CONFIGSTRING,
    SERVER_COMMAND_GAMESTATE,
    build_configstring_command,
    build_minimal_gamestate_commands,
    build_snapshot_probe_command,
    build_server_netchan_packet,
    build_common_address,
    encode_meep,
    dtls_init_ack,
    dtls_cookie_ack,
    extract_descriptor_security_key,
    extract_session_descriptor,
    float_bits,
    nat_intro_reply,
    oob_challenge_reply,
    oob_connect_reply,
    oob_heartbeat_reply,
    parse_client_reliable_commands,
    select_descriptor_source,
    xor_netchan_commands,
)


HOST_ADDRESS_HEX = (
    "C0A800723175"
    + "00FF00FF0000" * 4
    + "F0000001C41402"
)
DESCRIPTOR_HEX = "10416C776179736F66666C696E6500"
SECURITY_KEY_HEX = "A06763B65A6939F30776DAE5782E0434"
FULL_DESCRIPTOR_HEX = (
    "10416C776179736F66666C696E65000ADEC0ADDE0100100110416C776179736F"
    "66666C696E6500079B1FF0D60700000000070000000008000000000700000000"
    "070000000007000000000700000000130810000000" + SECURITY_KEY_HEX +
    "070000000007000000000700000000070800000007FFFFFFFF071C0300000721"
    "0000000700000000070500000007000000000798E3518D0ADEC0ADDE00000000"
    "0700000000070000000000"
)
DTLS_DATA_HEX = (
    "06025C85010050AD3F63373BF0C42600"
    "AD7A0E8C540C251ABD3B0231D91E7B54EFF1A2D832C7CF5B84261F2128C1C9DB796261984013"
)
DTLS_SHARED_SECRET_HEX = (
    "3ED7D4E0401026F746B975784A335A46792458BCC9027498B8FDD679" + SECURITY_KEY_HEX
)
NAT_INTRO_REQUEST_HEX = (
    "0D020035865AAB30D9B31827443021DF5D"
    "C0A800723175"
    "7F0000012071"
)
DTLS_INIT_HEX = "0102000000007F2376E64DFD6EE7CA2C"
DTLS_COOKIE_ECHO_HEX = (
    "030266150000"
    "02027C9E00005E4A2E7A00000000661566157C9E00000000"
    "7F0000013175B9BF2CA8C36D13F8"
    "C0A80072317500FF00FF000000FF00FF000000FF00FF000000FF00FF0000"
    "F0000001C03002"
    "B9BF2CA8C36D13F8"
    "30440302070002011C021D008619494506AF52484362F286317071A2343B021F3F"
    "C51634EE550487021C46D1509A19052CCA2469C9779ECD5854AECE9942284D1E40"
    "FB051715000000000000000000000000000000000000000000000000000000000000"
)
CREATE_PAYLOAD_HEX = (
    "130825000000" + HOST_ADDRESS_HEX + "08000000000806000000" + DESCRIPTOR_HEX
)


class CodolGameplayProbeTests(unittest.TestCase):
    def test_common_address_layout(self) -> None:
        encoded = build_common_address("127.0.0.1", 28960, 1)
        endpoint = bytes.fromhex("7F0000012071")
        self.assertEqual(len(encoded), 37)
        self.assertEqual(encoded, endpoint + EMPTY_IPV4_ENDPOINT * 4 + endpoint + b"\x01")

    def test_create_session_descriptor_extraction(self) -> None:
        self.assertEqual(
            extract_session_descriptor(CREATE_PAYLOAD_HEX),
            bytes.fromhex(DESCRIPTOR_HEX),
        )

    def test_descriptor_security_key_extraction(self) -> None:
        self.assertEqual(
            extract_descriptor_security_key(bytes.fromhex(FULL_DESCRIPTOR_HEX)),
            bytes.fromhex(SECURITY_KEY_HEX),
        )
        with self.assertRaises(ValueError):
            extract_descriptor_security_key(bytes.fromhex(DESCRIPTOR_HEX))

    def test_descriptor_watcher_uses_latest_task1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AlwaysofflineRe.Localnet32.log"
            path.write_text(
                "ignored\nLSG_REQUEST sequence=1 service=21 task=1 payload="
                + CREATE_PAYLOAD_HEX
                + "\n",
                encoding="utf-8",
            )
            watcher = DescriptorWatcher(path)
            self.assertTrue(watcher.poll())
            self.assertEqual(watcher.descriptor, bytes.fromhex(DESCRIPTOR_HEX))
            self.assertFalse(watcher.poll())

    def test_explicit_descriptor_takes_precedence_over_log(self) -> None:
        descriptor, watcher = select_descriptor_source("010203", Path("not-used.log"))
        self.assertEqual(descriptor, b"\x01\x02\x03")
        self.assertIsNone(watcher)

    def test_meep_envelope(self) -> None:
        packet = encode_meep("Matchmaking::Update", 7, '{"Session.Role":"server"}')
        self.assertTrue(packet.startswith(b"MEEP"))
        message = json.loads(base64.b64decode(packet[4:]))
        self.assertEqual(message["Event"], "Matchmaking::Update")
        self.assertEqual(message["Origin"], 7)
        self.assertEqual(
            base64.b64decode(message["Payload"]).decode("utf-8"),
            '{"Session.Role":"server"}',
        )

    def test_challenge_reply_only_handles_getchallenge(self) -> None:
        self.assertEqual(
            oob_challenge_reply(OOB_PREFIX + b"getchallenge", 1234),
            OOB_PREFIX + b"challengeResponse 1234",
        )
        self.assertIsNone(oob_challenge_reply(OOB_PREFIX + b"connect payload", 1234))
        self.assertIsNone(oob_challenge_reply(b"getchallenge", 1234))

    def test_connect_reply_only_handles_connect(self) -> None:
        self.assertEqual(
            oob_connect_reply(OOB_PREFIX + b"connect 01100001deadc0de \"\\name\\test\""),
            OOB_PREFIX + b"connectResponse",
        )
        self.assertEqual(
            oob_connect_reply(OOB_PREFIX + b"  CONNECT test\0ignored"),
            OOB_PREFIX + b"connectResponse",
        )
        self.assertIsNone(oob_connect_reply(OOB_PREFIX + b"connectResponse"))
        self.assertIsNone(oob_connect_reply(b"connect test"))

    def test_heartbeat_reply_only_handles_heartbeat(self) -> None:
        self.assertEqual(
            oob_heartbeat_reply(OOB_PREFIX + b"heartbeat\0"),
            OOB_PREFIX + b"heartbeatresponse",
        )
        self.assertEqual(
            oob_heartbeat_reply(OOB_PREFIX + b"  HEARTBEAT"),
            OOB_PREFIX + b"heartbeatresponse",
        )
        self.assertIsNone(oob_heartbeat_reply(OOB_PREFIX + b"heartbeatresponse"))
        self.assertIsNone(oob_heartbeat_reply(b"heartbeat"))

    def test_captured_client_netchan_packet_layout_and_xor(self) -> None:
        challenge = 0x7E55DB8F
        packet = ClientNetchanPacket.parse(
            bytes.fromhex("010000000000000000000000008C")
        )
        self.assertEqual(packet.netchan_sequence, 1)
        self.assertEqual(packet.server_id, 0)
        self.assertEqual(packet.message_acknowledge, 0)
        self.assertEqual(packet.reliable_acknowledge, 0)
        self.assertEqual(packet.decode_commands(challenge), bytes([CLIENT_COMMAND_EOF]))

    def test_minimal_server_netchan_packet_layout_and_xor(self) -> None:
        challenge = 0x7E55DB8F
        packet = build_server_netchan_packet(1, challenge)
        self.assertEqual(packet.hex(), "010000000000000088")
        self.assertEqual(
            xor_netchan_commands(packet[8:], challenge ^ 1),
            bytes([SERVER_COMMAND_EOF]),
        )

    def test_netchan_xor_restarts_reliable_command_at_nul(self) -> None:
        command = b"ab\0ignored"
        plaintext = bytes(range(8))
        encoded = xor_netchan_commands(plaintext, 0x42, command)
        self.assertEqual(xor_netchan_commands(encoded, 0x42, command), plaintext)

    def test_netchan_packet_rejects_invalid_ranges(self) -> None:
        with self.assertRaises(ValueError):
            ClientNetchanPacket.parse(bytes(13))
        with self.assertRaisesRegex(ValueError, "fragmented"):
            ClientNetchanPacket.parse(
                bytes.fromhex("66b8fabf8e141cf3ffff00000000")
            )
        with self.assertRaisesRegex(ValueError, "message acknowledge"):
            ClientNetchanPacket.parse(
                bytes.fromhex("0200000000141cf3ff0000000000")
            )
        with self.assertRaises(ValueError):
            build_server_netchan_packet(0, 1)

    def test_minimal_gamestate_command_layout(self) -> None:
        commands = build_minimal_gamestate_commands("mp_test", "tdm", client_num=2)
        self.assertEqual(commands[0], SERVER_COMMAND_GAMESTATE)
        self.assertEqual(struct.unpack_from("<I", commands, 1)[0], 0)
        self.assertEqual(commands[5:13], b"mp_test\0")
        self.assertEqual(commands[13:17], b"tdm\0")
        self.assertEqual(struct.unpack_from("<I", commands, 17)[0], 0)
        configstrings = build_configstring_command(CODOL_DEFAULT_CONFIGSTRINGS)
        self.assertEqual(commands[21:21 + len(configstrings)], configstrings)
        trailer = 21 + len(configstrings)
        self.assertEqual(commands[trailer], SERVER_COMMAND_EOF)
        self.assertEqual(struct.unpack_from("<II", commands, trailer + 1), (2, 0))
        self.assertEqual(commands[trailer + 9], SERVER_COMMAND_EOF)

    def test_raw_configstring_command_uses_split_byte_and_bit_cursors(self) -> None:
        command = build_configstring_command({2: "cod"})
        self.assertEqual(command[0], SERVER_COMMAND_CONFIGSTRING)
        self.assertEqual(command[1:].hex(), "01000400636f6400000000")

    def test_minimal_gamestate_includes_configstring_block(self) -> None:
        commands = build_minimal_gamestate_commands(
            "mp_crash_tropical",
            "sd",
            config_checksum=0xF7E89911,
            configstrings={2: "cod"},
        )
        checksum_offset = commands.index(struct.pack("<I", 0xF7E89911))
        expected = dict(CODOL_DEFAULT_CONFIGSTRINGS)
        expected[2] = "cod"
        encoded = build_configstring_command(expected)
        self.assertEqual(commands[checksum_offset + 4:checksum_offset + 4 + len(encoded)],
                         encoded)

    def test_minimal_gamestate_allows_timescale_configstring_override(self) -> None:
        commands = build_minimal_gamestate_commands(
            configstrings={0x190F: "0 500 0.5 1"},
        )
        self.assertIn(
            build_configstring_command({0x190F: "0 500 0.5 1"}),
            commands,
        )

    def test_snapshot_probe_command_layout(self) -> None:
        command = build_snapshot_probe_command(1234)
        self.assertEqual(command.hex(), "00d20400000008000000f87f06")

    def test_snapshot_probe_can_include_local_client_and_player_entity(self) -> None:
        command = build_snapshot_probe_command(1234, include_local_player=True)
        self.assertEqual(command[0:7], bytes.fromhex("00d20400000008"))
        self.assertNotEqual(command, build_snapshot_probe_command(1234))
        self.assertEqual(command[-1], SERVER_COMMAND_EOF)

        readcount = 7
        bit = 56

        def read_bit() -> int:
            nonlocal readcount, bit
            if bit & 7 == 0:
                bit = readcount * 8
                readcount += 1
            value = (command[bit >> 3] >> (bit & 7)) & 1
            bit += 1
            return value

        def read_bits(count: int) -> int:
            return sum(read_bit() << index for index in range(count))

        def read_raw_byte() -> int:
            nonlocal readcount
            value = command[readcount]
            readcount += 1
            return value

        self.assertEqual(read_bits(25), 0)  # Snapshot, playerstate, matchstate.
        self.assertEqual(read_bits(5), 0b00011)  # Client 0 and list terminator.
        self.assertEqual(read_bit(), 1)  # Sequential entity 0.
        self.assertEqual(read_bits(3), 0b010)  # Present, changed, no special delta.
        self.assertEqual(read_bits(6), 0)  # Last changed field is field 0.
        self.assertEqual(read_bit(), 1)  # First field-index delta.
        self.assertEqual(read_raw_byte(), 1)  # eType = ET_PLAYER.

        self.assertEqual(read_bits(2), 0b10)  # Absolute entity-list terminator.
        self.assertEqual(read_bits(11), 2047)
        self.assertEqual(read_bit(), 0)  # Empty auxiliary list.

    def test_snapshot_probe_writes_absolute_player_origin(self) -> None:
        command = build_snapshot_probe_command(1234, (1.0, 2.0, 3.0))
        readcount = 7
        bit = 56

        def read_bit() -> int:
            nonlocal readcount, bit
            if bit & 7 == 0:
                bit = readcount * 8
                readcount += 1
            value = (command[bit >> 3] >> (bit & 7)) & 1
            bit += 1
            return value

        def read_bits(count: int) -> int:
            return sum(read_bit() << index for index in range(count))

        def read_float() -> float:
            nonlocal readcount
            value = struct.unpack_from("<f", command, readcount)[0]
            readcount += 4
            return value

        self.assertEqual(read_bit(), 0)  # No delta snapshot baseline.
        self.assertEqual(read_bit(), 1)  # Origin and velocity are present.
        self.assertEqual(read_bits(8), 15)

        self.assertEqual((read_bit(), read_bits(4)), (0, 10))
        self.assertEqual(read_float(), 1.0)
        self.assertEqual((read_bit(), read_bits(4)), (0, 2))
        self.assertEqual(read_float(), 3.0)
        self.assertEqual(read_bit(), 1)
        self.assertEqual(read_float(), 2.0)
        self.assertEqual(read_bits(14), 0)
        self.assertEqual(bit, 187)
        self.assertEqual(readcount, 24)

    def test_client_reliable_command_parser(self) -> None:
        commands = (
            bytes([CLIENT_COMMAND_RELIABLE])
            + struct.pack("<I", 1)
            + b"gamestateupdate 1\0"
            + bytes([CLIENT_COMMAND_RELIABLE])
            + struct.pack("<I", 2)
            + b"next\0"
            + bytes([CLIENT_COMMAND_EOF])
        )
        self.assertEqual(
            parse_client_reliable_commands(commands),
            [(1, "gamestateupdate 1"), (2, "next")],
        )
        self.assertEqual(parse_client_reliable_commands(bytes([CLIENT_COMMAND_EOF])), [])

    def test_single_profile_stats_chunk_completes_upload(self) -> None:
        profile = bytes(0x8000)
        compressed = zlib.compress(profile)
        packet = OOB_PREFIX + b"stats\0" + b"\0" + b"\xb7\x03" + compressed
        upload = ProfileStatsUpload()
        result = upload.accept(packet)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.chunk, ProfileStatsChunk(0, 0x03B7, compressed))
        self.assertTrue(result.complete)
        self.assertEqual(result.profile, profile)
        self.assertEqual(result.remaining_mask, 0)
        self.assertEqual(result.reply, OOB_PREFIX + b"statResponse 0")

    def test_multi_chunk_profile_upload_requests_remaining_chunks(self) -> None:
        profile = bytes((index * 73 + index // 251) & 0xFF for index in range(0x8000))
        compressed = zlib.compress(profile, level=0)
        self.assertGreater(len(compressed), PROFILE_CHUNK_SIZE)
        chunks = [
            compressed[offset:offset + PROFILE_CHUNK_SIZE]
            for offset in range(0, len(compressed), PROFILE_CHUNK_SIZE)
        ]
        upload = ProfileStatsUpload()
        first = upload.accept(
            OOB_PREFIX + b"stats\0" + b"\0" + b"\0\0" + chunks[0]
        )
        self.assertIsNotNone(first)
        assert first is not None
        self.assertFalse(first.complete)
        self.assertEqual(first.remaining_mask, 0x07FFFFFE)

        result = first
        for index, chunk in enumerate(chunks[1:], 1):
            result = upload.accept(
                OOB_PREFIX
                + b"stats\0"
                + bytes([index])
                + b"\0\0"
                + chunk
            )
            self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.complete)
        self.assertEqual(result.profile, profile)
        self.assertEqual(result.remaining_mask, 0)

    def test_nat_intro_request_fixture(self) -> None:
        request = bytes.fromhex(NAT_INTRO_REQUEST_HEX)
        decoded = NATTraversalPacket.parse(request)
        self.assertEqual(decoded.packet_type, 0x0D)
        self.assertEqual(decoded.version, 2)
        self.assertEqual(decoded.hmac, bytes.fromhex("35865AAB30D9B3182744"))
        self.assertEqual(decoded.identifier, 0x5DDF2130)
        self.assertEqual(decoded.source_address, "192.168.0.114")
        self.assertEqual(decoded.source_port, 30001)
        self.assertEqual(decoded.destination_address, "127.0.0.1")
        self.assertEqual(decoded.destination_port, 28960)

        reply = nat_intro_reply(request)
        self.assertEqual(reply, bytes([NAT_INTRO_REPLY]) + request[1:])

    def test_nat_intro_reply_rejects_other_packets(self) -> None:
        request = bytes.fromhex(NAT_INTRO_REQUEST_HEX)
        self.assertIsNone(nat_intro_reply(bytes([NAT_INTRO_REPLY]) + request[1:]))
        self.assertIsNone(nat_intro_reply(request[:-1]))
        self.assertIsNone(nat_intro_reply(request[:1] + b"\x01\x00" + request[3:]))

    def test_dtls_init_fixture_and_ack_layout(self) -> None:
        request = bytes.fromhex(DTLS_INIT_HEX)
        decoded = DTLSInitPacket.parse(request)
        self.assertEqual(decoded.version, 2)
        self.assertEqual(decoded.verification_tag, 0)
        self.assertEqual(decoded.counter, 0)
        self.assertEqual(decoded.init_tag, 0x237F)
        self.assertEqual(decoded.security_id, bytes.fromhex("76E64DFD6EE7CA2C"))

        reply = dtls_init_ack(request, "127.0.0.1", 30001, 0x4567, 0x11223344)
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertEqual(len(reply), 38)
        self.assertEqual(reply[0], DTLS_INIT_ACK)
        self.assertEqual(
            reply.hex().upper(),
            "02027F2300004433221100000000674567457F2300000000"
            "7F000001317576E64DFD6EE7CA2C",
        )

    def test_dtls_init_ack_rejects_other_packets(self) -> None:
        request = bytes.fromhex(DTLS_INIT_HEX)
        self.assertIsNone(dtls_init_ack(request[:-1], "127.0.0.1", 30001, 1, 0))
        self.assertIsNone(
            dtls_init_ack(bytes([DTLS_INIT_ACK]) + request[1:], "127.0.0.1", 30001, 1, 0)
        )

    def test_dtls_cookie_echo_fixture_and_ack_layout(self) -> None:
        request = bytes.fromhex(DTLS_COOKIE_ECHO_HEX)
        decoded = DTLSCookieEchoPacket.parse(request)
        self.assertEqual(decoded.verification_tag, 0x1566)
        self.assertEqual(decoded.client_tag, 0x9E7C)
        self.assertEqual(len(decoded.common_address), 37)
        self.assertEqual(decoded.security_id, bytes.fromhex("B9BF2CA8C36D13F8"))
        self.assertEqual(len(decoded.public_key), 100)
        self.assertEqual(decoded.public_key[:2], bytes.fromhex("3044"))

        reply = dtls_cookie_ack(request)
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertEqual(len(reply), 114)
        self.assertEqual(reply[0], DTLS_COOKIE_ACK)
        self.assertEqual(reply[1], 2)
        self.assertEqual(reply[2:4], bytes.fromhex("7C9E"))
        self.assertEqual(reply[6:106], decoded.public_key)
        self.assertEqual(reply[106:114], decoded.security_id)

    def test_dtls_cookie_ack_rejects_other_packets(self) -> None:
        request = bytes.fromhex(DTLS_COOKIE_ECHO_HEX)
        self.assertIsNone(dtls_cookie_ack(request[:-1]))
        self.assertIsNone(dtls_cookie_ack(bytes([DTLS_COOKIE_ACK]) + request[1:]))

    def test_dtls_p224_export_and_shared_secret(self) -> None:
        first = DTLSECCKeyPair(ec.derive_private_key(1, ec.SECP224R1()))
        second = DTLSECCKeyPair(ec.derive_private_key(2, ec.SECP224R1()))
        self.assertEqual(len(first.public_key), 100)
        self.assertEqual(first.public_key[0], 0x30)
        self.assertLessEqual(first.public_key[1] + 2, len(first.public_key))
        self.assertEqual(
            DTLSECCKeyPair.import_public_key(first.public_key).public_numbers(),
            first.private_key.public_key().public_numbers(),
        )
        security_key = bytes.fromhex(SECURITY_KEY_HEX)
        first_secret = first.shared_secret(second.public_key, security_key)
        second_secret = second.shared_secret(first.public_key, security_key)
        self.assertEqual(first_secret, second_secret)
        self.assertEqual(len(first_secret), 44)
        self.assertEqual(first_secret[28:], security_key)

    def test_dtls_data_fixture_authentication_and_decryption(self) -> None:
        packet = DTLSDataPacket.parse(bytes.fromhex(DTLS_DATA_HEX))
        keys = DTLSSessionKeys.derive(bytes.fromhex(DTLS_SHARED_SECRET_HEX))
        self.assertEqual(packet.verification_tag, 0x855C)
        self.assertEqual(packet.sequence_number, 1)
        self.assertEqual(packet.encrypted_size, 38)
        self.assertTrue(packet.verify(keys))
        self.assertEqual(
            packet.decrypt(keys),
            bytes.fromhex(
                "FFFFFFFF6765746368616C6C656E6765"
                "20302022303131303030303164656164633064652200"
            ),
        )

    def test_dtls_data_build_round_trip_and_rejects_tampering(self) -> None:
        keys = DTLSSessionKeys.derive(bytes.fromhex(DTLS_SHARED_SECRET_HEX))
        plaintext = OOB_PREFIX + b"challengeResponse 1234"
        encoded = DTLSDataPacket.build(plaintext, 0x47A1, 1, keys)
        self.assertEqual(encoded[0], DTLS_DATA)
        decoded = DTLSDataPacket.parse(encoded)
        self.assertTrue(decoded.verify(keys))
        self.assertEqual(decoded.decrypt(keys), plaintext)

        tampered = bytearray(encoded)
        tampered[-1] ^= 1
        decoded = DTLSDataPacket.parse(bytes(tampered))
        self.assertFalse(decoded.verify(keys))
        with self.assertRaises(ValueError):
            decoded.decrypt(keys)


if __name__ == "__main__":
    unittest.main()
