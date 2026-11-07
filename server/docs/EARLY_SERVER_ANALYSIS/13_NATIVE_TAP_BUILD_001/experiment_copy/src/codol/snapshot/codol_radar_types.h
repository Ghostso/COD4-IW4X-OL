#ifndef CODOL_RADAR_TYPES_H
#define CODOL_RADAR_TYPES_H
#include "player.h"
#include "codol_playerstate.h"
#include <stdint.h>
typedef struct { uint8_t spyplane, satellite, motion_tracker; } codol_radar_types_t;
#ifdef __cplusplus
extern "C" {
#endif
/* Client input slots: 0 spyplane, 1 satellite, 2 motion tracker enabled.
 * Slot2 preserves a script integer; its captured wire value is boolean. */
int CODOL_GetClientRadarType(unsigned client,unsigned satellite);
void CODOL_SetClientRadarType(unsigned client,unsigned satellite,int value);
void CODOL_ResetClientRadarTypes(unsigned client);
void CODOL_ResetAllRadarTypes(void);
void CODOL_PublishClientRadarTypes(unsigned client);
int CODOL_OverlayRadarTypes(codol_player_fields_t *wire,const playerState_t *ps);
void CODOL_Scr_SetTeamSpyplane(void);
void CODOL_Scr_GetTeamSpyplane(void);
void CODOL_Scr_SetTeamSatellite(void);
void CODOL_Scr_GetTeamSatellite(void);
#ifdef __cplusplus
}
#endif
#endif
