# Dedicated two-client validation

## Result

The bounded orchestration flow was deployed and run with two real CODOL
clients:

- `01100001DEADC0DE` / `dest1yo`, bridge `28962`
- `01100001DEADC0DF` / `olmod-player2`, bridge `28963`

Both clients completed native frontend, match, enter, and ready handling. The
room owner observed `members=2 ready=2` and froze a two-member roster. Only the
roster owner submitted the effective booking; the second client's later native
booking was rejected as `non_owner_booking_ignored`, with the local and roster
owner XUIDs now included in the diagnostic.

## Dedicated evidence

The dedicated game-server log recorded:

```text
SessionStart queued ... members=2
SessionStart accepted ...
runtime clients=2 active=0 ...
runtime clients=2 active=1 packets=273 ... snapshots=202 socketError=0
runtime clients=2 active=1 packets=408 ... snapshots=302 socketError=0
```

This confirms the current room-owner, roster, booking, dedicated connect,
gamestate/world initialization, and multi-client snapshot path. The remaining
gameplay correctness work is independent of the two-client transport proof.

The first SD run after adding the objective diagnostic showed both clients with
`team=1`. The orchestration command had submitted `mr 0 1` to both clients,
which is valid for transport but cannot exercise SD's team-filtered A/B
objectives, bomb ownership, or plant/defuse rules. `CodolTwoClientMatch.py`
now submits menu `1` to client 0 and menu `2` to client 1 by default;
`--same-team` keeps the old transport-only behavior explicitly.

## Diagnostic boundary

`CodolGameServerControl.py` may report `target detached before status sample`
while the process is still alive and responsive. Always verify the PID and
`CodolGameServer.log` before treating that probe result as a crash.

## Follow-up timeout evidence

In a later deployed run, dedicated reached `runtime clients=2 active=1` and
continued sending snapshots. About four minutes after client 0 stopped
producing accepted packets, the server recorded:

```text
client timeout client=0 xuid=76561201696194782 state=1 last_packet=3320071859
runtime clients=1 active=1 ... socketError=0
```

Both client processes were still alive and responsive. The configured active
timeout is 240 seconds, so this is a client-side packet silence/transport
progress issue, not an early room-owner or roster eviction. Server-side timeout
logging now preserves the slot, XUID, state, and last packet timestamp.
