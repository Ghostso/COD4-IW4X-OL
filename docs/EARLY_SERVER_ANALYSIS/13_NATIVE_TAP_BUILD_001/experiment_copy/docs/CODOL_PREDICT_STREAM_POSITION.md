# predictstreampos protocol mismatch

Offline PE/source review, 2026-09-09; no client execution.

IW4 aligned handler5decb0 validates a player receiver, reads vector argument0,
converts z/y/x through6b5240 (SSE path truncates to signed integer), then formats
`X %i %i %i` with x/y/z in output order using format7185a4 at5ded39. It sends
this to the receiver's client through4bc3a0 with command type0 at5ded5a.
There is no argument-count check or script return. Native source has no current
predictstreampos implementation or registration.

C1's actual CG_ServerCommand469320 uses byte map46a118 and jump table46a024.
For ASCII X, the byte is60 and the target is469f7d. That path prints string
c44e44: `Unknown client game command: %s`. Verified by direct table reads and
aligned469f7d disassembly. Therefore sending IW4's X command cannot implement
this builtin for C1. No such sender/stub has been registered.

Next work must identify C1's stream-position consumer or establish an appropriate
native asset-loading equivalent. Absence of matching stream/predict/origin strings
in the static PE does not prove the capability absent. The two xrefs to C1 format
c5374c found so far include a stringtable-based commandw, not evidence for stream
position. Do not equate a matching printf format with the same operation.

Offline inspection helper: obj/claude-workers/parent-stream-command.py.
