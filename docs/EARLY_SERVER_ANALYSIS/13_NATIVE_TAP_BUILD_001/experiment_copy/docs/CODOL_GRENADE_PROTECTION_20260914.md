# Selected grenade protection

The current IW4 flash monitor and concussion damage callback apply their
full durations regardless of selected CoDOL perks. Native sources contain
no modStunProtectionScale or modFlashProtectionScale consumer. The native
perk aggregator already retains both as server-only numeric contributions.

The extracted C1 coAbilityModifiersTable gives modifier64/65 default1,
minimum0 and no client value slot. coPerkStatsTable's engineerpro contributes
-0.7 to each; coop_flakjacket_pro contributes -0.25 to stun protection.
Using the existing aggregation, those become0.3 and0.75 respectively.

The staged GSC adaptation retains IW4 blast angle/distance, friendly-fire
and duration formulae, then scales the recipient's flash and rumble duration
before simultaneous-flash aggregation. Reflected/shared flashes query their
actual recipient separately. Concussion duration is scaled before applying
shellshock and recording concussionEndTime. Zero skips a new shock without
clearing another effect. Undefined selection preserves ordinary behavior.
Optional attacker notifications are guarded against absent entities.

This is an IW4 lifecycle adaptation driven by CoDOL table values. The original
CoDOL server script, exact rumble policy and live protected-player behavior
are not recovered or verified. No automated tests were run.

Files staged under obj/grenade-protection-stage; parent review/deployment
state is tracked in CODOL_IMPLEMENTATION_PASS.json.

Lifecycle review also found applyFlash's one-frame wait and rumble loop lacked death/disconnect cancellation. Staged handlers now cancel on death/disconnect/monitor stop. The connect-lifetime monitor starts one spawn cleanup waiter to discard cancelled aggregate durations and flashEndTime on each spawned_player; restarting monitoring cancels the prior monitor/helpers first. This avoids killing the sole connect-lifetime monitor on death.
