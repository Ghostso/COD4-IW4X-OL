# Player-bot third-person animation audit

The reported working killcam view is the killer's first-person hands/weapon.
It does not establish working world-model or other-player animation state.

## Proven producer omissions corrected

`CODOL_PM_FootstepsC1` previously selected a body animation only while sprinting.
Ordinary walking/running never called `BG_AnimScriptAnimation`; idle reset the
bob counter and returned. This can leave the selected body pose unchanged while
the native player origin moves. The correction in `codol_pmove_c1_ground.c`
implements the measured C1 body-selection paths, using the existing native
animation namespace and condition setter:

- `413770`, table `C40978`: 32 forward/back stance, aiming/lean and stumble
  combinations, sprint 20/42 and dolphin movement 54.
- `4137D0`: normalized raw input publishes strafe condition8.
- `413370`, `413510`: idle, turn, directional flinch and stance fallback.
- `413860`: coasting without input chooses idle only at speed <=120.
- `413440`: ladder animation18/19 and signed vertical bob after the300ms
  post-jump delay; ordinary airborne movement retains its animation.
- `413983`: turret stance idle; `413952`: stance from actual target view height.

Body selectors feed the existing native `BG_PlayerStateToEntityState`, which
captures legs/torso and current/primary weapon identity. Entity overlay sends
C1 legs/torso at+d8/+dc and weapon pair+d4/+d6. Human local prediction can conceal
a missing server body producer; remote bot models cannot rely on that prediction.

Separately, parent owns the proven combat-bot weapon request correction:
`G_SelectWeaponIndex` calls `Bot_SetBotWeapon`, but the new combat command builder
returned before legacy `g_botai[].weapon` consumption and resent `ps.weapon`.
The old setter also narrowed to a byte. A recent native log showed slot2
`ps.weapon=0` while slots1/3 carried97/102; this establishes at least one missing
weapon before rendering, but does not explain every possible missing world gun.

## Runtime evidence boundary

Passive `obj/codol-live-player-render-probe.py` guards C1 executable instructions
and captures current snapshot type1 weapon pairs, flags, animations and actual
DObj model names. Capture `obj/codol-live-player-render-100756.json` found
commandTime0 and snapshotNULL, so no stale model state was interpreted.

Source corrected; parent review/build and active third-person observation pending.
No tests, client input, server restart or process writes by this worker.

## Native dog work preserved

Dog animation files remain staged in `obj/dogs-stage`. Added1200-slot immutable
pose archive ownership retains entity generations, parent indices and cloned
restart branches. Bootstrap reconstruction of cloned sync subtrees remains
incomplete and unactivated. Native XAnim ticking already occurs in
`G_RunFrame_50` and `G_RunFrame_520/550`; a second dog tick would double-advance.
The notification-free goal operation returns0; only nonzero notify lookup can
return2. Parent separately corrected the real DObj update return-value ABI.
