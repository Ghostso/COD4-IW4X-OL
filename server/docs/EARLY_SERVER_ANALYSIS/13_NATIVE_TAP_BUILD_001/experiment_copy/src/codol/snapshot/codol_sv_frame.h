#ifndef CODOL_SV_FRAME_H
#define CODOL_SV_FRAME_H
#include "codol_engine_state.h"
/* One current capture per recipient, not ACK history. Capture before losing
 * native HUD identity; the serializer's owned history retains sent frames.
 * Failure invalidates the previous capture so it cannot be reused by retry. */
int CODOL_CaptureClientSnapshotHud(unsigned,uint32_t,const hudElemState_t *);
int CODOL_CopyClientSnapshotHud(unsigned,uint32_t,codol_hud_state_t *);
void CODOL_ClearClientSnapshotHud(unsigned);
void CODOL_InvalidateClientSnapshotHud(unsigned);
/* Compose the exact native frame's player fields with its sequence-matched HUD.
 * Caller still supplies the complete seed, weapon/ammo/event bindings and clock.
 * Missing capture or any conversion failure preserves all four outputs. */
int CODOL_OverlayClientSnapshotPlayer(unsigned,uint32_t,codol_player_fields_t *,
    codol_player_array_updates_t *,codol_hud_state_t *,
    const playerState_t *,const codol_engine_player_bindings_t *);
#endif
