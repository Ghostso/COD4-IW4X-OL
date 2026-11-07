# CODOL out-of-band reply path — why replies were lost, and the fix (2026-09-22)

## TL;DR

Connectionless (OOB) replies from the native match server **never left the
process** whenever the destination had no established bdDTLS association. The
server received and executed `rcon status` / `getinfo` / `getstatus`, produced
the reply, handed it to `NET_OutOfBandPrint` → `NET_SendPacket(NS_SERVER, …)` —
and `CODOL_NetworkSend` returned `0` ("handled, drop") because it could not seal
a record for an un-associated address. `Sys_SendPacket` was never reached. The
netchan to `127.0.0.1:30001` worked only because that peer *has* an association.

**Fix:** `CODOL_NetworkSend` now returns `-1` (**"not mine — fall through to
plaintext"**) for every destination it cannot seal to, instead of `0`. OOB
replies to un-associated senders now go out as ordinary plaintext datagrams, the
way Quake connectionless traffic always has. The encrypted client transport is
untouched: a real gameplay client always has an established peer and still seals.
Objects-only build passes (`codol_network.o` compiles clean).

This is **not** an IPv6 `V6ONLY` / v4-mapped-address problem. That hypothesis is
refuted below (§3).

---

## 1. The traced path

### Inbound (works)
`NET_Event` (`sys_net.c:3658`) → `NET_GetPacket` (sets `from->sock` to the
receiving socket) → `NET_UDPPacketEvent` (`net_game.c:37`).

`NET_UDPPacketEvent` has a CoDOL-specific control-plane shortcut:

```c
/* 0xffffffff-prefixed packet from loopback / 127.x -> plaintext OOB */
if (len>=4 && data[0..3]==0xff && (from->type==NA_LOOPBACK ||
    (from->type==NA_IP && from->ip[0]==127))) {
    MSG_InitReadOnly(&localOob, data, len);
    SV_PacketEvent(from, &localOob);   // straight to the Quake OOB parser
    return;
}
if (CODOL_NetworkReceive(from, data, len)) return;   // else: bdDTLS/bdNAT
```

So an inbound `getinfo`/`getstatus`/`rcon` from `127.0.0.1:<ephemeral>` is parsed
in plaintext by `SV_ConnectionlessPacket` (`sv_main.c:2091`). That is why the
server **executed** the probe (log line 554 `Rcon from 127.0.0.1:57203: status`
followed by the full status text).

### Outbound (was lost)
The reply builders all funnel through one place:

- `SVC_Info`  → `NET_OutOfBandPrint(NS_SERVER, from, "infoResponse\n%s", …)`   (`sv_main.c:1134`)
- `SVC_Status`→ `NET_OutOfBandPrint(NS_SERVER, from, "statusResponse\n%s\n%s")`  (`sv_main.c:1012`)
- `SVC_RemoteCommand` → `svs.redirectAddress = *from;` (full copy, **including
  `from->sock`**, `sv_main.c:1699`) → `Com_BeginRedirect(SV_FlushRedirect)` →
  `SV_FlushRedirect` → `NET_OutOfBandPrint(NS_SERVER, &svs.redirectAddress,
  "print\n%s", …)` (`sv_main.c:1673-1674`).

`NET_OutOfBandPrint` (`netchan.c:527`) frames `\xff\xff\xff\xff` + text and calls
`NET_SendPacket(sock, len, string, adr)`.

`NET_SendPacket` (`netchan.c:485`) — **the choke point**:

```c
#ifdef CODOL_SERVER
    if (sock == NS_SERVER) {
        int sent = CODOL_NetworkSend(to, data, length);
        if (sent >= 0) return sent ? qtrue : qfalse;   // <-- 0 => "handled, DROP"
    }
#endif
    ... NA_LOOPBACK / NA_BOT / NA_BAD handling ...
    return Sys_SendPacket(length, data, to);           // the real UDP sendto()
```

`CODOL_NetworkSend` (`codol/net/codol_network.c`), **before the fix**:

```c
int mode = configuration(id);
if (!mode) return -1;                                   // plaintext-diag mode: fall through
if (mode < 0 || !to || to->type != NA_IP || n < 0) return 0;
p = find(to, Sys_Milliseconds(), 0);
if (!p) return 0;                    // <-- ephemeral rcon/probe sender: DROP
if (!p->handshake.established) return 0;                // <-- pending peer: DROP
size = CODOL_AssociationSeal(&p->handshake.data, wire, …, data, n);
return size && Sys_SendPacket((int)size, wire, to);
```

On the live server `codol_securityKeyPath` points at `securitykey.bin`
(non-empty), so `configuration()` returns `mode = 1`. The reply's destination is
the probe's ephemeral `127.0.0.1:<port>`, which has **no** peer slot → `find()`
returns `NULL` → **`return 0`**. Back in `NET_SendPacket`, `sent == 0` →
`return qfalse`, and **`Sys_SendPacket` is never called**. The datagram is
dropped inside the process. Exactly the measurement: request executed, no reply.

`127.0.0.1:30001` (the client's game port) works because after the bdDTLS
handshake it owns an established peer slot, so `find()` succeeds and the netchan
stream is sealed and sent.

---

## 2. The fix

`CODOL_NetworkSend` now treats "I cannot seal this" as **"not mine"** (`-1`,
fall through to plaintext) rather than "handled, drop" (`0`):

```c
if (mode <= 0 || !to || to->type != NA_IP || n < 0)
    return -1;                       /* plaintext-diag / non-IP / bad args -> plaintext */
p = find(to, Sys_Milliseconds(), 0);
if (!p || !p->handshake.established)
    return -1;                       /* no association -> plaintext OOB path */
size = CODOL_AssociationSeal(...);
return size && Sys_SendPacket((int)size, wire, to);
```

Return-value contract with `NET_SendPacket`: `>=0` = we own the send (sealed);
`-1` = not ours, `NET_SendPacket` calls `Sys_SendPacket` in plaintext.

**Why this is safe for the encrypted transport.** The C1 association only ever
carries the netchan gameplay stream to a client we finished a handshake with.
Connectionless OOB (`infoResponse`, `statusResponse`, rcon `print`, challenge
replies, bdNAT echoes, a bdQoS answer) is plaintext by definition and is
addressed to senders with no association. A real gameplay client always has an
established peer and still hits the seal path. An un-associated destination could
not have received an encrypted packet anyway — the old code was *already*
dropping it — so at worst a datagram the client discards is emitted in place of
one that was being lost. Nothing that used to be encrypted becomes plaintext.

Build: `tools\BUILD-CODOL.ps1 -ObjectsOnly` → `build OK (exit 0)`,
`codol_network.o` clean. Line endings preserved (LF; 0 CRs before and after).

### Reproduce without the client
`tools/codol_oob_probe.py` sends `getinfo`/`getstatus`/`rcon "<pw>" status` from
an IPv4 socket to `127.0.0.1:17733` and prints each reply or a timeout:

```
python tools/codol_oob_probe.py                 # getinfo + getstatus (harmless)
python tools/codol_oob_probe.py --rcon <PASSWORD>
```

Before the fix: all three TIMEOUT while the server log shows them executed.
After the fix (server rebuilt/relinked and relaunched by the parent): `getinfo`
returns `infoResponse\…`, `getstatus` returns `statusResponse\…`, rcon returns
the `print\…` status text. **The running server was NOT probed by this worker**
(parent did not authorize sending packets); run the tool once the parent says
the server may be probed, ideally against the rebuilt binary.

---

## 3. Socket facts (and why the V6ONLY hypothesis is refuted)

- `NET_OpenIP` (`sys_net.c:2568`) opens **both** an IPv6 socket (`ip6_socket`,
  when `net_enabled & NET_ENABLEV6`) and an IPv4 socket (`ip4_socket`, when
  `net_enabled & NET_ENABLEV4`). `net_enabled` defaults to `3` (v4+v6).
- Both `NET_IP6Socket` and `NET_IPSocket` set `IPV6_V6ONLY = 1`
  (`sys_net.c:1796`, `:1956`) — the v6 socket is v6-only and the v4 socket is a
  genuine `AF_INET` socket. There is no v4-mapped crossover.
- `Sys_SendPacket` (`sys_net.c:1373`) sends on **`to->sock`**. For an OOB reply,
  `to` is the `from` captured at receive time, whose `sock` was set by
  `SockadrToNetadr` (`sys_net.c:439`) to the socket the request arrived on — the
  IPv4 socket for a `127.0.0.1` sender. An IPv4 request therefore replies on the
  IPv4 socket to the IPv4 sender. Address family never crosses.
- The reply was **not** lost in `Sys_SendPacket`; `Sys_SendPacket` was **never
  called**. The loss was entirely `CODOL_NetworkSend` returning `0`. Hence the
  V6ONLY / v4-mapped theory does not apply; had the packet reached
  `Sys_SendPacket` it would have gone out correctly on the v4 socket.

---

## 4. What C1's QoS probe actually is

The lobby telemetry `QoSProbeStart` / `QoSProbeFail` (TENCENT svc 71 task 7) is
**not** the probe packet — it is the client reporting the outcome of a
DemonWare **bdQoS** probe it fired at the game port `127.0.0.1:17733`.

Identity, from C1.exe strings and the OpenBLOPS reference:

- C1.exe (ImageBase 0x400000) carries `bdQoS`, `bdQoSProbe`, `bdQoSReplyPacket`
  (`0x7e30e7`), `dwGetQoSProbe`, `StartQoSProbe`, `XNetQosListen`, and the
  Tencent `tqos_*` / `QOSSSQos` service strings — a full DemonWare bdCore QoS
  service distinct from the Quake OOB layer and from the bdDTLS gameplay
  association.
- OpenBLOPS `Engine/Network/DW/dwQoS.cpp` + `Game/Server/server_mp/
  sv_main_pc_mp.cpp`: the client drives `bdQoSProbe::probe(...)` per candidate
  host; the **server** answers by registering a listener,
  `bdQoSProbe::listen(qosProbe, dwGetSessionSecID(), 0, 0)` ("Qos listener
  started"), keyed to the session's **security ID + session key**. The reply is
  a `bdQoSReplyPacket` (latency + up/down bandwidth), consumed by
  `dwQoSMultiProbeListener::onQoSProbeSuccess`.

So the QoS probe is a **bdQoS/DemonWare UDP packet on the game port, keyed by the
session security ID** — not a `getinfo`, not a Quake OOB, not a bdDTLS DATA
record. In `CODOL_NetworkReceive` it matches neither the bdNAT INTRO (type 13)
nor the bdDTLS handshake/DATA leading bytes (1/3/6), so it falls into the
"neither a handshake nor a DATA record" drop bucket. **The native server
implements no bdQoS responder**, which is exactly why the client always logs
`QoSProbeFail`.

Neither the alpha0022 Python reference server answers it: `docs/ERRORS.md:209`
records `QoSProbeFail` as "the client's bdQoS probe to the game port is
unanswered. Cosmetic; the server does not implement bdQoS. Does not block
anything," and the same OOB-reply defect described here would have dropped a
Quake-style reply anyway. **`QoSProbeFail` does not gate the connect** — in this
very flow the client went on to reach `CS_CONNECTED` and then played (log lines
568/580). Answering bdQoS is a separate, optional implementation task (session
security-ID-keyed `bdQoSReplyPacket`), out of scope for this OOB-reply fix; the
OOB-reply fix does *not* make bdQoS answer, but it does make every plaintext OOB
reply (status/info/rcon, and any future bdNAT-style echo) actually reach the
sender.

---

## 5. The `181 frag_grenade_zm 0 2` first-connect drop in this flow

`ValidateWeaponConfigString @0x00483600` (C1) walks every `CS_WEAPONS` slot and,
for a non-empty name that `BG_GetWeaponIndexForName` cannot resolve, does
`Com_Error(ERR_DROP, "181 %s %d %d", name, got, weapIdx)`. The `0 2` shape is
`got == 0` — the name **did not resolve at all** (not the `N+1 N` partner
shape). See `docs/CODOL_CATEGORY_WEAPON_WINDOW_20260917.md` §2.

In this session the server was `zm` for both map loads and the lobby dispatched
`zm`, yet the first connect carried a slot-2 name from the **wrong category's
window** (`frag_grenade_zm`/`aa12_mp`-class mismatch: the client validated a name
its currently-mounted namespace could not resolve). The provenance is the same
one settled in §2.1 of that doc: the client fell back to the front end after the
QoS/timeout stall and a **deferred connect fired from the front-end (mp) mode**,
so its resident weapon namespace did not match the `zm` window the server
published — `got == 0` → `ERR_DROP` on the first attempt. The client then
reloaded the correct category and reconnected cleanly (log line 580,
`CS_CONNECTED` → active).

**Can the server reject/redirect such a connect gracefully instead of letting C1
ERR_DROP?** Yes, and it is worth a follow-up (separate from this OOB fix, and it
must not touch actor/snapshot/weapon-window code owned by other agents): at
`SV_DirectConnect` time the server already knows the session category it just
spawned. It can compare the connecting client's declared category/namespace
(carried in the connect userinfo / gamestate `type` field — see
`docs/…fs_game…`) against the running session and, on mismatch, answer the
connect with an **OOB `disconnect "<reason>"`** (the same `NET_OutOfBandPrint(…,
"disconnect")` used at `sv_main.c:2232`) *before* the gamestate is sent — which
returns the client to the front end without the C1-side `ERR_DROP`/`181` hard
error. **That redirect is itself an OOB reply, so it depended on this very fix to
be delivered at all.** Implementing the category-mismatch check is left as the
follow-up; this document delivers the transport fix that makes any such reply
reach the client.

---

## Files changed
- `src/codol/net/codol_network.c` — `CODOL_NetworkSend` return-value fix
  (drop → plaintext fall-through for un-associated destinations).
- `tools/codol_oob_probe.py` — client-free IPv4 OOB reproduction (new).
- `docs/CODOL_OOB_REPLY_20260922.md` — this document (new).
