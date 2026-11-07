/* Native player view / camera / controls linking.
 *
 * These are the linking builtins the reference multiplayer scripts call but the
 * retained registry never provided. `maps/mp/gametypes/_damage.gsc`,
 * `_playerlogic.gsc` and `_gameobjects.gsc` are compiled on every gametype load,
 * so an unregistered name in them is a compile-time startup failure.
 *
 * IW4 (D:\CoD\shx\iw4x.exe) supplies the names and the parameter shape; C1
 * 1.1.1.13 supplies the state each one actually publishes. C1's method table has
 * its name pointers stripped to the empty string at 0xc2fead, so the handlers
 * were located from their own error strings and then read positionally against
 * IW4's table order:
 *
 *   IW4 73d1e0 playerlinkto                5ef770 -> shared core 5ef3d0 mode 0
 *   IW4 73d1f8 playerlinkweaponviewtodelta 5ef790 -> shared core 5ef3d0 mode 2
 *   IW4 73d21c playerlinkedoffsetenable    5ef8d0     C1 0x53b4b0 (0xc56674)
 *   IW4 73d228 playerlinkedoffsetdisable   5ef940     C1 0x53b5a0 (0xc56674)
 *   IW4 73d6c0 cameralinkto                5f5050     C1 0x5481d0
 *   IW4 73d6cc cameraunlink                5f5090     C1 0x548290
 *   IW4 73d6d8 controlslinkto              5f50c0     C1 0x5483c0 (0xc5837c)
 *   IW4 73d6e4 controlsunlink              5f5130     C1 0x5484c0 (0xc583a8)
 *
 * C1 record 0xc3aa60 holds 0x5483c0, and its neighbours 0xc3aa54/0xc3aa4c and
 * 0xc3aa6c hold 0x548290/0x5481d0 and 0x5484c0, in IW4's order.
 *
 * Measured C1 playerState effects, all of which are entries in the wire field
 * table this server already publishes (src/codol_player_fields.inc, measured
 * from C1 0xC38CA8):
 *
 *   0x53b559  or  [ps+0x14], 2          linked-offset enable   (field 0x14, 3 bits)
 *   0x54824e  or  [ps+0x10], 2          camera linked          (field 0x10, 26 bits)
 *   0x548259  mov [ps+0x54], entnum     camera entity          (field 0x54, 11 bits)
 *   0x548268  mov [ps+0x58], tagIndex   camera tag index       (field 0x58, 6 bits)
 *   0x5482a5  and [ps+0x10], ~2         camera unlink
 *   0x548480  or  [ps+0xc], 0x80000     controls linked        (field 0x0c, 31 bits)
 *   0x548492  mov [ps+0x5c], entnum     controls entity        (field 0x5c, 11 bits)
 *   0x54856f  and [ps+0xc], ~0x80000    controls unlink
 *   0x548577  mov [ps+0x5c], 0x7ff      controls unlink sentinel
 *
 * C1's entity-number fields are 11 bits and its "no entity" value is 0x7ff;
 * the engine's ENTITYNUM_NONE is the same 2047 now (GENTITYNUM_BITS 11); the wire sentinel is still written explicitly by name.
 *
 * The camera tag is not a script string on the wire. C1 0x570650 keeps a
 * 64-entry table of registered tag names, publishes a newly used name as
 * configstring 0x14b3 + index and returns the index. This server already models
 * that table: CODOL_CS_TAGS is 5299 (0x14b3) with CODOL_TAG_SLOTS 64, and
 * CODOL_RegisterTagName performs the same allocation, which is why the camera
 * link stores an index and never retains a script string.
 *
 * Positioning uses the retained tag-link machinery (G_EntLinkTo,
 * G_EntLinkToWithOffset, G_GeneralLink, G_EntUnlink), the same mechanism
 * ScrCmd_LinkTo uses and the same one C1 tests when it decides whether a player
 * is linked (0x53b514 checks gentity+0x258, the tagInfo pointer, exactly as
 * this file checks ent->tagInfo).
 *
 * The view side of the two link builtins is traced through IW4's own consumers
 * and confirmed field for field in C1 1.1.1.13, whose shared core is 0x53a7xx..
 * 0x53b1xx (located from the same "only supports linking to tags named
 * 'tag_player'" and "failed to link entity" strings, 0xc565f8 and 0xc56534):
 *
 *   parameter 2   IW4 gclient+0x3410  C1 gclient+0x3768   view rotation fraction
 *   parameter 7   IW4 gclient+0x340e  C1 gclient+0x3766   playerLinkTo, collide
 *   parameter 7   IW4 gclient+0x340f  C1 gclient+0x3767   weaponview, absolute
 *   arcs 3..6     IW4 gclient+0x3424/0x3428/0x343c/0x3440 min/max pitch and yaw
 *                 C1  gclient+0x3780/0x3798 and neighbours, same order
 *   linkAngles    IW4 gclient+0x174   C1 gclient+0x1d4    clamp reference
 *   weapon delta  IW4 gclient+0x180   C1 gclient+0x1e0    viewangles at link
 *   otherFlags 4  IW4 5ef53c          C1 53ad9e           weapon-view link
 *
 * IW4's consumers: 0x4fdb80 establishes the clamp reference right after the
 * link, 0x4b3ee0 advances the link each frame, 0x5fdbb0 turns the frame's
 * rotation into ps.viewangles and ps.delta_angles and refreshes the clamp
 * through 0x5fdaf0, and 0x5fdf20 moves the origin, which 0x4b3f72 skips for a
 * weapon-view link.
 *
 * What is NOT claimed here: IW4 and C1 keep the clamp as an interpolating
 * min/max pair (IW4 gclient+0x3414.., snapped by 0x44e2f0 on link and lerped by
 * 0x5fda80 for the transition builtins), and their movement code reads that pair
 * directly. The retained playerState has only viewAngleClampBase/Range and the
 * retained PM_UpdateViewAngles gate, so the arcs are expressed through those and
 * the transition builtins are out of scope. No C1 wire field for the clamp pair
 * has been identified, so nothing here is published to C1.
 * See obj/claude-workers/playerlink-view-r3-report.md.
 */
#ifdef CODOL_SERVER

#include "q_shared.h"
#include "q_math.h"
#include "qcommon_io.h"
#include "entity.h"
#include "player.h"
#include "dobj.h"
#include "g_shared.h"
#include "codol_remote_missile.h"
#include "codol_remote_vehicle.h"
#include "codol_vehicle_ground_runtime.h"
#include "server.h"
#include "scr_vm.h"
#include "scr_vm_functions.h"
#include "cscr_stringlist.h"
#include "codol_configstrings.h"
#include "codol_playerstate.h"
#include "codol_sv_state.h"
#include "codol_script_startup_extra.h"
#include "codol_playerstate_ext.h"

#include <string.h>
#include <math.h>

/* Engine producers, declared here like the other native CoDOL script files.
 * The two link helpers only exist as retained assembly globals
 * (src/asmsource/_g_utils_mp.asm:91 and :123); their signatures are read from
 * the ScrCmd_LinkTo call sites at src/asmsource/_g_scr_main_mp.asm:9320 and
 * :9370, which push (ent, parent, tag) and (ent, parent, tag, originOffset,
 * anglesOffset). */
int __cdecl G_EntLinkTo(gentity_t *ent, gentity_t *parent, unsigned int tagName);
int __cdecl G_EntLinkToWithOffset(gentity_t *ent, gentity_t *parent,
                                  unsigned int tagName, const float *originOffset,
                                  const float *anglesOffset);
unsigned int __cdecl Scr_GetConstLowercaseString(unsigned int index);

static codolPlayerLink_t s_playerLink[MAX_CLIENTS];
/* Reverse of the controls link, the equivalent of the entity handle C1 stores at
 * gentity+0x248 (0x54850a reads it back when the link is released). */
static short s_entityController[MAX_GENTITIES];
static qboolean s_initialised;

static void link_clear_player_part(codolPlayerLink_t *link)
{
    link->mode = CODOL_PLAYERLINK_NONE;
    link->linkEntNum = ENTITYNUM_NONE;
    link->offsetEnabled = qfalse;
    link->rightArc = CODOL_PLAYERLINK_MAX_ARC;
    link->leftArc = CODOL_PLAYERLINK_MAX_ARC;
    link->topArc = CODOL_PLAYERLINK_MAX_ARC;
    link->bottomArc = CODOL_PLAYERLINK_MAX_ARC;
    link->viewRotationFraction = 0.0f;
    link->collideWhileLinked = qfalse;
    link->viewLinkAbsolute = qfalse;
    link->anglesLocked = qfalse;
    VectorClear(link->linkAngles);
    link->lastFrameQuat[0] = 0.0f;
    link->lastFrameQuat[1] = 0.0f;
    link->lastFrameQuat[2] = 0.0f;
    link->lastFrameQuat[3] = 1.0f;
    link->haveLastFrameQuat = qfalse;
    link->clampActive = qfalse;
    link->clampBase[0] = link->clampBase[1] = 0.0f;
    link->clampRange[0] = link->clampRange[1] = 0.0f;
    VectorClear(link->weaponViewAngles);
}

static void link_clear_record(codolPlayerLink_t *link)
{
    link_clear_player_part(link);
    link->cameraEntNum = 0;
    link->cameraTagIndex = 0;
    link->cameraFlags = 0;
    link->controlsEntNum = ENTITYNUM_NONE;
}

static void link_init_once(void)
{
    int i;

    if(s_initialised) return;
    for(i = 0; i < MAX_CLIENTS; ++i) link_clear_record(&s_playerLink[i]);
    for(i = 0; i < MAX_GENTITIES; ++i) s_entityController[i] = -1;
    s_initialised = qtrue;
}

void CODOL_PlayerLinkResetAll(void)
{
    int i;

    CODOL_RemoteVehicleResetAll();
    for(i = 0; i < MAX_CLIENTS; ++i) link_clear_record(&s_playerLink[i]);
    for(i = 0; i < MAX_GENTITIES; ++i) s_entityController[i] = -1;
    s_initialised = qtrue;
}

static gentity_t *link_live_entity(int entNum)
{
    gentity_t *ent;

    if(entNum < 0 || entNum >= MAX_GENTITIES) return NULL;
    ent = &g_entities[entNum];
    if(!ent->r.inuse) return NULL;
    return ent;
}

static void link_drop_controls(codolPlayerLink_t *link, int clientNum)
{
    if(link->controlsEntNum >= 0 && link->controlsEntNum < MAX_GENTITIES &&
       s_entityController[link->controlsEntNum] == (short)clientNum) {
        s_entityController[link->controlsEntNum] = -1;
    }
    link->controlsEntNum = ENTITYNUM_NONE;
}

/* Releases only the player link. The camera and the controls links have their
 * own script-visible unlink methods in every reference script that uses them
 * (`_remotemissile.gsc` unlinks all three separately), so they are deliberately
 * untouched here. */
static void link_publish_clamp(gentity_t *ent, const codolPlayerLink_t *link);

static void link_release_player(int clientNum, qboolean releaseTagLink)
{
    codolPlayerLink_t *link;
    gentity_t *ent;

    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return;
    link = &s_playerLink[clientNum];
    if(link->mode == CODOL_PLAYERLINK_NONE) return;
    ent = &g_entities[clientNum];

    /* Nothing in the retained playerState is written back. This module never
     * takes ps.viewlocked, ps.viewlocked_entNum or the turret eFlags, so
     * releasing a link cannot disturb a turret the player is also mounted on:
     * the clamp lives in this record and disappears with it. */
    (void)ent;
    if(releaseTagLink && ent->r.inuse && ent->tagInfo) G_EntUnlink(ent);
    link_clear_player_part(link);
    if(ent->r.inuse && ent->client) link_publish_clamp(ent, NULL);
}

void CODOL_PlayerLinkReset(int clientNum)
{
    link_release_player(clientNum, qtrue);
}

void CODOL_PlayerLinkResetClient(int clientNum)
{
    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return;
    CODOL_RemoteVehicleExit((unsigned)clientNum);
    link_release_player(clientNum, qtrue);
    link_drop_controls(&s_playerLink[clientNum], clientNum);
    s_playerLink[clientNum].cameraEntNum = 0;
    s_playerLink[clientNum].cameraTagIndex = 0;
    s_playerLink[clientNum].cameraFlags = 0;
}

/* G_FreeEntity already unlinks tag children, but the view lock, the camera link
 * and the controls link are this module's state and have to be dropped too, or a
 * recycled entity number would silently inherit them. Each link is dropped on
 * its own: freeing a camera target must not release an unrelated player link. */
void CODOL_PlayerLinkEntityFreed(const struct gentity_s *freed)
{
    int i, num;

    link_init_once();
    if(!freed) return;
    CODOL_RemoteVehicleEntityFreed(freed);
    CODOL_GroundVehicleEntityFreed(freed);
    num = freed->s.number;
    if(num < 0 || num >= MAX_GENTITIES) return;
    /* C1's controls owner is an EntHandle: its association with the owner
     * is removed when that owner is freed. Mirror dissociation for this
     * native side table, including targets no longer in a player's record. */
    for(i = 0; i < MAX_GENTITIES; ++i)
        if(s_entityController[i] == num) s_entityController[i] = -1;
    if(num < MAX_CLIENTS) link_clear_record(&s_playerLink[num]);
    s_entityController[num] = -1;
    for(i = 0; i < MAX_CLIENTS; ++i) {
        codolPlayerLink_t *link = &s_playerLink[i];

        if(link->cameraEntNum == num) {
            link->cameraFlags &= ~UINT32_C(2);
        }
        if(link->controlsEntNum == num) link->controlsEntNum = ENTITYNUM_NONE;
        if(link->mode != CODOL_PLAYERLINK_NONE && link->linkEntNum == num) {
            /* The tag link itself is already being torn down by G_FreeEntity. */
            link_release_player(i, qfalse);
        }
    }
}

qboolean CODOL_PlayerIsLinked(int clientNum)
{
    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return qfalse;
    return s_playerLink[clientNum].mode != CODOL_PLAYERLINK_NONE;
}

const codolPlayerLink_t *CODOL_PlayerLinkState(int clientNum)
{
    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return NULL;
    return &s_playerLink[clientNum];
}
int CODOL_PlayerLinkSetRemoteAngles(unsigned clientNum,const float angles[3])
{
    codolPlayerLink_t *link;
    unsigned i;
    link_init_once();
    if(clientNum>=MAX_CLIENTS || !angles)return 0;
    link=&s_playerLink[clientNum];
    if(link->mode!=CODOL_PLAYERLINK_NONE || (link->cameraFlags&2) ||
       link->controlsEntNum!=ENTITYNUM_NONE)return 0;
    for(i=0;i<3;++i)if(!isfinite(angles[i]))return 0;
    memcpy(link->linkAngles,angles,sizeof(link->linkAngles));
    return 1;
}

unsigned CODOL_PlayerLinkFlags(int clientNum)
{
    const codolPlayerLink_t *link;
    unsigned flags = 0;

    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return 0;
    link = &s_playerLink[clientNum];
    /* C1 0x53b37a/0x53bad6 own bit 0 (angles locked), 0x53b559 owns bit 1;
     * 0x53ad9e owns bit 2. */
    if(link->mode != CODOL_PLAYERLINK_NONE && link->anglesLocked) flags |= 0x1u;
    if(link->offsetEnabled) flags |= 0x2u;
    if(link->mode == CODOL_PLAYERLINK_WEAPONVIEW) flags |= 0x4u;
    return flags;
}

struct gentity_s *CODOL_PlayerControlsLinkedEntity(int clientNum)
{
    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return NULL;
    return link_live_entity(s_playerLink[clientNum].controlsEntNum);
}

struct gentity_s *CODOL_PlayerCameraLinkedEntity(int clientNum, int *tagIndex)
{
    gentity_t *ent;

    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return NULL;
    if(!(s_playerLink[clientNum].cameraFlags & 2)) return NULL;
    ent = link_live_entity(s_playerLink[clientNum].cameraEntNum);
    if(ent && tagIndex) *tagIndex = s_playerLink[clientNum].cameraTagIndex;
    return ent;
}

int CODOL_EntityControllingPlayer(int entNum)
{
    link_init_once();
    if(entNum < 0 || entNum >= MAX_GENTITIES) return -1;
    return s_entityController[entNum];
}

/* ------------------------------------------------------------- publication */

/* Capture the live record once on the playing-frame publication path. */
void CODOL_CaptureClientPlayerLinks(unsigned clientNum)
{
    const codolPlayerLink_t *link;
    codol_ps_ext_t *ext;
    codol_ps_links_t captured;
    gentity_t *ent;
    link_init_once();
    if(clientNum >= MAX_CLIENTS || (int)clientNum >= level.maxclients) return;
    CODOL_RemoteVehicleValidate(clientNum);
    ent = &g_entities[clientNum];
    if(!ent->r.inuse || !ent->client) return;
    ext = CODOL_PlayerStateExt(&ent->client->ps);
    if(!ext) return;
    link = &s_playerLink[clientNum];
    captured.mode = (uint32_t)link->mode;
    captured.offsetEnabled = link->offsetEnabled ? 1u : 0u;
    captured.anglesLocked = (link->mode != CODOL_PLAYERLINK_NONE && link->anglesLocked) ? 1u : 0u;
    captured.linkWeaponEntNum =
        link->mode == CODOL_PLAYERLINK_WEAPONVIEW && link_live_entity(link->linkEntNum) ?
        (uint32_t)link->linkEntNum : ENTITYNUM_NONE;
    captured.cameraEntNum = (uint32_t)link->cameraEntNum;
    captured.cameraTagIndex = (uint32_t)link->cameraTagIndex;
    captured.cameraFlags = link->cameraFlags;
    memcpy(captured.weaponViewAngleBits, link->weaponViewAngles,
           sizeof(captured.weaponViewAngleBits));
    memcpy(captured.linkAngleBits, link->linkAngles,
           sizeof(captured.linkAngleBits));
    if(!link_live_entity(link->cameraEntNum)) captured.cameraFlags &= ~UINT32_C(2);
    captured.controlsEntNum = link_live_entity(link->controlsEntNum) ?
        (uint32_t)link->controlsEntNum : ENTITYNUM_NONE;
    if(!CODOL_PlayerLinksValid(&captured)) {
        ext->links_known = 0;
        return;
    }
    ext->links = captured;
    ext->links_known = 1;
}

/* ---------------------------------------------------------------- receivers */

/* The link methods are player methods. IW4 5ef3d0 prints "not an entity"
 * (0x72c7f0) for a field reference and "not a player entity" (0x70684c) for an
 * entity without a client. */
static gentity_t *link_player(scr_entref_t entref)
{
    link_init_once();
    if(entref.classnum) {
        Scr_ObjectError("not an entity");
        return NULL;
    }
    if(entref.entnum >= MAX_CLIENTS || (int)entref.entnum >= level.maxclients ||
       !g_entities[entref.entnum].r.inuse || !g_entities[entref.entnum].client) {
        Scr_ObjectError("not a player entity");
        return NULL;
    }
    return &g_entities[entref.entnum];
}

/* -------------------------------------------------------------- transforms */

/* Resolves the frame a link is expressed in. With a tag this is the tag's world
 * matrix on the link entity's own model, which is what ScrCmd_LinkTo validates
 * before it links; without a tag it is the entity's own origin and angles. */
static qboolean link_frame(gentity_t *linkEnt, unsigned int tagName,
                           float axis[3][3], float origin[3])
{
    float tagMat[4][3];
    float entAxis[4][3];

    if(tagName) {
        if(!G_DObjGetWorldTagMatrix(linkEnt, tagName, tagMat)) return qfalse;
        VectorCopy(tagMat[0], axis[0]);
        VectorCopy(tagMat[1], axis[1]);
        VectorCopy(tagMat[2], axis[2]);
        VectorCopy(tagMat[3], origin);
        return qtrue;
    }
    AnglesToAxis(linkEnt->r.currentAngles, entAxis);
    VectorCopy(entAxis[0], axis[0]);
    VectorCopy(entAxis[1], axis[1]);
    VectorCopy(entAxis[2], axis[2]);
    VectorCopy(linkEnt->r.currentOrigin, origin);
    return qtrue;
}

/* World delta -> link-local delta. G_EntLinkToWithOffset takes the offset in the
 * frame the child is attached to, so the delta is projected onto the link axes
 * rather than stored in world space. */
static void link_world_to_local(const float axis[3][3], const float delta[3],
                                float out[3])
{
    out[0] = DotProduct(delta, axis[0]);
    out[1] = DotProduct(delta, axis[1]);
    out[2] = DotProduct(delta, axis[2]);
}

/* The tag a player is linked through is owned by the retained tagInfo record,
 * which is why it is read back from there instead of being retained in this
 * module: a script string kept past the calling frame would need its own
 * reference, and the engine already holds exactly one for the live link. */
static unsigned int link_current_tag(const gentity_t *ent)
{
    return ent->tagInfo ? ent->tagInfo->name : 0;
}

/* ------------------------------------------------------------- link builtins */

/* IW4 clamps each arc against 0 and 180 before storing it. An absent parameter
 * uses 180, the "no restriction" value supplied by the same constant at
 * 5ef64d, 5ef690 and 5ef6d6. */
static float link_arc_param(int index, int numParam)
{
    float value;

    if(numParam <= index) return CODOL_PLAYERLINK_MAX_ARC;
    value = Scr_GetFloat((unsigned int)index);
    if(!(value >= 0.0f)) return 0.0f;          /* also rejects NaN */
    if(value > CODOL_PLAYERLINK_MAX_ARC) return CODOL_PLAYERLINK_MAX_ARC;
    return value;
}

static float link_normalize180(float a)
{
    a = a - 360.0f * floorf(a / 360.0f + 0.5f);
    return a;
}

static float link_normalize360(float a)
{
    return a - 360.0f * floorf(a / 360.0f);
}

/* IW4 stores a signed minimum and maximum per axis, with parameters 3 and 5
 * negated: minimum pitch -topArc (5ef6be), minimum yaw -rightArc (5ef636),
 * maximum pitch +bottomArc (5ef6ff), maximum yaw +leftArc (5ef676). Index 0 is
 * pitch and index 1 is yaw. C1 1.1.1.13 stores the same four values in the same
 * order at gclient+0x3780/0x3798 and their neighbours (53aee2, 53af69).
 *
 * The retained PM_UpdateViewAngles (_bg_pmove.asm:5069..5104) reads a centre and
 * a half range as world angles: it keeps AngleDelta(base[i], viewangles[i])
 * inside +-range[i], otherwise snapping viewangles[i] to
 * AngleNormalize360(base -+ range) and folding the correction into
 * delta_angles[i]. A range of 180 or more is unrestricted, which is also the
 * arcs' own default. So base is the centre of the permitted interval. IW4's
 * writer at 5fdaf0 stores the negated centre because its movement code reads the
 * pair with the opposite sign; that sign belongs to IW4's layout, not this one.
 *
 * The result is produced into this record and nowhere else. The retained pair
 * ps.viewAngleClampBase/Range is only consulted behind the native turret flag
 * pair (C1 0x0c00; _bg_pmove.asm:5065), and turret_use is the retained engine's sole producer of
 * that state (_g_misc_mp.asm:132..160), and the same bits gate unrelated weapon,
 * animation, use and damage behaviour. Borrowing them would make a linked player
 * behave as if mounted on a turret, so the consumer this needs is a
 * link-specific one: see the PM_UpdateViewAngles hunk in
 * obj/claude-workers/playerlink-view-r3-report.md. */
static qboolean link_arcs_restrict(const codolPlayerLink_t *link)
{
    return (link->rightArc < CODOL_PLAYERLINK_MAX_ARC ||
            link->leftArc < CODOL_PLAYERLINK_MAX_ARC ||
            link->topArc < CODOL_PLAYERLINK_MAX_ARC ||
            link->bottomArc < CODOL_PLAYERLINK_MAX_ARC) ? qtrue : qfalse;
}

static void link_update_clamp(codolPlayerLink_t *link, const float referenceAngles[3])
{
    if(!link_arcs_restrict(link)) {
        link->clampActive = qfalse;
        link->clampBase[0] = link->clampBase[1] = 0.0f;
        link->clampRange[0] = link->clampRange[1] = 0.0f;
        return;
    }
    link->clampActive = qtrue;
    link->clampRange[0] = (link->bottomArc + link->topArc) * 0.5f;
    link->clampRange[1] = (link->leftArc + link->rightArc) * 0.5f;
    link->clampBase[0] = link_normalize360(referenceAngles[0] +
                                           (link->bottomArc - link->topArc) * 0.5f);
    link->clampBase[1] = link_normalize360(referenceAngles[1] +
                                           (link->leftArc - link->rightArc) * 0.5f);
}

/* C1 0x575e00 (IW4 0x5fdaf0) writes the link clamp into the playerState it
 * publishes: range = (max - min) / 2 at ps+0x174/0x178 and base = reference +
 * max - range at ps+0x16c/0x170. C1's own PM_UpdateViewAngles (0x414ee8..
 * 0x414fb1) clamps every NORMAL_LINKED or weapon-view player to exactly those
 * fields, so a link that kept its clamp private left the client clamping to
 * base 0 range 0: the chopper gunner and AC-130 views could not be turned.
 * An unrestricted link publishes 180, which that clamp skips (0x414301). A
 * turret owns these fields while it is in use. */
static void link_publish_clamp(gentity_t *ent, const codolPlayerLink_t *link)
{
    playerState_t *ps;

    if(!ent || !ent->client) return;
    ps = &ent->client->ps;
    if(ps->viewlocked || (ps->eFlags & 0x0c00)) return;
    if(link && link->mode != CODOL_PLAYERLINK_NONE && link->clampActive) {
        ps->viewAngleClampBase[0] = link->clampBase[0];
        ps->viewAngleClampBase[1] = link->clampBase[1];
        ps->viewAngleClampRange[0] = link->clampRange[0];
        ps->viewAngleClampRange[1] = link->clampRange[1];
    } else if(link && link->mode != CODOL_PLAYERLINK_NONE) {
        ps->viewAngleClampBase[0] = ps->viewAngleClampBase[1] = 0.0f;
        ps->viewAngleClampRange[0] = ps->viewAngleClampRange[1] = CODOL_PLAYERLINK_MAX_ARC;
    } else {
        /* Released: back to the retained default a spawned player has. */
        ps->viewAngleClampBase[0] = ps->viewAngleClampBase[1] = 0.0f;
        ps->viewAngleClampRange[0] = ps->viewAngleClampRange[1] = 0.0f;
    }
}

qboolean CODOL_PlayerLinkViewClamp(int clientNum, float base[2], float range[2])
{
    const codolPlayerLink_t *link;

    link_init_once();
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return qfalse;
    link = &s_playerLink[clientNum];
    if(link->mode == CODOL_PLAYERLINK_NONE || !link->clampActive) return qfalse;
    if(base) { base[0] = link->clampBase[0]; base[1] = link->clampBase[1]; }
    if(range) { range[0] = link->clampRange[0]; range[1] = link->clampRange[1]; }
    return qtrue;
}

void CODOL_PlayerLinkClampView(playerState_t *ps, float previousYaw)
{
    gentity_t *ent;
    const codolPlayerLink_t *link;
    float base[2], range[2];
    int clientNum, i;

    if(!ps) return;
    clientNum = ps->clientNum;
    if(clientNum < 0 || clientNum >= MAX_CLIENTS || clientNum >= level.maxclients) return;
    ent = &g_entities[clientNum];
    /* A spectator's ps may carry the followed client's number. Never use that
     * number alone to import the live player's clamp into a copied state. */
    if(!ent->r.inuse || !ent->client || ps != &ent->client->ps || !ent->tagInfo) return;
    if(!CODOL_PlayerLinkViewClamp(clientNum, base, range)) return;
    link = &s_playerLink[clientNum];
    if(!link_live_entity(link->linkEntNum) ||
       ent->tagInfo->parent != link_live_entity(link->linkEntNum)) return;

    for(i=0;i<2;++i) {
        float difference, correction;
        if(range[i] >= 180.0f) continue;
        /* Match retained PM_UpdateViewAngles_80: yaw uses two separately
         * wrapped differences around the pre-command yaw, preserving which
         * boundary the command crossed. Pitch uses the direct difference. */
        if(i == 1) {
            float oldDifference = (float)AngleDelta(base[i], previousYaw);
            difference = (float)AngleDelta(previousYaw, ps->viewangles[i]);
            difference += oldDifference;
        } else difference = (float)AngleDelta(base[i], ps->viewangles[i]);
        if(difference > range[i]) correction = difference - range[i];
        else if(difference < -range[i]) correction = difference + range[i];
        else continue;
        ps->delta_angles[i] += correction;
        ps->viewangles[i] = (float)AngleNormalize360(base[i] +
            (correction > 0.0f ? -range[i] : range[i]));
    }
}

/* IW4 4b3f72 tests the weapon-view bit and skips the whole origin update for it:
 * that link carries only the view, and the player keeps the origin its own
 * movement produced. The retained G_RunClient has no such test and drives every
 * linked player's origin through G_SetFixedLink(ent, 2), so this predicate is
 * what its integration hunk calls. */
qboolean CODOL_PlayerLinkSuppressesFixedLink(const struct gentity_s *ent)
{
    const codolPlayerLink_t *link;
    link_init_once();
    if(!ent || !ent->r.inuse || !ent->client || !ent->tagInfo) return qfalse;
    if(ent->s.number < 0 || ent->s.number >= MAX_CLIENTS) return qfalse;
    link = &s_playerLink[ent->s.number];
    return link->mode == CODOL_PLAYERLINK_WEAPONVIEW &&
        link_live_entity(link->linkEntNum) &&
        ent->tagInfo->parent == link_live_entity(link->linkEntNum) ? qtrue : qfalse;
}

int __cdecl G_DObjGetWorldTagPos(gentity_t *, unsigned int, float *);

/* IW4 G_GetPlayerViewOrigin 0x4b6d00, the view origin nearly every game caller
 * uses (weapon fire, melee, use/cursor hints, ClientEndFrame): when the
 * playerState carries the weapon-view link bit (linkFlags & 4, set by
 * playerLinkWeaponViewToDelta at 5ef53c) the view is the linked parent's
 * tag_player, and only otherwise the turret/eye origin of the base function
 * 0x434cc0. The retained IW3 G_GetPlayerViewOrigin had only the base half, so
 * an AC-130 gunner fired its 105mm/40mm/25mm from its own body on the ground
 * (the shell burst at its feet: a self kill in games_mp.log) instead of from
 * the gunship camera its C1 client aims from. Answers the link half; 0 means
 * the caller keeps the base behaviour. IW4 raises ERR_DROP when the parent has
 * no tag_player; the link method already refused such a parent, so a parent
 * that lost its model since falls back to the base origin instead. */
int CODOL_PlayerWeaponViewOrigin(const playerState_t *ps, float *origin)
{
    const codolPlayerLink_t *link;
    gentity_t *parent;
    link_init_once();
    if(!ps || !origin || ps->clientNum < 0 || ps->clientNum >= MAX_CLIENTS) return 0;
    link = &s_playerLink[ps->clientNum];
    if(link->mode != CODOL_PLAYERLINK_WEAPONVIEW) return 0;
    parent = link_live_entity(link->linkEntNum);
    if(!parent) return 0;
    return G_DObjGetWorldTagPos(parent, scr_const.tag_player, origin) ? 1 : 0;
}

/* ------------------------------------------------------ link orientation */

/* q = a * conjugate(b): the rotation that carries b onto a. */
static void link_quat_delta(const float a[4], const float b[4], float q[4])
{
    float c[4];

    c[0] = -b[0]; c[1] = -b[1]; c[2] = -b[2]; c[3] = b[3];
    q[0] = a[3] * c[0] + a[0] * c[3] + a[1] * c[2] - a[2] * c[1];
    q[1] = a[3] * c[1] + a[1] * c[3] + a[2] * c[0] - a[0] * c[2];
    q[2] = a[3] * c[2] + a[2] * c[3] + a[0] * c[1] - a[1] * c[0];
    q[3] = a[3] * c[3] - a[0] * c[0] - a[1] * c[1] - a[2] * c[2];
}

static void link_quat_mul(const float a[4], const float b[4], float q[4])
{
    q[0] = a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1];
    q[1] = a[3] * b[1] + a[1] * b[3] + a[2] * b[0] - a[0] * b[2];
    q[2] = a[3] * b[2] + a[2] * b[3] + a[0] * b[1] - a[1] * b[0];
    q[3] = a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2];
}

static void link_quat_to_angles(const float q[4], float angles[3])
{
    vec3_t axis[3];

    QuatToAxis(q, axis);
    AxisToAngles(axis, angles);
}

/* One frame of the link's view behaviour, IW4 0x5fdbb0.
 *
 * IW4 carries the link orientation as a quaternion, not as angles. 0x5fdd05
 * forms the delta against the orientation stored at gclient+0x33fc and 0x5fdd55
 * lerps identity -> delta by gclient+0x3410 through 0x49fc30 - it is not a lerp
 * between last frame's and this frame's angles, and scaling the Euler pitch/yaw
 * difference is not the same operation once both axes turn. 0x49fc30 is the
 * sign-corrected component lerp the retained QuatLerp already implements.
 *
 * The blended rotation is composed onto the orientation of the player's own
 * viewangles and the pitch and yaw difference that produces is added to both
 * ps.viewangles and ps.delta_angles (5fddf9..5fde70). delta_angles is what makes
 * the change survive the next PM_UpdateViewAngles, which rebuilds viewangles
 * from the client's command angles plus delta_angles. Roll is not part of that
 * loop: IW4 iterates indices 0 and 1 only. */
static void link_advance_view(gentity_t *ent, codolPlayerLink_t *link,
                              vec3_t frameAxis[3])
{
    static const float s_identityQuat[4] = {0.0f, 0.0f, 0.0f, 1.0f};
    playerState_t *ps = &ent->client->ps;
    float frameQuat[4], delta[4], scaled[4];
    float viewQuat[4], rotated[4], target[3], frameAngles[3];
    int i;

    AxisToQuat(frameAxis, frameQuat);
    /* IW4 5fdbca..5fdbdb passes the current parent frame angles directly
     * to the clamp writer. The relative link reference below is separate. */
    AxisToAngles(frameAxis, frameAngles);
    link_update_clamp(link, frameAngles);

    if(!link->haveLastFrameQuat) {
        /* IW4 5fdd5f: the first frame starts from the identity rotation and
         * only records the orientation. */
        Vector4Copy(s_identityQuat, scaled);
        link->haveLastFrameQuat = qtrue;
    } else {
        link_quat_delta(frameQuat, link->lastFrameQuat, delta);
        QuatLerp(s_identityQuat, delta, link->viewRotationFraction, scaled);
    }
    Vector4Copy(frameQuat, link->lastFrameQuat);

    AnglesToQuat(ps->viewangles, viewQuat);
    link_quat_mul(scaled, viewQuat, rotated);
    link_quat_to_angles(rotated, target);

    for(i = 0; i < 2; ++i) {
        float carried = link_normalize180(target[i] - ps->viewangles[i]);

        if(carried == 0.0f) continue;
        ps->delta_angles[i] += carried;
        ps->viewangles[i] = link_normalize360(ps->viewangles[i] + carried);
    }

    /* IW4 5fde7b: the clamp reference either follows the link frame outright
     * (5fde84) or is rotated by the same blended delta (5fdea9). */
    if(link->viewLinkAbsolute) {
        link_quat_to_angles(frameQuat, link->linkAngles);
    } else {
        float refQuat[4], rotatedRef[4];

        AnglesToQuat(link->linkAngles, refQuat);
        link_quat_mul(scaled, refQuat, rotatedRef);
        link_quat_to_angles(rotatedRef, link->linkAngles);
    }
}

/* Shared core, the equivalent of IW4 5ef3d0. Validate script arguments before
 * entering the native linker. G_EntLinkToInternal unlinks the old attachment
 * before checking the replacement tag/cycle, so a native failure must also
 * release our old player-link record and view lock. Camera/controls are separate. */
/* Which script method reached player_link_core. IW4 registers playerLinkTo,
 * playerLinkToDelta, playerLinkToAbsolute and playerLinkWeaponViewToDelta as
 * separate receivers over one record; C1 keeps the same split (0x53ae2b..,
 * 0x53b2e0.., 0x53ad7a..). */
typedef enum {
    LINK_VARIANT_PLAIN = 0,
    /* playerLinkToDelta: keep the origin delta to the tag (C1 0x53b559 bit 2
     * "linked offset"), parameter 7 = useTagAngles. */
    LINK_VARIANT_DELTA = 1,
    /* playerLinkToAbsolute: view follows the frame completely and the
     * angles lock (C1 0x53b359..0x53b38e). Only <entity> [, <tag>]. */
    LINK_VARIANT_ABSOLUTE = 2
} linkVariant_t;

static void player_link_core(scr_entref_t entref, codolPlayerLinkMode_t mode, linkVariant_t variant)
{
    gentity_t *ent, *linkEnt;
    codolPlayerLink_t pending;
    unsigned int tagName = 0;
    int numParam;
    float axis[3][3], frameOrigin[3], delta[3], localOffset[3], clampAngles[3];
    float zeroAngles[3] = {0.0f, 0.0f, 0.0f};
    qboolean haveFrame, withOffset = qfalse;

    ent = link_player(entref);
    if(!ent) return;

    numParam = Scr_GetNumParam();
    if(numParam < 1) {
        Scr_Error("playerLinkTo requires a link entity");
        return;
    }
    linkEnt = Scr_GetEntity(0);
    if(!linkEnt) return;
    if(linkEnt == ent) {
        Scr_ParamError(0, "a player cannot be linked to itself");
        return;
    }

    if(numParam > 1) {
        tagName = Scr_GetConstLowercaseString(1);
        if(tagName == scr_const.emptystring) tagName = 0;
    }
    if(mode == CODOL_PLAYERLINK_WEAPONVIEW && tagName != scr_const.tag_player) {
        /* IW4 0x6e1180, reached at 5ef50b before anything is written. */
        Scr_Error("This function only supports linking to tags named 'tag_player'.");
        return;
    }

    pending = s_playerLink[ent->s.number];
    link_clear_player_part(&pending);
    pending.mode = mode;
    pending.linkEntNum = linkEnt->s.number;
    /* IW4 reads a float at parameter 2 (5ef5cb) and four arcs at 3..6. The
     * script call `PlayerLinkWeaponviewToDelta( level.ac130, "tag_player", 1.0,
     * 35, 35, 35, 35 )` in `maps/mp/killstreaks/_ac130.gsc:865` fixes that
     * layout. Parameter 2 is the fraction of the link's rotation the view
     * follows; an absent parameter is zero, not one (IW4 5ef5dc, C1 53ae46). */
    if(variant == LINK_VARIANT_ABSOLUTE) {
        /* C1 0x53b35f fld1 -> gclient+0x3768; no arcs are read and the
         * view is not clamped (0x53b36d sets the no-clamp flag). */
        pending.viewRotationFraction = 1.0f;
        pending.rightArc = pending.leftArc = pending.topArc = pending.bottomArc = CODOL_PLAYERLINK_MAX_ARC;
    } else {
        pending.viewRotationFraction = numParam > 2 ? Scr_GetFloat(2) : 0.0f;
        pending.rightArc = link_arc_param(3, numParam);
        pending.leftArc = link_arc_param(4, numParam);
        pending.topArc = link_arc_param(5, numParam);
        pending.bottomArc = link_arc_param(6, numParam);
    }
    /* Parameter 7 lands in a different byte per mode, and IW4 hard-codes the
     * other byte: playerLinkTo sets the absolute-reference byte and takes the
     * parameter as the collision flag (5ef59b..5ef5c1), while
     * playerLinkWeaponViewToDelta clears the collision byte and takes the
     * parameter as the absolute-reference flag (5ef540..5ef56a). C1 repeats both
     * assignments at 53ae05..53ae25 and 53adc1..53adcb. */
    if(mode == CODOL_PLAYERLINK_WEAPONVIEW) {
        pending.collideWhileLinked = qfalse;
        pending.viewLinkAbsolute = (numParam > 7 && Scr_GetInt(7)) ? qtrue : qfalse;
        /* IW4 5ef518 / C1 53ad7a keep the view the player had at link time as
         * the delta the weapon view is expressed against. */
        VectorCopy(ent->client->ps.viewangles, pending.weaponViewAngles);
    } else if(variant == LINK_VARIANT_DELTA) {
        /* IW4 playerLinkToDelta: parameter 7 is useTagAngles, no collision. */
        pending.collideWhileLinked = qfalse;
        pending.viewLinkAbsolute = (numParam > 7 && Scr_GetInt(7)) ? qtrue : qfalse;
    } else if(variant == LINK_VARIANT_ABSOLUTE) {
        /* C1 0x53b38e byte +0x3765 = 1, +0x3767 stays the playerLinkTo default;
         * 0x53b37a locks the angles and 0x53b384 clears the weapon-view bit. */
        pending.collideWhileLinked = qfalse;
        pending.viewLinkAbsolute = qtrue;
        pending.anglesLocked = qtrue;
    } else {
        pending.collideWhileLinked = (numParam > 7 && Scr_GetInt(7)) ? qtrue : qfalse;
        pending.viewLinkAbsolute = qtrue;
    }

    haveFrame = link_frame(linkEnt, tagName, axis, frameOrigin);
    /* playerLinkToDelta keeps the player's current offset from the tag, the
     * same delta the weapon-view link keeps (C1 0x53b559 sets the offset bit). */
    if(variant == LINK_VARIANT_DELTA && haveFrame) {
        VectorSubtract(ent->client->ps.origin, frameOrigin, delta);
        link_world_to_local((const float (*)[3])axis, delta, localOffset);
        pending.offsetEnabled = qtrue;
        withOffset = qtrue;
    }

    /* IW4 mode 2 records the player's origin at link time and treats it as the
     * delta the link is expressed against (5ef518), so the gunship seat does not
     * teleport the player onto the tag. The same delta is kept here, projected
     * into the link frame so it stays correct while the platform rotates. */
    if(mode == CODOL_PLAYERLINK_WEAPONVIEW && haveFrame) {
        VectorSubtract(ent->client->ps.origin, frameOrigin, delta);
        link_world_to_local((const float (*)[3])axis, delta, localOffset);
        pending.offsetEnabled = qtrue;
        withOffset = qtrue;
    }

    if(withOffset) {
        if(!G_EntLinkToWithOffset(ent, linkEnt, tagName, localOffset, zeroAngles)) {
            link_release_player(ent->s.number, qfalse);
            Scr_Error(va("failed to link player to entity %i", linkEnt->s.number));
            return;
        }
    } else if(!G_EntLinkTo(ent, linkEnt, tagName)) {
        link_release_player(ent->s.number, qfalse);
        /* The same failure the retained ScrCmd_LinkTo reports: the target has no
         * model, or its model does not carry the requested tag. */
        if(tagName && SV_DObjExists(linkEnt)) {
            Scr_Error(va("failed to link player to entity %i: no tag \"%s\"",
                         linkEnt->s.number, SL_ConvertToString(tagName)));
        } else {
            Scr_Error(va("failed to link player to entity %i", linkEnt->s.number));
        }
        return;
    }

    /* IW4 4fdb80 establishes the reference angles the clamp is expressed
     * against right after the link succeeds, choosing the frame the player is
     * actually attached to when the absolute byte is set (4fdb97..4fdbc7) and
     * the parent entity's own angles when it is clear (4fdbd4..4fdbf8). */
    if(pending.viewLinkAbsolute && haveFrame) {
        AxisToAngles((vec3_t *)axis, pending.linkAngles);
        VectorCopy(pending.linkAngles, clampAngles);
    } else {
        /* IW4 4fdbda..4fdbf8 starts the relative reference at zero while
         * initializing the clamp from the parent's world angles. */
        VectorClear(pending.linkAngles);
        VectorCopy(linkEnt->r.currentAngles, clampAngles);
    }
    /* IW4 5ef718 clears the previous-orientation marker. The first frame
     * records the parent orientation and applies an identity delta, even if
     * the parent moved between this script call and the next frame. */
    pending.haveLastFrameQuat = qfalse;

    s_playerLink[ent->s.number] = pending;
    link_update_clamp(&s_playerLink[ent->s.number], clampAngles);
    link_publish_clamp(ent, &s_playerLink[ent->s.number]);
    /* C1 0x53add3..0x53adf7: a weapon-view link clears this player's bit in
     * the link entity's clientMask. C1 renders that view from the entity's own
     * tag_player (CG 0x476280, "Weaponview linked entity (#%i) is not in local
     * client #%i's snapshot"), so the entity must reach the linked player even
     * when script has hidden it - the AC-130 rig is spawned with hide(). The
     * bit is not restored on unlink, as in C1. */
    if(mode == CODOL_PLAYERLINK_WEAPONVIEW && ent->s.number < 64)
        linkEnt->r.clientMask[ent->s.number >> 5] &= ~(1 << (ent->s.number & 31));
    /* No position is published here. G_RunClient already advances every linked
     * player: _g_active_mp.asm:138..183 sets the linked pm_type, calls
     * G_SetFixedLink(ent, 2) - which transforms tagInfo+0x34 through the parent
     * axis into r.currentOrigin and leaves the angles alone (_g_utils_mp.asm
     * G_SetFixedLink_20) - then G_SetOrigin, G_SetAngle, SV_LinkEntity and the
     * copy into ps.origin. A second link/publish here would duplicate that. The
     * weapon-view link needs the opposite: G_RunClient must be told to skip that
     * block, which CODOL_PlayerLinkSuppressesFixedLink exists for. */
}

void CODOL_PlayerCmd_PlayerLinkTo(scr_entref_t entref)
{
    player_link_core(entref, CODOL_PLAYERLINK_VIEW, LINK_VARIANT_PLAIN);
}

void CODOL_PlayerCmd_PlayerLinkToDelta(scr_entref_t entref)
{
    player_link_core(entref, CODOL_PLAYERLINK_VIEW, LINK_VARIANT_DELTA);
}

void CODOL_PlayerCmd_PlayerLinkToAbsolute(scr_entref_t entref)
{
    player_link_core(entref, CODOL_PLAYERLINK_VIEW, LINK_VARIANT_ABSOLUTE);
}

void CODOL_PlayerCmd_PlayerLinkWeaponViewToDelta(scr_entref_t entref)
{
    player_link_core(entref, CODOL_PLAYERLINK_WEAPONVIEW, LINK_VARIANT_PLAIN);
}

/* C1 53b490..53b561 requires a player with tagInfo and sets mask 2 in
 * playerState+14. The handler does not resolve a transform or change position;
 * the movement consumer of this flag must be implemented separately. */
void CODOL_PlayerCmd_PlayerLinkedOffsetEnable(scr_entref_t entref)
{
    gentity_t *ent = link_player(entref);
    if(!ent) return;
    /* C1 53b514 checks tagInfo; 53b559 only sets the playerState flag.
     * Ordinary entity links satisfy this guard too. No relink or teleport. */
    if(!ent->tagInfo) {
        Scr_Error("Player is not linked.");
        return;
    }
    s_playerLink[ent->s.number].offsetEnabled = qtrue;
}

/* C1 53b570..53b641: same receiver/tagInfo check, then clear bit 2.
 * Movement consuming this flag is separate from the script setter. */
void CODOL_PlayerCmd_PlayerLinkedOffsetDisable(scr_entref_t entref)
{
    gentity_t *ent = link_player(entref);
    if(!ent) return;
    if(!ent->tagInfo) {
        Scr_Error("Player is not linked.");
        return;
    }
    s_playerLink[ent->s.number].offsetEnabled = qfalse;
}

/* C1 0x5481d0 takes the entity in parameter 0 and the tag in parameter 1, sets
 * playerState 0x10 bit 1, stores the entity number at 0x54 and the registered
 * tag index at 0x58. The index comes from C1 0x570650, which allocates a slot in
 * a 64-entry table and publishes the name as configstring 0x14b3 + index; this
 * server's CODOL_CS_TAGS/CODOL_TAG_SLOTS model the same table.
 * `maps/mp/killstreaks/_remotemissile.gsc:217` calls
 * `player CameraLinkTo( rocket, "tag_origin" )`. */
void CODOL_PlayerCmd_CameraLinkTo(scr_entref_t entref)
{
    gentity_t *ent, *cameraEnt;
    codolPlayerLink_t *link;
    const char *tagText;
    int slot, recipient;

    ent = link_player(entref);
    if(!ent) return;
    if(Scr_GetNumParam() < 2) {
        Scr_Error("cameraLinkTo requires an entity and a tag");
        return;
    }
    cameraEnt = Scr_GetEntity(0);
    if(!cameraEnt) return;
    if(cameraEnt->s.number < 0 || cameraEnt->s.number >= CODOL_WIRE_ENTITYNUM_NONE) {
        Scr_ParamError(0, "entity number cannot be published");
        return;
    }
    /* C1 54825c calls the ordinary string getter, then 570650 registers
     * the name without looking up a server DObj. Empty names map to slot0
     * (570726), and case must not be rewritten by the script wrapper. */
    tagText = Scr_GetString(1);
    slot = tagText && *tagText ?
        CODOL_RegisterInheritedTagName(CODOL_ServerConfigstrings(),
            CODOL_ServerInheritedConfigstrings(), tagText) : 0;
    if(slot < 0 || slot >= CODOL_TAG_SLOTS) {
        Scr_Error(va("cameraLinkTo: no free tag slot for \"%s\"", tagText));
        return;
    }
    /* A slot that was allocated now has to reach clients that already own a
     * gamestate, the same way the other late asset names are delivered. */
    for(recipient = 0; recipient < sv_maxclients->integer && recipient < MAX_CLIENTS;
        ++recipient) {
        client_t *target = &svs.clients[recipient];

        if(slot && target->state >= CS_PRIMED && target->gamestateSent) {
            SV_SendServerCommandNoLoss(target, "d %u %s",
                                       (unsigned)(CODOL_CS_TAGS + slot), tagText);
        }
    }

    link = &s_playerLink[ent->s.number];
    link->cameraEntNum = cameraEnt->s.number;
    link->cameraTagIndex = slot;
    /* C1 548274 sets80 when VM argument count >1. The required tag is arg1,
     * so every successful call sets it. CameraUnlink clears only bit2. */
    link->cameraFlags |= UINT32_C(0x82);
}

/* C1 0x548290 clears the flag unconditionally and complains about nothing;
 * `_remotemissile.gsc` relies on that when it cleans up after a missile that has
 * already ended. It also leaves 0x54 and 0x58 behind, which the overlay
 * reproduces. */
void CODOL_PlayerCmd_CameraUnlink(scr_entref_t entref)
{
    gentity_t *ent;

    ent = link_player(entref);
    if(!ent) return;
    s_playerLink[ent->s.number].cameraFlags &= ~UINT32_C(2);
}

/* C1 0x5483c0 refuses a second link with "Player's controls are already linked."
 * (0xc5837c), sets playerState 0xc bit 0x80000, stores the entity number at
 * 0x5c and records the controlling player on the entity itself (0x54848f writes
 * an entity handle at gentity+0x248, which 0x54850a reads back on release). */
void CODOL_PlayerCmd_ControlsLinkTo(scr_entref_t entref)
{
    gentity_t *ent, *controlEnt;
    codolPlayerLink_t *link;

    ent = link_player(entref);
    if(!ent) return;
    /* Let the VM entity getter diagnose missing/wrong parameter zero, as
     * C1 5483de does, before inspecting the player's existing link. */
    controlEnt = Scr_GetEntity(0);
    if(!controlEnt) return;
    /* C1 5483de..548441 resolves parameter0 before checking linked state.
     * Preserve VM error order; current target liveness is not that flag. */
    link = &s_playerLink[ent->s.number];
    if(link->controlsEntNum != ENTITYNUM_NONE) {
        Scr_Error("Player's controls are already linked.");
        return;
    }
    if(controlEnt->s.number < 0 || controlEnt->s.number >= MAX_GENTITIES) {
        Scr_ParamError(0, "invalid controls entity number");
        return;
    }
    /* C1 548480..54849a sets the target handle without self/owner guards.
     * EntHandle::setEnt at507f40 replaces an existing owner association;
     * the previous player's forward controls link is left intact. */
    link->controlsEntNum = controlEnt->s.number;
    s_entityController[controlEnt->s.number] = (short)ent->s.number;
    /* C1 54849a..5484a0: missile-only remote mode, separate from owner. */
    if(controlEnt->s.eType == ET_MISSILE)
        CODOL_SetMissileRemoteMode((unsigned)controlEnt->s.number, 1);
}

/* C1 0x5484c0 warns rather than errors when nothing was linked (0xc583a8,
 * channel 0x1a), releases the entity's controller handle and resets the
 * playerState field to 0x7ff. */
void CODOL_PlayerCmd_ControlsUnlink(scr_entref_t entref)
{
    gentity_t *ent;
    codolPlayerLink_t *link;

    ent = link_player(entref);
    if(!ent) return;
    link = &s_playerLink[ent->s.number];
    if(link->controlsEntNum == ENTITYNUM_NONE) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
                         "ControlsUnlink() called on a player who's controls were not linked.\n");
        return;
    }
    /* Script unlink is unconditional for a live target (C1 548501..54855f),
     * even if another player has since replaced its owner. Client reset's
     * link_drop_controls intentionally only drops that client's own handle. */
    if(link_live_entity(link->controlsEntNum)) {
        s_entityController[link->controlsEntNum] = -1;
        /* C1 54855f..548565 clears the missile flag even if its owner handle
         * was already absent. Owner dissociation alone does not do this. */
        if(g_entities[link->controlsEntNum].s.eType == ET_MISSILE)
            CODOL_SetMissileRemoteMode((unsigned)link->controlsEntNum, 0);
    }
    link->controlsEntNum = ENTITYNUM_NONE;
}

/* The retained "unlink" method releases a tag link. A linked player also has
 * playerState state to release, which the retained handler knows nothing about,
 * so the registration wrapper calls this first. The camera and controls links
 * are not affected: C1 has separate methods for them. */
qboolean CODOL_PlayerLinkUnlinkReceiver(scr_entref_t entref)
{
    link_init_once();
    if(entref.classnum) return qfalse;
    if(entref.entnum >= MAX_CLIENTS) return qfalse;
    if(CODOL_RemoteVehicleScriptExit(entref.entnum)) return qtrue;
    if(s_playerLink[entref.entnum].mode == CODOL_PLAYERLINK_NONE) return qfalse;
    link_release_player((int)entref.entnum, qtrue);
    return qtrue;
}

/* ------------------------------------------------------------------- frame */

/* One linked player, advanced once per server frame.
 *
 * IW4 runs this from the tag-link update rather than from the client think:
 * 0x4b3ee0 resolves the frame the player is attached to (0x4a16b0, the tag
 * matrix when the link uses a tag and the parent's angles otherwise), calls the
 * view update at 0x4b3f6a and, unless the weapon-view flag is set, the origin
 * update and its publication at 0x4b3f84/0x4b3f8a. The order matters: the view
 * clamp is refreshed from the link's new orientation before the movement code
 * that consumes it runs, and the origin is published in the same pass.
 *
 * G_RunClient invokes this after the parent frame and before its existing
 * G_SetFixedLink position publication. Synchronous client think has already
 * run; subsequent command processing consumes the refreshed view clamp. */
void CODOL_PlayerLinkRunFrame(struct gentity_s *ent)
{
    codolPlayerLink_t *link;
    gentity_t *linkEnt;
    float axis[3][3], frameOrigin[3];
    int clientNum;

    link_init_once();
    if(!ent || !ent->r.inuse || !ent->client) return;
    clientNum = ent->s.number;
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return;
    if(ent->client->ps.clientNum != clientNum ||
       (ent->client->sess.sessionState != SESS_STATE_PLAYING &&
        ent->client->sess.sessionState != SESS_STATE_DEAD)) return;
    link = &s_playerLink[clientNum];
    if(link->mode == CODOL_PLAYERLINK_NONE) return;

    linkEnt = link_live_entity(link->linkEntNum);
    if(!linkEnt || !ent->tagInfo || ent->tagInfo->parent != linkEnt) {
        /* The link was dropped underneath this module, for instance by a script
         * calling the retained unlink on the entity side. */
        link_release_player(clientNum, qfalse);
        return;
    }

    /* IW4 4b3ee0 reads the frame through the live tag; link_current_tag reads
     * back the tag the retained tagInfo record actually holds, so a relink that
     * changed the tag is followed without this module keeping its own string. */
    if(!link_frame(linkEnt, link_current_tag(ent), axis, frameOrigin)) {
        float entAxis[4][3];

        AnglesToAxis(linkEnt->r.currentAngles, entAxis);
        VectorCopy(entAxis[0], axis[0]);
        VectorCopy(entAxis[1], axis[1]);
        VectorCopy(entAxis[2], axis[2]);
    }
    if(link->offsetEnabled) {
        float composedAxis[3][3];

        /* IW4 4b3eec..4b3f05 composes the retained local link transform
         * with the live parent/tag frame before updating view and clamps.
         * MatrixMultiply requires a separate destination. */
        MatrixMultiply(ent->tagInfo->axis, axis, composedAxis);
        VectorCopy(composedAxis[0], axis[0]);
        VectorCopy(composedAxis[1], axis[1]);
        VectorCopy(composedAxis[2], axis[2]);
    }
    link_advance_view(ent, link, (vec3_t *)axis);
    link_publish_clamp(ent, link);
}

/* -------------------------------------------------------------- registration */

void CODOL_ScriptStartupExtra_Register(void)
{
    Scr_AddMethod("playerlinkto", CODOL_PlayerCmd_PlayerLinkTo, qfalse);
    Scr_AddMethod("playerlinktodelta", CODOL_PlayerCmd_PlayerLinkToDelta, qfalse);
    Scr_AddMethod("playerlinktoabsolute", CODOL_PlayerCmd_PlayerLinkToAbsolute, qfalse);
    Scr_AddMethod("playerlinkweaponviewtodelta",
                  CODOL_PlayerCmd_PlayerLinkWeaponViewToDelta, qfalse);
    Scr_AddMethod("playerlinkedoffsetenable",
                  CODOL_PlayerCmd_PlayerLinkedOffsetEnable, qfalse);
    Scr_AddMethod("playerlinkedoffsetdisable",
                  CODOL_PlayerCmd_PlayerLinkedOffsetDisable, qfalse);
}

#endif /* CODOL_SERVER */
