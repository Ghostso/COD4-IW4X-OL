# C1 dynamic configstring transport

Offline inspection of C1.exe 1.1.1.13; no runtime verification.

The aligned native sender at `0x5d30e0` accepts an index below `0x1977`
(6519). At `0x5d31a5..0x5d31ba` it measures the value including its NUL and
rejects a length above `0x3f8` (1016 bytes including NUL). The error format at
`0xc66690` is localized, not a useful English diagnostic. At
`0x5d3235..0x5d3246` it sends one command with opcode `0x64` (`d`), index,
and value, using `%c %i %s` at `0xc66698`. There is no chunk loop in this
sender. Empty values use the same command.

The command execution loop at `0x46a1a0` calls reader `0x487730` before the
CG dispatcher `0x469320`. The reader uses a 256-entry reliable ring with
1024-byte entries (`0x4877c2..0x4877d5`). Its dispatch table at
`0x4878d8`/`0x4878c8` maps `d` to `0x487869`, `k` and `x` to
`0x487892`, `t` to `0x48782e`, and the remaining characters from `d`
through `x` to ordinary pass-through. Characters outside that range also
pass through. Thus the earlier reader does not reassemble IW3 `x/y/z`.

For `d`, it retokenizes with a three-token limit, then calls `0x487440`.
That function reads index from argument 1 and the value from argument 2,
validates the index, and rebuilds the configstring pool. The command then
reaches CG's `d` branch at `0x469420`, which calls the asset/state dispatcher
`0x467350`. These are distinct storage and application steps.

## Native source change

The CoDOL generic fallback in `src/sv_main.c:SV_SetConfigstring` now bounds
the translated wire value to 1015 bytes and sends one reliable `d` command
to primed clients whose gamestate has been sent. IW3 chunk code remains
under the non-CoDOL branch. Existing specialized namespace publishers still
run first. This does not validate or fix every specialized publisher.

## Remaining work

The retained IW3 storage namespace is still distinct from the wire namespace.
Unmapped generic indices, including the legacy vote collision, need semantic
translation or native subsystem changes. Initial gamestate limits, all asset
publication paths, and actual client application remain separately unverified.
No builds, tests, assembly, game/server launches or client match entry were run.

### Client pool and server-ID update evidence (2026-09-09)
Aligned C1 `487440` storage update, continuation `4875b7..4876e3`, rebuilds all 6519 entries. It starts dataCount at 1 (`4875c8`), skips empty values (`4875ed`), and includes one NUL per nonempty string. At `487602..487614`, a total above `0x20000` takes the client error path. Thus the combined effective pool, including inherited strings and explicit overrides, must fit 128 KiB; summing override-bank bytes alone is insufficient and counts empty overrides differently from C1.

`487666..4876b2` separately handles changed index 3: parses its decimal value into `6d0d12c`, updates the connection field at +33d0 and invokes its follow-up routine. The unchanged-value path `487549..487566` also checks index 3 against connection state. This supports existing dedicated server-ID publication; it does not establish an IW3 systeminfo index1 equivalent.

Rechecked legacy vote collision against current source: generic sender still exposes retained vote13..16, while the map adapter separately maps end time11->15 and center12->16. No matching callvote/vote-time names found in the searched MP overlay/script roots; that limited search does not establish absence of a CoDOL vote mechanism. No speculative remap or suppression added. Next publication audit must check effective inherited pool size and C1 systeminfo/vote semantics.

Offline inspection only. No builds/tests/runtime.

### Replicated dvar batch publication
`CODOL_RefreshServerDvars` now stages changed value strings, validates the final effective pool, and commits/sends non-growing values before growing values. This avoids a transient pool overflow caused by ascending slot order when later slots release space. All allocations and validation precede any batch publication. The ordering concerns value slots only; the replicated name table is preserved. C1 still applies each command separately, so this is not an atomic client transaction. Other dynamic publishers are not covered by this change. Source reviewed only, no builds/tests/runtime.
