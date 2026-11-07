# Native offhand weapon controls

`enableoffhandweapons` and `disableoffhandweapons` now mutate a dedicated
native `weapFlags` extension (`CODOL_WEAP_OFFHAND_DISABLED`, 0x1000). They
require a player reference and preserve every other native flag. The retained
`PM_Weapon_CheckForOffHand` checks this bit before starting offhand selection.
It does not set the existing global weapon-disable bit (0x80), and does not
cancel an already-running offhand phase.

The IW4 methods in local `D:/CoD/shx/iw4x.exe` are at 0x5db050 (enable) and
0x5dafe0 (disable), clearing/setting bit 0x1000 at player-state offset 0x2bc.
The native fork uses its own named field, not that offset. C1 uses different
prediction flags: helper 0x41c5a0 checks player-state +0x344 bits 0x20000,
0x40000 and 0x80000 for frag/tactical/special restrictions. Offhand entry at
0x41caaf invokes that helper. `CODOL_OverlayEngineOffhandControl` therefore
publishes all three bits when disabled and clears them when enabled, preserving
global-disable, active-offhand and other flags. This producer owns that complete
group; individual offhand-type controls will need an extension of its state model.

The controls extend native gameplay state and source assembly directly. No hook,
Python gameplay path or executable-address call was added. The native extension
lies outside IW3's old nine-bit weapon-flags wire mask; it requires the semantic
CoDOL snapshot adapter, which is included in player composition.

Focused tests verify player validation, repeated enable/disable, preservation of
global/active weapon flags, all three CoDOL restrictions and unchanged unrelated
player fields. They pass with 32-bit AddressSanitizer/UndefinedBehaviorSanitizer.
These fixtures do not execute a live player throwing grenades or establish parity
for disabling an already-cooked grenade.

Windows build passes (`/tmp/sh1x-offhand-controls-win32-final.log`). The full
Linux `make -B -j6 all test-codol` also passes
(`/tmp/sh1x-offhand-controls-linux.log`). The full
reference script probe passes these methods and next stops at
`enableWeaponSwitch` in `common_scripts/utility.gsc:2692`. Probe PID 58608;
log `%TEMP%/sh1x-offhand-controls-reference-probe/main/qconsole.log`.
IW4 switch-control methods were located at 0x5db130/0x5db0c0 and use bit 0x800;
the corresponding native/C1 gates still need tracing before implementation.
The live CoDOL snapshot producer and client match entry remain incomplete.
