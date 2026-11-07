/* Source-level bridge for native CoDOL gamestate publication. */
#include "codol_sv_state.h"
/* The authored sun-sample override is a full-server feature; this file is also
 * compiled into the portable configstring fixtures, which link no game code. */
#ifdef CODOL_SERVER
#include "codol_map_shadow.h"
#else
#define CODOL_RefreshMapSunSampleSize() 1
#define CODOL_ResetMapSunSampleSize() ((void)0)
#endif
#include <stdio.h>
#include <string.h>

static codol_configstrings_t configstrings;
static codol_configstrings_t inherited_configstrings;
static char inherited_zone_type[5];
static char inherited_map_name[64];
static char inherited_map_zone_type[5];
static unsigned server_animlist_flags;

int CODOL_SetServerAnimListFlags(unsigned flags)
{
    if(flags & ~15u) return 0;
    server_animlist_flags = flags;
    return 1;
}
unsigned CODOL_ServerAnimListFlags(void) { return server_animlist_flags; }

codol_configstrings_t *CODOL_ServerConfigstrings(void) { return &configstrings; }
const codol_configstrings_t *CODOL_ServerInheritedConfigstrings(void)
{ return *inherited_zone_type ? &inherited_configstrings : NULL; }
const char *CODOL_ServerMenuName(unsigned slot)
{
    const char *name;
    if(slot>=CODOL_MENU_SLOTS) return NULL;
    name=CODOL_GetConfigstring(&configstrings,CODOL_CS_MENUS+slot);
    return name ? name : CODOL_GetConfigstring(CODOL_ServerInheritedConfigstrings(),
                                               CODOL_CS_MENUS+slot);
}
int CODOL_SetServerInheritedConfigstrings(const char *zone_type,size_t rows,const char *const *cells)
{
    uint32_t checksum;
    if(*inherited_zone_type || !CODOL_ConstConfigChecksum(zone_type,&checksum) ||
       !CODOL_ImportConstantConfigstrings(&inherited_configstrings,rows,cells)) return 0;
    strcpy(inherited_zone_type,zone_type);
    return CODOL_RefreshMapSunSampleSize();
}
void CODOL_ResetServerConfigstrings(void)
{
    CODOL_ResetMapSunSampleSize();
    CODOL_ClearConfigstrings(&configstrings);
    CODOL_ClearConfigstrings(&inherited_configstrings);
    memset(inherited_zone_type,0,sizeof(inherited_zone_type));
    memset(inherited_map_name,0,sizeof(inherited_map_name));
    memset(inherited_map_zone_type,0,sizeof(inherited_map_zone_type));
    server_animlist_flags = 0;
}
int CODOL_SetServerMapIdentity(const char *map,const char *zone_type)
{
    size_t length,i;
    if(!map || !*map || !zone_type ||
       (strcmp(zone_type,"mp") && strcmp(zone_type,"coop") && strcmp(zone_type,"zm")) ||
       (length=strlen(map))>=sizeof(inherited_map_name) || map[0]<'a' || map[0]>'z')
        return 0;
    for(i=1;i<length;++i)
        if((map[i]<'a' || map[i]>'z') && (map[i]<'0' || map[i]>'9') && map[i]!='_')
            return 0;
    if(*inherited_map_name)
        return !strcmp(inherited_map_name,map) && !strcmp(inherited_map_zone_type,zone_type);
    memcpy(inherited_map_name,map,length+1);
    strcpy(inherited_map_zone_type,zone_type);
    return 1;
}
/* The asset category the mounted map was installed with ("mp", "coop" or
 * "zm"). Latched by CODOL_SetServerMapIdentity during map setup, so every
 * consumer sees the category whose archives and constant configstrings are
 * actually mounted rather than a dvar a later command could relatch.
 * NULL until a map identity is installed. */
const char *CODOL_ServerZoneType(void)
{
    return *inherited_map_zone_type ? inherited_map_zone_type : NULL;
}
/* The mounted map's name, latched alongside the category above and cleared
 * between maps. NULL until a map identity is installed. Consumers use it to
 * scope per-map state that would otherwise silently persist for the whole
 * process -- see the missing-xmodel report table in db_load.cpp. */
const char *CODOL_ServerMapName(void)
{
    return *inherited_map_name ? inherited_map_name : NULL;
}
int CODOL_ServerMapIdentityMatches(const char *map,const char *zone_type)
{
    return map && zone_type && *inherited_map_name &&
        !strcmp(inherited_map_name,map) && !strcmp(inherited_map_zone_type,zone_type) &&
        !strcmp(inherited_zone_type,zone_type);
}
int CODOL_SetServerId(int32_t server_id)
{
    char value[16];
    int n = snprintf(value, sizeof(value), "%d", (int)server_id);
    return n > 0 && (size_t)n < sizeof(value) &&
        CODOL_SetConfigstring(&configstrings, CODOL_CS_SERVER_ID, value);
}
int CODOL_SetServerInfo(const char *map,const char *gametype,unsigned max_clients,const char *hostname)
{
    char info[1024]; int length;
    if(!map || !*map || !gametype || !*gametype || !max_clients ||
       max_clients>CODOL_MAX_GAME_CLIENTS || strchr(map,'\\') || strchr(gametype,'\\') ||
       (*inherited_map_name && strcmp(inherited_map_name,map)) ||
       !hostname || strlen(hostname)>255 || strpbrk(hostname,"\\\";\r\n")) return 0;
    /* CG_ParseServerinfo 0x465f57 reads "2485" at 0xc44704 as maxclients. */
    /* CG_ParseServerinfo 0x465bc1 copies numeric key 2492 into hostname[256]. */
    /* CG_ParseServerinfo465c27 stores key2482 for CG_Init's animlist loader.
     * Use the captured map-start mask, not a cvar that can change mid-map. */
    length=snprintf(info,sizeof(info),"\\g_gametype\\%s\\mapname\\%s\\2485\\%u\\2492\\%s\\2482\\%u",gametype,map,max_clients,hostname,server_animlist_flags);
    return length>=0 && (size_t)length<sizeof(info) && CODOL_SetConfigstring(&configstrings,0,info);
}

int CODOL_WriteServerGamestate(msg_t *msg, const char *map, const char *zone_type,
                               const char *gametype, unsigned max_clients, uint32_t sequence,
                               uint32_t client_number, uint32_t checksum_feed,const char *hostname)
{
    codol_msg_t wire;
    uint32_t crc;
    if (!msg || msg->overflowed || msg->splitData || msg->cursize < 0 ||
        msg->maxsize < msg->cursize || !max_clients || max_clients>CODOL_MAX_GAME_CLIENTS ||
        client_number>=max_clients || !map || !*map || !gametype || !*gametype ||
        strchr(map, '\\') || strchr(gametype, '\\') ||
        !CODOL_ConstConfigChecksum(zone_type, &crc)) goto fail;
    /* These textual serverinfo keys are accepted by 1.1.1.13. The replicated
     * numeric dvar and asset producers populate their own CoDOL slots. */
    if (!CODOL_SetServerInfo(map,gametype,max_clients,hostname) ||
        !CODOL_SetConfigstring(&configstrings, 2, "cod")) goto fail;
    /* The client inherits its fastfile table before applying these overrides.
     * Message capacity alone cannot protect the separate 128 KiB string pool.
     * Require the mounted table for this zone so validation includes exactly
     * the inherited namespace the client will use. */
    if (!CODOL_ServerMapIdentityMatches(map,zone_type) ||
        !CODOL_ConfigstringPoolSize(&configstrings, &inherited_configstrings, NULL))
        goto fail;
    CODOL_MsgWriteInit(&wire, msg->data + msg->cursize, msg->maxsize - msg->cursize);
    if (!CODOL_WriteGamestate(&wire, &configstrings, map, zone_type, crc,
                              sequence, client_number, checksum_feed)) goto fail;
    msg->cursize += wire.size;
    /* Gamestate ends in byte fields; do not share its bit pool with another svc. */
    msg->bit = msg->cursize * 8;
    return 1;
fail:
    if (msg) msg->overflowed = qtrue;
    return 0;
}
