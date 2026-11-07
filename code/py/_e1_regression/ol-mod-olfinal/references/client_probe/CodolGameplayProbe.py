#!/usr/bin/env python3
"""Exercise CODOL's client-side gameplay protocol and record the wire contract.

This is a conformance probe, not an authoritative gameplay server. Synthetic
gamestate and snapshot builders are intentionally limited to proving client
parsing, encryption, framing, and delta encoding. Gameplay must ultimately come
from a server frame loop which owns GSC, entities, player state, and usercmds.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import random
import re
import select
import socket
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runtime"))
from CodolGame import find_game_directory


DISCOVERY_PORT = 0x4321
OOB_PREFIX = b"\xff\xff\xff\xff"
EMPTY_IPV4_ENDPOINT = bytes.fromhex("00FF00FF0000")
NAT_TRAVERSAL_PACKET_SIZE = 29
NAT_INTRO_REPLY = 0x0C
NAT_INTRO_REQUEST = 0x0D
DTLS_INIT = 0x01
DTLS_INIT_ACK = 0x02
DTLS_COOKIE_ECHO = 0x03
DTLS_COOKIE_ACK = 0x04
DTLS_DATA = 0x06
DTLS_INIT_PACKET_SIZE = 16
DTLS_COOKIE_ECHO_PACKET_SIZE = 189
DTLS_VERSION = 0x02
PROFILE_CHUNK_COUNT = 27
PROFILE_CHUNK_SIZE = 1238
CLIENT_COMMAND_EOF = 3
CLIENT_COMMAND_RELIABLE = 2
SERVER_COMMAND_SNAPSHOT = 0
SERVER_COMMAND_EOF = 6
SERVER_COMMAND_GAMESTATE = 3
SERVER_COMMAND_CONFIGSTRING = 4
CODOL_DEFAULT_CONFIGSTRINGS = {
    0x190F: "0 0 1 1",  # Required slow-motion state: start time, duration, scales.
}
TASK1_PATTERN = re.compile(
    r"LSG_REQUEST .* service=21 task=1 payload=([0-9A-Fa-f]+)"
)


def read_typed_u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 5 > len(data) or data[offset] != 0x08:
        raise ValueError(f"expected typed uint32 at offset {offset}")
    return struct.unpack_from("<I", data, offset + 1)[0], offset + 5


def extract_session_descriptor(payload_hex: str) -> bytes:
    data = bytes.fromhex(payload_hex)
    if not data or data[0] != 0x13:
        raise ValueError("matchmaking createSession does not start with a typed blob")
    blob_size, offset = read_typed_u32(data, 1)
    if blob_size != 37 or offset + blob_size > len(data):
        raise ValueError(f"expected a 37-byte bdCommonAddr, got {blob_size}")
    offset += blob_size
    _, offset = read_typed_u32(data, offset)
    _, offset = read_typed_u32(data, offset)
    if offset >= len(data):
        raise ValueError("createSession has no native descriptor tail")
    return data[offset:]


def extract_descriptor_security_key(descriptor: bytes) -> bytes:
    marker = bytes.fromhex("130810000000")
    offset = descriptor.find(marker)
    if offset < 0 or offset + len(marker) + 16 > len(descriptor):
        raise ValueError("session descriptor has no 16-byte SecurityKey blob")
    return descriptor[offset + len(marker):offset + len(marker) + 16]


def encode_endpoint(address: str, port: int) -> bytes:
    if not 0 <= port <= 0xFFFF:
        raise ValueError("port must fit in uint16")
    return socket.inet_aton(address) + struct.pack("<H", port)


def build_common_address(address: str, port: int, nat_type: int = 1) -> bytes:
    if not 0 <= nat_type <= 3:
        raise ValueError("NAT type must be 0..3")
    endpoint = encode_endpoint(address, port)
    return endpoint + EMPTY_IPV4_ENDPOINT * 4 + endpoint + bytes([nat_type])


def encode_meep(event: str, origin: int, payload: str) -> bytes:
    encoded_payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    message = json.dumps(
        {"Event": event, "Origin": origin, "Payload": encoded_payload},
        separators=(",", ":"),
    )
    return b"MEEP" + base64.b64encode(message.encode("utf-8"))


def build_server_properties(
    address: str,
    port: int,
    descriptor: bytes,
    nat_type: int = 1,
) -> dict[str, Any]:
    return {
        "Demonware.Hostaddress": list(build_common_address(address, port, nat_type)),
        "Session.Gametype": 0,
        "Players.Max": 18,
        "Players.Current": 0,
        "Session.Demonware": list(descriptor),
        "Session.Role": "server",
    }


def oob_challenge_reply(packet: bytes, challenge: int) -> bytes | None:
    if not packet.startswith(OOB_PREFIX):
        return None
    command = packet[len(OOB_PREFIX):].split(b"\0", 1)[0].lstrip().lower()
    if not command.startswith(b"getchallenge"):
        return None
    return OOB_PREFIX + f"challengeResponse {challenge}".encode("ascii")


def oob_connect_reply(packet: bytes) -> bytes | None:
    if not packet.startswith(OOB_PREFIX):
        return None
    command = packet[len(OOB_PREFIX):].split(b"\0", 1)[0].lstrip().lower()
    if not command.startswith(b"connect "):
        return None
    return OOB_PREFIX + b"connectResponse"


def oob_heartbeat_reply(packet: bytes) -> bytes | None:
    if not packet.startswith(OOB_PREFIX):
        return None
    command = packet[len(OOB_PREFIX):].split(b"\0", 1)[0].lstrip().lower()
    if command != b"heartbeat":
        return None
    return OOB_PREFIX + b"heartbeatresponse"


def xor_netchan_commands(payload: bytes, seed: int, reliable_command: bytes = b"") -> bytes:
    key = seed & 0xFF
    command_index = 0
    output = bytearray()
    for index, value in enumerate(payload):
        if reliable_command:
            if command_index >= len(reliable_command) or reliable_command[command_index] == 0:
                command_index = 0
            command_byte = reliable_command[command_index]
            command_index += 1
        else:
            command_byte = 0
        key ^= (command_byte << (index & 1)) & 0xFF
        output.append(value ^ key)
    return bytes(output)


@dataclass(frozen=True)
class ClientNetchanPacket:
    netchan_sequence: int
    server_id: int
    message_acknowledge: int
    reliable_acknowledge: int
    encoded_commands: bytes

    @classmethod
    def parse(cls, packet: bytes) -> "ClientNetchanPacket":
        if len(packet) < 14 or packet.startswith(OOB_PREFIX):
            raise ValueError("not a CODOL client netchan packet")
        netchan_sequence = struct.unpack_from("<I", packet, 0)[0]
        server_id = packet[4]
        message_acknowledge, reliable_acknowledge = struct.unpack_from("<II", packet, 5)
        if not 0 < netchan_sequence <= 0x1FFFFFFF:
            raise ValueError("fragmented or invalid CODOL client netchan packet")
        if message_acknowledge > 0x1FFFFFFF:
            raise ValueError("client message acknowledge is outside the netchan sequence range")
        return cls(
            netchan_sequence,
            server_id,
            message_acknowledge,
            reliable_acknowledge,
            packet[13:],
        )

    def decode_commands(self, challenge: int, reliable_command: bytes = b"") -> bytes:
        seed = challenge ^ self.server_id ^ self.message_acknowledge
        return xor_netchan_commands(self.encoded_commands, seed, reliable_command)


def build_server_netchan_packet(
    sequence: int,
    challenge: int,
    reliable_acknowledge: int = 0,
    commands: bytes = bytes([SERVER_COMMAND_EOF]),
    reliable_command: bytes = b"",
) -> bytes:
    if not 0 < sequence <= 0x1FFFFFFF:
        raise ValueError("server netchan sequence must be in the unfragmented sequence range")
    encoded_commands = xor_netchan_commands(
        commands,
        challenge ^ sequence,
        reliable_command,
    )
    return struct.pack("<II", sequence, reliable_acknowledge) + encoded_commands


class MessageBitWriter:
    """Mirror CODOL msg_t's independent byte and bit cursors."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.readcount = 0
        self.bit = 0

    def write_raw(self, value: bytes) -> None:
        if self.readcount != len(self.data):
            raise RuntimeError("raw write cursor is not at the end of the message")
        self.data.extend(value)
        self.readcount += len(value)

    def write_bits(self, value: int, count: int) -> None:
        if count < 0 or value < 0 or value >= (1 << count):
            raise ValueError(f"value {value} does not fit in {count} bits")
        for index in range(count):
            if self.bit & 7 == 0:
                self.bit = self.readcount * 8
                self.data.append(0)
                self.readcount += 1
            if value & (1 << index):
                self.data[self.bit >> 3] |= 1 << (self.bit & 7)
            self.bit += 1


def build_configstring_command(configstrings: dict[int, str]) -> bytes:
    if len(configstrings) > 0x7FFF:
        raise ValueError("too many raw CODOL configstrings")
    writer = MessageBitWriter()
    writer.write_raw(struct.pack("<h", len(configstrings)))
    previous = -1
    for index, value in sorted(configstrings.items()):
        if not 0 <= index < 0x1B92:
            raise ValueError(f"configstring index {index} is out of range")
        encoded = value.encode("ascii")
        if b"\0" in encoded:
            raise ValueError("CODOL configstrings cannot contain NUL bytes")
        sequential = index == previous + 1
        writer.write_bits(int(sequential), 1)
        if not sequential:
            writer.write_bits(index, 13)
        writer.write_raw(encoded + b"\0")
        previous = index

    writer.write_bits(0, 10)
    writer.write_bits(0, 10)
    return bytes([SERVER_COMMAND_CONFIGSTRING]) + bytes(writer.data)


def build_minimal_gamestate_commands(
    map_name: str = "",
    game_type: str = "",
    config_checksum: int = 0,
    client_num: int = 0,
    checksum_feed: int = 0,
    configstrings: dict[int, str] | None = None,
) -> bytes:
    if not 0 <= client_num <= 18:
        raise ValueError("CODOL gamestate client number must be between 0 and 18")
    encoded_map = map_name.encode("ascii")
    encoded_game_type = game_type.encode("ascii")
    if b"\0" in encoded_map or b"\0" in encoded_game_type:
        raise ValueError("CODOL gamestate strings cannot contain NUL bytes")
    merged_configstrings = dict(CODOL_DEFAULT_CONFIGSTRINGS)
    if configstrings:
        merged_configstrings.update(configstrings)
    configstring_command = build_configstring_command(merged_configstrings)
    return (
        bytes([SERVER_COMMAND_GAMESTATE])
        + struct.pack("<I", 0)
        + encoded_map
        + b"\0"
        + encoded_game_type
        + b"\0"
        + struct.pack("<I", config_checksum)
        + configstring_command
        + bytes([SERVER_COMMAND_EOF])
        + struct.pack("<II", client_num, checksum_feed)
        + bytes([SERVER_COMMAND_EOF])
    )


def float_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def write_playerstate_origin(
    writer: MessageBitWriter,
    origin: tuple[float, float, float],
) -> None:
    """Write CODOL's absolute origin fields from a zero playerstate baseline."""
    writer.write_bits(1, 1)   # Origin and velocity are present, not predicted.
    writer.write_bits(15, 8)  # Last changed playerstate field plus one.

    # Field 10: origin[0], delta from the initial field index -1 is 11.
    writer.write_bits(0, 1)
    writer.write_bits(10, 4)
    writer.write_raw(struct.pack("<f", origin[0]))

    # Field 13: origin[2], delta from field 10 is 3.
    writer.write_bits(0, 1)
    writer.write_bits(2, 4)
    writer.write_raw(struct.pack("<f", origin[2]))

    # Field 14: origin[1], consecutive-field short form.
    writer.write_bits(1, 1)
    writer.write_raw(struct.pack("<f", origin[1]))
    writer.write_bits(0, 14)  # Empty playerstate auxiliary sections.


def build_snapshot_probe_command(
    server_time: int,
    origin: tuple[float, float, float] | None = None,
    include_local_player: bool = False,
) -> bytes:
    """Build a bounded CODOL snapshot with all variable lists terminated."""
    if not 0 <= server_time <= 0x7FFFFFFF:
        raise ValueError("snapshot server time must be a non-negative signed integer")

    writer = MessageBitWriter()
    writer.write_raw(
        bytes([SERVER_COMMAND_SNAPSHOT])
        + struct.pack("<I", server_time)
        + bytes([0, 8])
    )

    writer.write_bits(0, 1)   # No delta snapshot baseline.
    if origin is None:
        writer.write_bits(0, 23)  # Empty playerstate delta.
    else:
        write_playerstate_origin(writer, origin)
    writer.write_bits(0, 1)   # Empty matchstate delta.

    if include_local_player:
        # Client 0: sequential index, present, and unchanged from a zero baseline.
        writer.write_bits(1, 1)
        writer.write_bits(1, 1)
        writer.write_bits(0, 1)
        writer.write_bits(0, 1)
    writer.write_bits(0, 1)   # End packet-client list.

    if include_local_player:
        # Entity 0: sequential index, present, field 0 (eType) = ET_PLAYER.
        writer.write_bits(1, 1)
        writer.write_bits(0, 1)
        writer.write_bits(1, 1)
        writer.write_bits(0, 1)
        writer.write_bits(0, 6)
        writer.write_bits(1, 1)
        # CODOL netfield -77 advances msg_t's raw byte cursor, not its bit cursor.
        writer.write_raw(bytes([1]))

    # CODOL entity numbers use: sequential bit, absolute bit, then 11 bits.
    writer.write_bits(0, 1)
    writer.write_bits(1, 1)
    writer.write_bits(2047, 11)
    writer.write_bits(0, 1)   # Empty auxiliary snapshot list.
    writer.write_raw(bytes([SERVER_COMMAND_EOF]))
    return bytes(writer.data)


def parse_client_reliable_commands(commands: bytes) -> list[tuple[int, str]]:
    parsed: list[tuple[int, str]] = []
    offset = 0
    while offset < len(commands) and commands[offset] == CLIENT_COMMAND_RELIABLE:
        offset += 1
        if offset + 4 > len(commands):
            break
        sequence = struct.unpack_from("<I", commands, offset)[0]
        offset += 4
        end = commands.find(b"\0", offset)
        if end < 0:
            break
        command = commands[offset:end].decode("latin-1", errors="replace")
        parsed.append((sequence, command))
        offset = end + 1
    return parsed


@dataclass(frozen=True)
class ProfileStatsChunk:
    index: int
    checksum: int
    payload: bytes

    @classmethod
    def parse(cls, packet: bytes) -> "ProfileStatsChunk":
        prefix = OOB_PREFIX + b"stats\0"
        if not packet.startswith(prefix) or len(packet) < len(prefix) + 3:
            raise ValueError("not a CODOL profile stats packet")
        index = packet[len(prefix)]
        if index >= PROFILE_CHUNK_COUNT:
            raise ValueError(f"profile chunk index {index} is out of range")
        checksum = struct.unpack_from("<H", packet, len(prefix) + 1)[0]
        return cls(index, checksum, packet[len(prefix) + 3:])


@dataclass(frozen=True)
class ProfileStatsResult:
    chunk: ProfileStatsChunk
    remaining_mask: int
    complete: bool
    profile: bytes | None

    @property
    def reply(self) -> bytes:
        return OOB_PREFIX + f"statResponse {self.remaining_mask}".encode("ascii")


@dataclass
class ProfileStatsUpload:
    chunks: dict[int, bytes] = field(default_factory=dict)
    remaining_mask: int = (1 << PROFILE_CHUNK_COUNT) - 1

    def accept(self, packet: bytes) -> ProfileStatsResult | None:
        if not packet.startswith(OOB_PREFIX + b"stats\0"):
            return None
        chunk = ProfileStatsChunk.parse(packet)
        self.chunks[chunk.index] = chunk.payload
        self.remaining_mask &= ~(1 << chunk.index)

        contiguous = bytearray()
        for index in range(PROFILE_CHUNK_COUNT):
            payload = self.chunks.get(index)
            if payload is None:
                break
            contiguous.extend(payload)

        decompressor = zlib.decompressobj()
        try:
            profile = decompressor.decompress(bytes(contiguous))
        except zlib.error:
            profile = None
        complete = profile is not None and decompressor.eof
        if complete:
            self.remaining_mask = 0
        else:
            profile = None
        return ProfileStatsResult(chunk, self.remaining_mask, complete, profile)


@dataclass(frozen=True)
class NATTraversalPacket:
    packet_type: int
    version: int
    hmac: bytes
    identifier: int
    source_address: str
    source_port: int
    destination_address: str
    destination_port: int

    @classmethod
    def parse(cls, packet: bytes) -> "NATTraversalPacket":
        if len(packet) != NAT_TRAVERSAL_PACKET_SIZE:
            raise ValueError(f"expected a 29-byte NAT traversal packet, got {len(packet)}")
        version = struct.unpack_from("<H", packet, 1)[0]
        if version < 2:
            raise ValueError(f"unsupported NAT traversal packet version {version}")
        identifier = struct.unpack_from("<I", packet, 13)[0]
        return cls(
            packet_type=packet[0],
            version=version,
            hmac=packet[3:13],
            identifier=identifier,
            source_address=socket.inet_ntoa(packet[17:21]),
            source_port=struct.unpack_from("<H", packet, 21)[0],
            destination_address=socket.inet_ntoa(packet[23:27]),
            destination_port=struct.unpack_from("<H", packet, 27)[0],
        )


def nat_intro_reply(packet: bytes) -> bytes | None:
    try:
        decoded = NATTraversalPacket.parse(packet)
    except ValueError:
        return None
    if decoded.packet_type != NAT_INTRO_REQUEST:
        return None
    return bytes([NAT_INTRO_REPLY]) + packet[1:]


@dataclass(frozen=True)
class DTLSInitPacket:
    version: int
    verification_tag: int
    counter: int
    init_tag: int
    security_id: bytes

    @classmethod
    def parse(cls, packet: bytes) -> "DTLSInitPacket":
        if len(packet) != DTLS_INIT_PACKET_SIZE:
            raise ValueError(f"expected a 16-byte DTLS init packet, got {len(packet)}")
        if packet[0] != DTLS_INIT:
            raise ValueError(f"expected DTLS init type, got {packet[0]}")
        version, verification_tag, counter, init_tag = struct.unpack_from(
            "<BHHH", packet, 1
        )
        if version != DTLS_VERSION:
            raise ValueError(f"unsupported DTLS packet version {version}")
        return cls(
            version=version,
            verification_tag=verification_tag,
            counter=counter,
            init_tag=init_tag,
            security_id=packet[8:16],
        )


def dtls_init_ack(
    packet: bytes,
    peer_address: str,
    peer_port: int,
    server_tag: int,
    timestamp: int,
) -> bytes | None:
    try:
        decoded = DTLSInitPacket.parse(packet)
    except ValueError:
        return None
    if not 0 < server_tag <= 0xFFFF:
        raise ValueError("server DTLS tag must fit in uint16 and be nonzero")

    header = struct.pack(
        "<BBHH",
        DTLS_INIT_ACK,
        DTLS_VERSION,
        decoded.init_tag,
        0,
    )
    cookie = struct.pack(
        "<IIHHHHH",
        timestamp & 0xFFFFFFFF,
        0,
        server_tag,
        server_tag,
        decoded.init_tag,
        0,
        0,
    )
    return (
        header
        + cookie
        + encode_endpoint(peer_address, peer_port)
        + decoded.security_id
    )


@dataclass(frozen=True)
class DTLSCookieEchoPacket:
    verification_tag: int
    counter: int
    client_tag: int
    common_address: bytes
    security_id: bytes
    public_key: bytes

    @classmethod
    def parse(cls, packet: bytes) -> "DTLSCookieEchoPacket":
        if len(packet) != DTLS_COOKIE_ECHO_PACKET_SIZE:
            raise ValueError(
                f"expected a 189-byte DTLS cookie echo packet, got {len(packet)}"
            )
        packet_type, version, verification_tag, counter = struct.unpack_from(
            "<BBHH", packet
        )
        if packet_type != DTLS_COOKIE_ECHO or version != DTLS_VERSION:
            raise ValueError("not a supported DTLS cookie echo packet")
        init_ack_type, init_ack_version, client_tag = struct.unpack_from(
            "<BBH", packet, 6
        )
        if init_ack_type != DTLS_INIT_ACK or init_ack_version != DTLS_VERSION:
            raise ValueError("cookie echo does not contain a supported DTLS init ack")
        return cls(
            verification_tag=verification_tag,
            counter=counter,
            client_tag=client_tag,
            common_address=packet[44:81],
            security_id=packet[81:89],
            public_key=packet[89:189],
        )


class DTLSECCKeyPair:
    def __init__(self, private_key: ec.EllipticCurvePrivateKey | None = None) -> None:
        self.private_key = private_key or ec.generate_private_key(ec.SECP224R1())
        self.public_key = self._export_public_key(self.private_key.public_key())

    @staticmethod
    def _encode_integer(value: int) -> bytes:
        encoded = value.to_bytes(28, "big")
        if encoded[0] & 0x80:
            encoded = b"\x00" + encoded
        return b"\x02" + bytes([len(encoded)]) + encoded

    @classmethod
    def _export_public_key(cls, key: ec.EllipticCurvePublicKey) -> bytes:
        numbers = key.public_numbers()
        content = (
            b"\x03\x02\x07\x00"
            + b"\x02\x01\x1c"
            + cls._encode_integer(numbers.x)
            + cls._encode_integer(numbers.y)
        )
        exported = b"\x30" + bytes([len(content)]) + content
        if len(exported) > 100:
            raise ValueError("P-224 public key does not fit CODOL's 100-byte field")
        return exported.ljust(100, b"\x00")

    @staticmethod
    def _read_tlv(data: bytes, offset: int, expected_tag: int) -> tuple[bytes, int]:
        if offset + 2 > len(data) or data[offset] != expected_tag:
            raise ValueError(f"expected DER tag 0x{expected_tag:02x} at offset {offset}")
        size = data[offset + 1]
        start = offset + 2
        end = start + size
        if size & 0x80 or end > len(data):
            raise ValueError("unsupported or truncated DER length")
        return data[start:end], end

    @classmethod
    def import_public_key(cls, exported: bytes) -> ec.EllipticCurvePublicKey:
        sequence, _ = cls._read_tlv(exported, 0, 0x30)
        _, offset = cls._read_tlv(sequence, 0, 0x03)
        key_size, offset = cls._read_tlv(sequence, offset, 0x02)
        x, offset = cls._read_tlv(sequence, offset, 0x02)
        y, _ = cls._read_tlv(sequence, offset, 0x02)
        if int.from_bytes(key_size, "big") != 28:
            raise ValueError("CODOL DTLS public key is not P-224")
        numbers = ec.EllipticCurvePublicNumbers(
            int.from_bytes(x, "big"),
            int.from_bytes(y, "big"),
            ec.SECP224R1(),
        )
        return numbers.public_key()

    def shared_secret(self, peer_public_key: bytes, security_key: bytes) -> bytes:
        if len(security_key) != 16:
            raise ValueError("CODOL DTLS SecurityKey must be exactly 16 bytes")
        secret = self.private_key.exchange(
            ec.ECDH(), self.import_public_key(peer_public_key)
        )
        if len(secret) != 28:
            raise ValueError(f"expected a 28-byte P-224 shared secret, got {len(secret)}")
        return secret + security_key


def dtls_cookie_ack(packet: bytes, public_key: bytes | None = None) -> bytes | None:
    try:
        decoded = DTLSCookieEchoPacket.parse(packet)
    except ValueError:
        return None
    reply_key = public_key or decoded.public_key
    if len(reply_key) != 100:
        raise ValueError("DTLS cookie ack public key must be exactly 100 bytes")
    header = struct.pack(
        "<BBHH",
        DTLS_COOKIE_ACK,
        DTLS_VERSION,
        decoded.client_tag,
        0,
    )
    return header + reply_key + decoded.security_id


@dataclass(frozen=True)
class DTLSSessionKeys:
    digest: bytes

    @classmethod
    def derive(cls, shared_secret: bytes) -> "DTLSSessionKeys":
        if len(shared_secret) != 44:
            raise ValueError("CODOL DTLS shared material must be exactly 44 bytes")
        return cls(hashlib.sha1(shared_secret).digest())

    @property
    def aes_key(self) -> bytes:
        return self.digest[:16]

    @property
    def hmac_key(self) -> bytes:
        return self.digest + bytes(4)

    def iv(self, sequence_number: int, verification_tag: int) -> bytes:
        seed = struct.pack("<IH", sequence_number, verification_tag)
        return hashlib.sha1(seed).digest()[:16]


def aes_ctr_little_endian(key: bytes, iv: bytes, data: bytes) -> bytes:
    if len(iv) != 16:
        raise ValueError("CODOL AES-CTR IV must be exactly 16 bytes")
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    counter = int.from_bytes(iv, "little")
    output = bytearray()
    for offset in range(0, len(data), 16):
        block = data[offset:offset + 16]
        keystream = encryptor.update(counter.to_bytes(16, "little"))
        output.extend(left ^ right for left, right in zip(block, keystream))
        counter = (counter + 1) & ((1 << 128) - 1)
    encryptor.finalize()
    return bytes(output)


@dataclass(frozen=True)
class DTLSDataPacket:
    verification_tag: int
    sequence_number: int
    authenticator: bytes
    encrypted_size: int
    payload: bytes

    @classmethod
    def parse(cls, packet: bytes) -> "DTLSDataPacket":
        if len(packet) < 16:
            raise ValueError("DTLS data packet is shorter than its 16-byte header")
        packet_type, version, verification_tag, sequence_number = struct.unpack_from(
            "<BBHH", packet
        )
        if packet_type != DTLS_DATA or version != DTLS_VERSION:
            raise ValueError("not a supported DTLS data packet")
        encrypted_size = struct.unpack_from("<H", packet, 14)[0]
        payload = packet[16:]
        if encrypted_size > len(payload):
            raise ValueError("DTLS encrypted prefix exceeds the payload size")
        return cls(
            verification_tag=verification_tag,
            sequence_number=sequence_number,
            authenticator=packet[6:14],
            encrypted_size=encrypted_size,
            payload=payload,
        )

    def _header(self) -> bytes:
        return struct.pack(
            "<BBHH",
            DTLS_DATA,
            DTLS_VERSION,
            self.verification_tag,
            self.sequence_number,
        )

    def authenticated_bytes(self) -> bytes:
        return self._header() + struct.pack("<H", self.encrypted_size) + self.payload

    def verify(self, keys: DTLSSessionKeys) -> bool:
        expected = hmac.new(
            keys.hmac_key,
            self.authenticated_bytes(),
            hashlib.sha1,
        ).digest()[:8]
        return hmac.compare_digest(expected, self.authenticator)

    def decrypt(self, keys: DTLSSessionKeys) -> bytes:
        if not self.verify(keys):
            raise ValueError("DTLS data authenticator does not match")
        decrypted = aes_ctr_little_endian(
            keys.aes_key,
            keys.iv(self.sequence_number, self.verification_tag),
            self.payload[:self.encrypted_size],
        )
        return decrypted + self.payload[self.encrypted_size:]

    @classmethod
    def build(
        cls,
        payload: bytes,
        verification_tag: int,
        sequence_number: int,
        keys: DTLSSessionKeys,
        encrypted_size: int | None = None,
    ) -> bytes:
        if not 0 <= verification_tag <= 0xFFFF:
            raise ValueError("DTLS verification tag must fit in uint16")
        if not 0 <= sequence_number <= 0xFFFF:
            raise ValueError("DTLS sequence number must fit in uint16")
        prefix_size = len(payload) if encrypted_size is None else encrypted_size
        if not 0 <= prefix_size <= min(len(payload), 0xFFFF):
            raise ValueError("invalid DTLS encrypted prefix size")
        encrypted = aes_ctr_little_endian(
            keys.aes_key,
            keys.iv(sequence_number, verification_tag),
            payload[:prefix_size],
        )
        encrypted += payload[prefix_size:]
        candidate = cls(verification_tag, sequence_number, bytes(8), prefix_size, encrypted)
        authenticator = hmac.new(
            keys.hmac_key,
            candidate.authenticated_bytes(),
            hashlib.sha1,
        ).digest()[:8]
        return candidate._header() + authenticator + struct.pack("<H", prefix_size) + encrypted


@dataclass
class DescriptorWatcher:
    path: Path
    offset: int = 0
    descriptor: bytes | None = None

    def poll(self) -> bool:
        try:
            size = self.path.stat().st_size
        except OSError:
            return False
        if size < self.offset:
            self.offset = 0
        changed = False
        with self.path.open("r", encoding="utf-8", errors="replace") as stream:
            stream.seek(self.offset)
            for line in stream:
                match = TASK1_PATTERN.search(line)
                if not match:
                    continue
                try:
                    self.descriptor = extract_session_descriptor(match.group(1))
                    changed = True
                except ValueError:
                    continue
            self.offset = stream.tell()
        return changed


def select_descriptor_source(
    descriptor_hex: str | None,
    lsg_log: Path | None,
) -> tuple[bytes | None, DescriptorWatcher | None]:
    if descriptor_hex:
        return bytes.fromhex(descriptor_hex), None
    if lsg_log is None:
        return None, None
    watcher = DescriptorWatcher(lsg_log)
    watcher.poll()
    return watcher.descriptor, watcher


class Recorder:
    def __init__(self, path: Path | None, echo: bool = True) -> None:
        self.path = path
        self.echo = echo

    def write(self, event: str, **fields: Any) -> None:
        record = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            **fields,
        }
        if self.echo:
            try:
                print(json.dumps(record, ensure_ascii=True), flush=True)
            except BrokenPipeError:
                self.echo = False
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def default_lsg_log() -> Path | None:
    workspace = Path(__file__).resolve().parents[2]
    game = find_game_directory(workspace)
    if game is None:
        return None
    return game / "Ayria" / "Logs" / "AlwaysofflineRe.Localnet32.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1", help="UDP gameplay bind address")
    parser.add_argument("--port", type=int, default=28960, help="UDP gameplay port")
    parser.add_argument(
        "--advertise-address",
        help="Address written into bdCommonAddr (defaults to --bind)",
    )
    parser.add_argument("--nat-type", type=int, default=1, choices=range(4))
    parser.add_argument("--challenge", type=int, default=random.randint(1, 0x7FFFFFFF))
    parser.add_argument("--discovery-address", default="255.255.255.255")
    parser.add_argument("--discovery-port", type=int, default=DISCOVERY_PORT)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=0.0, help="Stop after N seconds; 0 waits")
    parser.add_argument("--descriptor-hex", help="Override native Session.Demonware bytes")
    parser.add_argument("--lsg-log", type=Path, default=default_lsg_log())
    parser.add_argument("--log", type=Path, help="Optional JSONL capture path")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not mirror JSONL events to standard output",
    )
    parser.add_argument(
        "--send-minimal-gamestate",
        action="store_true",
        help="Send one minimal svc_gamestate after the client enters netchan traffic",
    )
    parser.add_argument(
        "--send-snapshot-probe",
        action="store_true",
        help="Send a bounded empty snapshot after gamestateupdate 6",
    )
    parser.add_argument(
        "--send-local-player",
        action="store_true",
        help="Include client 0 and entity 0/ET_PLAYER in snapshot probes",
    )
    parser.add_argument(
        "--snapshot-rate",
        type=float,
        default=20.0,
        help="Snapshot frames per second after the first bounded snapshot",
    )
    parser.add_argument(
        "--spawn-origin",
        type=float,
        nargs=3,
        default=(0.0, 0.0, 256.0),
        metavar=("X", "Y", "Z"),
        help="Absolute player origin written into each snapshot",
    )
    parser.add_argument("--map-name", default="", help="Map name in the minimal gamestate")
    parser.add_argument("--game-type", default="", help="Game type in the minimal gamestate")
    parser.add_argument(
        "--config-checksum",
        type=lambda value: int(value, 0),
        default=0,
        help="Constant configstring checksum written into the minimal gamestate",
    )
    parser.add_argument(
        "--configstring",
        action="append",
        default=[],
        metavar="INDEX=VALUE",
        help="Raw CODOL gamestate configstring; may be repeated",
    )
    return parser.parse_args()


def parse_configstrings(values: list[str]) -> dict[int, str]:
    result: dict[int, str] = {}
    for value in values:
        index_text, separator, text = value.partition("=")
        if not separator:
            raise SystemExit(f"invalid --configstring {value!r}; expected INDEX=VALUE")
        try:
            index = int(index_text, 0)
        except ValueError as error:
            raise SystemExit(f"invalid configstring index {index_text!r}") from error
        if index in result:
            raise SystemExit(f"duplicate configstring index {index}")
        result[index] = text
    return result


def run(args: argparse.Namespace) -> int:
    advertise_address = args.advertise_address or args.bind
    if advertise_address == "0.0.0.0":
        raise SystemExit("--advertise-address is required when --bind is 0.0.0.0")
    if not 0.0 < args.snapshot_rate <= 60.0:
        raise SystemExit("--snapshot-rate must be greater than 0 and at most 60")

    descriptor, watcher = select_descriptor_source(args.descriptor_hex, args.lsg_log)

    recorder = Recorder(args.log, echo=not args.quiet)
    configstrings = parse_configstrings(args.configstring)
    origin = random.randint(1, 0xFFFFFFFFFFFFFFFF)
    dtls_server_tag = random.randint(1, 0xFFFF)
    dtls_key_pair = DTLSECCKeyPair()
    gameplay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gameplay.bind((args.bind, args.port))
    discovery = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    destination = (args.discovery_address, args.discovery_port)
    deadline = time.monotonic() + args.duration if args.duration > 0 else None
    next_advertisement = 0.0
    advertised = False
    waiting_reported = False
    dtls_keys: DTLSSessionKeys | None = None
    dtls_client_tag: int | None = None
    dtls_server_sequence = 1
    profile_upload = ProfileStatsUpload()
    netchan_server_sequence = 1
    client_reliable_sequence = 0
    gamestate_sent = False
    snapshot_sent = False
    snapshot_frame = 0
    next_snapshot = 0.0
    dtls_peer: tuple[str, int] | None = None

    recorder.write(
        "started",
        bind=f"{args.bind}:{args.port}",
        advertise=f"{advertise_address}:{args.port}",
        descriptor_source=str(args.lsg_log) if watcher else "command-line",
    )
    try:
        while deadline is None or time.monotonic() < deadline:
            now = time.monotonic()
            if watcher is not None and watcher.poll():
                descriptor = watcher.descriptor
                recorder.write("descriptor_updated", size=len(descriptor or b""))
                next_advertisement = 0.0
                waiting_reported = False

            if descriptor is not None and now >= next_advertisement:
                properties = build_server_properties(
                    advertise_address,
                    args.port,
                    descriptor,
                    args.nat_type,
                )
                packet = encode_meep(
                    "Matchmaking::Update",
                    origin,
                    json.dumps(properties, separators=(",", ":")),
                )
                discovery.sendto(packet, destination)
                if not advertised:
                    recorder.write(
                        "advertised",
                        origin=origin,
                        discovery=f"{destination[0]}:{destination[1]}",
                        descriptor_size=len(descriptor),
                    )
                advertised = True
                next_advertisement = now + args.interval
            elif descriptor is None and not waiting_reported:
                recorder.write("waiting_for_descriptor")
                waiting_reported = True

            if (
                args.send_snapshot_probe
                and snapshot_sent
                and dtls_keys is not None
                and dtls_client_tag is not None
                and dtls_peer is not None
                and now >= next_snapshot
            ):
                sent_netchan_sequence = netchan_server_sequence
                server_commands = build_snapshot_probe_command(
                    int(now * 1000) & 0x7FFFFFFF,
                    tuple(args.spawn_origin),
                    include_local_player=args.send_local_player,
                )
                inner_reply = build_server_netchan_packet(
                    sent_netchan_sequence,
                    args.challenge,
                    reliable_acknowledge=client_reliable_sequence,
                    commands=server_commands,
                )
                reply = DTLSDataPacket.build(
                    inner_reply,
                    dtls_client_tag,
                    dtls_server_sequence,
                    dtls_keys,
                )
                gameplay.sendto(reply, dtls_peer)
                recorder.write(
                    "sent_dtls_netchan_snapshot_frame",
                    destination=f"{dtls_peer[0]}:{dtls_peer[1]}",
                    sequence=dtls_server_sequence,
                    server_netchan_sequence=sent_netchan_sequence,
                    frame=snapshot_frame,
                    server_time=int(now * 1000) & 0x7FFFFFFF,
                    origin=list(args.spawn_origin),
                )
                netchan_server_sequence = sent_netchan_sequence + 1
                dtls_server_sequence = (dtls_server_sequence + 1) & 0xFFFF
                snapshot_frame += 1
                next_snapshot = now + 1.0 / args.snapshot_rate

            timeout = min(0.25, max(0.0, next_advertisement - now)) if descriptor else 0.25
            if snapshot_sent:
                timeout = min(timeout, max(0.0, next_snapshot - now))
            readable, _, _ = select.select([gameplay], [], [], timeout)
            if not readable:
                continue
            packet, source = gameplay.recvfrom(65535)
            text = packet[len(OOB_PREFIX):].decode("latin-1", errors="replace") \
                if packet.startswith(OOB_PREFIX) else ""
            recorder.write(
                "received",
                source=f"{source[0]}:{source[1]}",
                size=len(packet),
                oob=text,
                hex=packet.hex(),
            )
            reply = oob_challenge_reply(packet, args.challenge)
            if reply is not None:
                gameplay.sendto(reply, source)
                recorder.write(
                    "sent_challenge",
                    destination=f"{source[0]}:{source[1]}",
                    challenge=args.challenge,
                    hex=reply.hex(),
                )
                continue

            reply = nat_intro_reply(packet)
            if reply is not None:
                decoded = NATTraversalPacket.parse(packet)
                gameplay.sendto(reply, source)
                recorder.write(
                    "sent_nat_intro_reply",
                    destination=f"{source[0]}:{source[1]}",
                    identifier=f"0x{decoded.identifier:08x}",
                    packet_source=f"{decoded.source_address}:{decoded.source_port}",
                    packet_destination=(
                        f"{decoded.destination_address}:{decoded.destination_port}"
                    ),
                    hex=reply.hex(),
                )
                continue

            reply = dtls_init_ack(
                packet,
                source[0],
                source[1],
                dtls_server_tag,
                int(time.monotonic() * 1000),
            )
            if reply is not None:
                decoded = DTLSInitPacket.parse(packet)
                gameplay.sendto(reply, source)
                recorder.write(
                    "sent_dtls_init_ack",
                    destination=f"{source[0]}:{source[1]}",
                    client_tag=f"0x{decoded.init_tag:04x}",
                    server_tag=f"0x{dtls_server_tag:04x}",
                    security_id=decoded.security_id.hex(),
                    hex=reply.hex(),
                )
                continue

            reply = dtls_cookie_ack(packet, dtls_key_pair.public_key)
            if reply is not None:
                decoded = DTLSCookieEchoPacket.parse(packet)
                if descriptor is None:
                    recorder.write("dtls_key_error", error="no session descriptor")
                    continue
                try:
                    security_key = extract_descriptor_security_key(descriptor)
                    shared_secret = dtls_key_pair.shared_secret(
                        decoded.public_key,
                        security_key,
                    )
                except ValueError as error:
                    recorder.write("dtls_key_error", error=str(error))
                    continue
                dtls_keys = DTLSSessionKeys.derive(shared_secret)
                dtls_client_tag = decoded.client_tag
                dtls_server_sequence = 1
                profile_upload = ProfileStatsUpload()
                netchan_server_sequence = 1
                client_reliable_sequence = 0
                gamestate_sent = False
                snapshot_sent = False
                snapshot_frame = 0
                next_snapshot = 0.0
                dtls_peer = source
                gameplay.sendto(reply, source)
                recorder.write(
                    "sent_dtls_cookie_ack",
                    destination=f"{source[0]}:{source[1]}",
                    client_tag=f"0x{decoded.client_tag:04x}",
                    server_tag=f"0x{decoded.verification_tag:04x}",
                    security_id=decoded.security_id.hex(),
                    security_key=security_key.hex(),
                    ecdh_secret=shared_secret.hex(),
                    shared_digest=dtls_keys.digest.hex(),
                    hex=reply.hex(),
                )
                continue

            if packet[:1] == bytes([DTLS_DATA]):
                if dtls_keys is None or dtls_client_tag is None:
                    recorder.write("dtls_data_error", error="session keys are unavailable")
                    continue
                try:
                    decoded = DTLSDataPacket.parse(packet)
                    plaintext = decoded.decrypt(dtls_keys)
                except ValueError as error:
                    recorder.write("dtls_data_error", error=str(error), hex=packet.hex())
                    continue
                is_stats = plaintext.startswith(OOB_PREFIX + b"stats\0")
                is_netchan = not plaintext.startswith(OOB_PREFIX) and len(plaintext) >= 14
                recorder.write(
                    "received_dtls_data",
                    verification_tag=f"0x{decoded.verification_tag:04x}",
                    sequence=decoded.sequence_number,
                    encrypted_size=decoded.encrypted_size,
                    plaintext_hex=(plaintext[:13] if is_stats else plaintext).hex(),
                    plaintext=(
                        "stats"
                        if is_stats
                        else "netchan"
                        if is_netchan
                        else plaintext.decode("latin-1", errors="replace")
                    ),
                    plaintext_size=len(plaintext),
                )
                inner_reply = oob_challenge_reply(plaintext, args.challenge)
                reply_event = "sent_dtls_challenge"
                reply_fields: dict[str, Any] = {}
                if inner_reply is None:
                    inner_reply = oob_connect_reply(plaintext)
                    reply_event = "sent_dtls_connect_response"
                if inner_reply is None:
                    stats_result = profile_upload.accept(plaintext)
                    if stats_result is not None:
                        inner_reply = stats_result.reply
                        reply_event = "sent_dtls_stat_response"
                        reply_fields = {
                            "chunk_index": stats_result.chunk.index,
                            "chunk_checksum": f"0x{stats_result.chunk.checksum:04x}",
                            "chunk_size": len(stats_result.chunk.payload),
                            "remaining_mask": f"0x{stats_result.remaining_mask:08x}",
                            "complete": stats_result.complete,
                            "profile_size": (
                                len(stats_result.profile)
                                if stats_result.profile is not None
                                else None
                            ),
                        }
                if inner_reply is None:
                    inner_reply = oob_heartbeat_reply(plaintext)
                    reply_event = "sent_dtls_heartbeat_response"
                if inner_reply is None and is_netchan:
                    try:
                        client_netchan = ClientNetchanPacket.parse(plaintext)
                        client_commands = client_netchan.decode_commands(args.challenge)
                    except ValueError as error:
                        recorder.write("client_netchan_error", error=str(error))
                        continue
                    reliable_commands = parse_client_reliable_commands(client_commands)
                    for reliable_sequence, _ in reliable_commands:
                        if reliable_sequence > client_reliable_sequence:
                            client_reliable_sequence = reliable_sequence
                    if client_netchan.message_acknowledge >= netchan_server_sequence:
                        netchan_server_sequence = client_netchan.message_acknowledge + 1
                    sent_netchan_sequence = netchan_server_sequence
                    server_commands = bytes([SERVER_COMMAND_EOF])
                    if args.send_minimal_gamestate and not gamestate_sent:
                        server_commands = build_minimal_gamestate_commands(
                            args.map_name,
                            args.game_type,
                            args.config_checksum,
                            configstrings=configstrings,
                        )
                        gamestate_sent = True
                    inner_reply = build_server_netchan_packet(
                        sent_netchan_sequence,
                        args.challenge,
                        reliable_acknowledge=client_reliable_sequence,
                        commands=server_commands,
                    )
                    netchan_server_sequence = sent_netchan_sequence + 1
                    reply_event = (
                        "sent_dtls_netchan_gamestate"
                        if server_commands[0] == SERVER_COMMAND_GAMESTATE
                        else "sent_dtls_netchan_eof"
                    )
                    reply_fields = {
                        "client_netchan_sequence": client_netchan.netchan_sequence,
                        "client_server_id": client_netchan.server_id,
                        "client_message_acknowledge": client_netchan.message_acknowledge,
                        "client_reliable_acknowledge": client_netchan.reliable_acknowledge,
                        "client_commands_hex": client_commands.hex(),
                        "client_reliable_commands": [
                            {"sequence": sequence, "command": command}
                            for sequence, command in reliable_commands
                        ],
                        "client_reliable_sequence": client_reliable_sequence,
                        "server_netchan_sequence": sent_netchan_sequence,
                    }
                if (
                    inner_reply is None
                    and args.send_snapshot_probe
                    and gamestate_sent
                    and not snapshot_sent
                    and plaintext.startswith(OOB_PREFIX + b"gamestateupdate 6\0")
                ):
                    sent_netchan_sequence = netchan_server_sequence
                    server_commands = build_snapshot_probe_command(
                        int(time.monotonic() * 1000) & 0x7FFFFFFF,
                        tuple(args.spawn_origin),
                        include_local_player=args.send_local_player,
                    )
                    inner_reply = build_server_netchan_packet(
                        sent_netchan_sequence,
                        args.challenge,
                        reliable_acknowledge=client_reliable_sequence,
                        commands=server_commands,
                    )
                    netchan_server_sequence = sent_netchan_sequence + 1
                    snapshot_sent = True
                    snapshot_frame = 1
                    next_snapshot = time.monotonic() + 1.0 / args.snapshot_rate
                    reply_event = "sent_dtls_netchan_snapshot_probe"
                    reply_fields = {
                        "server_netchan_sequence": sent_netchan_sequence,
                        "snapshot_layout": "bounded_spawn",
                        "origin": list(args.spawn_origin),
                        "snapshot_rate": args.snapshot_rate,
                    }
                if inner_reply is None:
                    continue
                reply = DTLSDataPacket.build(
                    inner_reply,
                    dtls_client_tag,
                    dtls_server_sequence,
                    dtls_keys,
                )
                gameplay.sendto(reply, source)
                recorder.write(
                    reply_event,
                    destination=f"{source[0]}:{source[1]}",
                    sequence=dtls_server_sequence,
                    plaintext_hex=inner_reply.hex(),
                    hex=reply.hex(),
                    **reply_fields,
                )
                dtls_server_sequence = (dtls_server_sequence + 1) & 0xFFFF
    except KeyboardInterrupt:
        recorder.write("interrupted")
    finally:
        if advertised and descriptor is not None:
            discovery.sendto(encode_meep("Matchmaking::Terminate", origin, ""), destination)
        discovery.close()
        gameplay.close()
        recorder.write("stopped")
    return 0


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
