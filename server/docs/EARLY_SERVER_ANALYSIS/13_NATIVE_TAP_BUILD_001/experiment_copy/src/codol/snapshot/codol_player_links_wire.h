#ifndef CODOL_PLAYER_LINKS_WIRE_H
#define CODOL_PLAYER_LINKS_WIRE_H
#include "codol_playerstate_ext.h"
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_OverlayPlayerLinks(codol_player_fields_t *wire, const codol_ps_links_t *captured);
int CODOL_OverlayEnginePlayerLinks(codol_player_fields_t *wire, const playerState_t *ps);
#ifdef __cplusplus
}
#endif
#endif
