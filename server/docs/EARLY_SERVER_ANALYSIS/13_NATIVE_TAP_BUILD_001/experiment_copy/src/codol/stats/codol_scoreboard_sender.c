/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "g_shared.h"
#include "server.h"
#include "cvar.h"
#include "qcommon_io.h"
#include "codol_scoreboard_stats.h"
#include "codol_scoreboard_wire.h"
#include "codol_scoreboard_sender.h"

int __cdecl SV_GetClientPing(int clientNum);
static unsigned char skill_warned[MAX_CLIENTS];
/* Called when a slot is reused so a new player is reported again. */
void CODOL_ResetScoreboardSkillWarning(unsigned client)
{
    if(client<MAX_CLIENTS) skill_warned[client]=0;
}
void CODOL_SendScoreboard(gentity_t *entity)
{
    codol_scoreboard_row_t rows[MAX_CLIENTS];
    char command[MAX_STRING_CHARS];
    char gametype[64];
    cvar_t *skill_gate=Cvar_FindVar("2474");
    int count=level.numConnectedClients, i, limit, zm;
    if(!entity || !entity->client || !level.clients || !svs.clients || !sv_maxclients) return;
    Cvar_VariableStringBuffer("g_gametype",gametype,sizeof(gametype));
    /* C1 registration498372/498385: numeric name2474, bool default true.
     * Use its numeric identity, not the formerly guessed onlinegame alias. */
    if(!skill_gate) skill_gate=Cvar_RegisterBool("2474",qtrue,0,
        "Enable CoDOL profile skill display");
    zm=!Q_stricmp(gametype,"zm");
    if(count<0) return;
    if(count>MAX_CLIENTS) count=MAX_CLIENTS;
    for(i=0;i<count;++i) {
        int slot=level.sortedClients[i];
        gclient_t *client;
        codol_scoreboard_row_t *row=&rows[i];
        if(slot<0 || slot>=level.maxclients || slot>=sv_maxclients->integer) return;
        client=&level.clients[slot];
        *row=(codol_scoreboard_row_t){0};
        row->client=slot;
        row->score=client->sess.score;
        row->ping=client->sess.connected==CON_CONNECTING ? -1 : SV_GetClientPing(slot);
        row->deaths=client->sess.deaths;
        row->status_icon=client->sess.status_icon;
        row->kills=client->sess.kills;
        row->assists=client->sess.assists;
        row->headshots=CODOL_GetScoreStat(slot,CODOL_SCORE_HEADSHOTS);
        row->objectives=CODOL_GetScoreStat(slot,CODOL_SCORE_OBJECTIVES);
        row->downs=CODOL_GetScoreStat(slot,CODOL_SCORE_DOWNS);
        row->revives=CODOL_GetScoreStat(slot,CODOL_SCORE_REVIVES);
        /* C1 5d2480 returns zero when gated off or the network client is not
         * active. A missing active profile is an error, not a fabricated rank. */
        if(!zm && skill_gate && skill_gate->boolean && svs.clients[slot].state==CS_ACTIVE &&
            !CODOL_ReadScoreboardSkill((unsigned)slot,&row->skill)) {
            /* A profile without a skills record is not a reason to withhold
             * the whole board from every client: C1 5d2480 itself answers zero
             * when the value is unavailable. Report once per slot so a missing
             * profile stays visible, then send the row with skill zero. */
            if(!skill_warned[slot]) {
                skill_warned[slot]=1;
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "CoDOL scoreboard: no skills/%s profile for client %i; sending skill 0\n",
                    gametype,slot);
            }
            row->skill=0;
        }
    }
    limit=Cvar_VariableIntegerValue(va("scr_%s_scorelimit",gametype));
    if(!limit) limit=Cvar_VariableIntegerValue(va("scr_%s_roundlimit",gametype));
    if(CODOL_FormatScoreboard(command,sizeof(command),zm,
        level.teamScores[TEAM_RED],level.teamScores[TEAM_BLUE],limit,rows,(size_t)count)<0) return;
    SV_GameSendServerCommand((int)(entity-g_entities),1,command);
}
/* C1's own HUD score readout is NOT a playerstate field and NOT a HUD element:
 * it is read straight out of the cached scoreboard row table. MEASURED in
 * C1.exe:
 *
 *   - the named HUD/menu value "score" (string 0xc44478) is resolved at
 *     0x5dec2d by looking the LOCAL client (cg+0x35c0) up in the cached row
 *     table with 0x45fe50 and returning row+0x04; "ping", "deaths" and
 *     "kills" (0xc49678 / 0xc44470 / 0xc44468) come from row+0x08 / +0x0c /
 *     +0x14 of the same row;
 *   - that table is cg+0xBEB70, stride 0x40, 19 rows, and the ONLY writers
 *     are the scoreboard replies b (0x465130) and zm 4 (0x4655e0), and the
 *     incremental reliable command E (handler 0x469a4f, jump table 0x46a024
 *     index 14, byte map 0x46a118['E']), which reads "E <client> <score>" and
 *     calls 0x465990 to patch row+0x04 of that one client.
 *
 * So a score that changes without an E command is invisible until the player
 * opens the scoreboard, which is what makes the client send "s" and the server
 * answer with the whole board. That is exactly the reported "the bottom right
 * score only updates while TAB is held" bug.
 *
 * The retained producer of E is PlayerCmd_UpdateDMScores
 * (src/asmsource/_g_client_script_cmd_mp.asm:4464), the GSC method
 * updateDMScores: it sends the player their OWN row and the leader's row
 * (level.sortedClients[0], or the next sorted client when the player is the
 * leader). Only maps/mp/gametypes/_gamescore.gsc calls it, only through
 * sendUpdatedDMScores() and only when !level.teamBased, so a zm purse, a
 * team-based multiplayer score and every native score writer never reached it.
 *
 * Publishing it from the server frame instead makes the carrier follow
 * sess.score itself - the authoritative value the scoreboard reply already
 * reports - for every gametype and every writer, script or native. The wire
 * shape and the leader pairing are C1's, unchanged. Same idea, and the same
 * per-client "what did I last send" guard, as CODOL_RefreshWeaponHud. */
static int CODOL_ScoreLeaderFor(int self)
{
    /* PlayerCmd_UpdateDMScores_30/_40/_50/_80: no sorted clients at all is -1,
     * otherwise the first sorted client that is not the player. */
    int count=level.numConnectedClients,i;
    if(count<=0) return -1;
    if(count>MAX_CLIENTS) count=MAX_CLIENTS;
    for(i=0;i<count;++i) {
        int slot=level.sortedClients[i];
        if(slot==self || slot<0 || slot>=level.maxclients) continue;
        return slot;
    }
    return -1;
}
void CODOL_PublishPlayerScores(void)
{
    /* What each client was last told about its own row and about the leader
     * row C1 pairs with it. IW4 refreshes every player whenever anyone
     * scores, which is the same thing as noticing that a viewer's leader
     * pair moved, and costs nothing while nobody is scoring. */
    static int last_own[MAX_CLIENTS];
    static int last_leader[MAX_CLIENTS];
    static int last_leader_score[MAX_CLIENTS];
    static int next_send[MAX_CLIENTS];
    static unsigned char primed[MAX_CLIENTS];
    int i,limit;
    /* svs.clients is an array, not a pointer; testing it warns. */
    if(!level.clients || !sv_maxclients) return;
    limit=sv_maxclients->integer;
    if(limit>level.maxclients) limit=level.maxclients;
    if(limit>MAX_CLIENTS) limit=MAX_CLIENTS;
    for(i=0;i<limit;++i) {
        client_t *client=&svs.clients[i];
        int score,leader,leader_score;
        if(client->state!=CS_ACTIVE || !client->gamestateSent ||
           client->netchan.remoteAddress.type==NA_BOT) { primed[i]=0; continue; }
        score=level.clients[i].sess.score;
        leader=CODOL_ScoreLeaderFor(i);
        leader_score=leader>=0 ? level.clients[leader].sess.score : 0;
        if(primed[i]) {
            if(score==last_own[i] && leader==last_leader[i] &&
               leader_score==last_leader_score[i]) continue;
            /* IW4's sendUpdatedDMScores debounces with wait .05; a zm purse
             * moves on every bullet, so coalesce at the same 50 ms rather
             * than emit a reliable command per hit. The values are re-tested
             * next frame, so nothing is dropped, only delayed. */
            if(svs.time-next_send[i]<0) continue;
        }
        primed[i]=1; last_own[i]=score; last_leader[i]=leader;
        last_leader_score[i]=leader_score; next_send[i]=svs.time+50;
        /* C1 PlayerCmd_UpdateDMScores sends the viewer its own row first,
         * then the leader's, both with svscmd_type 0. */
        SV_GameSendServerCommand(i,0,va("%c %i %i",'E',i,score));
        if(leader>=0)
            SV_GameSendServerCommand(i,0,va("%c %i %i",'E',leader,leader_score));
    }
}
#endif
