# Splash and killcam HUD audit

## Implemented native killcam state publication

`src/codol/snapshot/codol_engine_state.c`, CODOL_OverlayEngineMovement now
publishes native playerState.deltaTime to C1 offset0xa50 and killCamEntity to
0xa54. This is a source correction, awaiting parent build and live verification.
No hooks, client patch, invented vision preset, or runtime setting changes.

Evidence chain:

- C1 expression-name tableCD08A8 has `inkillcam` atCD0974 (opcode51).
  Dispatch5E4C31 calls5DF490, whose accepted branch returns cg+C8B60.
- C1 transition46BE37 tests cg+A50. Nonzero sets cg+C8B60 at46BE48.
  Zero clears it at46BF0C..46BF1D. This drives actual client killcam state,
  rather than merely showing archived player movement.
- C1 active killcam46C09E reads snapshot+A54 as its entity selector;
  46C0B8 explicitly recognizes2047 as none.
- C1 server archive helper5D7DA1 adds its time displacement to ps+A50.
  Native SV_GetArchivedClientInfo in sv_snapshot.c already does the same to
  ps.deltaTime after retiming archived clocks. Its producer was present.
- Retained SpectatorClientEndFrame's successful forced-follow branch maps
  sess.killCamEntity -1 to2047 and puts that into the temporary archived
  playerState before copying it. That producer was also present.
- The native C1 movement/snapshot writer previously published neither field.
  The C1 netfield table already declares A50 as32bits and A54 as11bits.
  The correction publishes existing captured values, retaining native selector
  values outside replay instead of inventing a different sentinel rule.

Shipped common_mp contains compiled `killcam_fullscreen`, `killcam_blur` and
`killcam_blurred` menu/material references. The reference killcam fullscreen
menu gates on inKillcam. No specifically named killcam.vision was found in the
cached original C1 assets, so adding a generic grayscale/static vision would
not establish CoDOL behavior. Enabling the actual native C1 killcam lifecycle is
the supported first correction. Its visual result remains unverified here.

## Playercard wiring reviewed

Current _damage.gsc already assigns attacker card slot7 and opens
`killedby_card_display`; inherited _killcam.gsc repeats this for final killcam.
The shipped compiled display menu sets ui_show_killedBy. Native card setters
and CODOL_OverlayClientCards already publish ten-bit icon/title/nameplate
indices. No evidence currently justifies duplicating the existing menu calls
or changing slot7. The newly restored inKillcam state may restore missing
killcam presentation, but playercard visibility must still be observed.

## Intermittent medal report remains unconfirmed

The user subsequently qualified the missing-medal observation. No speculative
splash behavior change was made.

- Native ShowHudSplash uses the correct C1 `w slot row optionalNumber` command.
  C1 dispatcher469E0E..469E4B preserves this argument order.
- The third argument is **optionalNumber**, not duration despite existing
  native comments. C1 4691F8 reads duration from splashTable column4,
  multiplies to milliseconds and stores it at slot+8. Argument3 goes slot+C.
- C1 stores five records at cg+174384, stride16: row,startMilliseconds,
  durationMilliseconds,optionalNumber.
- IW4 _hud_message actionNotifyMessage sends ShowHudSplash and independently
  plays actionData.sound. Hearing the sound alone does not prove splash receipt
  or visibility. The native type0 reliable policy matches original C1's
  showhudsplash sender51E648; changing it blindly is not justified.
- Original code_post_gfx splashTable has914rows, patch has919; sampled
  rows4/13/17/170 retained identity. Full live table equivalence remains open.
- C1 4692B1 reads menu name column11 and5F5740 opens it through Scaleform or
  the named menu lookup. It does not resolve a server menu configstring index.
  Missing "precached" log messages alone do not establish missing menus.

Added passive `tools/codol_splash_probe.py`: exact C1 code guard, active-state
guard, received five slots, UI gates, and stability check. First capture
obj/codol-splash-slots-102092.json was inactive and correctly skipped slots.
No stale slot data was interpreted. Future active/killcam capture can correlate
server w commands with accepted row/timing and actual UI state.

## Whole-HUD report after the two-round session

Passive capture obj/codol-hud-killcam-after-crash-102092.json revalidated C1 PID102092: commandTime0, UIinitialized16FC2DA=0, inKillcam=0, deltaTime=0. Retained hud_drawHud valuecg+BF090=1 and local dvar952=1. These inactive values do not reconstruct the failed match, but do not show a currently stuck killcam or disabled HUD switch.

The native producer resets ps.deltaTime at every ClientEndFrame entry (_g_active_mp.asm, store+89c). Archived follow subsequently supplies the displaced state. C1 46BF0C..46BF1D explicitly clears inKillcam whenA50 becomeszero. Therefore no permanent restart latch is established merely by introducing the missing A50/A54 publication. Do not remove these required fields speculatively.

A distinct verified HUD gate is now captured: C1 468A64..468A84 recognizes the literal hud_drawHud client-dvar name and stores its integer atcg+BF090. C1 453A10 requires this field nonzero, then applies the local952/UIflags gate;455E10 adds pm_type and killcam-substate gating. Registration4983F6 names the local boolean952 (default1). The probe records all these raw inputs so a future active missing-HUD capture can distinguish them from inKillcam. Current server/source search found no hud_drawHud publisher and the two-round log has no explicit HUD-off reliable command. It does reset ui_opensummary to0 at the second-round connection. These are narrow exclusions, not proof every UI/menu path is correct.

## Shipped killcam vision recheck

A filename scan across all currently cached shipped zones found no killcam/static-named .vision. Common_mp contains missilecam.vision and generic grayscale/near_death/etc.; their presence alone does not identify ordinary killcam behavior. The currently used inherited IW4 _killcam.gsc has no visionSet call; it does perform the archive/session/card lifecycle described above. This inventory does not rule out a differently named effect, a non-vision material/renderer effect, or assets outside the cache.

C1 has literal mp_killcam_supressor_noise atC83AAC, referenced738773/73947C, but those references enter a separate resource playback path under numeric2620. Its name alone is not sufficient evidence for a vision or an ordinary-killcam screen filter. Existing killcam_fullscreen/killcam_blur menu evidence remains separate from an actual vision asset. No arbitrary substitute vision was added. The required next diagnostic is an active normal-play/killcam/respawn gate capture paired with the visual report, followed by the exact authored effect identity if the requested static remains absent.
