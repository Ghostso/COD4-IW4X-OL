# UAV action slot and missing icon

Read-only C1/native audit. No game input, process writes, tests or builds.

## Current key bindings, measured in C1 PID 102092

C1 `492db0` resolves command names through the 86-entry table at CD62C0.
`492e30` finds bound keys by scanning 256 records at
16f5164 + localClient*D28 + key*12. The binding word is a command ID.
A single passive read returned:

| Key | Command ID | Binding |
| --- | --- | --- |
| 8 | 17 | +actionslot 1 |
| 5 | 19 | +actionslot 2 |
| 6 | 21 | +actionslot 3 |
| 7 | 23 | +actionslot 4 |
| J | 25 | +actionslot 5 |

An earned reward assigned action slot 1 therefore uses key 8 with this user's
actual bindings. This is not evidence of a native off-by-one error. These are
current settings, not a claim about factory defaults. The encrypted on-disk
config was not decoded or modified.

## Native index contracts

The native script setter accepts slots 1..5, decrements once, and captures five
action types and weapon identities. Publication is types at playerState544..554,
weapon parameters558..568. C1 drawer42b3f0 uses a zero-based slot internally:
42b4d9 reads544+slot*4 and42b5a6 reads558+slot*4. Thus the native setter and
publication agree with the client.

Killstreak preview IDs68..78 and targets7c..8c are separate zero-based arrays.
Consumers45c4c0/45c500 read index*4 directly. Matching these five logical arrays
does not establish which action slot the shipped HUD presents for each selected
reward; that policy must come from the script/UI producer.

## Actual C1 icon gates

Drawer42b3f0 first checks material override578+slot*4 at42b4a1. Without an
override, type1 (weapon) follows42b5a6:

1. Action weapon parameter must be nonzero.
2. `40abb0` must find the weapon in player inventory (via40ab60), unless the
   client's special inventory mode is enabled.
3. `42a930` may hide an empty weapon only when definition byteBD1 is set;
   `41def0` sums applicable reserve/clip state.
4. Definition pointerB94 must contain a HUD material.

The UI expression5e41b0 is specifically an **override lookup**, not the complete
weapon action drawer. It accepts slots1..5 and reads574+slot*4, corresponding
to578..588. Zero override does not imply that the normal weapon icon is absent.

The same passive inspection found registered weapon100 named
`killstreak_uav_mp`, materialB94 `dpad_killstreak_uav`, byteBD1=0, ammo/clip
indices99. The current asset therefore has a valid HUD icon and does not hide
it because of empty ammo. No asset replacement is indicated.

At capture time the client had no gameplay snapshot: predicted commandTime0,
all action/preview fields zero and no snapshot pointer. These zeros cannot
establish what the failed earned-UAV snapshot contained. Next useful evidence
is the earned frame's action type, weapon parameter and owned inventory alongside
the selected script reward-to-slot mapping. Do not repair the icon by inventing
material overrides before verifying those producers.

## Follow-up active capture

`tools/codol_action_hud_probe.py` adds a bounded passive probe, guarded by the
actual42b5a6 action-weapon load instruction. It reports current bindings,
predicted/snapshot action fields, matching inventory entries, ammo entries,
definition icon/hide flags, preview data and clientInfo visibility gate. It
does not call client functions or alter gameplay.

One passive read subsequently found an active match at predicted command388174
and snapshot388117: progress5, IDs[18,17,20,0,0], targets[3,6,11,0,0]. Both states
contained action slot1 type1, weapon131 `rcbomb_mp`, owned in inventory, icon
`hud_icon_rcbomb_32x32`, hideWithoutAmmo0, clip entry[130,1,0], no override.
Other action slots were inactive. Connection state9 and clientInfo gate1 were
valid. This establishes working capture/publication for that earned RC reward;
it is not an earned-UAV capture and does not prove the user's missing UAV icon
resolved. No key bindings were changed.
