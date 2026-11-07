# Earned killstreak use path audit

Scope: verify actual generic grant -> selection -> use before adding new native
facilities. Source inspection only, no live scripts/process modifications.

- scripts/codol/maps/mp/killstreaks/_killstreaks.gsc giveKillstreak calls
  giveKillstreakWeapon, which invokes _giveWeapon and _setActionSlot(4,"weapon",weapon).
- maps/mp/_utility.gsc wrappers invoke actual giveWeapon and setActionSlot.
- Retained PlayerCmd_giveWeapon in _g_client_script_cmd_mp.asm calls native
  G_GivePlayerWeapon; on successful grant it calls G_InitializeAmmo. Missing
  explicit giveStartAmmo in the killstreak script is not proof of missing ammo.
- CODOL_Scr_SetActionSlot validates player/type/registered weapon, stores captured
  state, and CODOL_OverlayActionSlots publishes C1 type and weapon parameters.
- Native G_RunFrame in _g_main_mp.asm compares current ps.weapon with oldWeapon.
  On change it resolves BG_GetWeaponDef's name and emits scr_const.weapon_change
  (native constant offset0xc8), then records the new oldWeapon.
- killstreakUseWaiter waits for weapon_change, verifies the selected name matches
  the front earned reward, then invokes killstreakUsePressed.
- killstreakUsePressed calls the registered per-streak use function and only
  consumes the reward when that function succeeds. It then repopulates the item.
- isWeaponEnabled is a script utility, not an absent native builtin. The actual
  IW4 reference common_scripts/utility.gsc returns !self.disabledWeapon.
- getWeaponsListItems already enumerates owned native inventory-type items.

References: retained native sources above, plus IW4 devraw sources under
D:/CoD/CODOL Builds/Warfare2Client/DevData/devraw. The mounted retained override
uses the same generic queue/selection pattern. C1-specific action-slot setter
addresses and wire offsets are documented in CODOL_KILLSTREAK_HUD_AUDIT_20260914.md.

No additional generic missing producer/consumer was proven in this bounded pass.
A second weapon-change notifier or speculative action-slot server command would
risk duplicate use, not implement a demonstrated gap. Specific streak function
registration/activation dependencies remain separate; this audit does not claim
all selected streaks work. No speculative support source or live GSC change added.
