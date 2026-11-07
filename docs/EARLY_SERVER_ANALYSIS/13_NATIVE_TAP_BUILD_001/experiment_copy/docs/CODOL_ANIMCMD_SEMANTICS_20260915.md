# Native animation command float semantics

Source and C1 binary audit; actor animation gameplay is not yet verified.

The existing command codec inherited reversed semantic names from the Python
reference. C1 parser `5a1264` calls `5a10e0` and stores the result at command
`+1c`; `5a1278` calls `5a1060` and stores its result at `+20`. Blend is decoded
between them at `5a126e` and stored at `+24`.

Executor `443fc8..443fcf` passes command `+1c` as the first float to `63c520`.
The downstream XAnim goal setter `63bd80` writes that argument into the goal
weight at XAnimInfo `+2c` (`63bddf..63bde6`). Command `+20` supplies playback
rate, and `+24` supplies blend duration.

The native representation and writer now name these fields `goal_weight` and
`playback_rate`. The goal-weight codec retains its exact zero/one encoding and
0..1 / 1..5 ranges; the playback-rate codec retains exact one and 0..2 / 2..5
ranges. Wire ordering and quantization are unchanged. This corrects the input
contract for the incoming native actor animation producer rather than keeping
a reversed-name adapter in every caller.

The actor animation journal and XAnim owner remain staged. No current frame
producer supplies animation commands, so this is a prerequisite correction,
not evidence that dogs or their animations are playable.
