# Native weapon-switch controls

`enableweaponswitch` and `disableweaponswitch` now modify the player's native
weapon flags. They validate a player entity, preserve unrelated flags, and are
idempotent. They do not disable firing or offhand weapons.

The alpha0022 Python enumeration is `gsc/builtin_surface.py:531-532`; its gates
record `_weaponswitch`. Static inspection of local `D:/CoD/shx/iw4x.exe` confirms
the actual IW4 methods at 0x5db130 and 0x5db0c0 clear/set bit 0x800 at player
state +0x2bc. The fork reserves that bit in retained IW3 `weapFlags`.

The native `PM_Weapon_690` request comparison now rejects a different requested
weapon while this flag is set. Existing weapon-state completion and the earlier
forced mantle/global-disable transitions retain their original paths. This is
a source change compiled into the server, with no hooks or runtime patches.

The CoDOL player-state adapter owns bit 0x800 of wire field +0x344. Static C1
inspection found selection predicates at 0x480f37 and 0x4817af testing mask
0x880, combining this bit with known global weapon-disable bit 0x80. The switch
meaning is inferred from these consumers and the verified IW4 method; it has
not been tested in a connected CoDOL match. Offhand group bits 0xe0000 remain
owned by the separate offhand adapter.

The weapon-control fixture checks repeated enable/disable, independence of
switch/offhand/global flags, malformed entity references, wire-field isolation,
and null inputs. It does not execute a full movement frame or establish live
client prediction parity. The live snapshot writer still needs integration of
the CoDOL semantic adapters.

Validation on 2026-09-08: Linux `make -j6 all test-codol`, the weapon-control
fixture with ASan/UBSan, and a forced Windows MinGW rebuild all pass. The
isolated full-reference script probe in `%TEMP%/sh1x-weaponswitch-reference-probe`
advances past `enableWeaponSwitch` to missing `EnableUsability` in
`common_scripts/utility.gsc:2646`. This probe uses loopback port 17739 and its
own home directory. After the script compilation failure and completed game/
network shutdown, its remaining process was stopped by verified PID and command
line; the existing C1 client and Python lobby were not altered.
