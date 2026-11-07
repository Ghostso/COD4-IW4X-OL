# CoDOL / sh1x server instructions

## User-authorized architecture changes

The retained IW4OL engine is a starting point, not a compatibility constraint. The user explicitly
authorizes freely rewriting, replacing, or extending its native code and
subsystems to make the server compatible with Call of Duty Online. This applies
to all agents and Claude workers.

An absent native field, writer, VM facility, asset representation, or gameplay
subsystem is implementation work. Trace the reference behavior, then implement
the required representation and producers/consumers. Do not stop or request
additional permission merely because the work requires an architectural change.
Worker file ownership coordinates concurrent edits; it does not prohibit needed
changes. Coordinate ownership or supply concrete shared-file changes to the parent.

Implement missing GSC functions/methods using IW4 behavior first and T5 where IW4
does not provide it. Verify receiver types, arguments, returns, state transitions,
and lifecycle. Do not equate field offsets across IW3, IW4, T5, and C1 layouts.
Do not count empty bodies, constant stand-ins, or unsupported-error stubs as support.

## Current working constraints

- Implement in native source and retained assembly. Do not add hooks, injections,
  or proxy gameplay implementations.
- The user now requests periodic builds and Killhouse launcher checks (2026-09-10).
  Builds, relevant tests, and native server restarts/launcher runs are authorized.
  Continue missing-function implementation alongside these checks. Preserve the
  running C1 client and Python lobby/auth unless a restart is actually needed.
- Preserve the user's running C1 client and Python lobby/auth processes.
- Preserve existing work; never reset, checkout, stash or clean the tree.
  Commits ARE wanted (user, 2026-09-15): checkpoint each integrated iteration
  with `git add` of source/scripts/docs/tools (never bin/home runtime state,
  obj/, exes or .pre-* backups) and push to origin main so iterations are
  tracked. Only the parent session commits; workers report instead.
- Use alpha0022's Python implementation and C1 evidence for CoDOL behavior.
  The user reports broken behavior in the Python server: treat it as a source
  of leads and script data, not proof of correct engine semantics. Verify
  uncertain behavior against C1 and IW4/T5. Prioritize native GSC VM, script
  loading and startup methods so map scripts can reach meaningful gameplay.
  Weapons are composed from attachments; player appearance is composed from
  playerdata parts such as hands, body, vest, headgear, and boots.
- The user also provides `D:\CoD\OpenBLOPS` as a buildable T5 source reference,
  including bot/actor implementations. Consult its native producers and
  consumers where IW4 lacks a method; still verify CoDOL-specific behavior
  and layouts against C1 rather than copying offsets.
- For Black Ops killstreaks, use OpenBLOPS native code and T5 GSC as the
  primary behavioral references. Adapt CoDOL assets and C1 layouts explicitly;
  do not prefer IW4 reward behavior where the T5 implementation is available.
- Use sh1x server / Call of Duty Online Closed Alpha Server branding while
  preserving required license and attribution text.

## Local behavioral references

- User-designated native reference: `D:\CoD\OpenBLOPS`.
- User-designated script dumps: `D:\CoD\COD-GSC-Source`, containing
  `BO1-GSC`, `IW4-GSC`, `IW4x-GSC`, and `IW5-GSC`.
- Consult these directly when implementing or adapting equipment, killstreaks,
  actors and map behavior. Preserve source attribution. Verify C1-specific asset
  names and layouts; copied reference behavior alone does not prove CoDOL parity.

## Source layout

CoDOL code lives under `src/codol/<area>/` (net, snapshot, player, weapon,
vehicle, script, assets, collision, stats); the retained IW4OL engine stays in
`src/` and `src/asmsource/`. Put a new file in the area it belongs to; the
makefile globs every area and every area is an include path, so
`#include "codol_x.h"` needs no directory prefix. `docs/CODOL_SOURCE_LAYOUT.md`
describes each area and the naming conventions.

## Delegation and reporting

The user has reauthorized Claude workers. Use a small coordinated team, with
explicit nonoverlapping file ownership, prioritizing missing GSC methods and
VM/script startup. Parent review is required before integrating/counting output.
Do not launch duplicate assignments while an existing worker is active.

Every worker assignment must explicitly include the architecture authorization
above, including when CLI safe mode disables automatic instruction-file loading.
Distinguish source written, source reviewed, built/tested, and real C1 behavior.
Track actual state in docs/CODOL_IMPLEMENTATION_PASS.json and its companion .md.

## Script tree policy (user, 2026-09-16 01:30)

- `bin/home/codol_rawfiles/` is THE script tree the server loads and the only
  place GSC is edited. Edit it in place. Do NOT run `tools/collate_gsc.py` or
  `tools/verify_gsc_collation.py` any more; the vendor/overlay/native
  three-root collation is retired. `scripts/codol/` is historical and must not
  be edited or copied from. The `alpha0022` vendor/gsc/gsc_overlay trees are
  retired reference only.
- Static gate after every GSC edit:
  `python tools/codol_script_resolve.py --root bin/home/codol_rawfiles --only <subtree>`
  must exit 0 (unknown builtin = fatal map load).
- When IW4 GSC lacks a feature, port it from the IW5 or T5 dumps in
  `D:\CoD\COD-GSC-Source` (`IW5-GSC`, `T5-STEAM-GSC`, `BO1-GSC`) into
  `bin/home/codol_rawfiles`, keep the attribution header, and adapt asset
  names and builtins to C1 / this VM (verify each builtin is registered).
- The tree is committed to git; the parent commits after each iteration.

## Server lifecycle rule (user, 2026-09-16)

Never leave the live server down. A worker that stops or relaunches the
server for a test must end with a running server on udp/17733 (bots via
`CODOL_EXTRA_ARGS=+set scr_codol_bots 12`). Never send `quit` over rcon or
stop the process at the end of a soak; the user tests on it between sessions.
