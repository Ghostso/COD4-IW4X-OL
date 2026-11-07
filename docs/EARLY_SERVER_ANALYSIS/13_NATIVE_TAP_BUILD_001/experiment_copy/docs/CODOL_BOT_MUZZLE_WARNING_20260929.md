# Local bot muzzle warning: evidence and next test

The September 29 local `console_mp.log` contains 585 warnings of
`No tag_flash or DObj in CalcMuzzlePoint on entity 0 (eType 1)` during
Killhouse play. `games_mp.log` and the server log identify entity 0 as
Recruit bot Training 1; the human occupied slot 12. Recruit class 0 lists an
AK104 with `red_rmr` and `cam_arctic`, plus a Desert Eagle, but the selected
weapon at each warning was not captured.

In the exact C1 build (SHA-256
`086B2BCF109C8340A898606E5CAA2678242449452BCF62B2DDA22A6E37DDA91F`),
the call chain reaches `0x445230` from `.tvm0` `0x83EA826`, then enters
`CalcMuzzlePoint` at `0x4824D0`. The warning at `0x4826A5` follows a failed
entity DObj/tag lookup. For a player entity, `0x482606..0x482641` first
reads client-info `+0xAF4` as an alternate centity index. If that index is
zero, it falls back to the player centity. The exact client-state mapping in
`CODOL_UNPUBLISHED_FIELDS_20260916.md` identifies this as the vehicle/alternate
entity selector, not the linked world-gun child. Zero is expected for an
on-foot bot. The player appearance DObj does not contain the ordinary held
gun; this server creates a separate linked world-gun child, as documented in
`CODOL_BOT_WORLDGUN_20260915.md`.

This is a world-entity muzzle path for a bot. It does not establish a
first-person M4 model defect or incorrect server bullet damage. The decisive
test is one controlled slot-0 shot with a paired capture of the selected
centity DObj and `tag_flash` lookup, the separate C1 world-gun child and
weapon model, and the native world-gun child number, weapon selector and link
state. A missing DObj, missing tag, and transient shot timing require
different fixes. The alternate selector `+0xAF4` should stay zero on foot.

`tools/codol_client_muzzle_probe.py --pid <C1 PID> --entity 0 --seconds 120`
is a passive exact-build sampler for the client half. It records the selected
entity, DObj handle/model count and whether the mounted model bone-name
arrays contain the flash tags, with UTC timestamps. `selected_match=0` means
the selected centity's entity number did not match the requested alternate/player,
so the probe deliberately skips that unrelated DObj. Syntax, CLI, and a
focused mismatched-centity fixture pass. A 90-second live C1 capture (1,782
non-atomic samples) found entity 0 active as ET_PLAYER, `+0xAF4 = 0`
throughout, with a DObj in 1,721 samples and no `tag_flash` in the selected
player's sampled models. The other 61 samples were transitions without a
selected DObj. This does not capture a specific shot or the separate C1
world-gun child and cannot yet locate the warning's cause.
Pair its CSV with `codol_worldgunprobe 0` and, if needed,
`codol_hitprobe <child> models` on the same single live server. The read-only
world-gun command reports the selected primary/held weapon, the live child
entity and generation, its parent/tag, weapon selector, captured network link
and native DObj model names. The child uses a placeholder server model; C1
resolves the visible gun from the weapon selector. A server result alone
therefore cannot prove that C1 built the correct weapon DObj. The two probes
were run during the same live match, but their samples were not synchronized
to a specific shot.

The September 29 Windows cross-build linked `bin/codol_dedrun_probe.exe` with
the new command. It was promoted through the single-server restart guard;
PID 18036 became the sole server on UDP/17733, with Killhouse Combat and 12
Recruit bots. A live `codol_worldgunprobe 0` reported primary/selector 107,
child 988, parent 0, `tag_weapon_right`, captured link `0x00020001`, and a
`tag_origin` placeholder DObj. The invalid-client input was rejected. Repeated
samples observed an active linked world gun for every one of the 12 bot slots;
some single samples lacked a child because the bot was dead or respawning.
The recent server log had no script runtime/fatal error. This proves the
server child/link producer in the sampled states, not C1's separately built
weapon DObj or flash tag. `+0xAF4` is a vehicle/alternate selector and is
independent of this child.
