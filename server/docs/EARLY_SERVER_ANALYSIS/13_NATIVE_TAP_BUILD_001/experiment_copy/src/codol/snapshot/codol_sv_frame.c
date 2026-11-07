#ifdef CODOL_SERVER
#include "codol_sv_frame.h"
#include "codol_frame_builder.h"
#include <string.h>
#include <stdlib.h>
static struct {
    codol_hud_state_t *hud;
    uint32_t sequence;
    int valid;
} captures[MAX_CLIENTS];
void CODOL_InvalidateClientSnapshotHud(unsigned client)
{
    if(client<MAX_CLIENTS) captures[client].valid=0;
}

void CODOL_ClearClientSnapshotHud(unsigned client)
{
    if(client>=MAX_CLIENTS) return;
    free(captures[client].hud);
    captures[client].hud=NULL; captures[client].valid=0;
}
int CODOL_CaptureClientSnapshotHud(unsigned client,uint32_t sequence,const hudElemState_t *source)
{
    codol_hud_state_t next;
    if(client>=MAX_CLIENTS) return 0;
    captures[client].valid=0;
    codol_player_failure=NULL;
    if(!source || !CODOL_CollectServerHud(&next,source)) return 0;
    if(!captures[client].hud) captures[client].hud=malloc(sizeof(next));
    if(!captures[client].hud) return 0;
    *captures[client].hud=next;
    captures[client].sequence=sequence; captures[client].valid=1;
    return 1;
}
int CODOL_CopyClientSnapshotHud(unsigned client,uint32_t sequence,codol_hud_state_t *out)
{
    if(!out || client>=MAX_CLIENTS || !captures[client].valid || captures[client].sequence!=sequence) return 0;
    *out=*captures[client].hud; return 1;
}
int CODOL_OverlayClientSnapshotPlayer(unsigned client,uint32_t sequence,codol_player_fields_t *fields,
    codol_player_array_updates_t *arrays,codol_hud_state_t *hud,
    const playerState_t *source,const codol_engine_player_bindings_t *bindings)
{
    codol_hud_state_t captured;
    if(!CODOL_CopyClientSnapshotHud(client,sequence,&captured)) {
        if(!codol_player_failure || strncmp(codol_player_failure,"HUD",3))
            codol_player_failure="HUD capture missing for this sequence";
        return 0;
    }
    return CODOL_OverlayEnginePlayerWithHud(fields,arrays,hud,source,bindings,&captured);
}
#endif
