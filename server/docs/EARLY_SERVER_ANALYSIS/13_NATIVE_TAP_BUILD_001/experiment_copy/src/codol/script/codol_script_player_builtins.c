/* Native CoDOL player builtins. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * References: iw4x.exe (IW4) builtin tables and handlers, C1.exe 1.1.1.13
 * (SHA-256 d99061...390d) handlers located through their error strings, and
 * the IW4 gametype scripts under alpha0022/vendor/iw4. C1 wins wherever the
 * two disagree, because C1 is what receives the wire. Offline inspection only;
 * nothing here has run against a client.
 */
#ifdef CODOL_SERVER
#include "codol_weapon_bits.h"
#include "codol_script_player_builtins.h"
#include "scr_vm_functions.h"
#include "server.h"
#include "g_shared.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"
#include "cvar.h"
#include "q_math.h"
#include "xassets/weapondef.h"
#include "codol_playerstate_ext.h"
#include "codol_weapon_flags.h"
#include "codol_animation_tables.h"
#include "codol_profile.h"
#include "codol_usercmd.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

/* Retained item primitives (src/asmsource/_g_items.asm). bg_itemlist is the
 * table in _bg_misctables.asm: four-byte entries indexed by the item index,
 * weapon + CODOL_ITEM_STRIDE * weapon model (codol_weapon_slots.h), exactly as
 * PlayerCmd_dropItem indexes it. */
struct gitem_s;
gentity_t *__cdecl Drop_Item(gentity_t *ent, const struct gitem_s *item, float angle, int flags);
extern unsigned char bg_itemlist[];
/* The active animation script owner, NULL until mp/playeranim.script parsed. */
extern struct bgs_s *bgs;
/* Retained src/asmsource/_bg_animation_mp.asm:3955; bg_local.h cannot be
 * included on its own (it expects pml_t from bg_public.h's includes). */
int __cdecl BG_AnimScriptEvent(playerState_t *ps, int event, int isContinue, int force);
#define CODOL_ANIM_ET_DEATH 1 /* bg_local.h ANIM_ET_DEATH */
/* Means-of-death indices of the retained modNames table (g_combat_mp.cpp:4);
 * the meansOfDeath_t enum in g_shared.h sits inside a comment block. */
enum {
    NATIVE_MOD_GRENADE = 3, NATIVE_MOD_GRENADE_SPLASH = 4, NATIVE_MOD_PROJECTILE = 5,
    NATIVE_MOD_PROJECTILE_SPLASH = 6, NATIVE_MOD_EXPLOSIVE = 14, NATIVE_MOD_COUNT = NATIVE_DAMAGE_MOD_COUNT
};

/* ---------------------------------------------------------------------- */
/* Receiver validation shared by every method.                             */
/* ---------------------------------------------------------------------- */

/* IW4 0x5f03b0..0x5f03f0 and C1 0x53c8f0..0x53c936 (thermal), and all the
 * other handlers here: classnum != 0 -> "not an entity"; entity without a
 * client -> "entity %i is not a player". Both are object errors. */
static gentity_t *player_entity(scr_entref_t ref)
{
    if(ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if(ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return NULL;
    }
    return &g_entities[ref.entnum];
}

/* IW4 GetPlayerEntity (0x4bc270) variants raise a plain script error with a
 * builtin-specific text instead of the object error above. */
static gentity_t *player_entity_message(scr_entref_t ref, const char *message)
{
    if(ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if(ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients ||
       !g_entities[ref.entnum].client) {
        Scr_Error(message);
        return NULL;
    }
    return &g_entities[ref.entnum];
}

/* MSVC _ftol2 (C1 0xae0410) and IW4's SSE conversion (0x6b5240) both truncate
 * toward zero and yield the integer indefinite 0x80000000 for a value that is
 * not finite or does not fit. */
static int truncate_to_int(float value)
{
    double truncated;
    if(value != value) return INT_MIN;
    truncated = trunc((double)value);
    if(!(truncated >= -2147483648.0) || !(truncated <= 2147483647.0)) return INT_MIN;
    return (int)truncated;
}

/* C1 0x5433c0..0x5433dc and IW4 0x5f3418..0x5f3437: seconds * 1000.0, stored
 * back to single, plus 2^-30, then fistp under round-to-nearest. */
static int seconds_to_milliseconds(float seconds)
{
    volatile float scaled = (float)((double)seconds * 1000.0);
    double rounded;
    if(scaled != scaled) return INT_MIN;
    rounded = nearbyint((double)scaled + 0x1p-30);
    if(!(rounded >= -2147483648.0) || !(rounded <= 2147483647.0)) return INT_MIN;
    return (int)rounded;
}

/* ---------------------------------------------------------------------- */
/* GetThirdPersonCrosshairOffset                                           */
/* ---------------------------------------------------------------------- */

/* IW4 0x5df5a0: player receiver; if the camera_thirdPerson dvar (0x7ab3fc) is
 * false -> Scr_Error("Can not be called if 'camera_thirdPerson' dvar is
 * false"); otherwise Scr_AddFloat(0x445830(client)), which returns 0.0 when
 * 0x41c210 (the same dvar bool) is false and otherwise the float value of
 * camera_thirdPersonCrosshairOffset (0x7add1c; registered at 0x447b61 with
 * default 0.35, min -1, max 1, flags 4, "Amount to vertically offset the
 * crosshair from the center when in third person").
 *
 * C1 0x51e740 is the same handler over C1's numeric dvar names: "99" (bool,
 * flags 0xcc, registered at 0x40b064 -> 0x1509d58) is camera_thirdPerson and
 * "105" (float 0.35, -1..1, flags 4, registered at 0x40b181 -> 0x150c66c) is
 * the crosshair offset; the error string is at 0xc5389c. C1's value helper
 * 0x40ebf0 additionally answers 0.0 for a spectating or intermission
 * playerState (C1 pm_type 5/6, i.e. retained PM_SPECTATOR 4 / PM_INTERMISSION
 * 5), and for four more view states (ps+0x10 & 2, ps+0x14 & 4, ps.eFlags &
 * 0x100000, and helper 0x421ed0 with ps+0x348 == 1.0) whose retained
 * counterparts are not resolved and are not imitated. */
static cvar_t *camera_thirdPerson;
static cvar_t *camera_thirdPersonCrosshairOffset;

static void register_camera_dvars(void)
{
    if(!camera_thirdPerson)
        camera_thirdPerson = Cvar_RegisterBool("camera_thirdPerson", qfalse, 0,
            "Enable third-person camera");
    if(!camera_thirdPersonCrosshairOffset)
        camera_thirdPersonCrosshairOffset = Cvar_RegisterFloat("camera_thirdPersonCrosshairOffset",
            0.35f, -1.0f, 1.0f, 0,
            "Amount to vertically offset the crosshair from the center when in third person");
}

void CODOL_Scr_GetThirdPersonCrosshairOffset(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    const playerState_t *ps;
    if(!ent) return;
    register_camera_dvars();
    if(!camera_thirdPerson || !camera_thirdPerson->boolean) {
        Scr_Error("Can not be called if 'camera_thirdPerson' dvar is false");
        return;
    }
    ps = &ent->client->ps;
    /* C1 0x40ebfb..0x40ec06: spectator and intermission states read 0. */
    if(ps->pm_type == 5 || ps->pm_type == 6) { Scr_AddFloat(0.0f); return; }
    Scr_AddFloat(camera_thirdPersonCrosshairOffset ? camera_thirdPersonCrosshairOffset->value : 0.0f);
}

/* ---------------------------------------------------------------------- */
/* GetRestedTime                                                           */
/* ---------------------------------------------------------------------- */

/* IW4 0x5f9880: GetPlayerEntity; no client -> Scr_Error("setstat: entity must
 * be a player entity"); sess.connected (client+0x3148) != CON_CONNECTED (2)
 * -> Scr_ObjectError(va("cannot read persistent data: player has not finished
 * connecting, or ExitLevel has been called. (%s, %d)", name, connected));
 * then Scr_AddInt(0x5f9520(ent)). 0x5f9520 reads the stats field
 * "lastPlayedTime" (0x4a1fc0, StructuredData over the 0x1ffc-byte stats
 * buffer) and returns 0 when it is zero, otherwise now - lastPlayedTime, with
 * now from 0x473ce0: SYSTEMTIME seconds since 1970-01-01, i.e. Unix time.
 * lastPlayedTime is written by 0x462a10, called only from LiveStorage_EndGame
 * (0x468830, "LiveStorage_EndGame called when not in a game").
 *
 * C1 keeps the same "cannot read persistent data" gate (0x551510, reading
 * sess.connected at gclient+0x33a4) but its playerdata schema has no
 * lastPlayedTime field (no such string in C1.exe), so C1's own reader could
 * not be located. The native ledger below reproduces IW4's contract over the
 * trusted profile uid; it lives in server memory only. */
#define LAST_PLAYED_ENTRIES 256
static struct { uint64_t uid; int64_t seconds; } last_played[LAST_PLAYED_ENTRIES];
static unsigned last_played_next;

static int64_t unix_seconds(void)
{
    time_t now = time(NULL);
    return now == (time_t)-1 ? 0 : (int64_t)now;
}

static int64_t last_played_lookup(uint64_t uid)
{
    unsigned i;
    if(!uid) return 0;
    for(i = 0; i < LAST_PLAYED_ENTRIES; ++i)
        if(last_played[i].uid == uid) return last_played[i].seconds;
    return 0;
}

void CODOL_RecordPlayerLastPlayedTime(unsigned client)
{
    uint64_t uid = 0;
    unsigned i;
    int64_t now;
    if(client >= MAX_CLIENTS || !CODOL_ClientSecureProfile(client, &uid) || !uid) return;
    now = unix_seconds();
    if(!now) return;
    for(i = 0; i < LAST_PLAYED_ENTRIES; ++i)
        if(last_played[i].uid == uid) { last_played[i].seconds = now; return; }
    last_played[last_played_next].uid = uid;
    last_played[last_played_next].seconds = now;
    last_played_next = (last_played_next + 1) % LAST_PLAYED_ENTRIES;
}

void CODOL_RecordAllPlayersLastPlayedTime(void)
{
    int i;
    for(i = 0; i < level.maxclients && i < MAX_CLIENTS; ++i)
        if(g_entities[i].client && g_entities[i].client->sess.connected == CON_CONNECTED)
            CODOL_RecordPlayerLastPlayedTime((unsigned)i);
}

int CODOL_PlayerRestedSeconds(unsigned client)
{
    uint64_t uid = 0;
    int64_t last, delta;
    if(client >= MAX_CLIENTS || !CODOL_ClientSecureProfile(client, &uid)) return 0;
    last = last_played_lookup(uid);
    if(!last) return 0;
    delta = unix_seconds() - last;
    if(delta < 0) return 0;
    return delta > INT_MAX ? INT_MAX : (int)delta;
}

static int persistent_data_readable(gentity_t *ent)
{
    if(ent->client->sess.connected != CON_CONNECTED) {
        Scr_ObjectError(va("cannot read persistent data: player has not finished connecting, "
                           "or ExitLevel has been called. (%s, %d)",
                           ent->client->sess.newnetname, (int)ent->client->sess.connected));
        return 0;
    }
    return 1;
}

void CODOL_Scr_GetRestedTime(scr_entref_t ref)
{
    gentity_t *ent = player_entity_message(ref, "setstat: entity must be a player entity");
    if(!ent) return;
    if(!persistent_data_readable(ent)) return;
    Scr_AddInt(CODOL_PlayerRestedSeconds(ref.entnum));
}

/* ---------------------------------------------------------------------- */
/* IsUsingOnlineDataOffline                                                */
/* ---------------------------------------------------------------------- */

/* IW4 0x5f94e0: GetPlayerEntity; no client -> Scr_Error("setstat: entity must
 * be a player entity"); Scr_AddInt((byte)0x46b710(clientNum)), where 0x46b710
 * is byte [0x321ae88 + client*0xa6790], a per-controller Live session member
 * with no writer anywhere in iw4x.exe (its only reference is this reader).
 * The IW4 scripts use it once: _utility.gsc rankingEnabled() returns
 * level.rankedMatch && !usingOnlineDataOffline. The native flag is a session
 * byte raised by the profile owner when a client's online-format persistent
 * data cannot be written back; nothing raises it yet, so it reads false. */
static unsigned char online_data_offline[MAX_CLIENTS];

void CODOL_SetClientUsingOnlineDataOffline(unsigned client, int offline)
{
    if(client < MAX_CLIENTS) online_data_offline[client] = offline ? 1 : 0;
}

void CODOL_ResetClientOnlineDataFlag(unsigned client)
{
    if(client < MAX_CLIENTS) online_data_offline[client] = 0;
}

void CODOL_Scr_IsUsingOnlineDataOffline(scr_entref_t ref)
{
    gentity_t *ent = player_entity_message(ref, "setstat: entity must be a player entity");
    if(!ent) return;
    Scr_AddInt(online_data_offline[ref.entnum]);
}

/* ---------------------------------------------------------------------- */
/* PredictStreamPos                                                        */
/* ---------------------------------------------------------------------- */

/* C1 0x51d770: player receiver, Scr_GetVector(0), three _ftol2 conversions
 * (z, y, x in that order), _snprintf(buf, 0x40, "%c %i %i %i", 'U', x, y, z)
 * and 0x5d4880(0, "", buf) to that client - command type 0, the same type
 * IW4's 0x5decb0 uses for its "X %i %i %i". No argument-count check, no
 * return, the angles parameter is never read. C1's receiver for 'U'
 * (dispatcher 0x469320, table 0x46a118, target 0x46a013) is the dispatcher's
 * common epilogue, so a C1 client accepts the command and does nothing with
 * it; IW4's 'X' is "Unknown client game command" on C1 and is not sent. */
void CODOL_Scr_PredictStreamPos(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    vec3_t origin;
    char command[64];
    if(!ent) return;
    Scr_GetVector(0, origin);
    snprintf(command, sizeof(command), "%c %i %i %i", 'U',
             truncate_to_int(origin[0]), truncate_to_int(origin[1]), truncate_to_int(origin[2]));
    SV_GameSendServerCommand(ent->s.number, 0, command);
}

/* ---------------------------------------------------------------------- */
/* PlayerForceDeathAnim                                                    */
/* ---------------------------------------------------------------------- */

/* IW4 0x453670 / C1 0x555980: GetPlayerEntity, no client -> Scr_Error("Must be
 * called on a player."); arguments Scr_GetEntity(0) inflictor,
 * Scr_GetConstString(1) means of death, Scr_GetString(2) weapon name ->
 * G_GetWeaponIndexForName, hit location constant (3), Scr_GetVector(4);
 * then the core (IW4 0x416dc0, C1 0x520cf0) sets three animation conditions
 * on the victim and forces the death event.
 *
 * C1 0x520cf0 writes clientConditions[client][10..12] (0x6c3d284 + 0x92c70 +
 * client*0xb50 + 8*condition; the native names are damagetype, hitlocation and
 * hitdirection in codol_animation_conditions.inc):
 *   0x520990 damagetype: weapon offhandClass == FRAG (def+0x354 == 1):
 *            inflictor within 6400 (squared, 0xc84810) -> 2 (damage_explosion)
 *            else 1 (damage_explosion_light); otherwise means of death 3..7 or
 *            15 (the explosive family) -> 2; otherwise weapClass rocket
 *            launcher (def+0x344 == 4) -> 2, else 0 (damage_bullet).
 *   0x520af0 hitlocation: helmet/head -> 1 (hit_head), neck/torso_upper -> 2
 *            (hit_neck), legs and feet 12..17 -> 3 (hit_legs), else 0.
 *   0x520b60 hitdirection: forward from the victim's angles (ent+0x14c/+0x150
 *            through fsincos), dot = fwd.xy . dir.xy; dot*dot >= 0.49984902
 *            (0xc84800): dot >= 0 -> 3 (hit_back) else 0 (hit_front);
 *            otherwise cross = fwd.x*dir.y - fwd.y*dir.x > 0 -> 2 (hit_right)
 *            else 1 (hit_left). The value stored on the "else" branch at
 *            0x520c85 was not read and is taken as 1.
 * IW4 0x5dfad0/0x5dfba0/0x5dfc00 set the same three values on its conditions
 * 9..11 with the same 6400 threshold (0x6fc858).
 * After the conditions both engines force the death event and return its
 * duration: C1 returns -1 when no death script is loaded (0x520d2a..0x520d36)
 * and otherwise plays a random scripted death (0x405c80); the retained
 * BG_AnimScriptEvent(ps, ANIM_ET_DEATH, 0, 1) is the same operation the
 * retained player_die performs (_g_combat_mp.asm:208). */
static int mod_from_const_string(short name)
{
    int i;
    for(i = 0; i < NATIVE_MOD_COUNT; ++i)
        if(modNames[i] && *modNames[i] == (uint16_t)name) return i;
    return -1;
}

static int hitloc_from_const_string(short name)
{
    int i;
    for(i = 0; i < HITLOC_NUM; ++i)
        if(G_GetHitLocationString((enum hitLocation_t)i) == (uint16_t)name) return i;
    return -1;
}

static uint64_t death_damage_type(gentity_t *victim, gentity_t *inflictor, int mod, int weapon)
{
    struct WeaponDef *def = weapon > 0 ? BG_GetWeaponDef(weapon) : NULL;
    if(def && def->offhandClass == OFFHAND_CLASS_FRAG_GRENADE) {
        if(inflictor) {
            vec3_t delta;
            VectorSubtract(inflictor->r.currentOrigin, victim->r.currentOrigin, delta);
            if((double)DotProduct(delta, delta) < 6400.0) return 2;
        }
        return 1;
    }
    switch(mod) {
    case NATIVE_MOD_GRENADE: case NATIVE_MOD_GRENADE_SPLASH: case NATIVE_MOD_PROJECTILE:
    case NATIVE_MOD_PROJECTILE_SPLASH: case NATIVE_MOD_EXPLOSIVE:
        return 2;
    default: break;
    }
    if(def && def->weapClass == WEAPCLASS_ROCKETLAUNCHER) return 2;
    return 0;
}

static uint64_t death_hit_location(int hitloc)
{
    if(hitloc == HITLOC_HELMET || hitloc == HITLOC_HEAD) return 1;
    if(hitloc == HITLOC_NECK || hitloc == HITLOC_TORSO_UPR) return 2;
    if(hitloc >= HITLOC_R_LEG_UPR && hitloc <= HITLOC_L_FOOT) return 3;
    return 0;
}

static uint64_t death_hit_direction(gentity_t *victim, const vec3_t dir)
{
    vec3_t forward;
    float dot, cross;
    AngleVectors(victim->r.currentAngles, forward, NULL, NULL);
    dot = forward[0] * dir[0] + forward[1] * dir[1];
    if((double)(dot * dot) >= 0.49984902143478394) return dot >= 0.0f ? 3 : 0;
    cross = forward[0] * dir[1] - forward[1] * dir[0];
    return cross > 0.0f ? 2 : 1;
}

void CODOL_Scr_PlayerForceDeathAnim(scr_entref_t ref)
{
    gentity_t *victim = player_entity_message(ref, "Must be called on a player.");
    gentity_t *inflictor;
    int mod, weapon, hitloc, client;
    vec3_t dir;
    if(!victim) return;
    inflictor = Scr_GetEntity(0);
    mod = mod_from_const_string(Scr_GetConstString(1));
    if(mod < 0) { Scr_ParamError(1, "unknown means of death"); return; }
    weapon = G_GetWeaponIndexForName(Scr_GetString(2));
    hitloc = hitloc_from_const_string(Scr_GetConstString(3));
    if(hitloc < 0) hitloc = HITLOC_NONE;
    Scr_GetVector(4, dir);
    client = victim->s.number;
    /* C1 0x520d1a..0x520d36: without a loaded animation script the death event
     * cannot be evaluated and the reference answers -1. */
    if(!bgs) { Scr_AddInt(-1); return; }
    CODOL_SetAnimConditionValue(client, 10, death_damage_type(victim, inflictor, mod, weapon));
    CODOL_SetAnimConditionValue(client, 11, death_hit_location(hitloc));
    CODOL_SetAnimConditionValue(client, 12, death_hit_direction(victim, dir));
    Scr_AddInt(BG_AnimScriptEvent(&victim->client->ps, CODOL_ANIM_ET_DEATH, 0, 1));
}

/* ---------------------------------------------------------------------- */
/* StunPlayer                                                              */
/* ---------------------------------------------------------------------- */

/* C1 0x5433a0 / IW4 0x5f3400: player receiver (C1 through 0x534a80, "only
 * valid on players; called on entity %i at %.0f %.0f %.0f"); Scr_GetFloat(0)
 * * 1000.0 rounded to milliseconds with the 2^-30 bias (C1 0xc84590, IW4
 * 0x6ddc68); a negative result raises Scr_ParamError(0, va("duration %g
 * should be >= 0", ms * 0.001)); then stunTime = level.time + ms, stored at
 * C1 ps+0x3338 (0x543452) / IW4 ps+0x3118 (0x5f3477). No return.
 *
 * Consumers: C1 0x41d6xx / IW4 0x578280 in PM_Weapon gate weapon use while
 * stunTime >= cmd.serverTime and enter the two stunned weapon states (0x1a,
 * 0x1b); the client predicts the same from the 0x3338 wire field. The retained
 * IW3 PM_Weapon has no stunned states; the gate helpers below are what a
 * retained-assembly or native pmove producer must consult. */
int CODOL_PlayerStunTime(const playerState_t *ps)
{
    const codol_ps_ext_t *ext = ps ? CODOL_PlayerStateExtConst(ps) : NULL;
    if(!ext || !ext->stun_known) return 0;
    return ext->stun_time;
}

int CODOL_PlayerStunned(const playerState_t *ps, int serverTime)
{
    const codol_ps_ext_t *ext = ps ? CODOL_PlayerStateExtConst(ps) : NULL;
    if(!ext || !ext->stun_known) return 0;
    return ext->stun_time >= serverTime;
}

int CODOL_OverlayEngineStun(codol_player_fields_t *wire, const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i) if(CODOL_PlayerField(i)->offset == 0x3338) {
        wire->field[i] = (uint32_t)CODOL_PlayerStunTime(ps);
        return 1;
    }
    return 0;
}

void CODOL_Scr_StunPlayer(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    codol_ps_ext_t *ext;
    int milliseconds;
    if(!ent) return;
    milliseconds = seconds_to_milliseconds(Scr_GetFloat(0));
    if(milliseconds < 0) {
        Scr_ParamError(0, va("duration %g should be >= 0", (double)milliseconds * 0.001));
        return;
    }
    ext = CODOL_PlayerStateExt(&ent->client->ps);
    if(!ext) {
        Scr_Error("stun playerState storage unavailable");
        return;
    }
    ext->stun_time = level.time + milliseconds;
    ext->stun_known = 1;
}

/* ---------------------------------------------------------------------- */
/* Thermal vision                                                          */
/* ---------------------------------------------------------------------- */

/* IW4 0x5f03b0 / 0x5f0420 / 0x5f0490 / 0x5f0500 and C1 0x53c8f0 (+ the three
 * that follow it, ending 0x53cb6f): player receiver, then or/and of bit 8
 * (thermal) or bit 0x10 (friend-or-foe overlay) in client+0x10, which is
 * ps->otherFlags in both layouts. No argument, no return. C1's client reads
 * the same bits back from its playerState: 0x477546 tests ps+0x10 & 8 and
 * 0x43b90a tests ps+0x10 & 0x10 before drawing hud_fofbox_hostile over every
 * enemy (0x483fd0) and hud_fofbox_self (0x484160). The retained IW3
 * ClientEndFrame/SpectatorClientEndFrame used these same two bits for spectator
 * permissions and cleared them every frame, so the script's bits never reached
 * a snapshot; _g_active_mp.asm now keeps those permissions in C1's 0x2000 and
 * 0x4000 (POF_SPEC_ALLOW_CYCLE/FREELOOK). */
static void thermal_flag(scr_entref_t ref, int bit, int on)
{
    gentity_t *ent = player_entity(ref);
    if(!ent) return;
    if(on) ent->client->ps.otherFlags |= bit;
    else ent->client->ps.otherFlags &= ~bit;
}

/* ---------------------------------------------------------------------- */
/* Weapon pickup                                                           */
/* ---------------------------------------------------------------------- */

/* IW4 PlayerCmd_DisableWeaponPickup / EnableWeaponPickup and C1 0x5145c3
 * (`or [ps+0x344],0x100000`) / 0x5145dc (`and ~0x100000`): player receiver,
 * no argument, no return. The bit suppresses the C1 CG pickup hint
 * (0x481105..0x48113b) and, server-side, Touch_Item's weapon path through
 * CODOL_WeaponPickupAllowed (IW4 G_Touch_Item tests the same flag). */
void CODOL_Scr_DisableWeaponPickup(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    if(!ent) return;
    ent->client->ps.weapFlags |= CODOL_WEAP_PICKUP_DISABLED;
}
void CODOL_Scr_EnableWeaponPickup(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    if(!ent) return;
    ent->client->ps.weapFlags &= ~CODOL_WEAP_PICKUP_DISABLED;
}
int CODOL_WeaponPickupAllowed(const gentity_t *player)
{
    if(!player || !player->client) return 1;
    return (player->client->ps.weapFlags & CODOL_WEAP_PICKUP_DISABLED) ? 0 : 1;
}

void CODOL_Scr_ThermalVisionOn(scr_entref_t ref) { thermal_flag(ref, CODOL_OTHERFLAG_THERMAL, 1); }
void CODOL_Scr_ThermalVisionOff(scr_entref_t ref) { thermal_flag(ref, CODOL_OTHERFLAG_THERMAL, 0); }
void CODOL_Scr_ThermalVisionFOFOverlayOn(scr_entref_t ref) { thermal_flag(ref, CODOL_OTHERFLAG_THERMAL_FOF, 1); }
void CODOL_Scr_ThermalVisionFOFOverlayOff(scr_entref_t ref) { thermal_flag(ref, CODOL_OTHERFLAG_THERMAL_FOF, 0); }

int CODOL_OverlayEngineThermal(codol_player_fields_t *wire, const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i) if(CODOL_PlayerField(i)->offset == 0x010) {
        uint32_t flags = wire->field[i] & ~(uint32_t)(CODOL_OTHERFLAG_THERMAL | CODOL_OTHERFLAG_THERMAL_FOF);
        flags |= (uint32_t)ps->otherFlags & (CODOL_OTHERFLAG_THERMAL | CODOL_OTHERFLAG_THERMAL_FOF);
        wire->field[i] = flags;
        return 1;
    }
    return 0;
}

/* ---------------------------------------------------------------------- */
/* Player cards                                                            */
/* ---------------------------------------------------------------------- */

/* C1 integer setters store ten-bit callsign table row indices. Authored
 * common_mp ui_mp/hud_720.txt resolves title with getplayercardinfo(1),
 * background with (2), icon with (3), all through tableLookupByRow.
 * Cache filler 0x68e7d0 and snapshot consumer 0x46c9f1 prove the fields:
 * title cs+B0 -> cache+4, background cs+B4 -> cache+8, icon cs+AC -> cache+C.
 * The remaining cs+B8 -> cache+10 is the fourth card/nameplate field.
 * Marketplace profile IDs must first resolve to their callsign table row;
 * preserving the integer setter range prevents invalid network values. */
static uint16_t player_cards[MAX_CLIENTS][4];
enum { CARD_ICON, CARD_TITLE, CARD_NAMEPLATE, CARD_BACKGROUND };

static void set_card(scr_entref_t ref, unsigned slot)
{
    gentity_t *ent = player_entity(ref);
    int index;
    if(!ent) return;
    index = Scr_GetInt(0);
    if((unsigned)index >= CODOL_CARD_INDEX_LIMIT) {
        Scr_Error("Index is greater than the maximum allowed in code for networking. "
                  "Limit needs to be increased.");
        return;
    }
    player_cards[ref.entnum][slot] = (uint16_t)index;
}

void CODOL_Scr_SetCardIcon(scr_entref_t ref) { set_card(ref, CARD_ICON); }
void CODOL_Scr_SetCardTitle(scr_entref_t ref) { set_card(ref, CARD_TITLE); }
void CODOL_Scr_SetCardNameplate(scr_entref_t ref) { set_card(ref, CARD_NAMEPLATE); }
void CODOL_Scr_SetCardBackground(scr_entref_t ref) { set_card(ref, CARD_BACKGROUND); }

void CODOL_ResetPlayerCards(unsigned client)
{
    if(client < MAX_CLIENTS) memset(player_cards[client], 0, sizeof(player_cards[client]));
}

void CODOL_ResetAllPlayerCards(void)
{
    memset(player_cards, 0, sizeof(player_cards));
}

int CODOL_OverlayClientCards(codol_client_state_t *wire)
{
    unsigned i, found = 0;
    codol_client_state_t out;
    if(!wire || wire->number >= MAX_CLIENTS) return 0;
    out = *wire;
    for(i = 0; i < CODOL_CLIENT_FIELDS; ++i) {
        const codol_entity_field_t *field = CODOL_ClientField(i);
        switch(field->offset) {
        case CODOL_CARD_WIRE_ICON:
            out.field[i] = player_cards[wire->number][CARD_ICON]; found |= 1; break;
        case CODOL_CARD_WIRE_TITLE:
            out.field[i] = player_cards[wire->number][CARD_TITLE]; found |= 2; break;
        case CODOL_CARD_WIRE_NAMEPLATE:
            out.field[i] = player_cards[wire->number][CARD_NAMEPLATE]; found |= 4; break;
        case CODOL_CARD_WIRE_BACKGROUND:
            out.field[i] = player_cards[wire->number][CARD_BACKGROUND]; found |= 8; break;
        default: break;
        }
    }
    if(found != 15) return 0;
    *wire = out;
    return 1;
}

/* ---------------------------------------------------------------------- */
/* DropScavengerBag                                                        */
/* ---------------------------------------------------------------------- */

/* C1 0x51b880 / IW4 0x5dda70: player receiver; Scr_GetString(0) ->
 * G_GetWeaponIndexForName, 0 -> Scr_Error("Scavenger Item \"%s\" does not
 * exist or has not been pre-cached."); weapon definition inventoryType != 5
 * (scavenger; C1 def+0x34c, IW4 def+0x38) -> Scr_Error("Scavenger Item \"%s\"
 * does not have the 'scavenger' inventory type."); then the drop helper (C1
 * 0x529000, IW4 0x4fd360) and Scr_AddEntity of the result - C1 answers
 * undefined (0x5ce7b0) when the helper returns NULL.
 *
 * The helpers spawn an ET_ITEM entity for the weapon owned by the dropper,
 * launch it from the dropper's angles (IW4 0x4a79a0, C1 0x528bf0) and set the
 * entity's client mask so that only players holding the scavenger perk see
 * it: IW4 0x5e2990 sets clientMask bit i for every client whose ps+0x428 lacks
 * 0x400000; C1 0x528890 sets bit i (into ent+0x10c) for every client whose
 * ps+0x4d0 lacks bit 29 - the MSB-first ability mask word, ability id 2. The
 * retained snapshot writer (sv_snapshot.c:873) skips an entity for a client
 * whose clientMask bit is set, so a set bit hides the bag from that client.
 *
 * The retained Drop_Item(ent, item, 0.0f, 0) is the spawn-and-launch
 * primitive PlayerCmd_dropItem's Drop_Weapon also ends in; it registers the
 * bag in the level's dropped-weapon ring, which the reference bag spawners do
 * not, so a bag can be reclaimed by g_maxDroppedWeapons pressure. Pickup is
 * the bag's touch handler (CODOL_ScavengerBagTouch): C1 refuses to give a
 * scavenger item as a weapon ("G_GivePlayerWeapon() - Scavenger item are not
 * meant to be used as weapons.") and the scripts wait for the "scavenger"
 * notify with the picking player (_weapons.gsc handleScavengerBagPickup). */
int CODOL_PlayerHasScavengerAbility(unsigned client)
{
    const codol_ps_ext_t *ext;
    if(client >= MAX_CLIENTS || !g_entities[client].client) return 0;
    ext = CODOL_PlayerStateExtConst(&g_entities[client].client->ps);
    if(!ext || !ext->abilities_known) return 0;
    return (ext->abilities.masks[CODOL_SCAVENGER_ABILITY_ID >> 5] &
            (0x80000000u >> (CODOL_SCAVENGER_ABILITY_ID & 31))) != 0;
}

void CODOL_ScavengerBagTouch(gentity_t *bag, gentity_t *other, int touched)
{
    unsigned notify;
    int generation;
    (void)touched;
    if(!bag || !bag->r.inuse || !other || !other->client || !other->r.inuse) return;
    if(other->client->ps.pm_type >= 8) return; /* C1 PM_DEAD, PM_DEAD_LINKED */
    if(!CODOL_PlayerHasScavengerAbility((unsigned)other->s.number)) return;
    notify = SL_GetString("scavenger", 0);
    if(!notify) return;
    generation = bag->useCount;
    Scr_AddEntity(other);
    Scr_Notify(bag, (unsigned short)notify, 1);
    SL_RemoveRefToString(notify);
    /* Script notification may delete the bag or reuse its entity slot. */
    if(bag->r.inuse && bag->useCount == generation) G_FreeEntity(bag);
}

void CODOL_Scr_DropScavengerBag(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    gentity_t *bag;
    const char *name;
    struct WeaponDef *def;
    int weapon, model, i;
    if(!ent) return;
    name = Scr_GetString(0);
    weapon = G_GetWeaponIndexForName(name);
    if(!weapon) {
        Scr_Error(va("Scavenger Item \"%s\" does not exist or has not been pre-cached.", name));
        return;
    }
    def = BG_GetWeaponDef(weapon);
    if(!def || def->inventoryType != WEAPINVENTORY_SCAVENGER) {
        Scr_Error(va("Scavenger Item \"%s\" does not have the 'scavenger' inventory type.", name));
        return;
    }
    if(weapon >= CODOL_WEAPON_SLOTS) { Scr_AddUndefined(); return; }
    model = (int)CODOL_WeaponBitsModelGet(&ent->client->ps, (unsigned)weapon);
    bag = Drop_Item(ent, (const struct gitem_s *)(bg_itemlist + 4 * ((unsigned)weapon + CODOL_ITEM_STRIDE * (unsigned)model)), 0.0f, 0);
    if(!bag) { Scr_AddUndefined(); return; }
    bag->handler = CODOL_SCAVENGER_BAG_HANDLER;
    bag->r.clientMask[0] = bag->r.clientMask[1] = 0;
    for(i = 0; i < level.maxclients && i < MAX_CLIENTS; ++i) {
        if(!g_entities[i].client || !g_entities[i].r.inuse) continue;
        if(!CODOL_PlayerHasScavengerAbility((unsigned)i))
            bag->r.clientMask[i >> 5] |= 1u << (i & 31);
    }
    Scr_AddEntity(bag);
}

/* ---------------------------------------------------------------------- */
/* KC_RegWeaponForFXRemoval                                                */
/* ---------------------------------------------------------------------- */

/* IW4 0x5df320: player receiver; Scr_GetString(0) -> G_GetWeaponIndexForName,
 * 0 -> Scr_Error(va("invalid weapon: %s", name)); then 0x4a0970 sends
 * va("%c %i", 'V', weapon) reliably to that client. C1 0x51e340 is the same
 * with letter 'S' (0x51e433) and reliable type 1 (0x51e448). C1's receiver
 * 0x469960 ('S' in the dispatch table) atoi's the argument and appends it to
 * a five-entry killcam FX weapon list, ignoring a duplicate and warning
 * "Server is trying to register too many killcamFXWeapons" past five. The
 * integer it stores is the client's weapon index, which is the CoDOL wire
 * index of the native weapon. */
void CODOL_Scr_KC_RegWeaponForFXRemoval(scr_entref_t ref)
{
    gentity_t *ent = player_entity(ref);
    const char *name;
    int weapon, wire;
    if(!ent) return;
    name = Scr_GetString(0);
    weapon = G_GetWeaponIndexForName(name);
    if(!weapon) { Scr_Error(va("invalid weapon: %s", name)); return; }
    wire = CODOL_WeaponToWire((unsigned)weapon);
    if(wire <= 0) { Scr_Error(va("weapon %s has no CoDOL wire index", name)); return; }
    SV_GameSendServerCommand(ent->s.number, 1, va("%c %i", 'S', wire));
}

/* ---------------------------------------------------------------------- */
/* PrecacheLeaderboards                                                    */
/* ---------------------------------------------------------------------- */

/* IW4 0x4bb9b0 is a bare RET. C1 0x5500a0: if !level.initializing (0x24b7030)
 * -> Scr_Error("preacheLeaderboards must be called before any wait statements
 * in the gametype or level script\n" - the reference's own spelling);
 * names = Scr_GetString(0); replace = !stricmp(Scr_GetString(1), "replace");
 * 0x7279d0 splits the names on spaces into at most 100 tokens, empties the
 * ledger when replace is set, and appends, walking the tokens from last to
 * first, every name that resolves to a non-default leaderboarddef asset
 * (type 0x26). The scripts only reach this on consoles (level.console).
 * There is no mounted-asset lookup by type and name in the native registry,
 * so the ledger records the names without the asset check; a later
 * sendleaderboards producer reads it through the accessors. C1 reads the
 * second parameter unconditionally; here it is optional. */
static char leaderboard_names[CODOL_LEADERBOARD_PRECACHE_LIMIT][64];
static unsigned leaderboard_count;

unsigned CODOL_PrecachedLeaderboardCount(void) { return leaderboard_count; }

const char *CODOL_PrecachedLeaderboardName(unsigned index)
{
    return index < leaderboard_count ? leaderboard_names[index] : NULL;
}

void CODOL_ResetPrecachedLeaderboards(void)
{
    leaderboard_count = 0;
    memset(leaderboard_names, 0, sizeof(leaderboard_names));
}

void CODOL_Scr_PrecacheLeaderboards(void)
{
    char buffer[1024];
    const char *tokens[CODOL_LEADERBOARD_PRECACHE_LIMIT];
    const char *names;
    unsigned count = 0, i;
    char *cursor;
    if(!level.initializing) {
        Scr_Error("preacheLeaderboards must be called before any wait statements in the gametype or level script\n");
        return;
    }
    names = Scr_GetString(0);
    if(!names) return;
    if(Scr_GetNumParam() > 1) {
        const char *mode = Scr_GetString(1);
        if(mode && !Q_stricmp(mode, "replace")) CODOL_ResetPrecachedLeaderboards();
    }
    Q_strncpyz(buffer, names, sizeof(buffer));
    for(cursor = buffer; *cursor && count < CODOL_LEADERBOARD_PRECACHE_LIMIT; ) {
        while(*cursor == ' ') ++cursor;
        if(!*cursor) break;
        tokens[count++] = cursor;
        while(*cursor && *cursor != ' ') ++cursor;
        if(*cursor) *cursor++ = '\0';
    }
    /* C1 0x727a5a..0x727a9f appends in reverse token order. */
    for(i = count; i-- > 0; ) {
        if(leaderboard_count >= CODOL_LEADERBOARD_PRECACHE_LIMIT) break;
        if(strlen(tokens[i]) >= sizeof(leaderboard_names[0])) {
            Scr_Error(va("PrecacheLeaderboards: name too long: %s", tokens[i]));
            return;
        }
        Q_strncpyz(leaderboard_names[leaderboard_count], tokens[i], sizeof(leaderboard_names[0]));
        ++leaderboard_count;
    }
}

/* ---------------------------------------------------------------------- */
/* Session resets                                                          */
/* ---------------------------------------------------------------------- */

void CODOL_ResetPlayerBuiltinsClient(unsigned client)
{
    CODOL_ResetPlayerCards(client);
    CODOL_ResetClientOnlineDataFlag(client);
}

void CODOL_ResetPlayerBuiltinsAll(void)
{
    CODOL_ResetAllPlayerCards();
    memset(online_data_offline, 0, sizeof(online_data_offline));
    CODOL_ResetPrecachedLeaderboards();
}
#endif

/* <player> SetRearViewRenderEnabled( <bool> )
 * IW4 0x5f50b0 is the whole method: Scr_Error("ALTERNATE_SCENE_RENDER is
 * disabled"). The rear-view mirror scene is compiled out of the PC build, so
 * the builtin exists only to fail loudly if a perk ever enables it; C1 has no
 * such method at all. The receiver and argument are not inspected, as in IW4. */
void CODOL_Scr_SetRearViewRenderEnabled(scr_entref_t ref)
{
    (void)ref;
    Scr_Error("ALTERNATE_SCENE_RENDER is disabled");
}
