# Weapon-use control snapshot flags

The complete CoDOL player-state adapter now publishes native `weapFlags` values
0x1 (use-release/reload request) and 0x80 (global weapon disable) to CoDOL field
+0x344. Previously only active offhand, switch restriction and the three offhand
disable groups were composed there. This left global script weapon disable and
the server's use-release signal absent from the semantic snapshot state.

Static C1 evidence:

- 0x41a7a0 tests usercmd button 0x10 as a reload request.
- 0x41a7b0..0x41a7c3 consumes player-state +0x344 value 0x1, clears it and sets
  the same local reload request. Retained `PM_Weapon_CheckForReload_20` performs
  the corresponding operation on native player-state +0x10.
- 0x41bc00 and 0x41ca9d gate main/offhand weapon actions with value 0x80, matching
  retained weapon-disable state. The server's activation path generates the
  release flag, including while usability is disabled, as described in
  [native usability](CODOL_USABILITY.md).

`CODOL_OverlayEngineWeaponUseControl` owns only mask 0x81 and is called by the
complete player-state composition. It does not consume/mutate the native flags.
The test checks all four combinations, clearing, unrelated fields and extension
flags, plus null-input failure. The dedicated ASan/UBSan fixture passes.

Validation on 2026-09-08: Linux `make -j6 all test-codol` and the forced Windows
MinGW server rebuild both pass. No client or lobby process was changed.

The live snapshot writer still needs the complete CoDOL frame path. These
adapter checks do not prove connected-client firing/reload behavior.
