/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_minimap.h"
#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include "server.h"
#include "g_shared.h"
#include "scr_vm.h"
#include "cscr_stringlist.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

void CODOL_Scr_SetNorthYaw(void)
{
    float yaw=Scr_GetFloat(0);
    char value[32];
    float radians;
    /* IW4 5f36a0 publishes %g then updates compassNorth via sin/cos.
     * Retained getnorthyaw/worldspawn use 822; the CoDOL publisher maps
     * that native slot to 1302 for gamestate and reliable updates. */
    snprintf(value,sizeof(value),"%g",(double)yaw);
    SV_SetConfigstring(822,value);
    radians=(float)((double)yaw*0.01745329238474369);
    level.compassNorth[0]=(float)cos((double)radians);
    level.compassNorth[1]=(float)sin((double)radians);
}

static const char *minimap_icon(unsigned slot)
{
    unsigned index=CODOL_CS_MINIMAP_ICONS+slot;
    const char *name=CODOL_GetConfigstring(CODOL_ServerConfigstrings(),index);
    if(!name) name=CODOL_GetConfigstring(CODOL_ServerInheritedConfigstrings(),index);
    return name ? name : "";
}
static unsigned plane_icon(unsigned argument)
{
    const char *name;unsigned slot;
    if(Scr_GetNumParam()<=argument || Scr_GetType(argument)==VAR_UNDEFINED)return 0;
    name=Scr_GetString(argument);
    if(!*name)return 0;
    /* C1 54ffb0: distinct 15-entry minimap bank, not material indices. */
    for(slot=0;slot<CODOL_MINIMAP_ICON_SLOTS;++slot)
        if(!Q_stricmp(minimap_icon(slot),name))return slot+1;
    Scr_Error(va("Minimap icon '%s' was not precached",name));
    return 0;
}
void CODOL_Scr_SpawnPlane(void)
{
    gentity_t *owner=Scr_GetEntity(0),*plane;
    unsigned classname,friendly,enemy;int flags=0,ownerIndex;vec3_t origin;
    if(!owner->client){Scr_ParamError(0,"Owner entity is not a player");return;}
    classname=Scr_GetConstString(1);
    Scr_GetVector(2,origin);
    friendly=plane_icon(3);enemy=plane_icon(4);
    if(Scr_GetNumParam()>5)flags=Scr_GetInt(5);
    ownerIndex=(int)(owner->client-level.clients);
    if(ownerIndex<0 || ownerIndex>=level.maxclients){Scr_ParamError(0,"Invalid plane owner client");return;}
    plane=G_Spawn();
    Scr_SetString(&plane->classname,classname);
    VectorCopy(origin,plane->r.currentOrigin);
    plane->spawnflags=flags;
    if(!G_CallSpawnEntity(plane)){
        G_FreeEntity(plane);
        Scr_Error(va("unable to spawn \"%s\" entity",SL_ConvertToString(classname)));
        return;
    }
    /* C1 54c8ee/54c8f1/54c8f4: owner, friendly, enemy. No team packing. */
    plane->s.eType=ET_PLANE;
    plane->s.lerp.u.plane.ownerClient=ownerIndex;
    plane->s.lerp.u.plane.enemyIcon=(int)enemy;
    plane->s.lerp.u.plane.friendlyIcon=(int)friendly;
    Scr_AddEntity(plane);
}
void CODOL_Scr_PrecacheMinimapIcon(void)
{
    const char *name=Scr_GetString(0), *p;
    unsigned slot, index;
    int client;
    /* C1 54ff80 ->54f9d0: whole-bank case-insensitive duplicate pass before
     * first-empty search. Empty input matches an empty slot without writing. */
    for(slot=0;slot<CODOL_MINIMAP_ICON_SLOTS;++slot)
        if(!Q_stricmp(minimap_icon(slot),name)) return;
    for(slot=0;slot<CODOL_MINIMAP_ICON_SLOTS;++slot)
        if(!*minimap_icon(slot)) break;
    if(slot==CODOL_MINIMAP_ICON_SLOTS) {
        Scr_Error("Too many minimap icon precached. Max allowed is 15");
        return;
    }
    /* Use the existing asset-name command representation. Reject names that
     * cannot be represented as one reliable-command token before mutation. */
    if(strlen(name)>MAX_STRING_CHARS-32) {
        Scr_Error("Minimap icon name is too long"); return;
    }
    for(p=name;*p;++p)
        if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') {
            Scr_Error("Invalid minimap icon name"); return;
        }
    index=CODOL_CS_MINIMAP_ICONS+slot;
    if(!CODOL_SetConfigstring(CODOL_ServerConfigstrings(),index,name)) {
        Scr_Error("Could not register minimap icon"); return;
    }
    if(!svs.clients || !sv_maxclients) return;
    for(client=0;client<sv_maxclients->integer;++client) {
        client_t *target=&svs.clients[client];
        if(target->state>=CS_PRIMED && target->gamestateSent)
            SV_SendServerCommandNoLoss(target,"d %u %s",index,name);
    }
}
#endif
