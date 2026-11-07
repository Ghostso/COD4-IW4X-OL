# CODOL / IW4-Lineage Server Workbench

This directory is a local server kernel and protocol workbench for an IW4-lineage
compatibility project. It is deliberately not an account server, an anti-cheat
emulator, or a guessed CODOL gameplay server.

`codol_server.py` now provides:

- TCP and UDP listeners with a long-lived engine/room/player state model;
- adapter dispatch with observe, exact replay, explicit echo, fixed response,
  and minimal IW4-family `getinfo`/`getstatus` modes;
- raw frame and message logging as JSONL with hexadecimal prefixes;
- a replay adapter that only answers byte-for-byte captured requests.

Example:

```text
python CODOLServer/codol_server.py --mode iw4 --tcp-port 28000 --udp-port 28001
```

The IW4-style test mode is intentionally narrow:

```text
FF FF FF FF getinfo\nchallenge
FF FF FF FF getstatus\nchallenge
```

It does not implement `connect`, CODOL login, anti-cheat, or a guessed room
protocol. Unknown CODOL packets are logged and left unanswered in the default
observe mode.

The existing client captures are summarized with:

```text
python CODOLServer/analyze_captures.py --out CODOLServer/CAPTURE_REPORT.md
```

The current CODOL evidence still does not contain gameplay payload bytes.
Therefore this workbench does not claim to implement the CODOL gameplay
protocol yet. The next useful input is a payload-bearing, call-stack-bearing
capture from a legitimate local test run, after the game process reaches its
own network layer.

For the established client reproduction, use the canonical launcher from an
elevated PowerShell. It starts AFD ETW first and then runs the known-good
observer chain:

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\run_codol_001\capture_elevated_network.ps1' -DurationSeconds 75
```

The newer `capture_entry_failure_elevated.ps1` is experimental; PktMon is
disabled by default there because the baseline launch must remain unchanged.
Use `-EnablePktmon` only for a deliberate packet-capture run, and treat that
run as a separate experiment that must be followed by a fresh client restart.

## CODOL public-address probe (observed, byte-verified)

Capture `ENTRY_CAPTURE_ELEVATED_20260924_160326` (game PID 19040) contains the
first payload-bearing CODOL protocol exchange. The client sent one UDP packet
to `116.130.224.66:8000` and received one reply:

```text
client -> server   24 bytes
  75 72 00 10 00 08 00 03 00 00 00 0b 00 00 55 ed
  00 00 00 64 00 18 00 00

server -> client   73 bytes
  75 72 00 10 00 39 00 04 00 00 00 0b 00 00 55 ed
  00 00 00 00 00 00 00 18 00 00 00 01 00 00 00 0f
  31 31 36 2e 31 33 30 2e 32 32 34 2e 36 36 00
  00 00 1f 40
  00 00 00 0e 32 35 35 2e 32 35 35 2e 32 35 35 2e 30 00
  00 00 00 00 00
```

Response layout: `75 72` magic, header length `0x10`, body length, message type
(`03` request / `04` response), a stable session id, then a body containing the
client's reported address, the port `0x1f40` = 8000, and the netmask as
length-prefixed strings. The client then treats `address:8000` as its entry and
fails with `[100] cannot connect to lobby service` because nothing answers
there.

`CodolIpProbeAdapter` answers this probe. It is a byte template copied from the
real capture: only the address and netmask strings are rewritten from
`--advertise-address` / `--advertise-mask`, and every enclosing length field is
recomputed. With `--advertise-address 116.130.224.66` it reproduces the captured
reply byte-for-byte (verified).

Local hall-probe run:

```powershell
python CODOLServer\codol_server.py `
  --mode hall-probe `
  --bind 0.0.0.0 `
  --advertise-address 127.0.0.1 `
  --log CODOLServer\logs\hall_probe.jsonl
```

Do not solve this by changing the adapter address, routes, DNS, or firewall.
Those changes have previously broken network connectivity on this host, and
they are not required for a passive deep capture. The client currently sends
the probe to the real remote address `116.130.224.66:8000`; the local
`hall-probe` listener is useful for controlled local replays and for logging
only when traffic actually reaches the host.

Each iteration requires a full client restart; a running `codoMP` will not pick
up a changed server answer.

## Deep lobby-phase capture

Use the deep capture wrapper when the goal is to observe what happens after the
IIPS pre-check and around the `[100] cannot connect to lobby service` failure:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\capture_lobby_deep.ps1' `
  -DurationSeconds 240
```

Use the absolute `-File` path unless the current directory has already been set
to `D:\BaiduNetdiskDownload\使命召唤OL`. Running the relative path from
`C:\Windows\system32` makes PowerShell report that the `.ps1` file does not
exist before the capture script starts.

To run the optional user-mode probe listener as well:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\capture_lobby_deep.ps1' `
  -DurationSeconds 240 -StartServer -AdvertiseAddress 127.0.0.1
```

The wrapper:

- starts the AFD ETW capture before the established observer chain;
- optionally runs the user-mode `codol-ip-probe` UDP listener on port 8000;
- keeps PktMon off by default because it can disrupt the known-good launch;
- writes `phase_timeline.txt`, server logs, AFD output, and optional PktMon
  output into `run_codol_001\runs\LOBBY_DEEP_*`;
- does not modify adapters, routes, DNS, or firewall configuration.

For a deliberate packet-payload run, add `-EnablePktmon`; if the client exits
early in that mode, rerun without it and treat the PktMon run as a separate
experiment.

The IW4X comparison is recorded in `IW4X_CODOL_REUSE_REPORT.md`. The current
working model is that CODOL and IW4X are both IW4-lineage projects, while
their builds, resources, service layers, authentication, and wire contracts
still differ. IW4X therefore supplies a server/lifecycle reference, not a
drop-in CODOL protocol.
