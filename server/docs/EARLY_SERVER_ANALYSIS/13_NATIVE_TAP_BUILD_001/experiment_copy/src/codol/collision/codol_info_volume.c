/* C1 1.1.1.13 SP_info_volume (C1.exe 0x52dcb0..0x52dd2c):
 * install the map brush, hide the volume from snapshots, clear contents,
 * and link it so entity-contact queries can test its authored bounds.
 * The retained IW3 spawn table otherwise allocates info_volume without
 * setting a brush model, leaving Zombies player_zone tests unusable. */
#ifdef CODOL_SERVER
#include "entity.h"
#include "g_public.h"
#include "g_shared.h"
#include "server.h"
#include "server_public.h"

void CODOL_SP_info_volume(gentity_t *entity)
{
    if (!entity) return;
    if (!SV_SetBrushModel(entity)) {
        G_FreeEntity(entity);
        return;
    }

    entity->s.eType=ET_GENERAL;
    entity->r.svFlags|=SVF_NOCLIENT;
    entity->r.contents=0;
    entity->freeAfterEvent=0;
    entity->unlinkAfterEvent=0;
    entity->nextthink=0;
    SV_LinkEntity(entity);
}
#endif
