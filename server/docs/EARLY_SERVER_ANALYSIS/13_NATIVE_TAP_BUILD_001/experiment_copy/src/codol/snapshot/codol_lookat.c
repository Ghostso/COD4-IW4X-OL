/* Crosshair friend/foe identification (IW4 Player_UpdateLookAtEntity).
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 evidence: CG_GetCrosshairColor 0x43c4e1..0x43c611 takes the crosshair
 * colour from ps+0x344 alone. Bit 8 (0x43c509) selects the friendly colour
 * dvar after a settle time; bit 0x10 (0x43c546) selects the enemy colour when
 * cg_crosshairEnemyColor (dvar 690, global 0x16da19c) is on and 250 ms have
 * passed (0x43c563). CG_DrawCrosshairNames 0x43a52f tests the same 0x10. No
 * client-side entity trace feeds either bit and nothing in C1.exe .text writes
 * them: this is the IW4 server contract, where ClientEndFrame traces the
 * player's view and stores PWF_FRIENDLY_FIRE (8) / PWF_ENEMY_FIRE (0x10) in
 * ps->weapFlags. The retained IW3 game code (_g_active_mp.asm) carries no such
 * producer, and g_redCrosshairs (C1 dvar 1278, registered 0x52b678; retained
 * g_sv_main.c:775) had no reader.
 *
 * What C1 1.1.1.13 can and cannot draw with those two bits (re-disassembled
 * 2026-09-16, CG_GetCrosshairColor 0x0043c4a0; the colour it returns tints the
 * centre pic 0x0043cae0 AND the four crosshair segments 0x0043cd60 through
 * CG_DrawCrosshair 0x0043d1d0, call 0x0043d34d):
 *
 *   friendly (bit 8, 0x0043c509): falls through to the colour at 0x0043c528
 *     because the settle test is `cmp (cg+0xbf050 - cg+0xbf054), dvar"775"+0xc`
 *     / `jl white` (0x0043c51f/0x0043c522) with a SIGNED compare, the two cg
 *     fields have no writer anywhere in the image (cg_t is memset at
 *     0x0044e152) and dvar "775" is 0 -> `0 < 0` is false. It then paints
 *     Dvar_GetUnpackedColor("291") -- whose registered value is (0.4, 0.6,
 *     0.85), a STEEL BLUE, not green. "No green crosshair" was the correct
 *     output of a working path; the colour is what is wrong, so the server
 *     sets dvar 291 below.
 *   enemy (bit 0x10, 0x0043c546): UNREACHABLE. 0x0043c563 is
 *     `cmp ecx,0xfa / jl white` on the same permanently-zero delta, so every
 *     frame takes the white exit. No value the server publishes can make the
 *     crosshair red on this client build. The bit is still published because
 *     CG_DrawCrosshairNames 0x0043a52f uses it for the enemy name.
 *   the held WeaponDef's byte +0xbc3 (crosshairColorChange, the only reader in
 *     the whole image is 0x0043c4f6) gates the colour, and it is 1 on all 42
 *     stock and all 20 live composed definitions -- it is never the blocker
 *     for a gun; it is 0 only on grenades/equipment/markers. */
#ifdef CODOL_SERVER
#include "codol_lookat.h"
#include "g_shared.h"
#include "server.h"
#include "cvar.h"
#include "g_sv_shared.h"
#include "q_shared.h"
#include "player.h"
#include "entity.h"
#include "cm_public.h"
#include "game/surfaceflags.h"

extern cvar_t *g_redCrosshairs;

/* C1 registers dvar "291" (the friendly crosshair colour CG_GetCrosshairColor
 * paints at 0x0043c528) as a colour dvar at 0x0052b1ff with (0.4,0.6,0.85).
 * PlayerCmd_SetClientDvar's wire form on CoDOL is `s <name> "<value>"`
 * (_g_client_script_cmd_mp.asm:3468-3486, C1 CG_SetClientDvarFromServer
 * 0x468a00), so one reliable command per client per map makes the reachable
 * half of the friend/foe crosshair actually read as FRIENDLY. */
/* The four C1 colour dvars these two features read, all numeric ids in the
 * stripped 1.1.1.13 build:
 *   "291" friendly crosshair  (registered 0x0052b1ff, 0.40 0.60 0.85 1)
 *   "292" enemy    crosshair  (registered 0x0052b277, 0.75 0.25 0.25 1)
 *   "794" friendly name tag   (CG_DrawCrosshairNames 0x0043a55c, dvar pointer
 *                              global 0x016da254, shipped 0.90 1.00 0.90 0.70)
 *   "796" enemy    name tag   (CG_DrawCrosshairNames 0x0043a53b, dvar pointer
 *                              global 0x016cf884, shipped 1.00 0.90 0.90 0.70)
 * 795/797 are the drop-shadow colours painted behind 794/796; they stay at the
 * shipped dark green / dark red, which reads correctly behind either colour.
 * The wire form is PlayerCmd_SetClientDvar's `s <name> "<value>"`
 * (_g_client_script_cmd_mp.asm:3468-3486, C1 CG_SetClientDvarFromServer
 * 0x468a00), sent reliably once per client per map. */
#define CODOL_CROSSHAIR_FRIENDLY_DVAR "291"
#define CODOL_CROSSHAIR_ENEMY_DVAR    "292"
#define CODOL_NAMETAG_FRIENDLY_DVAR   "794"
#define CODOL_NAMETAG_ENEMY_DVAR      "796"
#define CODOL_CROSSHAIR_FRIENDLY_RGBA "0 1 0 1"
#define CODOL_CROSSHAIR_ENEMY_RGBA    "0.75 0.25 0.25 1"
static cvar_t *codol_friendlyColor;
static cvar_t *codol_enemyColor;
/* C1's weapon code reads the same bit as a fire lock: PM 0x0041DAAE tests
 * ps+0x344 & 8 and, when set, leaves before the fire path (IW single-player's
 * PWF_FRIENDLY_FIRE "do not shoot friendlies").  Publishing the friendly
 * crosshair therefore withholds shots while the crosshair rests on a
 * teammate; off by default so multiplayer fires normally. */
static cvar_t *codol_friendlyCrosshair;
static int crosshair_colour_sent[MAX_CLIENTS];
void CODOL_ResetLookAtClientState(unsigned client)
{
    if(client<MAX_CLIENTS) crosshair_colour_sent[client]=0;
}

/* Registered lazily so no extra init hook is needed and any caller order stays
 * valid. Plain "r g b a" strings: that is exactly what C1's
 * CG_SetClientDvarFromServer feeds to Dvar_SetFromStringByName. */
static void crosshair_colour_cvars(void)
{
    if(!codol_friendlyColor)
        codol_friendlyColor=Cvar_RegisterString("codol_friendlyColor",
            CODOL_CROSSHAIR_FRIENDLY_RGBA,CVAR_ARCHIVE,
            "Colour (\"r g b a\") for the friendly crosshair (C1 dvar 291) and the "
            "friendly floating name tag (C1 dvar 794).");
    if(!codol_friendlyCrosshair)
        codol_friendlyCrosshair=Cvar_RegisterBool("codol_friendlyCrosshair",qfalse,0,
            "Publish the friendly crosshair bit (ps weapFlags 8). C1 also treats it as a "
            "fire lock (0x0041DAAE): while set, shots at a teammate are withheld.");
    if(!codol_enemyColor)
        codol_enemyColor=Cvar_RegisterString("codol_enemyColor",
            CODOL_CROSSHAIR_ENEMY_RGBA,CVAR_ARCHIVE,
            "Colour (\"r g b a\") for the enemy crosshair (C1 dvar 292) and the "
            "enemy floating name tag (C1 dvar 796).");
}

static const char *colour_string(const cvar_t *v,const char *fallback)
{
    if(v && v->string && v->string[0]) return v->string;
    return fallback;
}

static void send_crosshair_colours(unsigned client)
{
    const char *friendly,*enemy;
    crosshair_colour_cvars();
    friendly=colour_string(codol_friendlyColor,CODOL_CROSSHAIR_FRIENDLY_RGBA);
    enemy=colour_string(codol_enemyColor,CODOL_CROSSHAIR_ENEMY_RGBA);
    SV_GameSendServerCommand((int)client,1,va("s " CODOL_CROSSHAIR_FRIENDLY_DVAR " \"%s\"",friendly));
    SV_GameSendServerCommand((int)client,1,va("s " CODOL_NAMETAG_FRIENDLY_DVAR " \"%s\"",friendly));
    SV_GameSendServerCommand((int)client,1,va("s " CODOL_CROSSHAIR_ENEMY_DVAR " \"%s\"",enemy));
    SV_GameSendServerCommand((int)client,1,va("s " CODOL_NAMETAG_ENEMY_DVAR " \"%s\"",enemy));
    if(CODOL_TRACE_VERBOSE())
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL crosshair colour: client %u -> 291/794 \"%s\", 292/796 \"%s\"\n",
        client,friendly,enemy);
}

/* C1 PmoveSingle pm_type values (codol_pmove_c1.c): only normal and linked
 * normal play produce a targetable view. */
#define C1_PM_NORMAL        0
#define C1_PM_NORMAL_LINKED 1
/* Bullet-like line: world, shot clip, glass-class contents and bodies, the
 * same body/solid mask the native actor sight tests use (0x2800011) plus
 * CONTENTS_CLIPSHOT. */
#define LOOKAT_MASK (CONTENTS_SOLID|0x10|CONTENTS_CLIPSHOT|0x800000|CONTENTS_BODY)
#define LOOKAT_RANGE 8192.0f

static int playing(const gentity_t *ent)
{
    return ent && ent->r.inuse && ent->client &&
        ent->client->sess.sessionState==SESS_STATE_PLAYING && ent->health>0;
}

void CODOL_UpdateLookAtEntity(unsigned client)
{
    gentity_t *ent, *hit;
    gclient_t *cl;
    trace_t tr;
    vec3_t start, forward, end, zero={0,0,0};
    unsigned flags=0;
    team_t mine, theirs;

    if(client>=MAX_CLIENTS || client>=(unsigned)level.maxclients) return;
    ent=&g_entities[client];
    if(!ent->r.inuse || !ent->client) return;
    cl=ent->client;
    cl->ps.weapFlags&=~(int)(CODOL_WEAP_CROSSHAIR_FRIENDLY|CODOL_WEAP_CROSSHAIR_ENEMY);
    if(!playing(ent)) return;
    if(!crosshair_colour_sent[client]) {
        crosshair_colour_sent[client]=1;
        send_crosshair_colours(client);
    }
    if(cl->ps.pm_type!=C1_PM_NORMAL && cl->ps.pm_type!=C1_PM_NORMAL_LINKED) return;

    G_GetPlayerViewOrigin(&cl->ps,start);
    AngleVectors(cl->ps.viewangles,forward,NULL,NULL);
    VectorMA(start,LOOKAT_RANGE,forward,end);
    G_TraceCapsule(&tr,start,zero,zero,end,ent->s.number,LOOKAT_MASK);
    if(tr.fraction>=1.0f || tr.hitType!=TRACE_HITTYPE_ENTITY || tr.hitId>=MAX_CLIENTS) return;
    hit=&g_entities[tr.hitId];
    /* Only living players in play; a hidden entity (SVF_NOCLIENT) is not on the
     * viewer's screen so it cannot recolour the crosshair. Non-client entities
     * (actors, vehicles) carry no published team here and stay neutral. */
    if(hit==ent || !playing(hit) || (hit->r.svFlags&SVF_NOCLIENT)) return;
    mine=cl->sess.cs.team;
    theirs=hit->client->sess.cs.team;
    if(theirs!=TEAM_FREE && theirs==mine) {
        crosshair_colour_cvars();
        if(!codol_friendlyCrosshair || !codol_friendlyCrosshair->boolean) return;
        flags=CODOL_WEAP_CROSSHAIR_FRIENDLY;
    }
    else if(!g_redCrosshairs || g_redCrosshairs->boolean) flags=CODOL_WEAP_CROSSHAIR_ENEMY;
    cl->ps.weapFlags|=(int)flags;
    /* Server-side verification: one line per client per second at most, on a
     * change of target or colour, capped for the whole process. Bots are
     * excluded: twelve of them exhaust any process-wide cap within a minute
     * and the only line that diagnoses the crosshair is the human's. */
    {
        static unsigned last_target[MAX_CLIENTS], last_flags[MAX_CLIENTS];
        static int last_time[MAX_CLIENTS], lines;
        if(CODOL_TRACE_VERBOSE() && lines<400 && svs.clients[client].netchan.remoteAddress.type!=NA_BOT &&
           (last_target[client]!=tr.hitId || last_flags[client]!=flags) &&
           level.time-last_time[client]>=1000) {
            last_target[client]=tr.hitId; last_flags[client]=flags; last_time[client]=level.time; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL lookat: client %u -> client %u team %d/%d flags 0x%x weapFlags 0x%x (g_redCrosshairs %d)\n",
                client,(unsigned)tr.hitId,(int)mine,(int)theirs,flags,(unsigned)cl->ps.weapFlags,
                g_redCrosshairs ? g_redCrosshairs->boolean : -1);
        }
    }
}
#endif
