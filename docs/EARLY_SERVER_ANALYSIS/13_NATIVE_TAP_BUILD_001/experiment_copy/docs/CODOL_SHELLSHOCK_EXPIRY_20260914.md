# Persistent shellshock: native expiry clears the wrong flag

Read-only source and C1 executable audit, 2026-09-14. No tests, builds,
process changes, or live-memory writes. Parent owns the implementation.

## Proven defect

The native `GScr_ShellShock` producer in `_g_scr_main_mp.asm` stores start at
native playerState `0x630`, duration at `0x634`, and sets `pm_flags 0x8000`.
The snapshot publisher copies these into C1 `0x594/0x598` and publishes the
existing flags. However, retained `ClientThink_real_130` in `_g_active_mp.asm`
still uses `and dword [edi+0xc],0xfffeffff`: it clears IW3 bit `0x10000`, not
C1 shellshock bit `0x8000`. The flag therefore survives ordinary expiry.

The expiry branch is reached from start+duration minus `level.time` at
`ClientThink_real` near source lines1600–1604. It currently branches on `jle`.
No replacement expiry producer was found in `codol_pmove_c1.c`.

## Exact C1 behavior

C1 `50cbf5..50cc22`, immediately before movement call `416c30`:

```text
50cbf5 eax = [playerState+598]             duration
50cbfb eax += [playerState+594]            start
50cc0b compare [level.time at24b74c0],eax
50cc11 jle 50cc1a                         equal still active
50cc13 and [playerState+0c],ffff7fff       clear8000 only
50cc22 call416c30
```

Expiry is strictly `level.time > start + duration`. It uses the complete
stored duration, including its low seven bits. It does not clear index, start,
or duration and does not rewrite other movement flags. Addition is the x86
32-bit operation; avoid introducing signed C overflow if implemented in C.

The C1 script producer `543215/543226/543232` writes index590/start594/duration598,
then `54324b` sets8000 for a living player. StopShellShock `538aa2..538aae`
zeros duration and clears8000. FadeOutShellShock `538b3b..538b87` computes a
shorter duration from current time and the parameter's fade interval, then
preserves the old duration's low seven bits. That packing does not authorize
masking those bits out of the authoritative expiry comparison.

## Why symptoms fit

`codol_pmove_c1_ground.c::command_scale` correctly requires8000 and the shock
record's movement byte264, then multiplies speed by0.4. A stale flag therefore
keeps stun movement reduction active after the visual duration ends.
Retained `PM_Weapon_CheckForOffHand` already rejects a negative low word of
`pm_flags` (`cmp word [ebx+0xc],0; js`), which is precisely bit8000. Its gate
therefore continues denying equipment until that bit clears.

The narrow correction is to clear8000 in the CoDOL expiry branch and match
the C1 strict comparison. Preserve the legacy branch for non-CoDOL builds.
This is a source-proven lifecycle bug; whether it is the sole cause of the
reported live grenade behavior still requires observation after deployment.
