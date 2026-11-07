# Intermission score publication

Status: source corrected and reviewed. Parent owns build and runtime verification. No tests, process changes or UI input performed.

Retained `ClientEndFrame_140` publishes `level+0x200` and `level+0x204` (teamScores[TEAM_RED/TEAM_BLUE]) to configstrings4 and5 when entering intermission. The CoDOL fallback `SV_SetConfigstring` broadcasts those numeric indices directly, and the asset interception has no score4/5 mapping. This can overwrite C1's first-team score with the second-team value without updating the native C1 bank. Because the ordinary team-score publisher compares against that bank, an unchanged score can prevent it from repairing the client-side overwrite.

The exact C1 consumer confirms the intended pairing independently of native comments: at0x46705e it reads offset-table entry0x6d0d144 (base0x6d0d130 +5*4), resolves against0x6d1370c, parses integer and stores cg+0xbeb20 at0x467072. At0x467078 it reads entry0x6d0d148 (+6*4) and stores cg+0xbeb24 at0x46708c. Reliable commands C at0x4699d5 and D at0x469a12 write those same fields. The earlier comment naming0x550960 as the score consumer is inaccurate: that routine is a server winning-team producer, not this configstring reader.

The CODOL_SERVER intermission branch now calls existing `CODOL_PublishTeamScores` instead of the two retained array writes. That helper publishes TEAM_RED to C1 slot5 and TEAM_BLUE to slot6, records the values in the native C1 bank, and deduplicates unchanged values. This shares the normal-frame publication path and retains gamestate consistency. Merely changing the retained literals would leave two banks with independent change detection.

The call has no arguments. ESI contains the entity and survives the C ABI call; the following code reloads its client pointer. EBX is not consumed after this branch except by the epilogue restoring its saved value. The non-CoDOL branch retains its original code. No shadow causation is implied; this is a separate intermission/HUD correctness defect.
