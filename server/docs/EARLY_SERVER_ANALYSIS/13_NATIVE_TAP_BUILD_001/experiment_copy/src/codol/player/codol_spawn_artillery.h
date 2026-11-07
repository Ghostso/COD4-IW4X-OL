#ifndef CODOL_SPAWN_ARTILLERY_H
#define CODOL_SPAWN_ARTILLERY_H
/* T5 artillery's static NORMAL cylinder subset. Not a replacement for the
 * complete attached/player/weapon spawn-influencer system. */
void CODOL_ResetArtilleryInfluencers(void);
void CODOL_Scr_AddArtilleryInfluencer(void);
void CODOL_Scr_RemoveArtilleryInfluencer(void);
void CODOL_Scr_ArtillerySpawnWeight(void);
#endif
