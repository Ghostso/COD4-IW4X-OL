# Killcam card rank producer audit

Source-only narrow fix in codol_engine_state.c; no builds/tests/process writes.

CODOL_SendCardDisplaySlot correctly sends `L <client> <slot>`, matching C1
51e2d1..51e31a and receiver469af1. It does not contain rank. C1 copies captured
clientState+A0 at46c964 into clientInfo+60; playercard builder68e7d0 consumes
that field into row+14. Rank must be fixed at its producer/publication boundary.

Native SetRank writes client+305c/3060 (clientSession.cs.rank/prestige).
_rank.gsc initialization computes rankId then invokes SetRank. C1 rank setter
51dd04..51dd18 reads script integer, checks unsigned<=255, and stores it at
client+3508. This establishes actual client-state rank production.

Previously CODOL_EngineClientState ignored the supplied cs.rank/prestige and
queried the IW4-only legacy profile store, defaulting absent values to zero.
The C1 schema declares rank, so generic profile access routes it to real C1
storage, not the legacy store. The serializer could therefore publish rank0
despite a populated native rank. It also read live account state while serializing
a captured client state. The fix publishes cs.rank/prestige, retaining existing
eight-bit wire encoding and naturally preserving archived killcam state.

## Remaining upstream issue

_rank::onPlayerConnect currently reads generic experience and treats it as
lifetime XP. CODOL_ProfileExperience already documents/reconstructs C1's
one-based rank, within-rank XP, and rankVersion behavior (58efa7..58efd4).
Generic profile VM reads do not perform this conversion. Likewise
_rank::syncXPStat stores lifetime XP directly into experience at687. Thus fixing
the serializer alone does not prove correct human progression/rank initialization.
A coordinated bridge for total-XP reads and encoded rank/XP/version writes is
needed; it must preserve generic playerdata semantics and bot match-local stats.
No speculative conversion or persistent profile mutation was added here.

## Follow-up implementation, source review pending

Added isolated codol_script_rank_experience.c/.h with explicit
getRankExperience()/setRankExperience(total) methods. The getter invokes the
existing recovered C1 total-XP conversion on the current secure session view.
The setter uses validated numeric rank intervals, then normalizes all three
secure fields together: rank=zeroBasedRank+1, experience=total-rankMinimum,
rankVersion=current maxrank-row column3. This is a coherent encoding of the
recovered read contract; it is not claimed to be a recovered C1 setter body.
Unknown/malformed profiles or tables produce a descriptive script error rather
than inventing rank0. Caller supplies nonnegative total XP; above-max values
retain the existing rank table's maximum-rank semantics.

Writes are transactional: resolve integer fields, copy the complete32768-byte
profile, write all fields, re-read/validate the normalized total, seal CRC, then
copy once into the existing secure session view. CODOL_ProfileRecord explicitly
returns record=blob+4; it selects version/checksum but does not verify CRC, so
validation before CRC reseal is valid. Original attached bytes, identity, and
generic playerdata access semantics remain unchanged. Existing profile-owner
persistence handles that session view; the helper adds no transport or file IO.

Staged obj/rank-experience-stage/maps/mp/gametypes/_rank.gsc uses the methods
for human initialization, syncXPStat and developer force-XP. Bots keep their
existing match-local experience store. Script promotion/SetRank uses the now
correct total XP; the earlier captured-client-state publication fix supplies
that rank to scoreboard/playercard/killcam consumers. Generic callers that
explicitly read raw profile experience retain the C1 schema value.

Resolver integration needed:
`#include "codol_script_rank_experience.h"`, and within CODOL registration:
`Scr_AddMethod("getrankexperience", CODOL_Scr_GetRankExperience, 0);`
`Scr_AddMethod("setrankexperience", CODOL_Scr_SetRankExperience, 0);`

No tests/builds/live script deployment or profile mutation performed by worker.
Existing profiles previously modified by the incorrect total-XP writer are not
silently repaired: recovering their intended prior rank needs account evidence.
