/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_player_worldweapon.h"
#include "codol_entitystate_ext.h"
#include "codol_weapon_native.h"
#include "codol_weapon_state.h"
#include "codol_bomb.h"
#include "codol_animation_tables.h"
#include "g_shared.h"
#include "server.h"
#include "bg.h"
#include "dobj.h"
#include "q_math.h"
#include "cmd.h"
#include "cscr_stringlist.h"
#include <stdlib.h>
#include <string.h>

extern void SP_script_model(gentity_t *);
extern int G_TagIndex(const char *);
extern int G_EntLinkToWithOffset(gentity_t *,gentity_t *,unsigned,const float *,const float *);
/* These are owned native entities, not synthetic snapshot-only models. */
typedef struct { unsigned number; int generation; } worldweapon_child_t;
typedef struct {
    int initialized,generation;
    unsigned weapon,hands;
    worldweapon_child_t child[2];
} worldweapon_owner_t;
static worldweapon_owner_t owners[MAX_CLIENTS];

static gentity_t *child_entity(const worldweapon_child_t *ref)
{
    gentity_t *ent;
    if(!ref->number || ref->number>ENTITYNUM_WORLD)return NULL;
    ent=&g_entities[ref->number-1];
    return ent->r.inuse && ent->useCount==ref->generation ? ent : NULL;
}
static void clear_owner(unsigned client)
{
    worldweapon_owner_t old=owners[client]; unsigned i;
    memset(&owners[client],0,sizeof(owners[client]));
    for(i=0;i<2;++i) {
        gentity_t *ent=child_entity(&old.child[i]);
        if(ent)G_FreeEntity(ent);
    }
}
void CODOL_ResetPlayerWorldWeapons(void)
{
    /* Map reset owns destruction of all entities; do not walk a reset pool. */
    memset(owners,0,sizeof(owners));
    /* A new map re-registers tag names and renumbers entities, so a link that
     * failed on the old map must be able to report again on the new one. */
    CODOL_ResetEntityLinkReports();
}
void CODOL_ResetPlayerWorldWeaponEntity(unsigned number)
{
    unsigned client,hand;
    if(number<MAX_CLIENTS)clear_owner(number);
    for(client=0;client<MAX_CLIENTS;++client)for(hand=0;hand<2;++hand)
        if(owners[client].child[hand].number==number+1)
            memset(&owners[client].child[hand],0,sizeof(owners[client].child[hand]));
}
static int using_knife(const playerState_t *ps)
{
    unsigned anim=(unsigned)ps->torsoAnim&~0x400u; uint32_t flags;
    if(anim>=CODOL_AnimationCount || anim>=CODOL_ANIM_RECORD_COUNT)return 0;
    /* Native parser and BG_IsKnifeMeleeAnim own 0x60 records, flags+50.
     * C1 4062a0 reads the corresponding C1 0x68 record; no offset equivalence. */
    memcpy(&flags,CODOL_AnimationRecords+anim*0x60+0x50,4);
    return (flags&0x100u)!=0;
}
static unsigned attach_tag(unsigned source_type,unsigned source_class,unsigned hand)
{
    /* C1 570cf3..570d31: grenade-type (1) weapons other than class 11 use
     * the scr_const word at 0x24ee002, everything else 0x24ee014/0x24ee012.
     * Those words are filled at 0x5770f8..0x5771df from "tag_inhand",
     * "tag_weapon_left" and "tag_weapon_right" (length arguments 0xb, 0x10,
     * 0x11 agree); the client's own tag choice 0x450330 matches. The player
     * skeleton has no "tag_weapon", so the name used here before linked
     * nothing for those weapons. */
    const char *name=source_type==1 && source_class!=11 ? "tag_inhand" :
        (hand ? "tag_weapon_left" : "tag_weapon_right");
    return SL_FindString(name);
}
static gentity_t *spawn_worldweapon(gentity_t *player,unsigned weapon,unsigned tag)
{
    float matrix[4][3]; vec3_t angles,zero={0,0,0}; gentity_t *child;
    if(!tag || !G_DObjGetWorldTagMatrix(player,tag,matrix))return NULL;
    child=G_Spawn();
    if(!child)return NULL;
    Scr_SetString(&child->classname,scr_const.script_model);
    G_SetOrigin(child,matrix[3]); AxisToAngles(matrix,angles); G_SetAngle(child,angles);
    G_SetModel(child,"tag_origin");
    SP_script_model(child);
    child->r.contents=0;
    /* C1 570b0a: plain full weapon index at child entityState+68. Native
     * selector is captured by existing anonymous.data[4] archive storage. */
    child->s.lerp.u.scriptMover.weaponIndex=weapon;
    if(!G_EntLinkToWithOffset(child,player,tag,zero,zero)) {
        G_FreeEntity(child); return NULL;
    }
    return child;
}
/* This runs every frame for every entity, so the warnings below must be
 * rate limited - but the old single counter capped the WHOLE function at
 * eight messages for the life of the process, and boot alone spent all eight
 * on one repeating tag. Anything that failed to link later in the match was
 * then silent, which is exactly the state an unpublished killstreak link
 * would hide in. Rate limit per (cause, tag) instead, so a new tag is always
 * reported once however long the server has been up, and a tag that keeps
 * failing still says so only once. */
#define CODOL_LINK_REPORTS 32
static struct { unsigned cause, key; } codol_link_reported[CODOL_LINK_REPORTS];
static unsigned codol_link_reported_count;
static int link_report_once(unsigned cause,unsigned key)
{
    unsigned i;
    for(i=0;i<codol_link_reported_count;++i)
        if(codol_link_reported[i].cause==cause && codol_link_reported[i].key==key) return 0;
    if(codol_link_reported_count>=CODOL_LINK_REPORTS) return 0;
    codol_link_reported[codol_link_reported_count].cause=cause;
    codol_link_reported[codol_link_reported_count].key=key;
    ++codol_link_reported_count;
    return 1;
}
/* Rate limiting alone cannot distinguish "failed once during startup" from
 * "fails forever": both print exactly one line. So when a tag that previously
 * failed does resolve, say so once and drop its entry. The boot-time
 * tag_player failure is expected to be an ordering artefact - G_RunFrame calls
 * this before the first SV_BuildClientSnapshot has run
 * CODOL_RefreshServerAssetNames, so no native tag has a wire slot yet on the
 * very first frame - and this is what proves it rather than assuming it. A tag
 * that is genuinely unpublishable simply never produces the second line. */
static void link_report_resolved(unsigned cause,unsigned key,const char *name,int slot)
{
    unsigned i;
    for(i=0;i<codol_link_reported_count;++i)
        if(codol_link_reported[i].cause==cause && codol_link_reported[i].key==key) {
            codol_link_reported[i]=codol_link_reported[--codol_link_reported_count];
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL link: tag '%s' now resolves to wire slot %d; links publish normally\n",
                name,slot);
            return;
        }
}
void CODOL_ResetEntityLinkReports(void) { codol_link_reported_count=0; }
static void capture_entity_links(void)
{
    unsigned number;
    for(number=0;number<ENTITYNUM_WORLD;++number) {
        gentity_t *ent=&g_entities[number];struct tagInfo_s *link;unsigned info;
        vec3_t origin={0,0,0},angles={0,0,0};
        if(!ent->r.inuse)continue;
        info=ent->tagChildren ? 1u<<24 : 0;
        /* Clear first: invalid/recycled parents or unresolved tags must never
         * retain a previous frame's link in a subsequent archive. */
        CODOL_EntityStateLinkCaptured(&ent->s,info,origin,angles);
        link=ent->tagInfo;
        /* C1 52d3e0: client entities do not carry the generic parent link. */
        if(link && !ent->client && link->parent && link->parent->r.inuse &&
           !(link->parent->r.svFlags&SVF_NOCLIENT)) {
            int tag=0;unsigned parent=(unsigned)(link->parent-g_entities);
            if(parent>=ENTITYNUM_WORLD) {
                if(link_report_once(1,parent))
                    Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL link: entity %u invalid parent %u\n",number,parent);
                continue;
            }
            if(link->name) {
                /* Report BOTH indices: a native index of zero means the tag was
                 * never registered as a server tag at all, while a nonzero
                 * native index with no wire slot means the C1 tag bank has not
                 * published it yet (or is full). The two need different fixes
                 * and the old message could not tell them apart. */
                const char *name=SL_ConvertToString(link->name);
                int native=G_TagIndex(name);
                tag=CODOL_ServerTagToWire((unsigned)native);
                /* A native index with no wire slot is the registration-time gap: the
                 * C1 tag bank was only refreshed from the snapshot path. Allocate the
                 * slot now (IW4 publishes CS_TAGS at G_TagIndex time) so the link
                 * publishes in this frame instead of being dropped. */
                if((tag<=0 || tag>255) && native>0 && CODOL_RefreshServerTagNames())
                    tag=CODOL_ServerTagToWire((unsigned)native);
                if(tag<=0 || tag>255) {
                    if(link_report_once(2,(unsigned)link->name))
                        Com_PrintWarning(CON_CHANNEL_SERVER,
                            "CoDOL link: entity %u parent %u tag '%s' unresolved"
                            " (native index %d, wire slot %d); link not published\n",
                            number,parent,name,native,tag);
                    continue;
                }
                link_report_resolved(2,(unsigned)link->name,name,tag);
            } else info|=2u<<24;
            info|=(parent+1)|((unsigned)tag<<16);
            memcpy(origin,link->axis[3],sizeof(origin));
            AxisToAngles(link->axis,angles);
        }
        if(!CODOL_EntityStateLinkCaptured(&ent->s,info,origin,angles) &&
           link_report_once(3,number))
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL link: entity %u invalid transform\n",number);
    }
}
void CODOL_UpdatePlayerWorldWeapons(void)
{
    unsigned client;
    for(client=0;client<MAX_CLIENTS;++client) {
        gentity_t *player=&g_entities[client]; worldweapon_owner_t *state=&owners[client];
        const codol_weapon_state_t *weapon_state;
        struct WeaponDef *def; codol_bomb_weapon_t original; unsigned weapon=0,held,source_class,hands,hand;
        if(!player->r.inuse || !player->client || player->s.eType!=ET_PLAYER ||
            (player->r.svFlags&SVF_NOCLIENT) || (player->client->ps.eFlags&0xc00)) {
            if(state->initialized || state->child[0].number || state->child[1].number)clear_owner(client);
            continue;
        }
        /* C1 570b76..570ba1 links a model of entityState +60, the "hold"
         * offhand being placed (claymore, C4, betty, scrambler), and
         * otherwise of the primary behind an alternate mode (ps+340). The
         * C1 client builds no ordinary gun into the player DObj (its attach
         * callback 450370 adds only the knife/+38 models, and +38 is empty on
         * every live composed weapon), so this server also links the primary
         * of an ordinary weapon: without it no one's gun is drawn at all. The
         * semantic accessor preserves the primary behind an alternate mode. */
        held=CODOL_EntityStateHeldOffhand(&player->s);
        if(held && held<(unsigned)BG_GetNumWeapons())
            weapon=held;
        else if(!CODOL_WeaponStatePrimaryWeapon(&player->client->ps,&weapon) ||
            !weapon || weapon>=(unsigned)BG_GetNumWeapons()) {
            if(state->initialized)clear_owner(client);
            continue;
        }
        def=BG_GetWeaponDef(weapon);
        if(!CODOL_GetNativeBombWeapon(def,&original) || !CODOL_GetNativeWeaponClass(def,&source_class)) {
            if(state->initialized)clear_owner(client);
            continue;
        }
        if(original.type==3) { if(state->initialized)clear_owner(client); continue; }
        weapon_state=CODOL_ClientWeaponState(client);
        hands=weapon!=held && weapon_state && weapon_state->initialized && weapon_state->dual_wield && !(def->worldKnifeModel && using_knife(&player->client->ps)) ? 2 : 1;
        if(!state->initialized || state->generation!=player->useCount || state->weapon!=weapon || state->hands!=hands) {
            clear_owner(client);
            state->initialized=1;state->generation=player->useCount;state->weapon=weapon;state->hands=hands;
        }
        for(hand=0;hand<hands;++hand) {
            gentity_t *child=child_entity(&state->child[hand]);
            if(!child) {
                child=spawn_worldweapon(player,weapon,attach_tag(original.type,source_class,hand));
                if(!child)continue; // Parent skeleton may still be rebuilding.
                state->child[hand].number=child->s.number+1;
                state->child[hand].generation=child->useCount;
            }
            G_GeneralLink(child);
            SV_LinkEntity(child);
        }
    }
    capture_entity_links();
}

/* Read-only paired diagnostic for C1 CalcMuzzlePoint. The owner cache alone
 * cannot prove that the child is still alive, linked, and published. */
void CODOL_WorldGunProbe_f(void)
{
    unsigned client,hand,primary=0,held;
    unsigned long parsed;
    char *end;
    gentity_t *player;
    worldweapon_owner_t *state;
    if(Cmd_Argc()!=2) {
        Com_Printf(CON_CHANNEL_DONT_FILTER,"usage: codol_worldgunprobe <client 0..%d>\n",MAX_CLIENTS-1);
        return;
    }
    parsed=strtoul(Cmd_Argv(1),&end,10);
    if(!Cmd_Argv(1)[0] || *end || parsed>=MAX_CLIENTS ||
       strspn(Cmd_Argv(1),"0123456789")!=strlen(Cmd_Argv(1))) {
        Com_Printf(CON_CHANNEL_DONT_FILTER,"codol_worldgunprobe: invalid client\n");
        return;
    }
    client=(unsigned)parsed;
    player=&g_entities[client];state=&owners[client];
    if(!player->r.inuse || !player->client) {
        Com_Printf(CON_CHANNEL_DONT_FILTER,"codol_worldgunprobe %u: no live player\n",client);
        return;
    }
    held=CODOL_EntityStateHeldOffhand(&player->s);
    CODOL_WeaponStatePrimaryWeapon(&player->client->ps,&primary);
    Com_Printf(CON_CHANNEL_DONT_FILTER,
        "codol_worldgunprobe %u: generation %d owner %d weapon %u hands %u primary %u held %u playerType %d\n",
        client,player->useCount,state->initialized,state->weapon,state->hands,primary,held,player->s.eType);
    for(hand=0;hand<2;++hand) {
        gentity_t *child=child_entity(&state->child[hand]);
        unsigned info=0;
        float origin[3],angles[3];
        DObj *obj;
        unsigned m;
        if(!child) {
            Com_Printf(CON_CHANNEL_DONT_FILTER,"  hand %u: no live child (cached %u generation %d)\n",
                hand,state->child[hand].number,state->child[hand].generation);
            continue;
        }
        obj=Com_GetServerDObj(child->s.number);
        if(!CODOL_EntityStateLink(&child->s,&info,origin,angles))info=0;
        Com_Printf(CON_CHANNEL_DONT_FILTER,
            "  hand %u: child %d type %d selector %u parent %d tag %s link 0x%08x DObj %u\n",
            hand,child->s.number,child->s.eType,child->s.lerp.u.scriptMover.weaponIndex,
            child->tagInfo && child->tagInfo->parent ?
                (int)(child->tagInfo->parent-g_entities) : -1,
            child->tagInfo && child->tagInfo->name ?
                SL_ConvertToString(child->tagInfo->name) : "<none>",
            info,obj ? (unsigned)obj->numModels : 0);
        if(obj)for(m=0;m<(unsigned)obj->numModels;++m)
            Com_Printf(CON_CHANNEL_DONT_FILTER,"    model %u: %s\n",m,
                obj->models[m] && obj->models[m]->name ? obj->models[m]->name : "<none>");
    }
}
#endif
