#ifndef CODOL_HUD_FONTSCALE_H
#define CODOL_HUD_FONTSCALE_H
#include "q_shared.h"
/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct { float from; int start, duration; } codol_hud_fontscale_t;
struct game_hudelem_s;
struct gclient_s;
void CODOL_ResetHudFontScale(struct game_hudelem_s *);
void CODOL_ResetHudFontScales(void);
void CODOL_CopyClientHudFontScale(struct gclient_s *,int,hudelem_t *,const struct game_hudelem_s *);
/* Only live native HUD objects/copies captured by HudElem_UpdateClient have
 * identity here. Historical snapshots must capture bindings before copying. */
int CODOL_GetHudFontScale(const hudelem_t *,codol_hud_fontscale_t *);
#pragma pack(pop)
#endif
