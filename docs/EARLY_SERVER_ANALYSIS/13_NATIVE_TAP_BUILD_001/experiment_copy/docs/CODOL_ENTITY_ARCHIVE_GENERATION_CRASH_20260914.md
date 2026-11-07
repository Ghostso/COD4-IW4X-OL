# Entity reuse and archive crash

## Evidence

`bin/home/main/qconsole.log` first reports entity 859/type 6 conversion refusal at
line 18496, around server time 300550. This follows Betty spin sounds and tag FX
publication. The diagnostic says `overlay: type-specific seed`; that label is
initialized by the seed function and remains unchanged when the later common
overlay fails. It does not identify the failed field.

At line 19170, around server time 334750, the log explicitly reports captured
entity event epoch 1 with native event counter 0. The subsequent frame rejects
entity 108/type 3. Line 19269 reports `SV_GetCachedSnapshot: end of message`.
The tiny message sizes (including 5 bytes) rule out actual buffer exhaustion.

The native source contains a concrete broken lifetime boundary:

* `G_FreeEntity` in `src/g_main_mp.cpp` clears the complete entity with `memset`,
  including `entityState.eventSequence`, but previously reset only selected
  native side stores (sound and vehicle spawner).
* The event/model/missile extension reset was attached to `G_InitGentity` in
  `_g_utils_mp.asm`.
* `G_Spawn` in that same assembly file **inlines** initialization. It does not
  call `G_InitGentity`. Ordinary freed-slot reuse therefore bypassed the reset.
* `CODOL_EntityStateExtCopy` correctly copies the stale live extension alongside
  the freshly initialized entity state, reproducing epoch 1/counter 0 in the
  snapshot ring.
* Both archive writer variants write the native state followed by its captured
  extension. The reader explicitly rejects differing epoch/counter halves by
  setting `msg->overflowed`. The next reader check reports the generic
  end-of-message error. The mismatch does not require corrupt byte framing.

## Source change

`src/g_main_mp.cpp` now calls `CODOL_ResetEntityEventGeneration` immediately
before the entity memset, after teardown and `Scr_FreeEntity` complete.
The existing reset clears live event, model-animation, missile, bomb and spawner
state. `CODOL_ResetEntityEventEpoch` clears only the live entity extension;
snapshot and archive storage retain their captured generations. Entity slot
reuse cannot inherit the previous incarnation's event counter or animation
identity.

The archive validity check and message capacity rules remain intact. No event
epoch is fabricated, no failed entity is silently dropped by this change, and
no archived state is read back from the current live slot.

## Review boundary

Source inspected; no worker build, automated tests, process writes or restart.
Parent owns compilation, deployment and live verification. The earlier Betty
type-6 conversion refusal is not conclusively explained by this fix: no epoch
warning precedes it. Its common-overlay failure may require a separate
trajectory/loop-sound diagnostic if it recurs. Do not count it as proven fixed.
