# Native player usability

`enableusability` and `disableusability` now control native player activation.
The methods require a player entity and preserve all unrelated state. Python
enumerates them in alpha0022 `gsc/gscbuiltins.py:2126-2129` as `_usability_off`.

Static inspection of local `D:/CoD/shx/iw4x.exe` establishes the behavior:

- Disable at 0x5dae20 sets bit 8 of gclient +0x3394; enable at 0x5dae90 clears it.
- `Player_UpdateActivate` at 0x4d78f0 clears weapon flag 1 each update.
- At 0x4d7909 it tests the private disable flag. The disabled branch reports
  release of button 0x20 using weapon flag 1, clears `useHoldEntity` through the
  handle service, sets `useButtonDone` to 1 and returns before activation.

The retained IW3 gclient has separate noclip/ufo/frozen fields instead of that
IW4 flag word. The fork reserves native `weapFlags` bit 0x2000 for private
usability state, avoiding a change to the assembly-facing gclient layout. It
is outside the original 9-bit IW3 wire mask. No CoDOL serializer maps this
private bit to a client field. The source addition to `_player_use_mp.asm`
reuses the native handle-clearing and completion path and preserves the IW4
release-edge behavior. Cursor-hint behavior is unchanged, matching the inspected
IW4 flag consumer. No binary patch or hook is installed.

`test_codol_usability` links the actual modified activation assembly. It covers
all eight combinations of current/previous/latched use inputs while disabled,
pending-handle cancellation, use-button completion, release edges, unrelated
flags, repeated method calls, invalid player references and restoration of the
enabled path. Its checked handle-service substitute verifies the native call;
it does not test the handle registry itself. Unrelated gameplay services abort
if reached. This is not a full connected-client interaction test.

The Windows MinGW build, standalone assembly fixture, and forced Linux
`make -B -j6 all test-codol` build/suite pass (2026-09-08).
The isolated full-reference probe in `%TEMP%/sh1x-usability-reference-probe`
passes `EnableUsability` and next reports missing `changeFontScaleOverTime`
in `maps/mp/gametypes/_hud_util.gsc:677`, then shuts down its game and network.
The existing C1 and Python lobby processes were not altered.
