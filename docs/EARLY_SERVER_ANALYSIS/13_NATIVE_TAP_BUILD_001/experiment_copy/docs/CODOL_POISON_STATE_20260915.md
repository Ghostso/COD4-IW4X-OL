# Native poison state

Source reviewed and built: `obj/codol-poison-state.exe`, SHA256
`479623CD38BBF937A882E0003BE8658DD97C1005415170291137B812579DD644`.
Build exit 0. Deployed to both native executable names; server PID104388
started with four bots. Subsequent log shows mp_fav_tropical gamestate and
map music publication to Nucleur. No poison gameplay verification or automated tests.

## C1 evidence

C1 `CG_UpdatePoisonFX` at 0x4775a0 reads predicted player state +0x59c.
The existing C1 netfield at 0x059c carries one bit. The routine also considers
cg+0x1743fc and suppresses the effect using killcam state. Its target/current
effect values are cg+0xb0444/+0xb0448. The refdef starts at cg+0xb036c.
The renderer copies refdef+d8/dc at 0xa82d35/0xa82d41 into render-frame
+0x407c/+0x4080, then copies the latter to view+0xfb8 at 0xa8229c.
0xab9637 checks that value; 0xab9665 selects material 0xcf3a70, registered as
`poison`. These are C1 addresses, not copied T5 structure offsets.

## Implementation

The T5 player methods startpoisoning, stoppoisoning and ispoisoned now operate
on a real per-player state extension. Snapshot publication writes C1 +0x59c.
Archive writer and reader carry the same bit after dive_end_time and before
the scripted event queue, so delayed spectators use captured state rather
than the current client's state. Spawn and client reset clear poison.

This supplies one native dependency of T5 Tabun. The complete Tabun trigger,
damage, HUD visibility, asset selection and cleanup script is still pending.
DoDamage's T5 destructible-piece branch also remains incomplete.
