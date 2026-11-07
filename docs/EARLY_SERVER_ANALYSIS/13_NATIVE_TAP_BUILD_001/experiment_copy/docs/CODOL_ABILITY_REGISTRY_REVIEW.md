# Ability method registry evidence

Offline inspection of C1.exe, 2026-09-08. No process was attached or launched.

The native table contains the following function pointers; the adjacent name
pointer is 0xc2fead, the empty string, in the on-disk image. These records prove
the methods occupy the table, but do not prove their GSC spellings.

| Function-pointer address | Routine | Inspected behavior |
|---|---|---|
| 0xc3bfd4 | 0x518530 | Set ability modifier |
| 0xc3bfe0 | 0x518640 | Query ability modifier mask |
| 0xc3bfec | 0x518850 | Clear four ability masks |
| 0xc3bff8 | 0x518750 | Unset ability modifier mask |
| 0xc3c004 | 0x518910 | Set ability modifier value |
| 0xc3c010 | 0x518a10 | Set perk slot ID |
| 0xc3c01c | 0x518b80 | Query perk slot ID |
| 0xc3c028 | 0x518db0 | Clear eight perk slots |
| 0xc3c034 | 0x518ca0 | Unset perk slot |

The case-insensitive string scan found `usingabilitymodifier` at 0xc69eec,
referenced at 0xcd0980. That reference is in a string-pointer table alongside
operators and UI expression names such as `dvarbool`, `flashbanged`, and
`inkillcam`. It is not evidence for adding a GSC method alias.

The existing source registration names remain pending an independent script
name/ID mapping audit. Usage strings support the SetPerk/HasPerk/UnsetPerk names;
an empty native registry name is not confirmation of a guessed ability name.

Full aligned disassembly of 0x518850..0x518906 shows receiver validation followed
directly by four zero stores at playerState+0x4d0..0x4dc. It has no argument-count
check and preserves all value slots. The source dispatcher now reflects that
behavior. No build, VM execution, or client behavior was verified.
