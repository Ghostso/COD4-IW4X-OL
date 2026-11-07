#!/usr/bin/env python3
"""IW4-lineage server kernel and CODOL protocol workbench.

This is a runnable server core, not a claim that the CODOL wire protocol has
already been recovered. It borrows the useful IW4/IW4X server shape:

* a long-lived engine state and room/player model;
* transport independent message adapters;
* an OOB info/status path for controlled IW4-family tests;
* exact request -> response replay for payload-bearing captures;
* raw frame logging for unknown CODOL traffic.

The default mode is observation. Unknown packets are never answered with a
guessed CODOL handshake. Use --echo only for a local transport smoke test,
--mode iw4 for explicit IW4-style getinfo/getstatus tests, or --replay after
capturing a legitimate request/response exchange.
"""

from __future__ import annotations

import argparse
import json
import signal
import socket
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
OOB_MAGIC = b"\xff\xff\xff\xff"


def parse_hex(value: str | None) -> bytes | None:
    if value is None:
        return None
    compact = "".join(value.split())
    if len(compact) % 2:
        raise argparse.ArgumentTypeError("hex value must contain an even number of digits")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid hex value: {exc}") from exc


def safe_text(value: str, limit: int = 128) -> str:
    """Keep info strings and logs from gaining control characters."""
    value = value.replace("\\", "/").replace("\r", " ").replace("\n", " ")
    return value[:limit]


def info_string(fields: dict[str, str]) -> bytes:
    """Render the classic IW-family backslash info-string shape."""
    parts: list[str] = []
    for key, value in fields.items():
        parts.extend((safe_text(str(key), 64), safe_text(str(value))))
    return ("\\" + "\\".join(parts)).encode("utf-8", "replace")


def oob_packet(command: str, data: bytes = b"") -> bytes:
    return OOB_MAGIC + command.encode("ascii") + b"\n" + data


@dataclass
class Player:
    slot: int
    name: str
    score: int = 0
    ping: int = 0
    team: str = "spectator"
    ready: bool = False
    connected: bool = True


class EngineState:
    """Small server-side state model shaped after the IW4 server dvars."""

    def __init__(
        self,
        *,
        hostname: str,
        gamename: str,
        version: str,
        protocol: int,
        mapname: str,
        gametype: str,
        max_clients: int,
        motd: str,
    ) -> None:
        self.hostname = safe_text(hostname)
        self.gamename = safe_text(gamename)
        self.version = safe_text(version)
        self.protocol = protocol
        self.mapname = safe_text(mapname, 64)
        self.gametype = safe_text(gametype, 32)
        self.max_clients = max(1, min(max_clients, 128))
        self.motd = safe_text(motd)
        self.room_state = "lobby"
        self.match_generation = 0
        self.started_at = time.time()
        self.players: dict[int, Player] = {}
        self.lock = threading.RLock()

    def add_player(self, name: str, *, slot: int | None = None) -> Player:
        with self.lock:
            if slot is None:
                free = (i for i in range(self.max_clients) if i not in self.players)
                slot = next(free, None)
            if slot is None or not 0 <= slot < self.max_clients:
                raise ValueError("room is full")
            player = Player(slot=slot, name=safe_text(name, 32), team="allies")
            self.players[slot] = player
            return player

    def remove_player(self, slot: int) -> None:
        with self.lock:
            self.players.pop(slot, None)

    def info_fields(self, challenge: str = "") -> dict[str, str]:
        with self.lock:
            fields = {
                "gamename": self.gamename,
                "sv_hostname": self.hostname,
                "sv_maxclients": str(self.max_clients),
                "clients": str(len(self.players)),
                "protocol": str(self.protocol),
                "version": self.version,
                "mapname": self.mapname,
                "g_gametype": self.gametype,
                "isPrivate": "0",
                "matchtype": "2",
                "roomstate": self.room_state,
                "match_generation": str(self.match_generation),
                "motd": self.motd,
            }
            if challenge:
                fields["challenge"] = safe_text(challenge, 64)
            return fields

    def status_body(self, challenge: str = "") -> bytes:
        with self.lock:
            rows = [
                f'{p.score} {p.ping} "{safe_text(p.name, 32)}"'
                for p in sorted(self.players.values(), key=lambda item: item.slot)
                if p.connected
            ]
        return info_string(self.info_fields(challenge)) + b"\n" + "\n".join(rows).encode() + b"\n\n"


@dataclass
class DecodedMessage:
    adapter: str
    recognized: bool
    command: str | None = None
    note: str | None = None


@dataclass
class AdapterResult:
    adapter: str
    recognized: bool
    responses: list[bytes] = field(default_factory=list)
    message: DecodedMessage | None = None


class ProtocolAdapter:
    name = "base"

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        raise NotImplementedError


class ObserveAdapter(ProtocolAdapter):
    name = "observe"

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        return AdapterResult(
            adapter=self.name,
            recognized=False,
            message=DecodedMessage(self.name, False, note="unknown payload left unanswered"),
        )


class EchoAdapter(ProtocolAdapter):
    name = "echo"

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        return AdapterResult(
            adapter=self.name,
            recognized=True,
            responses=[payload],
            message=DecodedMessage(self.name, True, note="explicit local echo"),
        )


class FixedResponseAdapter(ProtocolAdapter):
    name = "fixed"

    def __init__(self, tcp_response: bytes | None, udp_response: bytes | None) -> None:
        self.responses = {"tcp": tcp_response, "udp": udp_response}

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        response = self.responses.get(transport)
        if response is None:
            return AdapterResult(self.name, False, message=DecodedMessage(self.name, False))
        return AdapterResult(
            self.name,
            True,
            [response],
            DecodedMessage(self.name, True, note="explicit fixed response"),
        )


class ReplayAdapter(ProtocolAdapter):
    """Replay exact captured request bytes without inventing a decoder."""

    name = "replay"

    def __init__(self, path: Path) -> None:
        self.routes: dict[tuple[str, bytes], deque[bytes]] = defaultdict(deque)
        self.path = path
        self._load()

    def _load(self) -> None:
        with self.path.open("r", encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        pending: dict[tuple[str, tuple[Any, ...]], deque[bytes]] = defaultdict(deque)
        for record in records:
            if record.get("event") != "frame":
                continue
            transport = str(record.get("transport", ""))
            peer = tuple(record.get("peer") or ())
            try:
                payload = bytes.fromhex(str(record.get("hex", "")))
            except ValueError:
                continue
            key = (transport, peer)
            if record.get("direction") == "in":
                pending[key].append(payload)
            elif record.get("direction") == "out" and pending[key]:
                request = pending[key].popleft()
                self.routes[(transport, request)].append(payload)

        for record in records:
            if "request_hex" not in record or "response_hex" not in record:
                continue
            try:
                request = bytes.fromhex(str(record["request_hex"]))
                response = bytes.fromhex(str(record["response_hex"]))
            except ValueError:
                continue
            self.routes[(str(record.get("transport", "udp")), request)].append(response)

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        queue = self.routes.get((transport, payload))
        if not queue:
            return AdapterResult(self.name, False, message=DecodedMessage(self.name, False, note="no exact replay match"))
        response = queue.popleft()
        return AdapterResult(
            self.name,
            True,
            [response],
            DecodedMessage(self.name, True, note="exact request replay"),
        )


class Iw4OobAdapter(ProtocolAdapter):
    """Minimal explicit IW4-family discovery/status adapter.

    It intentionally implements only getinfo/getstatus. It does not accept
    connect because IW4X authentication and CODOL authentication are separate
    trust domains and a guessed connect response would be misleading.
    """

    name = "iw4-oob"

    @staticmethod
    def _parse(payload: bytes) -> tuple[str, bytes] | None:
        if not payload.startswith(OOB_MAGIC):
            return None
        command_data = payload[len(OOB_MAGIC):]
        command, separator, data = command_data.partition(b"\n")
        if not separator:
            command, data = command_data, b""
        return command.decode("ascii", "replace").strip().lower(), data

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        parsed = self._parse(payload)
        if parsed is None:
            return AdapterResult(self.name, False, message=DecodedMessage(self.name, False, note="not IW4 OOB"))
        command, data = parsed
        challenge = data.decode("ascii", "replace").strip()
        if command == "getinfo":
            return AdapterResult(
                self.name,
                True,
                [oob_packet("infoResponse", info_string(state.info_fields(challenge)))],
                DecodedMessage(self.name, True, command, "IW4-style discovery response"),
            )
        if command == "getstatus":
            return AdapterResult(
                self.name,
                True,
                [oob_packet("statusResponse", state.status_body(challenge))],
                DecodedMessage(self.name, True, command, "IW4-style status response"),
            )
        return AdapterResult(
            self.name,
            False,
            message=DecodedMessage(self.name, False, command, "unsupported OOB command left unanswered"),
        )


class CodolIpProbeAdapter(ProtocolAdapter):
    """Answer the CODOL public-address probe observed on UDP port 8000.

    Captured exchange from ENTRY_CAPTURE_ELEVATED_20260924_160326 (game PID
    19040), verified against AFD byte counts (request 24, response 73):

      client -> server  (24 bytes)
        75 72 00 10 00 08 00 03 00 00 00 0b 00 00 55 ed
        00 00 00 64 00 18 00 00

      server -> client  (73 bytes)
        75 72 00 10 00 39 00 04 00 00 00 0b 00 00 55 ed
        ... two length-prefixed strings: "116.130.224.66" and
        "255.255.255.0" ...

    The response is kept as a byte template copied from that real capture.
    Only the two length-prefixed strings are rewritten from
    --advertise-address / --advertise-mask, and every enclosing length field
    is recomputed. Nothing else is invented.
    """

    name = "codol-ip-probe"

    MAGIC = b"\x75\x72"

    CAPTURED_REQUEST = bytes.fromhex(
        "75720010000800030000000b000055ed0000006400180000"
    )
    CAPTURED_RESPONSE = bytes.fromhex(
        "75720010003900040000000b000055ed"
        "0000000000000018000000010000000f"
        "3131362e3133302e3232342e36360000001f400000000e"
        "3235352e3235352e3235352e300000000000"
    )
    CAPTURED_IP = b"116.130.224.66\x00"
    CAPTURED_MASK = b"255.255.255.0\x00"

    def __init__(self, advertise_address: str, advertise_mask: str) -> None:
        self.advertise_address = advertise_address
        self.advertise_mask = advertise_mask

    @staticmethod
    def _rewrite_prefixed(data: bytes, old: bytes, new: bytes) -> bytes:
        """Replace a 4-byte-length-prefixed byte string inside a template."""
        pattern = len(old).to_bytes(4, "big") + old
        index = data.find(pattern)
        if index < 0:
            raise ValueError("template field not found: %r" % (old,))
        return data[:index] + len(new).to_bytes(4, "big") + new + data[index + len(pattern):]

    def build_response(self) -> bytes:
        body = self.CAPTURED_RESPONSE[16:]
        body = self._rewrite_prefixed(body, self.CAPTURED_IP, self.advertise_address.encode() + b"\x00")
        body = self._rewrite_prefixed(body, self.CAPTURED_MASK, self.advertise_mask.encode() + b"\x00")
        head = bytearray(self.CAPTURED_RESPONSE[:16])
        head[4:6] = len(body).to_bytes(2, "big")
        return bytes(head) + body

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        if transport != "udp" or not payload.startswith(self.MAGIC):
            return AdapterResult(self.name, False, message=DecodedMessage(self.name, False, note="not a CODOL ur-probe"))
        if payload != self.CAPTURED_REQUEST:
            return AdapterResult(
                self.name,
                False,
                message=DecodedMessage(
                    self.name,
                    False,
                    "urProbe",
                    "unrecognised ur-magic payload (%d bytes): %s" % (len(payload), payload[:48].hex()),
                ),
            )
        return AdapterResult(
            self.name,
            True,
            [self.build_response()],
            DecodedMessage(self.name, True, "urProbe", "public-address probe answered with advertise address"),
        )


class AdapterPipeline(ProtocolAdapter):
    name = "pipeline"

    def __init__(self, adapters: Iterable[ProtocolAdapter]) -> None:
        self.adapters = list(adapters)

    def handle(self, transport: str, peer: tuple[str, int], payload: bytes, state: EngineState) -> AdapterResult:
        last: AdapterResult | None = None
        for adapter in self.adapters:
            result = adapter.handle(transport, peer, payload, state)
            last = result
            if result.recognized or result.responses:
                return result
        return last or AdapterResult(self.name, False)


@dataclass(frozen=True)
class ServerConfig:
    bind: str
    tcp_port: int | None
    udp_port: int | None
    log_path: Path
    max_frame: int
    once: bool
    state: EngineState
    adapter: ProtocolAdapter


class ProtocolRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **event: object) -> None:
        record = {"time": time.time(), **event}
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        with self.lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


class LocalProtocolServer:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.recorder = ProtocolRecorder(config.log_path)
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.sockets: list[socket.socket] = []
        self.connection_number = 0
        self.connection_lock = threading.Lock()

    def _next_connection_id(self) -> int:
        with self.connection_lock:
            self.connection_number += 1
            return self.connection_number

    @staticmethod
    def _peer(peer: tuple[str, int] | None) -> list[Any] | None:
        return [peer[0], peer[1]] if peer else None

    def _record_frame(self, direction: str, transport: str, peer: tuple[str, int] | None, payload: bytes, **extra: object) -> None:
        self.recorder.write(
            event="frame",
            direction=direction,
            transport=transport,
            peer=self._peer(peer),
            length=len(payload),
            hex=payload.hex(),
            prefix_hex=payload[:64].hex(),
            **extra,
        )

    def _dispatch(self, transport: str, peer: tuple[str, int], payload: bytes, connection_id: int | None = None) -> list[bytes]:
        self._record_frame("in", transport, peer, payload, connection_id=connection_id)
        result = self.config.adapter.handle(transport, peer, payload, self.config.state)
        message = result.message
        self.recorder.write(
            event="message",
            transport=transport,
            peer=self._peer(peer),
            connection_id=connection_id,
            adapter=result.adapter,
            recognized=result.recognized,
            command=message.command if message else None,
            note=message.note if message else None,
            response_count=len(result.responses),
        )
        return result.responses

    def _send(self, sock: socket.socket, transport: str, peer: tuple[str, int], payload: bytes, connection_id: int | None = None) -> None:
        try:
            if transport == "udp":
                sock.sendto(payload, peer)
            else:
                sock.sendall(payload)
            self._record_frame("out", transport, peer, payload, connection_id=connection_id)
        except OSError as exc:
            self.recorder.write(
                event="send_error",
                transport=transport,
                peer=self._peer(peer),
                connection_id=connection_id,
                error=str(exc),
            )

    def _udp_loop(self, sock: socket.socket) -> None:
        while not self.stop_event.is_set():
            try:
                payload, peer = sock.recvfrom(self.config.max_frame)
            except socket.timeout:
                continue
            except OSError:
                return
            for response in self._dispatch("udp", peer, payload):
                self._send(sock, "udp", peer, response)
            if self.config.once:
                self.stop_event.set()

    def _tcp_client(self, client: socket.socket, peer: tuple[str, int], connection_id: int) -> None:
        with client:
            client.settimeout(0.25)
            self.recorder.write(event="connection_open", transport="tcp", peer=self._peer(peer), connection_id=connection_id)
            while not self.stop_event.is_set():
                try:
                    payload = client.recv(self.config.max_frame)
                except socket.timeout:
                    continue
                except OSError as exc:
                    self.recorder.write(event="recv_error", transport="tcp", peer=self._peer(peer), connection_id=connection_id, error=str(exc))
                    return
                if not payload:
                    return
                for response in self._dispatch("tcp", peer, payload, connection_id):
                    self._send(client, "tcp", peer, response, connection_id)
                if self.config.once:
                    self.stop_event.set()
                    return
            self.recorder.write(event="connection_close", transport="tcp", peer=self._peer(peer), connection_id=connection_id)

    def _tcp_loop(self, sock: socket.socket) -> None:
        while not self.stop_event.is_set():
            try:
                client, peer = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            connection_id = self._next_connection_id()
            self.recorder.write(event="accept", transport="tcp", peer=self._peer(peer), connection_id=connection_id)
            thread = threading.Thread(target=self._tcp_client, args=(client, peer, connection_id), daemon=True)
            self.threads.append(thread)
            thread.start()

    def start(self) -> None:
        self.recorder.write(
            event="server_start",
            mode=self.config.adapter.name,
            state={
                "hostname": self.config.state.hostname,
                "mapname": self.config.state.mapname,
                "gametype": self.config.state.gametype,
                "max_clients": self.config.state.max_clients,
            },
        )
        if self.config.udp_port is not None:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp.bind((self.config.bind, self.config.udp_port))
            udp.settimeout(0.25)
            self.sockets.append(udp)
            self.recorder.write(event="listen", transport="udp", bind=[udp.getsockname()[0], udp.getsockname()[1]])
            thread = threading.Thread(target=self._udp_loop, args=(udp,), daemon=True)
            self.threads.append(thread)
            thread.start()

        if self.config.tcp_port is not None:
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp.bind((self.config.bind, self.config.tcp_port))
            tcp.listen(16)
            tcp.settimeout(0.25)
            self.sockets.append(tcp)
            self.recorder.write(event="listen", transport="tcp", bind=[tcp.getsockname()[0], tcp.getsockname()[1]])
            thread = threading.Thread(target=self._tcp_loop, args=(tcp,), daemon=True)
            self.threads.append(thread)
            thread.start()

    def serve(self) -> None:
        self.start()
        print(f"log={self.config.log_path}")
        print(f"adapter={self.config.adapter.name}")
        print(f"state={self.config.state.hostname} map={self.config.state.mapname} mode={self.config.state.gametype}")
        for sock in self.sockets:
            transport = "tcp" if sock.type & socket.SOCK_STREAM else "udp"
            print(f"listen={transport} {sock.getsockname()[0]}:{sock.getsockname()[1]}")
        try:
            while not self.stop_event.wait(0.25):
                pass
        finally:
            self.stop()

    def stop(self) -> None:
        self.stop_event.set()
        for sock in self.sockets:
            try:
                sock.close()
            except OSError:
                pass
        for thread in self.threads:
            thread.join(timeout=1.0)
        self.recorder.write(event="server_stop")


def build_adapter(args: argparse.Namespace) -> ProtocolAdapter:
    adapters: list[ProtocolAdapter] = []
    if args.replay:
        adapters.append(ReplayAdapter(args.replay))
    if args.mode in ("iw4", "hybrid"):
        adapters.append(Iw4OobAdapter())
    if args.mode in ("hall-probe", "hybrid"):
        adapters.append(CodolIpProbeAdapter(args.advertise_address, args.advertise_mask))
    if args.tcp_response_hex is not None or args.udp_response_hex is not None:
        adapters.append(FixedResponseAdapter(args.tcp_response_hex, args.udp_response_hex))
    if args.echo:
        adapters.append(EchoAdapter())
    adapters.append(ObserveAdapter())
    return AdapterPipeline(adapters)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IW4-lineage server kernel and CODOL protocol workbench")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--tcp-port", type=int, default=None)
    parser.add_argument("--udp-port", type=int, default=None)
    parser.add_argument("--no-tcp", action="store_true")
    parser.add_argument("--no-udp", action="store_true")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "frames.jsonl")
    parser.add_argument("--mode", choices=("observe", "iw4", "hybrid", "replay", "hall-probe"), default="observe")
    parser.add_argument("--replay", type=Path, help="JSONL replay source produced by this server")
    parser.add_argument(
        "--advertise-address",
        default="127.0.0.1",
        help="address returned by the CODOL public-address probe (mode hall-probe)",
    )
    parser.add_argument(
        "--advertise-mask",
        default="255.255.255.0",
        help="netmask returned by the CODOL public-address probe (mode hall-probe)",
    )
    parser.add_argument("--tcp-response-hex", type=parse_hex)
    parser.add_argument("--udp-response-hex", type=parse_hex)
    parser.add_argument("--echo", action="store_true", help="explicit local echo fallback")
    parser.add_argument("--hostname", default="CODOL-IW4 adapter")
    parser.add_argument("--gamename", default="CODOL-IW4")
    parser.add_argument("--version", default="experimental")
    parser.add_argument("--protocol", type=int, default=0)
    parser.add_argument("--map", dest="mapname", default="mp_rust")
    parser.add_argument("--gametype", default="war")
    parser.add_argument("--max-clients", type=int, default=18)
    parser.add_argument("--motd", default="local protocol workbench")
    parser.add_argument("--max-frame", type=int, default=1024 * 1024)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_frame <= 0:
        raise SystemExit("--max-frame must be positive")
    if args.no_tcp and args.no_udp:
        raise SystemExit("at least one transport must be enabled")
    if args.mode == "replay" and not args.replay:
        raise SystemExit("--mode replay requires --replay FILE")
    state = EngineState(
        hostname=args.hostname,
        gamename=args.gamename,
        version=args.version,
        protocol=args.protocol,
        mapname=args.mapname,
        gametype=args.gametype,
        max_clients=args.max_clients,
        motd=args.motd,
    )
    adapter = build_adapter(args)

    tcp_port = args.tcp_port
    udp_port = args.udp_port
    if args.mode == "hall-probe":
        # The CODOL public-address probe is UDP-only and arrives on 8000.
        if udp_port is None:
            udp_port = 8000
    else:
        if tcp_port is None:
            tcp_port = 28000
        if udp_port is None:
            udp_port = 28001
    if args.no_tcp:
        tcp_port = None
    if args.no_udp:
        udp_port = None

    config = ServerConfig(
        bind=args.bind,
        tcp_port=tcp_port,
        udp_port=udp_port,
        log_path=args.log,
        max_frame=args.max_frame,
        once=args.once,
        state=state,
        adapter=adapter,
    )
    server = LocalProtocolServer(config)
    signal.signal(signal.SIGINT, lambda *_: server.stop())
    signal.signal(signal.SIGTERM, lambda *_: server.stop())
    server.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
