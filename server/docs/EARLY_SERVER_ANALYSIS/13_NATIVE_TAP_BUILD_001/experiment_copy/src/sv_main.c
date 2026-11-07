/*
===========================================================================
    Copyright (C) 2010-2013  Ninja and TheKelm
    Copyright (C) 1999-2005 Id Software, Inc.

    This file is part of IW4OL source code, a fork of CoD4x.

    IW4OL source code is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    IW4OL source code is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
===========================================================================
*/


#include "q_shared.h"
#ifdef CODOL_SERVER
#include "codol_scoreboard_stats.h"
#include "codol_scoreboard_sender.h"
#endif
#include "qcommon_io.h"
#include "qcommon_mem.h"
#include "qcommon.h"
#include "cvar.h"
#include "cmd.h"
#include "msg.h"
#include "server.h"
#include "plugin_handler.h"
#include "net_game_conf.h"
#include "misc.h"
#include "g_sv_shared.h"
#include "g_shared.h"
#include "q_platform.h"
#include "punkbuster.h"
#include "sys_thread.h"
#include "sys_main.h"
#include "scr_vm.h"
#include "xassets.h"
#include "nvconfig.h"
#include "codol_playerstate_ext.h"
#include "codol_clientstate_ext.h"
#include "codol_entitystate_ext.h"
#include "hl2rcon.h"
#include "crc.h"
#include "sv_bots.h"
#include "q_shared.h"
#include "math.h"
#include "httpftp.h"
#include "cscr_stringlist.h"
#include "cscr_variable.h"
#include "g_sv_main.h"
#include "sapi.h"
#include "xac_helper.h"
#include "db_load.h"
#include "sec_crypto.h"

#include <string.h>
#include <stdarg.h>
#ifdef CODOL_SERVER
#include "codol_game.h"
#ifdef CODOL_SERVER
#include "codol_script_startup_extra.h"
#include "codol_script_slowmotion.h"
#endif
#include "codol_script_notify.h"
#include "codol_matchdata.h"
#include "codol_matchdata_server.h"
#include "codol_match_report.h"
#include "codol_profile.h"
#include "codol_profile_push.h"
#include "codol_profile_progress.h"
#include "codol_script_profile_vm.h"
#include "codol_network.h"
#include "codol_weapon_input.h"
#include "codol_bot.h"
#include "codol_bot_nav.h"
#include "codol_weapon_state.h"
#include "codol_weapon_native.h"
#include "codol_stats.h"
#include "codol_assets.h"
#include "codol_sv_state.h"
#include "codol_replicated_dvars.h"
#include "codol_sv_weapons.h"
#include "codol_sv_entities.h"
#include "codol_model_animation.h"
#include "codol_actor_scripts.h"
static cvar_t *codol_zoneType;
unsigned codol_previous_checksum_feed;
static unsigned codol_current_checksum_feed;
static cvar_t *codol_animlistMask;
static cvar_t *codol_sessionMap;
/* The asset category the currently mounted archives belong to ("" before the
 * first mount).  A spawn whose resolved category differs from this one has to
 * retire the previous gametype zones and their script set before mounting. */
static char codol_loadedZoneType[8];
static char codol_loadedMapName[MAX_QPATH];
/* Installed by the asset layer (src/codol/assets) rather than called by name,
 * exactly like the weapon resolvers further down in SV_SpawnServer: it keeps
 * this translation unit link-clean while that side is still being written, and
 * it means a build without the teardown simply skips it. */
static void (*codol_categoryTeardown)(const char *previous, const char *next);
static void (*codol_sessionMapInstaller)(const char *session_map);

void SV_SetCoDOLCategoryTeardown(void (*fn)(const char *previous, const char *next))
{
    codol_categoryTeardown = fn;
}

void SV_SetCoDOLSessionMapInstaller(void (*fn)(const char *session_map))
{
    codol_sessionMapInstaller = fn;
}

/* The playlist/session spelling of the map for this match, or "" when the
 * lobby did not send one.  A coop match has two spellings: the playlist zone
 * (coop_training_mp_killhouse_sh) and the level zone that goes on the wire
 * (mp_killhouse_sh); only the latter is `mapname`. */
const char *SV_CoDOLSessionMapName(void)
{
    return codol_sessionMap ? codol_sessionMap->string : "";
}

const char *SV_CoDOLAssetCategory(void)
{
    return codol_zoneType ? codol_zoneType->string : "mp";
}
#endif
#include <unistd.h>

cvar_t	*sv_protocol;
cvar_t	*sv_privateClients;		// number of clients reserved for password
cvar_t	*sv_hostname;
#ifdef PUNKBUSTER
cvar_t	*sv_punkbuster;
#endif
cvar_t	*sv_minPing;
cvar_t	*sv_maxPing;
cvar_t	*sv_queryIgnoreMegs;
cvar_t	*sv_queryIgnoreTime;
cvar_t	*sv_privatePassword;		// password for the privateClient slots
cvar_t	*sv_allowDownload;
cvar_t	*sv_wwwDownload;
cvar_t	*sv_wwwBaseURL;
cvar_t	*sv_wwwDlDisconnected;
cvar_t	*sv_voice;
cvar_t	*sv_voiceQuality;
cvar_t	*sv_cheats;
cvar_t	*sv_rconPassword;		// password for remote server commands
cvar_t	*sv_reconnectlimit;		// minimum seconds between connect messages
cvar_t	*sv_padPackets;			// add nop bytes to messages
cvar_t	*sv_mapRotation;
cvar_t	*sv_mapRotationCurrent;
cvar_t  *sv_randomMapRotation;
cvar_t	*sv_nextmap;
cvar_t	*sv_paused;
cvar_t	*sv_killserver;			// menu system can set to 1 to shut server down
cvar_t	*sv_timeout;			// seconds without any message while in game
cvar_t	*sv_connectTimeout;		// seconds without any message while connecting
cvar_t	*sv_zombieTime;			// seconds to sink messages after disconnect
cvar_t	*sv_consayname;
cvar_t	*sv_contellname;
cvar_t	*sv_password;
cvar_t	*g_motd;
cvar_t	*sv_modStats;
cvar_t	*sv_authorizemode;
cvar_t	*sv_showasranked;
cvar_t	*sv_statusfile;
cvar_t	*g_friendlyPlayerCanBlock;
cvar_t	*g_FFAPlayerCanBlock;
cvar_t	*sv_autodemorecord;
cvar_t	*sv_demoCompletedCmd;
cvar_t	*sv_screenshotArrivedCmd;
cvar_t	*sv_mapDownloadCompletedCmd;
cvar_t	*sv_master[MAX_MASTER_SERVERS];	// master server ip address
cvar_t	*sv_masterservers;
cvar_t	*g_mapstarttime;
cvar_t	*sv_uptime;

cvar_t* sv_g_gametype;
cvar_t* sv_mapname;
cvar_t* sv_maxclients;
cvar_t* sv_clientSideBullets;
cvar_t* sv_maxRate;
cvar_t* sv_floodProtect;
cvar_t* sv_showcommands;
cvar_t* sv_iwds;
cvar_t* sv_iwdNames;
cvar_t* sv_referencedIwds;
cvar_t* sv_referencedIwdNames;
cvar_t* sv_FFCheckSums;
cvar_t* sv_FFNames;
cvar_t* sv_referencedFFCheckSums;
cvar_t* sv_referencedFFNames;
cvar_t* sv_serverid;
cvar_t* sv_pure;
cvar_t* sv_fps;
cvar_t* sv_showAverageBPS;
cvar_t* sv_botsPressAttackBtn;
cvar_t* sv_debugRate;
cvar_t* sv_debugReliableCmds;
cvar_t* sv_clientArchive;
cvar_t* sv_shownet;
cvar_t* sv_updatebackendname;
cvar_t* sv_legacymode;
cvar_t* sv_steamgroup;
cvar_t* sv_authtoken;
cvar_t* sv_disableChat;
cvar_t* sv_maxDownloadRate;

serverStatic_t		svs;
server_t		sv;
svsHeader_t		svsHeader;
permServerStatic_t	psvs;	// persistant even if server does shutdown

qboolean svsHeaderValid;


#define SV_OUTPUTBUF_LENGTH 1024

/*
cvar_t	*sv_fps = NULL;			// time rate for running non-clients
cvar_t	*sv_timeout;			// seconds without any message
cvar_t	*sv_zombietime;			// seconds to sink messages after disconnect

cvar_t	*sv_showloss;			// report when usercmds are lost


cvar_t	*sv_mapname;
cvar_t	*sv_mapChecksum;
cvar_t	*sv_serverid;
cvar_t	*sv_minRate;


cvar_t	*sv_pure;

cvar_t	*sv_lanForceRate; // dedicated 1 (LAN) server forces local client rates to 99999 (bug #491)
#ifndef STANDALONE
cvar_t	*sv_strictAuth;
#endif

cvar_t	*sv_banFile;

serverBan_t serverBans[SERVER_MAXBANS];
int serverBansCount = 0;
*/

#define MASTERSERVERSECRETLENGTH 64

static netadr_t	atvimaster;
static char masterServerSecret[MASTERSERVERSECRETLENGTH +1];

/*
=============================================================================

EVENT MESSAGES

=============================================================================
*/

/*
void SV_DumpReliableCommands( client_t *client, const char* cmd) {

    if(!com_developer || com_developer->integer < 2)
        return;


    char msg[1040];

    Com_sprintf(msg, sizeof(msg), "Cl: %i, Seq: %i, Time: %i, NotAck: %i, Len: %i, Msg: %s\n",
        client - svs.clients, client->reliableSequence, svs.time ,client->reliableSequence - client->reliableAcknowledge, strlen(cmd), cmd);

    Com_Printf(CON_CHANNEL_SERVER,"^5%s", msg);

    Sys_EnterCriticalSection(5);

    if ( com_logfile && com_logfile->integer ) {
    // TTimo: only open the qconsole.log if the filesystem is in an initialized state
    //   also, avoid recursing in the qconsole.log opening (i.e. if fs_debug is on)
        if ( !reliabledump && FS_Initialized()) {
            struct tm *newtime;
            time_t aclock;

            time( &aclock );
            newtime = localtime( &aclock );

            reliabledump = FS_FOpenFileWrite( "reliableCmds.log" );

            if ( com_logfile->integer > 1 && reliabledump) {
                // force it to not buffer so we get valid
                // data even if we are crashing
                FS_ForceFlush(reliabledump);
            }
            if ( reliabledump ) FS_Write(va("\nLogfile opened on %s\n", asctime( newtime )), strlen(va("\nLogfile opened on %s\n", asctime( newtime ))), reliabledump);
        }
        if ( reliabledump && FS_Initialized()) {
        FS_Write(msg, strlen(msg), reliabledump);
        }
    }
    Sys_LeaveCriticalSection(5);
}
*/

/*
======================
SV_AddServerCommand

The given command will be transmitted to the client, and is guaranteed to
not have future snapshot_t executed before it is executed
======================
*/

#ifdef CODOL_SERVER
/* Numeric-only splash admission diagnostics. A pre-admission command log is
 * not evidence that a type-zero notification entered the reliable queue.
 * Cap each client's output at eight events/second; report omitted events on
 * the next emitted record. No command text, names, or addresses are logged. */
static void CODOL_TraceSplashAdmission(client_t *client, const char *command,
                                      const char *outcome, int sequence)
{
    static struct { unsigned window, count, suppressed; } rate[MAX_CLIENTS];
    unsigned now;
    int clientNum, slot, row, number;
    char extra;
    if (!com_developer || !com_developer->integer || !command ||
        command[0] != 'w' || command[1] != ' ' ||
        client->netchan.remoteAddress.type == NA_BOT)
        return;
    clientNum = (int)(client - svs.clients);
    if ((unsigned)clientNum >= MAX_CLIENTS ||
        sscanf(command, "w %d %d %d %c", &slot, &row, &number, &extra) != 3)
        return;
    now = (unsigned)svs.time;
    if (now - rate[clientNum].window >= 1000u) {
        rate[clientNum].window = now;
        rate[clientNum].count = 0;
    }
    if (rate[clientNum].count >= 8u) {
        ++rate[clientNum].suppressed;
        return;
    }
    ++rate[clientNum].count;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL splash admission: client %d %s slot %d row %d number %d "
        "sequence %d sent %d ack %d state %d time %u omitted %u\n",
        clientNum, outcome, slot, row, number, sequence,
        client->reliableSent, client->reliableAcknowledge, client->state, now,
        rate[clientNum].suppressed);
    rate[clientNum].suppressed = 0;
}
#endif

void sub_5310E0(client_t *client)
{
    int v1;
    int i;

    v1 = client->reliableSent + 1;

    for(i = client->reliableSent + 1 ; i <= client->reliableSequence; ++i)
    {
        if ( client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].cmdType )
        {
            if ( (v1 & (MAX_RELIABLE_COMMANDS - 1)) != (i & (MAX_RELIABLE_COMMANDS - 1)) )
            {
                memcpy(&client->reliableCommands[v1 & (MAX_RELIABLE_COMMANDS - 1)], &client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)], sizeof(reliableCommands_t));
            }
            ++v1;
        }
#ifdef CODOL_SERVER
        else
            CODOL_TraceSplashAdmission(client,
                client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].command,
                "pruned-unsent", i);
#endif
    }
    client->reliableSequence = v1 - 1;
}




int sub_530FC0(client_t *client, const char *command)
{

    int i;

    for( i = client->reliableSent + 1; i <= client->reliableSequence; ++i)
    {

        if ( client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].cmdType == 0 )
            continue;

        if(client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].command[0] != command[0])
            continue;

        if ( command[0] >= 120 && command[0] <= 122 )
            continue;

#ifdef CODOL_SERVER
        /* C1 renumbered IW3's letters: 'q' is openMenu (0x00467D80) and 'r'
         * is closeMenu (0x00468060), and neither may be coalesced.  Each 'r'
         * is one pass of C1's two-pass teardown 0x005F4F20: pass one closes
         * the open legacy menus, pass two releases KEYCATCH_UI.  closeMenu
         * emits two, but the identical unsent second 'r' was folded into the
         * first, so a menu still open at the close (dirt_effect_*,
         * endgameupdate) left the key-catcher set and UI_Refresh drew the
         * mouse cursor over the game until the player's next key event.  Any
         * later unsent 'q' also replaced an earlier one whatever its menu:
         * a kill inside the perk-icon window pulses youkilled_card_display
         * and hidePerksOnKill's perk_hide in one frame, and only the later
         * survived, re-queued behind the earlier open's close.  Menu
         * commands are ordered state
         * transitions; send them all. */
        if ( command[0] == 'q' || command[0] == 'r' )
            continue;
#endif

        if ( !strcmp(&command[1], &client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].command[1]) )
            return i;


        switch ( command[0] )
        {
            case 100:
            case 118:
                if ( !I_IsEqualUnitWSpace( (char*)&command[2], &client->reliableCommands[i & (MAX_RELIABLE_COMMANDS - 1)].command[2]))
                {
                    continue;
                }
            case 67:
            case 68:
            case 97:
            case 98:
            case 111:
            case 112:
            case 113:
            case 114:
            case 116:
                return i;

            default:
                continue;

        }
    }
    return -1;
}



#ifdef CODOL_SERVER
/*
=============
Deferred configstring updates for loading clients

A client that has received its gamestate but has not yet sent "begin"
(CS_PRIMED) is loading the map and acknowledges nothing for several seconds.
Every configstring change in that window - bot names, appended weapon
definitions, precached effects and models - was queued as its own reliable
"d <index> <value>" command. A full map_restart with 11 training bots queued
well over MAX_RELIABLE_COMMANDS of them and the human was dropped with
EXE_SERVERCOMMANDOVERFLOW before it ever finished loading (qconsole.log,
2026-09-22 21:3x).

Record the latest command for each index instead, and send it once the
client is active, a bounded batch per frame so the reliable window never
fills.

What is recorded is the command's own value, never a table lookup made at
pump time. Wire index numbers do not identify a table: the CoDOL bank, the
fastfile's inherited constants and the retained IW3 table all feed "d"
commands with overlapping numbers, and an inherited asset name (a bot's body
part, a viewmodel arm, a tag) is published with no bank value at all. The
lookup this replaces filed those commands as "retained" and re-read the IW3
table at the CoDOL index, so every human who loaded a map while the bots
dressed received "d 1377 " (empty) or "d 1604 smoke/fog_ground_200_heavy_
rundown_tropical" in place of character part names: bodies lost parts, the
local viewmodel's arms resolved to a nameless XModel with no tag_weapon, and
C1's DObjCreate (0x633f9a) dropped the client with "1073 tag_weapon" (VPS
2026-09-27, zzVertigo).
=============
*/
#define CODOL_CS_DEFER_WORDS ((CODOL_MAX_CONFIGSTRINGS + 31) / 32)
static uint32_t codol_cs_deferred_bits[MAX_CLIENTS][CODOL_CS_DEFER_WORDS];
/* Per client, the latest deferred value of each index. Allocated on first
 * use; bots never receive reliable commands and never allocate. */
static char **codol_cs_deferred_values[MAX_CLIENTS];
static int codol_cs_deferred_count[MAX_CLIENTS];
/* Deferred updates queued since this client's snapshots were last held back
 * for them; bounds the hold (see CODOL_DeferredConfigstringsHoldSnapshot). */
static int codol_cs_pumped_while_held[MAX_CLIENTS];
static int codol_cs_hold_started[MAX_CLIENTS];
/* Set while the pump itself sends, so its commands are queued, not re-deferred. */
static int codol_cs_pumping;

void CODOL_ClearDeferredConfigstrings(client_t *client)
{
    unsigned slot = (unsigned)(client - svs.clients), word;
    if(slot >= MAX_CLIENTS) return;
    if(codol_cs_deferred_values[slot]) {
        for(word = 0; word < CODOL_CS_DEFER_WORDS; ++word) {
            uint32_t bits = codol_cs_deferred_bits[slot][word];
            while(bits) {
                unsigned index = word * 32 + (unsigned)__builtin_ctz(bits);
                bits &= bits - 1;
                free(codol_cs_deferred_values[slot][index]);
                codol_cs_deferred_values[slot][index] = NULL;
            }
        }
    }
    memset(codol_cs_deferred_bits[slot], 0, sizeof(codol_cs_deferred_bits[slot]));
    codol_cs_deferred_count[slot] = 0;
}

/* Returns 1 while this client's snapshot must wait for deferred updates.
 *
 * A snapshot may only name assets whose configstrings C1 has already
 * executed. C1 runs the pending reliable commands up to the snapshot's
 * command sequence first (CG_SetInitialSnapshot 0x46c670 -> 0x46a1a0 at
 * 0x46c89a) and only then builds each entity's model. The pump below sends
 * the backlog a half window at a time and in index order, so a map change
 * with bots spawning during the human's load (about ten updates per bot:
 * name, body models, then the composed weapons at 5363+ and the count 6517
 * last) left the weapons unsent when the first snapshot went out. C1 then
 * built a bot's model with its primary weapon (entityState +0xd6,
 * 0x407bce) and the unbounded bg_weaponDefs[primary] read at 0x45038e hit
 * a slot it had never registered: EXE_CRASH 62c530,45038e,407d8b,45bcfb,
 * 443bd3,46dadc (VPS 2026-09-27, mp_crash_tropical, 11 bots).
 *
 * Holding sends reliable commands only, which is what a loading client
 * already receives, and costs a first snapshot a few round trips. C1 keeps
 * 256 unexecuted commands and executes them only on a snapshot, so the hold
 * is bounded: after CODOL_CS_HOLD_BUDGET pumped updates one snapshot goes
 * out anyway and the hold starts over. */
#define CODOL_CS_HOLD_BUDGET 160
int CODOL_DeferredConfigstringsHoldSnapshot(client_t *client)
{
    unsigned slot = (unsigned)(client - svs.clients);
    if(slot >= MAX_CLIENTS) return 0;
    if(codol_cs_deferred_count[slot] && codol_cs_pumped_while_held[slot] < CODOL_CS_HOLD_BUDGET) {
        if(!codol_cs_hold_started[slot]) {
            codol_cs_hold_started[slot] = svs.time ? svs.time : 1;
            Com_Printf(CON_CHANNEL_SERVER, "CoDOL configstrings: holding snapshots for %s until %d deferred update(s) are sent\n",
                       client->name, codol_cs_deferred_count[slot]);
        }
        return 1;
    }
    if(codol_cs_hold_started[slot])
        Com_Printf(CON_CHANNEL_SERVER, "CoDOL configstrings: snapshots resume for %s after %d ms (%d update(s) sent, %d still deferred)\n",
                   client->name, svs.time - codol_cs_hold_started[slot], codol_cs_pumped_while_held[slot],
                   codol_cs_deferred_count[slot]);
    codol_cs_hold_started[slot] = 0;
    codol_cs_pumped_while_held[slot] = 0;
    return 0;
}

/* 1 while updates recorded for this client are still unsent. A later "d"
 * command must join that backlog rather than overtake it. C1 validates a
 * weapon slot the moment its "d" executes (CG_ConfigStringModified 0x4673c7
 * -> 0x483600) and registers the name at the next free definition, so a new
 * slot 137 sent directly while slots 120..136 still waited in the backlog
 * registered at 120 and dropped the client with "181 *a 39 0 120 137" (VPS
 * 2026-09-27, zzVertigo: a bot dressed during the snapshot hold). */
int CODOL_HasDeferredConfigstrings(const client_t *client)
{
    unsigned slot = (unsigned)(client - svs.clients);
    return !codol_cs_pumping && slot < MAX_CLIENTS && codol_cs_deferred_count[slot] > 0;
}

/* Returns 1 when cmd was a configstring update that is now recorded for
 * later delivery, 0 when it must be queued normally. */
int CODOL_DeferConfigstringCommand(client_t *client, const char *cmd)
{
    unsigned slot = (unsigned)(client - svs.clients);
    unsigned long index;
    const char *p, *value;
    char *copy;
    size_t length;

    if(slot >= MAX_CLIENTS || !cmd || cmd[0] != 'd' || cmd[1] != ' ') return 0;
    p = cmd + 2;
    if(*p < '0' || *p > '9') return 0;
    index = strtoul(p, (char **)&p, 10);
    if(*p != ' ' && *p != '\0') return 0;
    if(index >= CODOL_MAX_CONFIGSTRINGS) return 0;
    value = *p ? p + 1 : p;

    if(!codol_cs_deferred_values[slot]) {
        codol_cs_deferred_values[slot] = calloc(CODOL_MAX_CONFIGSTRINGS, sizeof(char *));
        if(!codol_cs_deferred_values[slot]) return 0; /* queue it normally */
    }
    length = strlen(value);
    copy = malloc(length + 1);
    if(!copy) return 0;
    memcpy(copy, value, length + 1);
    free(codol_cs_deferred_values[slot][index]);
    codol_cs_deferred_values[slot][index] = copy;
    if(!(codol_cs_deferred_bits[slot][index / 32] & (1u << (index % 32)))) {
        codol_cs_deferred_bits[slot][index / 32] |= 1u << (index % 32);
        codol_cs_deferred_count[slot]++;
    }
    if(com_developer && com_developer->integer)
        Com_DPrintf(CON_CHANNEL_SERVER, "CoDOL configstring %lu deferred for client %u (%d pending)\n",
                    index, slot, codol_cs_deferred_count[slot]);
    return 1;
}

/* Called once per server frame for every active client. Index order keeps
 * weapon slots ascending with the count (6517) after them. */
void CODOL_PumpDeferredConfigstrings(client_t *client)
{
    unsigned slot = (unsigned)(client - svs.clients);
    unsigned word, bit, index;
    int sent = 0;

    if(slot >= MAX_CLIENTS || !codol_cs_deferred_count[slot]) return;
    if(client->state != CS_ACTIVE || client->netchan.remoteAddress.type == NA_BOT) {
        if(client->state < CS_CONNECTED) CODOL_ClearDeferredConfigstrings(client);
        return;
    }
    for(word = 0; word < CODOL_CS_DEFER_WORDS; ++word) {
        while(codol_cs_deferred_bits[slot][word]) {
            char *value;
            /* Keep half the window free for gameplay commands. */
            if(client->reliableSequence - client->reliableAcknowledge >= MAX_RELIABLE_COMMANDS / 2)
                goto done;
            bit = __builtin_ctz(codol_cs_deferred_bits[slot][word]);
            index = word * 32 + bit;
            value = codol_cs_deferred_values[slot] ? codol_cs_deferred_values[slot][index] : NULL;
            if(codol_cs_deferred_values[slot]) codol_cs_deferred_values[slot][index] = NULL;
            codol_cs_deferred_bits[slot][word] &= ~(1u << bit);
            codol_cs_deferred_count[slot]--;
            /* The pump's own send must reach the queue even though later
             * indices are still pending (see CODOL_HasDeferredConfigstrings). */
            codol_cs_pumping = 1;
            SV_SendServerCommandNoLoss(client, "d %u %s", index, value ? value : "");
            codol_cs_pumping = 0;
            free(value);
            ++sent;
        }
    }
done:
    codol_cs_pumped_while_held[slot] += sent;
    if(sent && com_developer && com_developer->integer)
        Com_DPrintf(CON_CHANNEL_SERVER, "CoDOL configstrings: sent %d deferred update(s) to %s, %d left\n",
                    sent, client->name, codol_cs_deferred_count[slot]);
    if(!codol_cs_deferred_count[slot]) CODOL_ClearDeferredConfigstrings(client);
}
#endif

void __cdecl SV_AddServerCommand(client_t *client, int type, const char *cmd)
{
#ifdef CODOL_SERVER
    if(com_developer && com_developer->integer && cmd && client->state>=CS_CONNECTED)
        if(CODOL_TRACE_VERBOSE())
            Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL reliable -> %s: %s\n",client->name,cmd);

    /* Menu-stack visibility, for the stuck-cl_paused investigation.
     *
     * C1 clears cl_paused only from its own UI code, and the normal
     * menu-close path (UI_KeyEvent 0x005F3760, write at 0x005F38EE) only
     * does it when, in that same key event, no menu is left open AND the UI
     * key-catcher bit 0x10 is still set AND cl_paused reads exactly 1.
     * C1's "r" handler (0x00468060 -> 0x005F4F20) closes EVERY menu and
     * clears KEYCATCH_UI without ever touching cl_paused, so a server-sent
     * "r" that lands while the escape menu is up tears that menu down behind
     * the client's back and permanently disarms the unpause.
     *
     * q/u open, v closes a popup, r is the close-everything teardown. They
     * are emitted only from the script menu verbs and are rare, so log them
     * unconditionally -- correlating them against the cl_paused userinfo
     * edges logged in SV_UpdateUserinfo_f is the whole test. */
    if(cmd && cmd[0] && (cmd[1] == '\0' || cmd[1] == ' ') &&
       (cmd[0] == 'q' || cmd[0] == 'u' || cmd[0] == 'v' || cmd[0] == 'r'))
    {
        Com_Printf(CON_CHANNEL_SERVER, "CoDOL menucmd -> %i (%s): %s\n",
            (int)(client - svs.clients), client->name, cmd);
    }
#endif
  int v4;
  int i;
  int index;
  char string[64];

    if(client->netchan.remoteAddress.type == NA_BOT)
    {
        return;
    }
    if ( client->canNotReliable ) {
#ifdef CODOL_SERVER
        CODOL_TraceSplashAdmission(client, cmd, "rejected-disabled", -1);
#endif
        return;
    }

#ifdef CODOL_SERVER
    /* A loading client acknowledges nothing; hold its configstring updates
     * until it is active instead of filling the reliable window. That
     * includes a client reconnected by a map change (CS_CONNECTED, no
     * gamestate yet): the new level spawns its bots while it waits for the
     * gamestate, and those updates overflowed the window on the VPS
     * (EXE_SERVERCOMMANDOVERFLOW, 86 "d" commands, 2026-09-27). The
     * gamestate carries every current configstring and clears the record. */
    if ( type && (client->state == CS_CONNECTED ||
                  (client->state == CS_PRIMED && client->gamestateSent) ||
                  (client->state == CS_ACTIVE && CODOL_HasDeferredConfigstrings(client))) &&
         CODOL_DeferConfigstringCommand(client, cmd) )
    {
        return;
    }
#endif

    if ( client->reliableSequence - client->reliableAcknowledge >= MAX_RELIABLE_COMMANDS / 2 || client->state != CS_ACTIVE)
    {
        sub_5310E0(client);

        if(!type) {
#ifdef CODOL_SERVER
            CODOL_TraceSplashAdmission(client, cmd,
                client->state != CS_ACTIVE ? "rejected-inactive" : "rejected-pressure", -1);
#endif
            return;
        }

    }

    v4 = sub_530FC0(client, cmd);

    if ( v4 < 0 )
    {
        ++client->reliableSequence;
    }
    else
    {
        for ( i = v4 + 1; i <= client->reliableSequence; ++v4 )
        {
          memcpy(&client->reliableCommands[v4 & (MAX_RELIABLE_COMMANDS - 1)], &client->reliableCommands[i++ & (MAX_RELIABLE_COMMANDS - 1)], sizeof(reliableCommands_t));
        }
    }

    if ( client->reliableSequence - client->reliableAcknowledge == (MAX_RELIABLE_COMMANDS + 1) )
    {
        Com_PrintNoRedirect(CON_CHANNEL_SERVER,"Client: %i lost reliable commands\n", client - svs.clients);
        /* Dump what filled the window: an overflow drop is otherwise a
         * one-line mystery in qconsole.log. */
        SV_ShowClientUnAckCommands(client);
        Com_PrintNoRedirect(CON_CHANNEL_SERVER,"cmd (overflowing): %8d: %s\n", svs.time, cmd);

    NET_OutOfBandPrint( NS_SERVER, &client->netchan.remoteAddress, "disconnect" );
    SV_DelayDropClient(client, "EXE_SERVERCOMMANDOVERFLOW");

#ifdef CODOL_SERVER
        CODOL_TraceSplashAdmission(client, cmd, "replaced-overflow", -1);
#endif
        type = 1;
        Com_sprintf(string,sizeof(string),"%c \"EXE_SERVERCOMMANDOVERFLOW\"", SV_WIRE_DISCONNECT_COMMAND);
        cmd = string;
    }

    index = client->reliableSequence & ( MAX_RELIABLE_COMMANDS - 1 );
    MSG_WriteReliableCommandToBuffer(cmd, client->reliableCommands[ index ].command, sizeof( client->reliableCommands[ index ].command ));
    client->reliableCommands[ index ].cmdTime = svs.time;
    client->reliableCommands[ index ].cmdType = type;
#ifdef CODOL_SERVER
    CODOL_TraceSplashAdmission(client, cmd, "admitted", client->reliableSequence);
#endif
//    Com_Printf(CON_CHANNEL_SERVER,"ReliableCommand: %s\n", cmd);
}




/*
=================
SV_SendServerCommand

Sends a reliable command string to be interpreted by
the client game module: "cp", "print", "chat", etc
A NULL client will broadcast to all clients
=================
*/
/*known stuff
"t \" ==  open callvote screen
"h \" ==  chat
"c \" ==  print bold to players screen
"e \" ==  print to players console
*/
#ifdef CODOL_SERVER
#include <malloc.h>
int CODOL_ScriptLowerSelfTest(void);
/* Boot-time heap validation. A corrupted allocator only faults later, in
 * whatever allocates next, so the first failing checkpoint is what localises
 * the damage. Developer builds only. */
void CODOL_HeapCheck(const char *where)
{
    int status,probe;
    if(!com_developer || !com_developer->integer) return;
#ifdef _WIN32
    /* _heapchk and its status codes are MSVCRT's; glibc has no equivalent
     * whole-heap walk (mcheck/MALLOC_CHECK_ are armed outside the program).
     * The container-layout probe below is portable and still runs everywhere,
     * so the Linux server build keeps the half of this checkpoint it can. */
    status=_heapchk();
    if(status!=_HEAPOK && status!=_HEAPEMPTY)
        Com_PrintError(CON_CHANNEL_SYSTEM,"CoDOL HEAP DAMAGED at %s (status %d)\n",where,status);
#else
    (void)status;
#endif
    /* Container layout guard. A wrong answer means some translation unit
     * built its standard-library templates under a different #pragma pack and
     * the linker chose those copies for the whole program, which corrupts
     * every container in the build. See the note in stringed_ingame.cpp. */
    probe=CODOL_ScriptLowerSelfTest();
    if(probe!=3)
        Com_PrintError(CON_CHANNEL_SYSTEM,"CoDOL CONTAINER LAYOUT WRONG at %s (probe %d, want 3)\n",where,probe);
}
#endif

#ifdef CODOL_SERVER
/* Developer census of the reliable command letters this server actually emits.
 *
 * C1 kept IW3's one-letter dispatch format but renumbered the table, so a
 * stale letter does not fail, it runs a different valid command. Every send
 * funnels through here, so printing each distinct leading byte once, with its
 * first payload, is enough to catch a sender this tree has not audited.
 * Cross-reference the letter against docs/CODOL_PARITY_PLAN.md appendix A. */
static void CODOL_TraceReliableLetter(const char *message)
{
    static unsigned char seen[128];
    unsigned char letter;
    if (!message || !com_developer || !com_developer->integer) return;
    letter = (unsigned char)message[0];
    if (letter >= sizeof(seen) || seen[letter]) return;
    seen[letter] = 1;
    Com_DPrintf(CON_CHANNEL_SERVER, "CoDOL reliable letter '%c' (0x%02x) first use: %.80s\n",
                (letter >= 0x20 && letter < 0x7f) ? letter : '?', letter, message);
}
#endif

void QDECL SV_SendServerCommandString(client_t *cl, int type, char *message)
{
    client_t	*client;
    int		j;

#ifdef CODOL_SERVER
    CODOL_TraceReliableLetter(message);
#endif

    if ( cl != NULL ){
        SV_AddServerCommand(cl, type, (char *)message );
        return;
    }

    // hack to echo broadcast prints to console
    if ( !strncmp( (char *)message, "say", 3) ) {
        Com_Printf(CON_CHANNEL_SERVER,"broadcast: %s\n", SV_ExpandNewlines((char *)message) );
    }

    // send the data to all relevent clients
    for (j = 0, client = svs.clients; j < sv_maxclients->integer; j++, client++) {
        if ( client->state < CS_PRIMED ) {
            continue;
        }
        SV_AddServerCommand(client, type, (char *)message );
    }
}

void QDECL SV_SendServerCommand_IW(client_t *cl, int cmdtype, const char *fmt, ...) {

    va_list		argptr;
    byte		message[MAX_MSGLEN];


    va_start (argptr,fmt);
    Q_vsnprintf ((char *)message, sizeof(message), fmt,argptr);
    va_end (argptr);
    SV_SendServerCommandString(cl, cmdtype, (char *)message);

}

void QDECL SV_SendServerCommand(client_t *cl, const char *fmt, ...) {
    va_list		argptr;
    byte		message[MAX_MSGLEN];

    va_start (argptr,fmt);
    Q_vsnprintf ((char *)message, sizeof(message), fmt,argptr);
    va_end (argptr);

    SV_SendServerCommandString(cl, 0, (char *)message);

}

void QDECL SV_SendServerCommandNoLoss(client_t *cl, const char *fmt, ...) {
    va_list		argptr;
    byte		message[MAX_MSGLEN];

    va_start (argptr,fmt);
    Q_vsnprintf ((char *)message, sizeof(message), fmt,argptr);
    va_end (argptr);

    SV_SendServerCommandString(cl, 1, (char *)message);

}


/*
==============================================================================

CONNECTIONLESS COMMANDS

==============================================================================
*/

typedef struct leakyBucket_s leakyBucket_t;
struct leakyBucket_s {

    byte	type;

    union {
        byte	_4[4];
        byte	_6[16];
    } ipv;

    unsigned long long	lastTime;
    signed char	burst;

    long		hash;

    leakyBucket_t *prev, *next;
};


typedef struct{

    int max_buckets;
    int max_hashes;
    leakyBucket_t *buckets;
    leakyBucket_t **bucketHashes;
    int queryLimitsEnabled;
    leakyBucket_t infoBucket;
    leakyBucket_t statusBucket;
    leakyBucket_t rconBucket;
}queryLimit_t;


    static queryLimit_t querylimit;



// This is deliberately quite large to make it more of an effort to DoS

/*
================
SVC_RateLimitInit

Init the rate limit system
================
*/
static void SVC_RateLimitInit( ){

    int bytes;

    if(!sv_queryIgnoreMegs->integer)
    {
        Com_Printf(CON_CHANNEL_SERVER,"QUERY LIMIT: Querylimiting is disabled\n");
        querylimit.queryLimitsEnabled = 0;
        return;
    }

    bytes = sv_queryIgnoreMegs->integer * 1024*1024;

    querylimit.max_buckets = bytes / sizeof(leakyBucket_t);
    querylimit.max_hashes = 4096; //static

    int totalsize = querylimit.max_buckets * sizeof(leakyBucket_t) + querylimit.max_hashes * sizeof(leakyBucket_t*);

    querylimit.buckets = L_Malloc(totalsize);
    memset(querylimit.buckets, 0, totalsize);

    if(!querylimit.buckets)
    {
        Com_PrintError(CON_CHANNEL_SERVER,"QUERY LIMIT: System is out of memory. All queries are disabled\n");
        querylimit.queryLimitsEnabled = -1;
    }

    querylimit.bucketHashes = (leakyBucket_t**)&querylimit.buckets[querylimit.max_buckets];
    Com_Printf(CON_CHANNEL_SERVER,"QUERY LIMIT: Querylimiting is enabled\n");
    querylimit.queryLimitsEnabled = 1;
}



/*
================
SVC_HashForAddress
================
*/
__optimize3 __regparm1 static long SVC_HashForAddress( netadr_t *address ) {
    byte 		*ip = NULL;
    size_t	size = 0;
    int			i;
    long		hash = 0;

    switch ( address->type ) {
        case NA_IP:  ip = address->ip;  size = 4; break;
        case NA_IP6: ip = address->ip6; size = 16; break;
        default: break;
    }

    for ( i = 0; i < size; i++ ) {
        hash += (long)( ip[ i ] ) * ( i + 119 );
    }

    hash = ( hash ^ ( hash >> 10 ) ^ ( hash >> 20 ) ^ psvs.randint);
    hash &= ( querylimit.max_hashes - 1 );

    return hash;
}

/*
================
SVC_BucketForAddress

Find or allocate a bucket for an address
================
*/
__optimize3 __regparm3 static leakyBucket_t *SVC_BucketForAddress( netadr_t *address, int burst, int period ) {
    leakyBucket_t		*bucket = NULL;
    int			i;
    long			hash = SVC_HashForAddress( address );
    unsigned long long	now = com_uFrameTime;

    for ( bucket = querylimit.bucketHashes[ hash ]; bucket; bucket = bucket->next ) {

        switch ( bucket->type ) {
            case NA_IP:
                if ( memcmp( bucket->ipv._4, address->ip, 4 ) == 0 ) {
                    return bucket;
                }
                break;

            case NA_IP6:
                if ( memcmp( bucket->ipv._6, address->ip6, 16 ) == 0 ) {
                    return bucket;
                }
                break;

            default:
                break;
        }

    }

    for ( i = 0; i < querylimit.max_buckets; i++ ) {
        int interval;

        bucket = &querylimit.buckets[ i ];
        interval = now - bucket->lastTime;

        // Reclaim expired buckets
        if ( bucket->lastTime > 0 && ( interval > ( burst * period ) || interval < 0 ) )
        {
            if ( bucket->prev != NULL ) {
                bucket->prev->next = bucket->next;
            } else {
                querylimit.bucketHashes[ bucket->hash ] = bucket->next;
            }

            if ( bucket->next != NULL ) {
                bucket->next->prev = bucket->prev;
            }

            Com_Memset( bucket, 0, sizeof( leakyBucket_t ) );
        }

        if ( bucket->type == NA_BAD ) {
            bucket->type = address->type;
            switch ( address->type ) {
                case NA_IP:	bucket->ipv._4[0] = address->ip[0];
                        bucket->ipv._4[1] = address->ip[1];
                        bucket->ipv._4[2] = address->ip[2];
                        bucket->ipv._4[3] = address->ip[3];
                        break;

                case NA_IP6: Com_Memcpy( bucket->ipv._6, address->ip6, 16 ); break;

                default: return NULL;
            }

            bucket->lastTime = now;
            bucket->burst = 0;
            bucket->hash = hash;

            // Add to the head of the relevant hash chain
            bucket->next = querylimit.bucketHashes[ hash ];
            if ( querylimit.bucketHashes[ hash ] != NULL ) {
                querylimit.bucketHashes[ hash ]->prev = bucket;
            }

            bucket->prev = NULL;
            querylimit.bucketHashes[ hash ] = bucket;

            return bucket;
        }
    }

    // Couldn't allocate a bucket for this address
    return NULL;
}


/*
================
SVC_RateLimit
================
*/
/*__optimize3 __attribute__((always_inline)) */
static qboolean SVC_RateLimit( leakyBucket_t *bucket, int burst, int period ) {
    if ( bucket != NULL ) {
        unsigned long long now = com_uFrameTime;
        int interval = now - bucket->lastTime;
        int expired = interval / period;
        int expiredRemainder = interval % period;

        if ( expired > bucket->burst ) {
            bucket->burst = 0;
            bucket->lastTime = now;
        } else {
            bucket->burst -= expired;
            bucket->lastTime = now - expiredRemainder;
        }

        if ( bucket->burst < burst ) {
            bucket->burst++;

            return qfalse;
        }
    }

    return qtrue;
}

/*
================
SVC_RateLimitAddress

Rate limit for a particular address
================
*/
__optimize3 __regparm3 static qboolean SVC_RateLimitAddress( netadr_t *from, int burst, int period ) {

    if(Sys_IsLANAddress(from))
        return qfalse;


    if(querylimit.queryLimitsEnabled == 1)
    {
        leakyBucket_t *bucket = SVC_BucketForAddress( from, burst, period );
        return SVC_RateLimit( bucket, burst, period );

    }else if(querylimit.queryLimitsEnabled == 0){
        return qfalse;

    }else{//Init error, to be save we deny everything
        return qtrue;
    }

}


/*
================
SVC_Status

Responds with all the info that qplug or qspy can see about the server
and all connected players.  Used for getting detailed information after
the simple info query.
================
*/

__optimize3 __regparm1 void SVC_Status( netadr_t *from ) {
    char player[1024];
    char status[MAX_MSGLEN];
    int i;
    client_t    *cl;
    gclient_t *gclient;
    int statusLength;
    int playerLength;
    char infostring[MAX_INFO_STRING];
    mvabuf;

    // Prevent using getstatus as an amplifier
    if ( SVC_RateLimitAddress( from, 2, sv_queryIgnoreTime->integer*1000 ) ) {
    //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Status: rate limit from %s exceeded, dropping request\n", NET_AdrToString( *from ) );
        return;
    }


    // Allow getstatus to be DoSed relatively easily, but prevent
    // excess outbound bandwidth usage when being flooded inbound
    if ( SVC_RateLimit( &querylimit.statusBucket, 20, 20000 ) ) {
    //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Status: overall rate limit exceeded, dropping request\n" );
        return;
    }



    if(strlen(SV_Cmd_Argv(1)) > 128)
        return;

    strcpy( infostring, Cvar_InfoString( CVAR_SERVERINFO | CVAR_NORESTART) );
    // echo back the parameter to status. so master servers can use it as a challenge
    // to prevent timed spoofed reply packets that add ghost servers
    Info_SetValueForKey( infostring, "challenge", SV_Cmd_Argv( 1 ) );

    if(*sv_password->string)
        Info_SetValueForKey( infostring, "pswrd", "1");

    // add "demo" to the sv_keywords if restricted
    if(NET_CompareBaseAdr(&atvimaster, from))
    {
        Info_SetValueForKey( infostring, "protocol", "6" );
    }

    status[0] = 0;
    statusLength = 0;

    for ( i = 0, gclient = level.clients ; i < sv_maxclients->integer ; i++, gclient++ ) {
        cl = &svs.clients[i];
        if ( cl->state >= CS_CONNECTED && !cl->undercover) {
            Com_sprintf( player, sizeof( player ), "%i %i \"%s\"\n",
                         gclient->sess.score, cl->ping, cl->name );
            playerLength = strlen( player );
            if ( statusLength + playerLength >= sizeof( status ) ) {
                break;      // can't hold any more
            }
            strcpy( status + statusLength, player );
            statusLength += playerLength;
        }
    }
    NET_OutOfBandPrint( NS_SERVER, from, "statusResponse\n%s\n%s", infostring, status );
}


/*
================
SVC_Info

Responds with a short info message that should be enough to determine
if a user is interested in a server to do a full status
================
*/
__optimize3 __regparm1 void SVC_Info( netadr_t *from ) {
    int		i, count, humans;
    char		infostring[MAX_INFO_STRING];
    char*		s;
    mvabuf;


    s = SV_Cmd_Argv(1);


    // Prevent using getstatus as an amplifier
    if ( SVC_RateLimitAddress( from, 4, sv_queryIgnoreTime->integer*1000 )) {
    //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Info: rate limit from %s exceeded, dropping request\n", NET_AdrToString( *from ) );
        return;
    }


    // Allow getstatus to be DoSed relatively easily, but prevent
    // excess outbound bandwidth usage when being flooded inbound
    if ( SVC_RateLimit( &querylimit.infoBucket, 100, 100000 ) ) {
    //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Info: overall rate limit exceeded, dropping request\n" );
        return;
    }

    infostring[0] = 0;

    /*
     * Check whether Cmd_Argv(1) has a sane length. This was not done in the original Quake3 version which led
     * to the Infostring bug discovered by Luigi Auriemma. See http://aluigi.altervista.org/ for the advisory.
     */

    // A maximum challenge length of 128 should be more than plenty.
    if(strlen(SV_Cmd_Argv(1)) > 128)
        return;

    // don't count privateclients
    count = humans = 0;
    for ( i = 0 ; i < sv_maxclients->integer ; i++ )
    {
        if ( svs.clients[i].state >= CS_CONNECTED ) {
            count++;
            if (svs.clients[i].netchan.remoteAddress.type != NA_BOT) {
                humans++;
            }
        }
    }

    // echo back the parameter to status. so servers can use it as a challenge
    // to prevent timed spoofed reply packets that add ghost servers

    Info_SetValueForKey( infostring, "challenge", s);


    //Info_SetValueForKey( infostring, "gamename", com_gamename->string );
    Info_SetValueForKey(infostring, "protocol", "6");
    Info_SetValueForKey( infostring, "hostname", sv_hostname->string );

    Info_SetValueForKey( infostring, "mapname", sv_mapname->string );
    Info_SetValueForKey( infostring, "clients", va("%i", count) );
    Info_SetValueForKey( infostring, "g_humanplayers", va("%i", humans));
    Info_SetValueForKey( infostring, "sv_maxclients", va("%i", sv_maxclients->integer - sv_privateClients->integer ) );
    Info_SetValueForKey( infostring, "gametype", sv_g_gametype->string );
    Info_SetValueForKey( infostring, "pure", va("%i", sv_pure->boolean ) );
    Info_SetValueForKey( infostring, "build", va("%i", Sys_GetBuild()));
    Info_SetValueForKey( infostring, "shortversion", va("x%d", PROTOCOL_VERSION) );

    if(*sv_password->string)
    {
        Info_SetValueForKey( infostring, "pswrd", "1");
    }else{
        Info_SetValueForKey( infostring, "pswrd", "0");
    }

    Info_SetValueForKey( infostring, "ff", va("%d", Cvar_VariableIntegerValue("scr_team_fftype")));

        if(Cvar_GetVariantString("scr_game_allowkillcam")){
        Info_SetValueForKey( infostring, "ki", "1");
    }

        if(Cvar_GetVariantString("scr_hardcore")){
        Info_SetValueForKey( infostring, "hc", "1");
    }

        if(Cvar_GetVariantString("scr_oldschool")){
        Info_SetValueForKey( infostring, "od", "1");
    }
    Info_SetValueForKey( infostring, "hw", "1");

#ifdef CODOL_SERVER
    /* Same reason as SV_SetSystemInfoConfig: a pending category token must
     * not become a "mod" flag or a "game" key in the browser reply. */
    FS_CoDOLNormalizeGameDir();
#endif
        if(fs_gameDirVar->string[0] == '\0' || sv_showasranked->boolean){
        Info_SetValueForKey( infostring, "mod", "0");
    }else{
        Info_SetValueForKey( infostring, "mod", "1");
    }
    Info_SetValueForKey( infostring, "voice", va("%i", sv_voice->boolean ) );
#ifdef PUNKBUSTER
    Info_SetValueForKey( infostring, "pb", va("%i", sv_punkbuster->boolean) );
#endif
    if( sv_maxPing->integer ) {
        Info_SetValueForKey( infostring, "sv_maxPing", va("%i", sv_maxPing->integer) );
    }

    if( fs_gameDirVar->string[0] != '\0' ) {
        Info_SetValueForKey( infostring, "game", fs_gameDirVar->string );
    }

    NET_OutOfBandPrint( NS_SERVER, from, "infoResponse\n%s", infostring );
}

#if 0

typedef struct
{
    int challenge;
    int protocol;
    char hostname[256];
    char mapname[64];
    char gamemoddir[64];
    char gamename[64];
    unsigned short steamappid;
    int numplayers;
    int maxclients;
    int numbots;
    char hostos;
    qboolean joinpassword;
    qboolean secure;
    char gameversion[64];
    unsigned int steamid_lower;
    unsigned int steamid_upper;
    unsigned int gameid_lower;
    unsigned int gameid_upper;
    unsigned short joinport;
}queryinfo_t;

typedef struct{
    int challenge;
    int receivedchunks;
    int numchunks;
    char splitmessage[8192];
    int frameseq;
}querysplitmsg_t;


typedef struct{
    int cid;
    char name[32];
    int score;
    float connectedtime;
}queryplayer_t;

typedef struct{
    int count;
    queryplayer_t players[128];
}queryplayers_t;

typedef struct
{
    char name[64];
    char value[256];
}queryrule_t;

typedef struct{
    int count;
    queryrule_t rules[256];
}queryrules_t;

//void CLC_SourceEngineQuery_Players(msg_t* msg, queryinfo_t* query)


void CLC_SourceEngineQuery_Info(msg_t* msg, queryinfo_t* query)
{
    int extrafields;
    char stringbuf[8192];

    //OBB-Header already read
    MSG_ReadLong(msg);
    //I message is already read
    MSG_ReadByte(msg);

    //Start of message
    query->protocol = MSG_ReadByte(msg);
    MSG_ReadString(msg, query->hostname, sizeof(query->hostname));
    MSG_ReadString(msg, query->mapname, sizeof(query->mapname));
    MSG_ReadString(msg, query->gamemoddir, sizeof(query->gamemoddir));
    MSG_ReadString(msg, query->gamename, sizeof(query->gamename));
    query->steamappid = MSG_ReadShort(msg);
    query->numplayers = MSG_ReadByte(msg);
    query->maxclients = MSG_ReadByte(msg);
    query->numbots = MSG_ReadByte(msg);
    //Reading 'd' ?
    MSG_ReadByte(msg);
    //'l', 'm', 'w'
    query->hostos = MSG_ReadByte(msg);
    query->joinpassword = MSG_ReadByte(msg);
    //Reading 0 ?
    query->secure = MSG_ReadByte(msg);
    MSG_ReadString(msg, query->gameversion, sizeof(query->gameversion));

    /* The extra datafields */
    extrafields = MSG_ReadByte(msg);

    if (extrafields & 0x80)
    {
        //Read the join port
        query->joinport = MSG_ReadShort(msg);
    }
    if(extrafields & 0x10)
    {
        //Read the steam id
        query->steamid_lower = MSG_ReadLong(msg);
        query->steamid_upper = MSG_ReadLong(msg);
    }
    if(extrafields & 0x40)
    {
        //Read the sourceTV stuff
        MSG_ReadShort(msg);
        MSG_ReadString(msg, stringbuf, sizeof(stringbuf));
    }
    if(extrafields & 0x20)
    {
        //Read the tags (future use)
        MSG_ReadString(msg, stringbuf, sizeof(stringbuf));
    }
    if(extrafields & 0x01)
    {
        query->gameid_lower = MSG_ReadLong(msg);
        query->gameid_upper = MSG_ReadLong(msg);
    }
    /* Finished with message of type "I" */


}

void CLC_SourceEngineQuery_ReadChallenge(msg_t* msg, queryinfo_t* query)
{
    //OBB-Header already read
    MSG_ReadLong(msg);
    //A message is already read
    MSG_ReadByte(msg);

    query->challenge = MSG_ReadLong(msg);
}

void CLC_SourceEngineQuery_ReadSplitMessage(msg_t* msg, querysplitmsg_t* query)
{
    int receivedindex;
    int splitsize;

    /* reading the split header */
    MSG_ReadLong(msg);
    /* An unique number */
    query->frameseq = MSG_ReadLong(msg);
    /* Total number of packets */
    query->numchunks = MSG_ReadByte(msg);
    /* Packetnumber */
    receivedindex = MSG_ReadByte(msg);
    if(receivedindex > 31)
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CLC_SourceEngineQuery_ReadSplitMessage: Received out of range splitmessage index packet\n");
        return;
    }

    query->receivedchunks |= (1 << receivedindex);
    /* Splitsize */
    splitsize = MSG_ReadShort(msg);
    if(query->numchunks * splitsize >= sizeof(query->splitmessage))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CLC_SourceEngineQuery_ReadSplitMessage: Size of the splitmessage would exceed the splitbuffer size\n");
        return;
    }
    if(receivedindex * splitsize >= (sizeof(query->splitmessage) - splitsize))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CLC_SourceEngineQuery_ReadSplitMessage: Received out of range splitmessage buffer packet\n");
        return;
    }
    MSG_ReadData(msg, &query->splitmessage[receivedindex * splitsize], splitsize);
}

void CLC_SourceEngineQuery_ReadPlayer(msg_t* msg, queryplayers_t* query)
{
    int numcl, i;
    //MSG_WriteLong(&playermsg, -1);
    /* Write the Command-Header */
    //MSG_WriteByte(&playermsg, 'D');
    /* numClients is 0 for now */
    query->count = MSG_ReadByte(msg);

    if(query->count > (  sizeof(query->players)/sizeof(query->players[0])))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CLC_SourceEngineQuery_ReadPlayer: Received out of range player count\n");
        query->count = 0;
        return;
    }

    for ( i = 0; i < numcl ; i++)
    {
        query->players[i].cid = MSG_ReadByte(msg);
        MSG_ReadString(msg, query->players[i].name, sizeof(query->players[i].name));
        query->players[i].score = MSG_ReadLong(msg);
        query->players[i].connectedtime = MSG_ReadFloat(msg);
    }
}

void CLC_SourceEngineQuery_ReadRules(msg_t* msg, queryrules_t* query)
{
    int i;
    //MSG_ReadLong(msg);
    /* Write the Command-Header */
    //MSG_ReadByte(msg);
    /* count */
    query->count = MSG_ReadShort(msg);

    if(query->count > ( sizeof(query->rules)/sizeof(query->rules[0])))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CLC_SourceEngineQuery_ReadPlayer: Received out of range player count\n");
        query->count = sizeof(query->rules)/sizeof(query->rules[0]);
    }
    for ( i = 0; i < query->count ; i++)
    {
        MSG_ReadString(msg, query->rules[i].name, sizeof(query->rules[i].name));
        MSG_ReadString(msg, query->rules[i].value, sizeof(query->rules[i].value));
    }
}
#endif

void SVC_SourceEngineQuery_WriteInfo( msg_t* msg, const char* challengeStr, qboolean masterserver)
{
    int i, humans, bots;
    char cleanhostname[1024];

    MSG_WriteLong(msg, -1);
    MSG_WriteByte(msg, 'I');
    MSG_WriteByte(msg, sv_protocol->integer);

    if(challengeStr[0] || masterserver)
    {
        MSG_WriteString(msg, sv_hostname->string);
    }else{
        Q_strncpyz(cleanhostname, sv_hostname->string, sizeof(cleanhostname));
        Q_CleanStr(cleanhostname);
        MSG_WriteString(msg, cleanhostname);
    }

    MSG_WriteString(msg, sv_mapname->string);

    if(fs_gameDirVar->string[0] == '\0')
    {
        MSG_WriteString(msg, "main");
    }else{
        MSG_WriteString(msg, fs_gameDirVar->string);
    }
    MSG_WriteString(msg, "Call of Duty 4 - Modern Warfare");
    MSG_WriteShort(msg, 7940);

    // don't count privateclients
    bots = humans = 0;
    for ( i = 0 ; i < sv_maxclients->integer ; i++ )
    {
        if ( svs.clients[i].state >= CS_CONNECTED )
        {
            if (svs.clients[i].netchan.remoteAddress.type != NA_BOT) {
                humans++;
            }else{
                bots++;
            }
        }
    }

    MSG_WriteByte(msg, humans);
    MSG_WriteByte(msg, sv_maxclients->integer - sv_privateClients->integer);
    MSG_WriteByte(msg, bots);
    MSG_WriteByte(msg, 'd');

#ifdef _WIN32
    MSG_WriteByte(msg, 'w');
#else
    #ifdef MACOS_X
    MSG_WriteByte(msg, 'm');
    #else
    MSG_WriteByte(msg, 'l');
    #endif
#endif

        if(*sv_password->string){
        MSG_WriteByte(msg, 1);
    }else{
        MSG_WriteByte(msg, 0);
    }
    MSG_WriteByte(msg, 0);
    MSG_WriteString(msg, "1.8");
    /*The extra datafield for port*/
    MSG_WriteByte(msg, 0x80);

    MSG_WriteShort(msg, NET_GetHostPort());

    if(challengeStr[0] || masterserver)
    {
        MSG_WriteString(msg, challengeStr);
        MSG_WriteString(msg, sv_g_gametype->string );

        MSG_WriteByte( msg, Cvar_VariableIntegerValue("scr_team_fftype"));
        MSG_WriteByte( msg, Cvar_VariableBooleanValue("scr_game_allowkillcam"));
        MSG_WriteByte( msg, Cvar_VariableBooleanValue("scr_hardcore"));
        MSG_WriteByte( msg, Cvar_VariableBooleanValue("scr_oldschool"));
        MSG_WriteByte( msg, sv_voice->boolean);


        if(masterserver)
        {
            MSG_WriteLong( msg, psvs.masterServer_id);
            MSG_WriteLong( msg, Sys_GetBuild());
            MSG_WriteString( msg, masterServerSecret);

        }
    }

}



void SVC_SourceEngineQuery_Info( netadr_t* from, const char* challengeStr)
{

    msg_t msg;
    byte buf[MAX_INFO_STRING];

    // Prevent using getstatus as an amplifier
    if ( SVC_RateLimitAddress( from, 4, sv_queryIgnoreTime->integer*1000 )) {
        //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Info: rate limit from %s exceeded, dropping request\n", NET_AdrToString( *from ) );
        return;
    }

    // Allow getstatus to be DoSed relatively easily, but prevent
    // excess outbound bandwidth usage when being flooded inbound
    if ( SVC_RateLimit( &querylimit.infoBucket, 100, 100000 ) ) {
        //	Com_Printf(CON_CHANNEL_SERVER, "SVC_Info: overall rate limit exceeded, dropping request\n" );
        return;
    }

    MSG_Init(&msg, buf, sizeof(buf));

    SVC_SourceEngineQuery_WriteInfo( &msg, challengeStr, qfalse);

    NET_SendPacket(NS_SERVER, msg.cursize, msg.data, from);

}


void SVC_SourceEngineQuery_Challenge( netadr_t* from )
{
    msg_t msg;
    byte buf[MAX_INFO_STRING];

    MSG_Init(&msg, buf, sizeof(buf));

    MSG_WriteLong(&msg, -1);

    MSG_WriteByte(&msg, 'A');

    MSG_WriteLong(&msg, NET_CookieHash(from));

    NET_SendPacket(NS_SERVER, msg.cursize, msg.data, from);
}

#define SPLIT_SIZE 1248

void SVC_SourceEngineQuery_SendSplitMessage( netadr_t* from, msg_t* longmsg )
{
    msg_t msg;
    static int seq;
    byte buf[SPLIT_SIZE + 100];
    int i, numpackets;

    seq++;

    /* In case this packet is short enough */
    if(longmsg->cursize <= SPLIT_SIZE)
    {
        NET_SendPacket(NS_SERVER, longmsg->cursize, longmsg->data, from);
        return;
    }
    /* This will become a split response */

    MSG_Init(&msg, buf, sizeof(buf));

    numpackets = 1 + (longmsg->cursize / SPLIT_SIZE);

    for(i = 0; i < numpackets; i++)
    {
        MSG_Clear(&msg);
        /* writing the split header */
        MSG_WriteLong(&msg, -2);
        /* An unique number */
        MSG_WriteLong(&msg, seq);
        /* Total number of packets */
        MSG_WriteByte(&msg, numpackets);
        /* Packetnumber */
        MSG_WriteByte(&msg, i);
        /* Splitsize */
        MSG_WriteShort(&msg, SPLIT_SIZE);

        if(longmsg->cursize - longmsg->readcount > SPLIT_SIZE)
        {
            Com_Memcpy(&msg.data[msg.cursize], &longmsg->data[longmsg->readcount], SPLIT_SIZE);
            longmsg->readcount += SPLIT_SIZE;
            msg.cursize += SPLIT_SIZE;
        }else{
            Com_Memcpy(&msg.data[msg.cursize], &longmsg->data[longmsg->readcount], longmsg->cursize - longmsg->readcount);
            msg.cursize += (longmsg->cursize - longmsg->readcount);
            longmsg->readcount = longmsg->cursize;
        }
        NET_SendPacket(NS_SERVER, msg.cursize, msg.data, from);
    }

}

void SVC_SourceEngineQuery_Player( netadr_t* from, msg_t* recvmsg )
{

    msg_t playermsg;
    byte pbuf[MAX_MSGLEN];

    int i, numClients, challenge;
    client_t    *cl;
    gclient_t *gclient;
    char cleanplayername[128];


    /* 1st check the challenge */
    MSG_BeginReading(recvmsg);
    /* OOB-Header */
    MSG_ReadLong(recvmsg);
    /* Command Header */
    MSG_ReadByte(recvmsg);
    /* Challenge */
    challenge = MSG_ReadLong(recvmsg);

    if(NET_CookieHash(from) != challenge)
    {
        SVC_SourceEngineQuery_Challenge( from );
        return;
    }

    MSG_Init(&playermsg, pbuf, sizeof(pbuf));
    /* Write the OOB-Header */
    MSG_WriteLong(&playermsg, -1);
    /* Write the Command-Header */
    MSG_WriteByte(&playermsg, 'D');
    /* numClients is 0 for now */
    MSG_WriteByte(&playermsg, 0);

    for ( i = 0, cl = svs.clients, gclient = level.clients, numClients = 0; i < sv_maxclients->integer ; i++, gclient++, cl++) {

        if ( cl->state >= CS_CONNECTED ) {

            MSG_WriteByte(&playermsg, i);

            Q_strncpyz(cleanplayername, cl->name, sizeof(cleanplayername));
            Q_CleanStr(cleanplayername);

            MSG_WriteString(&playermsg, cleanplayername);
            MSG_WriteLong(&playermsg, gclient->sess.score);
            int connectedTime = svs.time - cl->connectedTime;
            if(cl->connectedTime == 0)
            {
                connectedTime = 0;
            }
            MSG_WriteFloat(&playermsg, ((float)(connectedTime))/1000);
            numClients++;
        }
    }
    /* update the playercount */
    playermsg.data[5] = numClients;

    SVC_SourceEngineQuery_SendSplitMessage( from, &playermsg );

}

struct sourceEngineCvars_s
{
    msg_t* msg;
    int num;
};

void	SVC_SourceEngineQuery_WriteCvars(cvar_t const* cvar, void *var ){
    struct sourceEngineCvars_s *data = var;

    if(cvar->flags & (CVAR_SERVERINFO | CVAR_NORESTART) )
    {
        MSG_WriteString(data->msg, cvar->name);
        MSG_WriteString(data->msg, Cvar_DisplayableValue(cvar));
        data->num++;
    }
}


void SVC_SourceEngineQuery_Rules( netadr_t* from, msg_t* recvmsg )
{
    msg_t msg;
    byte buf[MAX_MSGLEN];
    struct sourceEngineCvars_s data;
    int numvars, challenge;

    /* 1st check the challenge */
    MSG_BeginReading(recvmsg);
    /* OOB-Header */
    MSG_ReadLong(recvmsg);
    /* Command Header */
    MSG_ReadByte(recvmsg);
    /* Challenge */
    challenge = MSG_ReadLong(recvmsg);

    if(NET_CookieHash(from) != challenge)
    {
        SVC_SourceEngineQuery_Challenge( from );
        return;
    }

    numvars = 0;

    MSG_Init(&msg, buf, sizeof(buf));
    /* Write the OOB header */
    MSG_WriteLong(&msg, -1);
    /* Write the Command-Header */
    MSG_WriteByte(&msg, 'E');
    /* Number of rules = 0 for now */
    MSG_WriteShort(&msg, numvars);
    /* Write each cvar */
    data.msg = &msg;
    data.num = 0;
    Cvar_ForEach( SVC_SourceEngineQuery_WriteCvars, &data );

    *(short*)&msg.data[5] = data.num;

    SVC_SourceEngineQuery_SendSplitMessage( from, &msg );

}


/*
================
SVC_FlushRedirect

================
*/
static void SV_FlushRedirect( char *outputbuf, qboolean lastcommand ) {
    NET_OutOfBandPrint( NS_SERVER, &svs.redirectAddress, "print\n%s", outputbuf );
}

/*
===============
SVC_RemoteCommand

An rcon packet arrived from the network.
Shift down the remaining args
Redirect all printfs
===============
*/
__optimize3 __regparm2 static void SVC_RemoteCommand( netadr_t *from, msg_t *msg ) {
    // TTimo - scaled down to accumulate, but not overflow anything network wise, print wise etc.
    // (OOB messages are the bottleneck here)
    static int printMsg = 1;
    char		sv_outputbuf[SV_OUTPUTBUF_LENGTH];
    char *cmd_aux;
    char stringlinebuf[MAX_STRING_CHARS];
#ifdef CODOL_SERVER
    int oldInvokerPower, oldInvokerClient;
    uint64_t oldInvokerSteamId;
    char oldInvokerName[64];
#endif

    svs.redirectAddress = *from;

    if ( strcmp (SV_Cmd_Argv(1), sv_rconPassword->string )) {
        //Send only one deny answer out in 100 ms
        if ( SVC_RateLimit( &querylimit.rconBucket, 1, 100 ) ) {
            if (printMsg) {
                Com_Printf(CON_CHANNEL_SERVER, "SVC_RemoteCommand: rate limit exceeded for bad rcon\n" );
                printMsg = 0;
            }
            return;
        }
        printMsg = 1;

        Com_Printf (CON_CHANNEL_SERVER,"Bad rcon from %s\n", NET_AdrToString (from) );
        Com_BeginRedirect (sv_outputbuf, SV_OUTPUTBUF_LENGTH, SV_FlushRedirect);
        Com_Printf (CON_CHANNEL_SERVER,"Bad rcon");
        Com_EndRedirect ();
        return;
    }

    if ( strlen( sv_rconPassword->string) < 8 ) {
        Com_BeginRedirect (sv_outputbuf, SV_OUTPUTBUF_LENGTH, SV_FlushRedirect);
        Com_Printf (CON_CHANNEL_SERVER,"No rconpassword set on server or password is shorter than 8 characters.\n");
        Com_EndRedirect ();
        return;
    }

    //Everything fine, process the request

    MSG_BeginReading(msg);
    MSG_ReadLong(msg); //0xffffffff
    MSG_ReadLong(msg); //rcon

    cmd_aux = MSG_ReadStringLine(msg, stringlinebuf, sizeof(stringlinebuf));

    // https://zerowing.idsoftware.com/bugzilla/show_bug.cgi?id=543
    // get the command directly, "rcon <pass> <command>" to avoid quoting issues
    // extract the command by walking
    // since the cmd formatting can fuckup (amount of spaces), using a dumb step by step parsing

    while(cmd_aux[0]==' ')//Skipping space before the password
        cmd_aux++;

    if(cmd_aux[0]== '"')//Skipping the password
    {
        cmd_aux++;
        while(cmd_aux[0] != '"' && cmd_aux[0])
            cmd_aux++;

        cmd_aux++;
    }else{
        while(cmd_aux[0] != ' ' && cmd_aux[0])
            cmd_aux++;

    }

    while(cmd_aux[0] == ' ')//Skipping space after the password
        cmd_aux++;

    Com_Printf (CON_CHANNEL_SERVER,"Rcon from %s: %s\n", NET_AdrToString (from), cmd_aux );

    Com_BeginRedirect (sv_outputbuf, SV_OUTPUTBUF_LENGTH, SV_FlushRedirect);
#ifdef CODOL_SERVER
    /* Password-authenticated legacy rcon did not establish an invoker.  The
     * power-aware command registry therefore discarded map/map_restart while
     * ordinary set commands succeeded, leaving the advertised map different
     * from the loaded BSP.  Give this authenticated command the same console
     * identity used by Source RCON and restore the prior frame identity. */
    oldInvokerPower = Cmd_GetInvokerPower();
    oldInvokerClient = Cmd_GetInvokerClnum();
    oldInvokerSteamId = Cmd_GetInvokerSteamID();
    Cmd_GetInvokerName(oldInvokerName, sizeof(oldInvokerName));
    Cmd_SetCurrentInvokerInfo(100, -1, 0, "rcon");
#endif
#ifdef PUNKBUSTER
    if(!Q_stricmpn(cmd_aux, "pb_sv_", 6)){

        Q_strchrrepl(cmd_aux, '\"', ' ');
        Cmd_ExecuteSingleCommand(0,0, cmd_aux);
        PbServerForceProcess();
    }else
#endif
        Cmd_ExecuteSingleCommand(0,0, cmd_aux);

#ifdef CODOL_SERVER
    Cmd_SetCurrentInvokerInfo(oldInvokerPower, oldInvokerClient,
                              oldInvokerSteamId, oldInvokerName);
#endif
    Com_EndRedirect ();

}

#ifdef IW4OL_UPDATE
#define UPDATE_PROXYSERVER_NAME ""
#define UPDATE_PROXYSERVER_PORT_RELEASE 27953
#define UPDATE_PROXYSERVER_PORT_BETA 27954
#define UPDATE_PROXYSERVER_PORT_RC 27955

#ifdef RELEASE_CANDIDATE

    #define UPDATE_PROXYSERVER_PORT UPDATE_PROXYSERVER_PORT_RC

#else

#ifndef BETA_RELEASE
    #define UPDATE_PROXYSERVER_PORT UPDATE_PROXYSERVER_PORT_RELEASE
#else
    #define UPDATE_PROXYSERVER_PORT UPDATE_PROXYSERVER_PORT_BETA
#endif
#endif

typedef enum
{
    UPDCONN_CHALLENGING,
    UPDCONN_CONNECT
}update_connState_t;

typedef struct
{
    update_connState_t state;
    int mychallenge;
    int serverchallenge;
    char authkey[128];
    netadr_t updateserveradr;
    unsigned int lastsenttime;
    unsigned int lastseentime;
}update_connection_t;

update_connection_t update_connection;



void SV_UpdateProxyUpdateBadChallenge(netadr_t* from)
{
    int mychallenge;

    if(SV_Cmd_Argc() < 2)
    {
        return;
    }
    update_connection.lastseentime = Sys_Seconds();
    mychallenge = atoi(SV_Cmd_Argv(1));

    if(mychallenge != update_connection.mychallenge)
    {
        return;
    }

    if(!NET_CompareAdr(from, &update_connection.updateserveradr))
    {
        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyUpdateBadChallenge: Packet not from updateserver\n");
        return;
    }

    update_connection.state = UPDCONN_CHALLENGING;
    Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyUpdateBadChallenge: Will start challenging\n");
}

void SV_UpdateProxyChallengeResponse(netadr_t* from)
{
    int mychallenge;
    int svchallenge;

    if(SV_Cmd_Argc() < 3)
    {
        return;
    }

    update_connection.lastseentime = Sys_Seconds();

    mychallenge = atoi(SV_Cmd_Argv(2));

    if(mychallenge != update_connection.mychallenge)
    {
        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyChallengeResponse: Bad challenge\n");
        return;
    }

    if(!NET_CompareAdr(from, &update_connection.updateserveradr))
    {
        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyChallengeResponse: Packet not from updateserver\n");
        return;
    }

    svchallenge = atoi(SV_Cmd_Argv(1));
    update_connection.serverchallenge = svchallenge;
    update_connection.state = UPDCONN_CONNECT;
}

void SV_UpdateProxyConnectResponse( netadr_t* from )
{

    int mychallenge;
    int clchallenge;
    int i;
    unsigned short qport;
    client_t* cl;

    if(SV_Cmd_Argc() < 4)
    {
        return;
    }
    mychallenge = atoi(SV_Cmd_Argv(1));

    update_connection.lastseentime = Sys_Seconds();

    if(mychallenge != update_connection.mychallenge)
    {
//        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyConnectResponse: Bad challenge\n");
        return;
    }

    if(!NET_CompareAdr(from, &update_connection.updateserveradr))
    {
//        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyConnectResponse: Packet not from updateserver\n");
        return;
    }

    clchallenge = atoi(SV_Cmd_Argv(2));
    qport = atoi(SV_Cmd_Argv(3));

    for(cl = svs.clients, i = 0; i < sv_maxclients->integer; ++i, ++cl)
    {
        if(cl->state == CS_ZOMBIE && cl->challenge == clchallenge && cl->netchan.qport == qport)
        {
            break;
        }
    }

    if(i == sv_maxclients->integer)
    {
//        Com_Printf(CON_CHANNEL_SERVER,"SV_UpdateProxyConnectResponse: Bad challenge for client\n");
        return;
    }

    cl->updateconnOK = qtrue;

}

void SV_ReceiveFromUpdateProxy( msg_t *msg )
{
    int i;
    client_t* cl;

    /* Callenge 0x4 */
    int clchallenge = MSG_ReadLong(msg);
    /* sequence 0x8 */
    int sequence = MSG_ReadLong(msg);
    /* qport 0xC */
    unsigned short qport = MSG_ReadShort(msg);

    update_connection.lastseentime = Sys_Seconds();

    /* data 0xE */
    for(cl = svs.clients, i = 0; i < sv_maxclients->integer; ++i, ++cl)
    {
        if(cl->state == CS_ZOMBIE && cl->challenge == clchallenge && cl->netchan.qport == qport)
        {
            break;
        }
    }

    if(i == sv_maxclients->integer)
    {
//        Com_Printf(CON_CHANNEL_SERVER,"SV_ReceiveFromUpdateProxy: Received packet for bad client\n");
        NET_OutOfBandPrint(NS_SERVER, &update_connection.updateserveradr, "disconnect %d %d", update_connection.serverchallenge, clchallenge);
        return;
    }

    *(uint32_t*)&msg->data[10] = sequence;
    NET_SendPacket(NS_SERVER, msg->cursize - 10, msg->data +10, &svs.clients[i].netchan.remoteAddress);

}

void SV_PassToUpdateProxy(msg_t *msg, client_t *cl)
{
    byte outbuf[MAX_MSGLEN];

    msg_t outmsg;

    MSG_Init(&outmsg, outbuf, sizeof(outbuf));

    /* Update packet header */
    MSG_WriteLong(&outmsg, 0xfffffffe);
    /* client challenge */
    MSG_WriteLong(&outmsg, cl->challenge);
    MSG_WriteData(&outmsg, msg->data, msg->cursize);

    NET_SendPacket(NS_SERVER, outmsg.cursize, outmsg.data, &update_connection.updateserveradr);

}

void SV_ConnectWithUpdateProxy(client_t *cl)
{


    int res;
    char info[MAX_STRING_CHARS];
    mvabuf;
    netadr_t* defif;

    switch(update_connection.state)
    {
        case UPDCONN_CHALLENGING:

            if(update_connection.mychallenge == 0)
            {
                Com_RandomBytes((byte*)&update_connection.mychallenge, sizeof(update_connection.mychallenge));
            }

            if(update_connection.updateserveradr.type == NA_BAD || sv_updatebackendname->modified)
            {
                if(!sv_updatebackendname->string[0])
                {
                    Com_Printf(CON_CHANNEL_SERVER,"Cvar sv_updatebackendname is empty. Can not update cod4 client.\n");
                    return;
                }

                Com_Printf(CON_CHANNEL_SERVER,"Resolving %s\n", sv_updatebackendname->string);
                Cvar_ClearModified(sv_updatebackendname);
                res = NET_StringToAdr(sv_updatebackendname->string, &update_connection.updateserveradr, NA_IP);
                defif = NET_GetDefaultCommunicationSocket(NA_IP);
                if(defif == NULL)
                {
                    Com_Printf(CON_CHANNEL_SERVER,"Missing outgoing interface. Can not send data to updateserver\n");
                    update_connection.updateserveradr.type = NA_BAD;
                    return;
                }
                update_connection.updateserveradr.sock = defif->sock;
                if(res == 2)
                {
                    // if no port was specified, use the default master port
                    update_connection.updateserveradr.port = BigShort(UPDATE_PROXYSERVER_PORT);
                }
                if(res)
                {
                    Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", sv_updatebackendname->string, NET_AdrToString(&update_connection.updateserveradr));
                }else{
                    Com_Printf(CON_CHANNEL_SERVER, "%s has no IPv4 address.\n", sv_updatebackendname->string);
                    return;
                }
            }

            if(update_connection.updateserveradr.type == NA_IP)
            {
                NET_OutOfBandPrint( NS_SERVER, &update_connection.updateserveradr, "updgetchallenge %d %s", update_connection.mychallenge, "noguid");
                update_connection.lastsenttime = Sys_Seconds();
            }
            return;

        case UPDCONN_CONNECT:
            if(sv_updatebackendname->modified)
            {
                update_connection.state = UPDCONN_CHALLENGING;
                return;
            }
            info[0] = '\0';

            Info_SetValueForKey(info, "challenge", va("%d", update_connection.serverchallenge));
            Info_SetValueForKey(info, "rtnchallenge", va("%d", update_connection.mychallenge));
            Info_SetValueForKey(info, "clchallenge", va("%d", cl->challenge));
            Info_SetValueForKey(info, "name", cl->name);
            Info_SetValueForKey(info, "clremote", NET_AdrToString(&cl->netchan.remoteAddress));
            Info_SetValueForKey(info, "qport", va("%hi", cl->netchan.qport));
            Info_SetValueForKey(info, "protocol", va("%hi", cl->protocol));

            NET_OutOfBandPrint( NS_SERVER, &update_connection.updateserveradr, "updconnect \"%s\"", info);
            update_connection.lastsenttime = Sys_Seconds();
            return;

    }


}


#endif


void SV_HostMigrationReadPacket(netadr_t* from, msg_t* msg);


/*
=================
SV_ConnectionlessPacket

A connectionless packet has four leading 0xff
characters to distinguish it from a game channel.
Clients that are in the game can still send
connectionless packets.
===========h======
*/
__optimize3 __regparm2 void SV_ConnectionlessPacket( netadr_t *from, msg_t *msg ) {
    char	*s;
    char	*c;
    char	stringlinebuf[MAX_STRING_CHARS];

    MSG_BeginReading( msg );
    MSG_ReadLong( msg );		// skip the -1 marker

    s = MSG_ReadStringLine( msg, stringlinebuf, sizeof(stringlinebuf) );
    SV_Cmd_TokenizeString( s );

    c = SV_Cmd_Argv(0);
    Com_DPrintf(CON_CHANNEL_SERVER,"SV packet %s: %s\n", NET_AdrToString(from), s);
    //Most sensitive OOB commands first
        if (!Q_stricmp(c, "getstatus")) {
        SVC_Status( from );

        } else if (!Q_stricmp(c, "getinfo")) {
        SVC_Info( from );

        } else if (!Q_stricmp(c, "rcon")) {
        SVC_RemoteCommand( from, msg );
    } else if (!Q_stricmp(c, "connect")) {
        SV_DirectConnect( from );
#ifdef CODOL_SERVER
    } else if (!Q_stricmp(c, "heartbeat")) {
        int i;
        static const byte response[] = "\xff\xff\xff\xffheartbeatresponse";
        if(CODOL_NetworkAuthenticated(from)) {
            for(i = 0; i < sv_maxclients->integer; ++i) {
                client_t *cl = &svs.clients[i];
                if(cl->state >= CS_CONNECTED && CODOL_ClientStatsUpload(i) &&
                   NET_CompareAdr(from, &cl->netchan.remoteAddress)) {
                    cl->lastPacketTime = svs.time;
                    NET_SendPacket(NS_SERVER, sizeof(response), response, from);
                    break;
                }
            }
        }
#endif
#ifdef IW4OL_UPDATE

    } else if (!Q_stricmp(c, "stats")) {
        SV_ReceiveStats(from, msg);

#endif

        } else if (!Q_stricmp(c, "rcon")) {
        SVC_RemoteCommand( from, msg );

    } else if (!Q_stricmp(c, "getchallenge")) {
        SV_GetChallenge(from);

#ifdef IW4OL_UPDATE
    } else if (!Q_stricmp(c, "updbadchallenge")) {
        SV_UpdateProxyUpdateBadChallenge( from );
    } else if (!Q_stricmp(c, "updchallengeResponse")) {
        SV_UpdateProxyChallengeResponse( from );
    } else if (!Q_stricmp(c, "updconnectResponse")) {
        SV_UpdateProxyConnectResponse( from );

#endif

    } else if (!Q_stricmp(c, "HostMigrationPacket")) {
        SV_HostMigrationReadPacket(from, msg);

    } else if (!strcmp(c, "v")) {
        SV_VoicePacket(from, msg);

    } else if (!Q_strncmp("TSource Engine Query", (char *) &msg->data[4], 20)) {
        SVC_SourceEngineQuery_Info( from, SV_Cmd_Argv(3));
    } else if(msg->data[4] == 'V'){
        SVC_SourceEngineQuery_Rules( from, msg );
    } else if(msg->data[4] == 'U'){
        SVC_SourceEngineQuery_Player( from, msg );
    } else if(msg->data[4] == 'W'){
        SVC_SourceEngineQuery_Challenge( from );
    } else if (!Q_stricmp(c, "error")) {
        char errbuf[256];
        Com_Printf(CON_CHANNEL_SERVER,"Error: %s\n", MSG_ReadString(msg, errbuf, sizeof(errbuf)));
    } else {
        Com_DPrintf(CON_CHANNEL_SERVER,"bad connectionless packet from %s\n", NET_AdrToString (from));
    }
    SV_Cmd_EndTokenizedString();
    return;
}


//============================================================================

/*
=================
SV_PacketEvent
=================
*/
__optimize3 __regparm2 void SV_PacketEvent( netadr_t *from, msg_t *msg ) {

    client_t    *cl;
    unsigned short qport;
    int seq;
#ifndef CODOL_SERVER
    int csack;
#endif

    if(!com_sv_running->boolean)
            return;

    if ( msg->cursize < 4 )
    {
        return;
    }
    MSG_BeginReading( msg );
    seq = MSG_ReadLong( msg );           // sequence number

    // check for connectionless packet (0xffffffff) first
    if ( seq == -1 )
    {
        SV_ConnectionlessPacket( from, msg );
        return;
    }
    // SV_ResetSekeletonCache();

    // read the qport out of the message so we can fix up
    // stupid address translating routers

#ifdef IW4OL_UPDATE
    if(seq == 0xfffffffe)
    {
        SV_ReceiveFromUpdateProxy( msg );
        return;
    }
#endif
    qport = MSG_ReadShort( msg );  // & 0xffff;

    // find which client the message is from
    cl = SV_ReadPackets( from, qport );

    if(cl == NULL)
    {
        // if we received a sequenced packet from an address we don't recognize,
        // send an out of band disconnect packet to it
        NET_OutOfBandPrint( NS_SERVER, from, "disconnect" );
        return;
    }

    if(seq == 0xfffffff0)
    {
#ifndef CODOL_SERVER
        ReliableMessagesReceiveNextFragment( cl->reliablemsg.netstate , msg );
#endif
        return;
    }
#ifdef IW4OL_UPDATE
    if(cl->needupdate && cl->updateconnOK)
    {
        cl->lastPacketTime = svs.time;
        SV_PassToUpdateProxy(msg, cl);
        return;
    }
#endif
    // make sure it is a valid, in sequence packet
    if ( !Netchan_Process( &cl->netchan, msg ) )
    {
        return;
    }

    // zombie clients still need to do the Netchan_Process
    // to make sure they don't need to retransmit the final
    // reliable message, but they don't do any other processing
#ifdef CODOL_SERVER
    if (msg->cursize - msg->readcount < 9) return;
    cl->serverId = MSG_ReadByte(msg);
    cl->messageAcknowledge = (uint32_t)MSG_ReadLong(msg) & 0x7fffffff;
#else
    cl->serverId = MSG_ReadLong( msg );
    cl->messageAcknowledge = MSG_ReadLong( msg );
#endif

    if(cl->messageAcknowledge < 0){
        Com_Printf(CON_CHANNEL_SERVER,"Invalid reliableAcknowledge message from %s - reliableAcknowledge is %i\n", cl->name, cl->reliableAcknowledge);
        return;
    }

    cl->reliableAcknowledge = MSG_ReadLong( msg );

    if((cl->reliableSequence - cl->reliableAcknowledge) > (MAX_RELIABLE_COMMANDS - 1) || (cl->reliableSequence - cl->reliableAcknowledge) < 0){
        Com_Printf(CON_CHANNEL_SERVER,"Out of range reliableAcknowledge message from %s - reliableSequence is %i, reliableAcknowledge is %i\n",
        cl->name, cl->reliableSequence, cl->reliableAcknowledge);
        cl->reliableAcknowledge = cl->reliableSequence;
        return;
    }

    //New info for configdata


#ifndef CODOL_SERVER
    csack = MSG_ReadLong( msg );
    if(csack > cl->configDataAcknowledge)
    { //csack can be lower than cl->configDataAcknowledge in case when server wrote gamestate the client has not yet parsed. Ignoring this data here.
        cl->configDataAcknowledge = csack;
    }
#endif
    if (msg->overflowed) return;

    SV_Netchan_Decode(cl, &msg->data[msg->readcount], msg->cursize - msg->readcount);

    if ( cl->state == CS_ZOMBIE )
    {
        return;
    }

    cl->lastPacketTime = svs.time;  // don't timeout

    SV_ExecuteClientMessage( cl, msg );
}


/*
==============================================================================

MASTER SERVER FUNCTIONS

==============================================================================
*/

#define HEARTBEAT_TIMELIMIT 20000

typedef struct
{
    netadr_t adr4;
    netadr_t adr6;
    byte message[2000];
    int messagelen;
    qboolean locked;
    qboolean authoritative;
    netadr_t* iplist;
    int ipcount;
    qboolean* needticket;
    qboolean* threadlock;
    char* challengei4;
    char* challengei6;
    byte* msgtokenstart;
    char token[48];
}masterHeartbeatThreadOptions_t;


void SV_HeartBeatMessageLoop(msg_t* msg, qboolean authoritative, qboolean *needticket, char* challenge)
{
    byte databuf[8192];
    char stringline[1024];
    char newchallenge[65];
    msg_t singlemsg;
    int ic;
    int k;
    client_t* cl;

    while(msg->readcount < msg->cursize)
    {
        int messagelen = MSG_ReadLong(msg);
        if(messagelen >= sizeof(databuf))
        {
            Com_PrintError(CON_CHANNEL_SERVER,"Oversizemessage from masterserver\n");
            return;
        }
        MSG_ReadData(msg, databuf, messagelen);

        MSG_InitReadOnly(&singlemsg, databuf, messagelen);
        singlemsg.cursize = singlemsg.maxsize;
        MSG_BeginReading(&singlemsg);

        switch(MSG_ReadLong(&singlemsg))
        {
            case -1:
            case 0:
                return;
            case 1:
                //Response about the registering state
                ic = MSG_ReadLong(&singlemsg);
                if(ic == 1)
                {
                    Com_DPrintf(CON_CHANNEL_SERVER,"Server is registered on the masterserver\n");
                }else if(ic == 0){
                    Com_PrintError(CON_CHANNEL_SERVER,"Failure registering server on masterserver. Errorcode: 0x%x\n", MSG_ReadLong(&singlemsg));
                }else if(ic == 2){
                    Com_PrintError(CON_CHANNEL_SERVER,"Failure registering server on masterserver. Server address is banned: %s\n", MSG_ReadString(&singlemsg, stringline, sizeof(stringline)));
                }else if(ic == 3){
                    Com_Printf(CON_CHANNEL_SERVER,"Masterserver needs token to complete registration\n");
                    *needticket = qtrue;
                    MSG_ReadString(&singlemsg, challenge, 65);
                    svs.nextHeartbeatTime = com_uFrameTime + 3000000; //Now but with ticket
                }else if(ic == 5){
                    Com_Printf(CON_CHANNEL_SERVER,"Masterserver didn't load token database yet. Try again later\n");
                    *needticket = qtrue;
                    MSG_ReadString(&singlemsg, challenge, 65);
                    svs.nextHeartbeatTime = com_uFrameTime + 300000000; //try again in 5 minutes
                }else if(ic == 4){
                    MSG_ReadString(&singlemsg, newchallenge, 65);
                    if(strcmp(challenge, newchallenge) == 0)
                    {
                        Com_Printf(CON_CHANNEL_SERVER, "sv_authtoken is invalid! Abandoning master server registration\n");
                        svs.nextHeartbeatTime = com_uFrameTime + 3600000000u; //Try again in 1 hour
                    }else{
                        Com_Printf(CON_CHANNEL_SERVER, "Bad challenge! Retrying...\n");
                        svs.nextHeartbeatTime = com_uFrameTime + 8000000; //Now but with ticket
                        Q_strncpyz(challenge, newchallenge, 65);
                    }
                    *needticket = qtrue;
                }
                break;
            case 2:
                //Remote enforced restart (Usually for protocol mismatch) (Servers which don't respond to this are usually rendered obsolete soon after a new protocol update)
                ic = MSG_ReadLong(&singlemsg);
                if(ic == 1)
                {
                    MSG_ReadString(&singlemsg, stringline, sizeof(stringline));
                    if(authoritative)
                    {
                        Q_strncpyz(svs.sysrestartmessage, stringline, sizeof(svs.sysrestartmessage));
                        Com_Printf(CON_CHANNEL_SERVER,"Received restart message: %s\n", svs.sysrestartmessage);
                        for(cl = svs.clients, k = 0; k < sv_maxclients->integer; ++k, ++cl)//Restart server immediately when empty
                        {
                            if(cl->state == CS_ACTIVE && cl->netchan.remoteAddress.type != NA_BOT)
                            {
                                break;
                            }
                        }
                        if(k == sv_maxclients->integer)
                        {
                            Cbuf_AddText("map_restart;\n");
                        }
                    }else{
                        Com_Printf(CON_CHANNEL_SERVER,"Received restart message from masterserver which is not authoritative. Ignoring\n");
                    }
                }
                break;
            case 3:
                ic = MSG_ReadLong(&singlemsg);
                if(ic == 1)
                {
                    MSG_ReadString(&singlemsg, stringline, sizeof(stringline));
                    if(authoritative)
                    {
                        SV_SendServerCommand(NULL, SV_CHAT_CMD " \"^5Broadcast^7: %s\"\n", stringline);
                    }else{
                        Com_Printf(CON_CHANNEL_SERVER,"Received broadcast message from masterserver which is not authoritative. Ignoring\n");
                    }
                }
                break;
            default:
                //Unsupported Cmds just ignore
                break;
        }
    }
}


void SV_SendReceiveHeartbeatTCP(netadr_t* adr, netadr_t* sourceadr, byte* message, int qlen, qboolean authoritative, qboolean* needticket, char* challenge)
{
    int l = 0;
    byte response[16384];
    char line[256];
    msg_t msg;
    int socket;
    netadr_t bindaddr = *sourceadr;
    bindaddr.port = 0;
    socket = -1;

    if((bindaddr.type == NA_IP6 || bindaddr.type == NA_TCP6) && bindaddr.ip6[0] == 0)
    {
        netadr_t ip6announce;
        ip6announce.port = 0;
        int dx = 0;
        do
        {
            dx = NET_GetStaticIPv6Address(&ip6announce, dx);
            if(dx > 0)
            {
                if(com_developer->integer)
                {
                    socket = NET_TcpClientConnectFromAdrToAdr( adr, &ip6announce );
                }else{
                    socket = NET_TcpClientConnectFromAdrToAdrSilent( adr, &ip6announce );
                }
            }
        }while(dx > 0 && socket == -1);
        if(socket >= 0)
        {
            NET_AdrToStringShortMT(&ip6announce, line, sizeof(line));
            Com_DPrintf(CON_CHANNEL_SERVER,"Cvar net_ip6 is undefined. Announcing address %s!\n", line);
        }
    }

    if(socket == -1)
    {
        if(com_developer->integer)
        {
            socket = NET_TcpClientConnectFromAdrToAdr( adr, &bindaddr );
        }else{
            socket = NET_TcpClientConnectFromAdrToAdrSilent( adr, &bindaddr );
        }
    }
    if(socket >= 0)
    {
        qboolean error = qtrue;
        int slen;
        int rlen;
        int rlentotal = 0;
        int timeout = Sys_Milliseconds() + HEARTBEAT_TIMELIMIT;

        do
        {
            slen = NET_TcpSendData( socket, message +l, qlen -l, NULL, 0);
            if(slen >= 0)
            {
                l += slen;
            }
            Sys_SleepUSec(20000);
        }while(l != qlen && (slen >= 0 || slen == NET_WANT_WRITE) && timeout > Sys_Milliseconds());

        if(l == qlen && slen >= 0)
        {
            while (timeout > Sys_Milliseconds())
            {
                rlen = NET_TcpClientGetData( socket, response + rlentotal, sizeof(response) - rlentotal, NULL, 0);
                if(rlen > 0)
                {
                    rlentotal += rlen;
                }else if(rlen == 0){
                    //We are done
                    error = qfalse;
                    break;
                }else if(rlen != NET_WANT_READ){
                    //Error case...
                    break;
                }
                Sys_SleepUSec(20000);
            }
        }
        if(!error && rlentotal > 4)
        {
            MSG_Init(&msg, response, rlentotal);
            msg.cursize = msg.maxsize;
            MSG_BeginReading(&msg);
            if(MSG_ReadLong(&msg) == -1)
            {
                MSG_ReadString(&msg, line, sizeof(line));
                if(Q_stricmp(line, "masterHeartbeatResponse") == 0)
                {
                    MSG_ReadLong(&msg); //MessageID maybe future use but placeholder here
                    SV_HeartBeatMessageLoop(&msg, authoritative, needticket, challenge);
                }else{
                    Com_Printf(CON_CHANNEL_SERVER,"Corrupted Masterserver response\n");
                }
            }else{
                Com_Printf(CON_CHANNEL_SERVER,"Corrupted Masterserver response\n");
            }
        }else{
            if(timeout < Sys_Milliseconds())
            {
                Com_Printf(CON_CHANNEL_SERVER,"Connection to masterserver timeout\n");
            }else{
                Com_Printf(CON_CHANNEL_SERVER,"Invalid or empty response from masterserver\n");
            }
        }
        NET_TcpCloseSocket(socket);
    }else{
    //	Com_Printf(CON_CHANNEL_SERVER,"Network error while attempting to register on masterserver \n");
    }
}

void* SV_SendHeartbeatThread(void* arg)
{
    masterHeartbeatThreadOptions_t* opts = arg;
    int count = opts->ipcount;
    int i;
    char challengehash[512];
    char finalsha[65];

    netadr_t* iplist = opts->iplist;
    for(i = 0; i < count; ++i)
    {
        char adrstr[128];
        char adrstrdst[128];

        if(iplist[i].type == NA_IP && opts->adr4.type == NA_IP && iplist[i].ip[0] != 127 && iplist[i].ip[0] < 224)
        {
            //IPv4
            Com_DPrintf(CON_CHANNEL_SERVER,"Sending master heartbeat from %s to %s\n", NET_AdrToStringMT(&iplist[i], adrstr, sizeof(adrstr)),
            NET_AdrToStringMT(&opts->adr4, adrstrdst, sizeof(adrstrdst)));
            if(opts->msgtokenstart)
            {
                Com_sprintf(challengehash, sizeof(challengehash), "%s.%s", opts->token, opts->challengei4);
                unsigned long size = sizeof(finalsha);
                Sec_HashMemory(SEC_HASH_SHA256,(void *)challengehash,strlen(challengehash),finalsha,&size,qfalse);
                Q_strupr(finalsha);
                memcpy(opts->msgtokenstart, finalsha, 64);
            }
            SV_SendReceiveHeartbeatTCP(&opts->adr4, &iplist[i], opts->message, opts->messagelen, opts->authoritative, opts->needticket, opts->challengei4);
        }else if(iplist[i].type == NA_IP6 && opts->adr6.type == NA_IP6 && iplist[i].ip6[0] < 0xfe){
            //IPv6
            Com_DPrintf(CON_CHANNEL_SERVER,"Sending master heartbeat from %s to %s\n", NET_AdrToStringMT(&iplist[i], adrstr, sizeof(adrstr)),
            NET_AdrToStringMT(&opts->adr6, adrstrdst, sizeof(adrstrdst)));

            if(opts->msgtokenstart)
            {
                Com_sprintf(challengehash, sizeof(challengehash), "%s.%s", opts->token, opts->challengei6);
                unsigned long size = sizeof(finalsha);
                Sec_HashMemory(SEC_HASH_SHA256,(void *)challengehash,strlen(challengehash),finalsha,&size,qfalse);
                Q_strupr(finalsha);
                memcpy(opts->msgtokenstart, finalsha, 64);
            }

            SV_SendReceiveHeartbeatTCP(&opts->adr6, &iplist[i], opts->message, opts->messagelen, opts->authoritative, opts->needticket, opts->challengei6);
        }
    }

    opts->locked = qfalse;
    *(opts->threadlock) = qfalse;
    return NULL;
}


typedef struct
{
    netadr_t i4;
    netadr_t i6;
    qboolean authoritative; //Can send commands server executes. Like restart etc.
    char name[64];
    qboolean needticket;
    char challengei4[73];
    char challengei6[73];
    qboolean threadlock;
}masterserver_t;


/*
================
SV_MasterHeartbeat

Send a message to the masters every few minutes to
let it know we are alive, and log information.
We will also have a heartbeat sent when a server
changes from empty to non-empty, and full to non-full,
but not on every player enter or exit.
================
*/
void SV_CreateAndSendMasterheartbeatMessage(const char* message, masterserver_t* masrv)
{
    msg_t msg;
    char string[1024];
    masterHeartbeatThreadOptions_t *opts = NULL;
    static masterHeartbeatThreadOptions_t options[8];
    int i;

    netadr_t *adr4 = &masrv->i4;
    netadr_t *adr6 = &masrv->i6;
    qboolean authoritative = masrv->authoritative;


    if(adr4 == NULL || adr6 == NULL || message == NULL)
    {
        return;
    }

    for(i = 0; i < 8; ++i)
    {
        if(options[i].locked == qfalse)
        {
            opts = &options[i];
            break;
        }
    }
    if(opts == NULL)
    {
        return;
    }
    if(masrv->threadlock)
    {
        return;
    }

    opts->locked = qtrue;
    masrv->threadlock = qtrue;
    opts->authoritative = authoritative;
    opts->adr4 = *adr4;
    opts->adr6 = *adr6;
    Com_sprintf(string, sizeof(string), "\xff\xff\xff\xffheartbeat %s", message);

    MSG_Init(&msg, opts->message, sizeof(opts->message));
    MSG_WriteString(&msg, string);

    MSG_WriteShort(&msg, NET_GetHostPort());
    MSG_WriteLong(&msg, psvs.masterserver_messageid);
    ++psvs.masterserver_messageid;

    opts->msgtokenstart = NULL;

    if(masrv->needticket){

        Q_strncpyz(opts->token, sv_authtoken->string, sizeof(opts->token));


        if(opts->token[0] == 0)
        {
            Com_Printf(CON_CHANNEL_SERVER, "Can not register server on the masterserver. Server needs to provide a valid token in cvar sv_authtoken.\n");
            opts->locked = qfalse;
            masrv->needticket = qfalse; //Try again next time without ticket in case this was only temporarily
            masrv->threadlock = qfalse;
            return;
        }

            MSG_BeginWriteMessageLength(&msg); //Messagelength
            MSG_WriteLong(&msg, 2); //Command encryptedappidticket

        //First 8 bytes of token
        for(i = 0; i < 8; ++i)
        {
            MSG_WriteByte(&msg, opts->token[i]);
        }

        opts->msgtokenstart = msg.data + msg.cursize;

        //Sourceip depended. Write empty message first
        for(i = 0; i < 64; ++i)
        {
            MSG_WriteByte(&msg, 0xff);
        }
        MSG_WriteByte(&msg, 0x0);
        MSG_EndWriteMessageLength(&msg);
    }

    MSG_BeginWriteMessageLength(&msg); //Messagelength
    MSG_WriteLong(&msg, 1); //Command sourceenginequery
    SVC_SourceEngineQuery_WriteInfo(&msg, "", qtrue);
    MSG_EndWriteMessageLength(&msg);


    MSG_BeginWriteMessageLength(&msg); //Messagelength
    MSG_WriteLong(&msg, 0); //EOF
    MSG_EndWriteMessageLength(&msg);

    opts->messagelen = msg.cursize;
    opts->iplist = NET_GetLocalAddressList(&opts->ipcount);
    opts->needticket = &masrv->needticket;
    opts->threadlock = &masrv->threadlock;
    opts->challengei4 = masrv->challengei4;
    opts->challengei6 = masrv->challengei6;

    threadid_t tinfo;
    Sys_CreateNewThread(SV_SendHeartbeatThread, &tinfo, opts);

}


typedef struct
{
    masterserver_t *servers;
    int count;
}masterservers_t;

static masterservers_t	masterservers;

void SV_MasterHeartbeatInit()
{
    char svlist[4096];
    char* tok;
    const char* name;
    int i;
    int res;
    char line[1024];

    Q_strncpyz(svlist, sv_masterservers->string, sizeof(svlist));

    tok = strtok(svlist, ";");
    for(i = 0; tok; ++i)
    {
        tok = strtok(NULL, ";");
    }
    masterservers.servers = Z_Malloc(i*sizeof(masterserver_t));

    Q_strncpyz(svlist, sv_masterservers->string, sizeof(svlist));

    tok = strtok(svlist, ";");
    for(i = 0; tok; ++i)
    {
        Q_strncpyz(line, tok, sizeof(line));
        Cmd_TokenizeString(line);
        name = Cmd_Argv(0);
        if(name[0] == '*')
        {
            masterservers.servers[i].authoritative = qtrue;
            name++;
        }
        Q_strncpyz(masterservers.servers[i].name, name, sizeof(masterservers.servers[i].name));
        Cmd_EndTokenizedString();

        Com_Printf(CON_CHANNEL_SERVER,"Master%d: %s\n", i, masterservers.servers[i].name);

        if(strlen(masterservers.servers[i].name) > 3)
        {
            Com_Printf(CON_CHANNEL_SERVER,"Resolving %s \n", masterservers.servers[i].name);
            //NA_IPANY For broadcasting to all interfaces
            res = NET_StringToAdr(masterservers.servers[i].name, &masterservers.servers[i].i4, NA_IP);				
            if(res == 2)
            {
                masterservers.servers[i].i4.port = BigShort(PORT_MASTER);
            }
            masterservers.servers[i].i4.sock = 0;
            if(res)
            {
                Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", masterservers.servers[i].name, NET_AdrToString(&masterservers.servers[i].i4));
            }else{
                Com_Printf(CON_CHANNEL_SERVER, "Couldn't resolve(IPv4) %s\n", masterservers.servers[i].name);
                masterservers.servers[i].i4.type = NA_DOWN;
            }
            res = NET_StringToAdr(masterservers.servers[i].name, &masterservers.servers[i].i6, NA_IP6);				
            if(res == 2)
            {
                masterservers.servers[i].i6.port = BigShort(PORT_MASTER);
            }
            masterservers.servers[i].i6.sock = 0;
            if(res)
            {
                Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", masterservers.servers[i].name, NET_AdrToString(&masterservers.servers[i].i6));
            }else{
                Com_Printf(CON_CHANNEL_SERVER, "Couldn't resolve(IPv6) %s\n", masterservers.servers[i].name);
                masterservers.servers[i].i6.type = NA_DOWN;
            }
            if(masterservers.servers[i].i4.type == NA_DOWN && masterservers.servers[i].i6.type == NA_DOWN)
            {
                Com_PrintError(CON_CHANNEL_SERVER,"Couldn't resolve masterserver %s\n", masterservers.servers[i].name);
                Com_Memset(&masterservers.servers[i], 0, sizeof(masterserver_t));
            }
        }
        tok = strtok(NULL, ";");
    }
    masterservers.count = i;
}


#define	HEARTBEAT_USEC	180*1000*1000
void SV_MasterHeartbeat(const char *message)
{
#ifdef CODOL_SERVER
    /* CoDOL matchmaking is separate from the IW4OL master service. */
    return;
#endif
    int			i;
    int			res;
    int			netenabled;
    static netadr_t	master_adr[MAX_MASTER_SERVERS][2];

    netenabled = net_enabled->integer;


    // "dedicated 1" is for lan play, "dedicated 2" is for inet public play
    if (com_dedicated->integer != 2 || !(netenabled & (NET_ENABLEV4 | NET_ENABLEV6)))
        return;		// only dedicated servers send heartbeats

    // if not time yet, don't send anything
    if ( com_uFrameTime < svs.nextHeartbeatTime )
        return;

    svs.nextHeartbeatTime = com_uFrameTime + HEARTBEAT_USEC;

    // this command should be changed if the server info / status format
    // ever incompatably changes
    
    /* Master servers used also by ingame serverbrowser */
    for(i = 0; i < masterservers.count; ++i)
    {
        SV_CreateAndSendMasterheartbeatMessage(message, &masterservers.servers[i]);
    }
    /* Activision master servers */
    if(netenabled & NET_ENABLEV4)
    {
        if(atvimaster.type == NA_BAD)
        {
            Com_Printf(CON_CHANNEL_SERVER,"Resolving %s \n", MASTER_SERVER_NAME);
            //NA_IPANY For broadcasting to all interfaces
            res = NET_StringToAdr(MASTER_SERVER_NAME, &atvimaster, NA_IP);
            atvimaster.port = BigShort(PORT_MASTER);
            atvimaster.sock = 0;
            if(res)
            {
                Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", MASTER_SERVER_NAME, NET_AdrToString(&atvimaster));
                netadr_t* defif = NET_GetDefaultCommunicationSocket(NA_IP);
                atvimaster.sock = defif ? defif->sock : 0;
            }else{
                Com_Printf(CON_CHANNEL_SERVER, "Couldn't resolve %s\n", MASTER_SERVER_NAME);
                atvimaster.type = NA_DOWN;
            }
        }
        if(atvimaster.type == NA_IP)
        {
            NET_OutOfBandPrint( NS_SERVER, &atvimaster, "heartbeat %s\n", message);
        }
    }

    /* User added masterservers */
    for (i = 0; i < MAX_MASTER_SERVERS; i++)
    {
        if(!sv_master[i]->string[0])
            continue;

        // see if we haven't already resolved the name
        // resolving usually causes hitches on win95, so only
        // do it when needed
        if(sv_master[i]->modified || (master_adr[i][0].type == NA_BAD && master_adr[i][1].type == NA_BAD))
        {
            sv_master[i]->modified = qfalse;

            if(netenabled & NET_ENABLEV4)
            {
                Com_Printf(CON_CHANNEL_SERVER,"Resolving %s (IPv4)\n", sv_master[i]->string);
                //NA_IPANY For broadcasting to all interfaces
                res = NET_StringToAdr(sv_master[i]->string, &master_adr[i][0], NA_IP);

                if(res == 2)
                {
                    // if no port was specified, use the default master port
                    master_adr[i][0].port = BigShort(PORT_MASTER);
                }
                master_adr[i][0].sock = 0;

                if(res)
                    Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", sv_master[i]->string, NET_AdrToString(&master_adr[i][0]));
                else
                    Com_Printf(CON_CHANNEL_SERVER, "%s has no IPv4 address.\n", sv_master[i]->string);
            }

            if(netenabled & NET_ENABLEV6)
            {
                Com_Printf(CON_CHANNEL_SERVER,"Resolving %s (IPv6)\n", sv_master[i]->string);
                res = NET_StringToAdr(sv_master[i]->string, &master_adr[i][1], NA_IP6);

                if(res == 2)
                {
                    // if no port was specified, use the default master port
                    master_adr[i][1].port = BigShort(PORT_MASTER);
                }

                master_adr[i][1].sock = 0;

                if(res)
                    Com_Printf(CON_CHANNEL_SERVER, "%s resolved to %s\n", sv_master[i]->string, NET_AdrToString(&master_adr[i][1]));
                else
                    Com_Printf(CON_CHANNEL_SERVER, "%s has no IPv6 address.\n", sv_master[i]->string);
            }

            if(master_adr[i][0].type == NA_BAD && master_adr[i][1].type == NA_BAD)
            {
                // if the address failed to resolve, clear it
                // so we don't take repeated dns hits
                Com_Printf(CON_CHANNEL_SERVER,"Couldn't resolve address: %s\n", sv_master[i]->string);
                Cvar_SetString(sv_master[i], "");
                sv_master[i]->modified = qfalse;
                continue;
            }
        }
        Com_Printf (CON_CHANNEL_SERVER,"Sending heartbeat to %s\n", sv_master[i]->string );

        if(master_adr[i][0].type != NA_BAD)
            NET_OutOfBandPrint( NS_SERVER, &master_adr[i][0], "heartbeat %s\n", message);
        if(master_adr[i][1].type != NA_BAD)
            NET_OutOfBandPrint( NS_SERVER, &master_adr[i][1], "heartbeat %s\n", message);
    }
}

/*
=================
SV_MasterShutdown

Informs all masters that this server is going down
=================
*/
void SV_MasterShutdown( void ) {
    // send a hearbeat right now
    svs.nextHeartbeatTime = 0;
    SV_MasterHeartbeat(HEARTBEAT_DEAD);

    // send it again to minimize chance of drops
    svs.nextHeartbeatTime = 0;
    SV_MasterHeartbeat(HEARTBEAT_DEAD);

    // when the master tries to poll the server, it won't respond, so
    // it will be removed from the list
}

/*
==================
SV_FinalMessage

Used by SV_Shutdown to send a final message to all
connected clients before the server goes down.  The messages are sent immediately,
not just stuck on the outgoing message list, because the server is going
to totally exit after returning from this function.
==================
*/
void SV_FinalMessage( const char *message, qboolean arg2 ) {
    int i, j;
    client_t    *cl;


    // send it twice, ignoring rate
    for ( j = 0 ; j < 2 ; j++ )
    {


        for ( i = 0, cl = svs.clients ; i < sv_maxclients->integer ; i++, cl++ )
        {
            if ( cl->state == CS_ACTIVE ) {
                // don't send a disconnect to a local client
                if ( cl->netchan.remoteAddress.type != NA_LOOPBACK ) {

                    if(arg2)
                        SV_SendServerCommandNoLoss( cl, "%c \"%s\"", SV_WIRE_DISCONNECT_COMMAND, message );
                    else
                        SV_SendServerCommandNoLoss( cl, "%c \"%s^7 %s\" PB", SV_WIRE_DISCONNECT_COMMAND, cl->name ,message);
                }
                // force a snapshot to be sent
                cl->nextSnapshotTime = -1;
                SV_SendClientSnapshot( cl );

            }else if( cl->state >= CS_CONNECTED ){

                NET_OutOfBandPrint(NS_SERVER, &cl->netchan.remoteAddress, "disconnect %s", message);

            }
        }

    }
}


void SV_DisconnectAllClients(){

    int i;
    client_t    *cl;

    for ( i = 0, cl = svs.clients ; i < sv_maxclients->integer ; i++, cl++ )
    {

        if( cl->state >= CS_CONNECTED ){

            SV_DropClient(cl, "EXE_DISCONNECTED");

        }
    }
}



/*
================
SV_ClearServer
================
*/
void SV_ClearServer( void ) {
    int i;
#ifdef CODOL_SERVER
    /* Before anything is torn down: the session secure profiles the report's XP
     * delta is read from, and the mounted rank table it is converted through,
     * are both about to go away. A match that ended by map change rather than by
     * its own game-over has not been reported yet. */
    CODOL_ResetMatchReport();
    CODOL_ResetClientMatchData();
    CODOL_ReleaseServerMatchDataSchema();
    /* A player who stays connected through this map change (map_rotate with
     * codol_exitToLobby 0) keeps the profile they are actually playing with.
     * The report just written settled everything up to here, so the carried
     * bytes are the correct baseline for the next match; the lobby's file
     * would be the one from before the last match until the lobby folds it. */
    if (sv_maxclients) {
        for (i = 0; i < sv_maxclients->integer && i < MAX_CLIENTS; ++i) {
            if (svs.clients[i].state >= CS_CONNECTED &&
                svs.clients[i].netchan.remoteAddress.type != NA_BOT) {
                /* The re-attach restores the IW4-only roots from disk too. */
                CODOL_SaveClientProgressIfAttached((unsigned)i);
                CODOL_CarryClientSecureProfile((unsigned)i);
            } else
                CODOL_DropCarriedSecureProfile((unsigned)i);
        }
    }
    CODOL_ResetClientSecureProfiles();
    CODOL_ResetScriptProfiles();
    CODOL_ResetGameInput();
    CODOL_PlayerLinkResetAll();
    CODOL_SlowMotionReset();
    CODOL_ClearCommandNotifications();
    CODOL_ResetSnapshotHistories();
    CODOL_ResetEntityEventGenerations();
    CODOL_ResetServerConfigstrings();
    CODOL_ResetServerWeaponRegistry();
    CODOL_ResetServerAssetNames();
#endif

    for ( i = 0 ; i < MAX_CONFIGSTRINGS ; i++ ) {
        if ( SV_GetConfigstringIndex(i) ) {
            SL_RemoveRefToString( SV_GetConfigstringIndex(i) );
        }
    }

    if(sv.emptyConfigString)
    {
        SL_RemoveRefToString(sv.emptyConfigString);
    }

    Com_Memset( &sv, 0, sizeof( sv ) );
}




/*
================
SV_Shutdown

Called when each game quits,
before Sys_Quit or Sys_Error
================
*/

__cdecl void SV_Shutdown( const char *finalmsg ) {

    if ( !com_sv_running || !com_sv_running->integer ) {
        return;
    }

    Com_Printf(CON_CHANNEL_SERVER, "----- Server Shutdown -----\n" );
    Com_Printf(CON_CHANNEL_SERVER, "\nWith the reason: %s\n", finalmsg );
    if(SEH_StringEd_GetString(finalmsg)){
        SV_FinalMessage( finalmsg, qtrue );
    }else {
        SV_FinalMessage( finalmsg, qfalse );
    }



//	SV_RemoveOperatorCommands();
    SV_MasterShutdown();
    SV_ShutdownGameProgs();
    SV_DisconnectAllClients();
#ifdef CODOL_SERVER
    CODOL_NetworkReset();
#endif
    SV_DemoSystemShutdown();
    SV_FreeClients();

    // free current level
    SV_ClearServer();

//	InsertPluginEvent
/*
    CL_ShutdownConnections( );


*/

    // free server static data
    Cvar_SetBool( com_sv_running, qfalse );

    memset( &svs, 0, sizeof( svs ) );

    Com_Printf(CON_CHANNEL_SERVER, "---------------------------\n" );

    // disconnect any local clients
//	CL_Disconnect( qfalse );

}


/*
=============================================================================

Writing the serverstatus out to a XML-File.
This can be usefull to display serverinfo on a website

=============================================================================
*/

void	serverStatus_WriteCvars(cvar_t const* cvar, void *var ){
    xml_t *xmlbase = var;

    if(cvar->flags & (CVAR_SERVERINFO | CVAR_NORESTART)){
        XML_OpenTag(xmlbase,"Data",2, "Name",cvar->name, "Value",Cvar_DisplayableValue(cvar));
        XML_CloseTag(xmlbase);
    }
}

void	serverStatus_Write(){

    xml_t xmlbase;
    char outputbuffer[32768];
    int i, c;
    client_t    *cl;
    gclient_t	*gclient;
    char	score[16];
    char	team[4];
    char	kills[16];
    char	deaths[16];
    char	assists[16];
    char	teamname[32];
    char	cid[4];
    char	ping[4];
    char	power[4];
    char	rank[4];
    char        timestamp[16];
    mvabuf;
    char ssti[128];
    char psti[128];


    time_t	realtime = Com_GetRealtime();
    char *timestr = ctime(&realtime);
    timestr[strlen(timestr)-1]= 0;

    if(!*sv_statusfile->string) return;

    XML_Init(&xmlbase,outputbuffer,sizeof(outputbuffer), "ISO-8859-1");
    Com_sprintf(timestamp,sizeof(timestamp),"%d",time(NULL));
    XML_OpenTag(&xmlbase,"B3Status",2,"Time",timestr,"TimeStamp",timestamp);

        XML_OpenTag(&xmlbase,"Game",9,"CapatureLimit","", "FragLimit","", "Map",sv_mapname->string, "MapTime","", "Name","cod4", "RoundTime","", "Rounds","", "TimeLimit","", "Type",sv_g_gametype->string);
            Cvar_ForEach(serverStatus_WriteCvars, &xmlbase);
            if(sv_password->string && *sv_password->string)
            {
                XML_OpenTag(&xmlbase,"Data",2, "Name", "pswrd", "Value", "1");
            }else{
                XML_OpenTag(&xmlbase,"Data",2, "Name", "pswrd", "Value", "0");
            }
            XML_CloseTag(&xmlbase);
            XML_OpenTag(&xmlbase,"Data",2, "Name", "sv_type", "Value", va("%d", sv_authorizemode->integer));
            XML_CloseTag(&xmlbase);
        XML_CloseTag(&xmlbase);

        for ( i = 0, c = 0, cl = svs.clients; i < sv_maxclients->integer ; cl++, i++ ) {
            if ( cl->state >= CS_CONNECTED ) c++;
        }
        XML_OpenTag(&xmlbase, "Clients", 1, "Total",va("%i",c));

            for ( i = 0, cl = svs.clients, gclient = level.clients; i < sv_maxclients->integer ; i++, cl++, gclient++ ) {
                if ( cl->state >= CS_CONNECTED ){
                        Com_sprintf(cid,sizeof(cid),"%i", i);

                        if(cl->state == CS_ACTIVE){


                            Com_sprintf(team,sizeof(team),"%i", gclient->sess.cs.team);
                            Com_sprintf(score,sizeof(score),"%i", gclient->sess.score);
#ifdef CODOL_SERVER
                            Com_sprintf(kills,sizeof(kills),"%i", CODOL_ScoreInteger(gclient->sess.kills));
#else
                            Com_sprintf(kills,sizeof(kills),"%i", gclient->sess.kills);
#endif
                            Com_sprintf(deaths,sizeof(deaths),"%i", gclient->sess.deaths);
                            Com_sprintf(assists,sizeof(assists),"%i", gclient->sess.assists);
                            Com_sprintf(ping,sizeof(ping),"%i", cl->ping);
                            Com_sprintf(power,sizeof(power),"%i", cl->power);
                            Com_sprintf(rank,sizeof(rank),"%i", gclient->sess.cs.rank +1);
                            switch(gclient->sess.cs.team){

                                case TEAM_RED:
                                    if(!Q_strncmp(g_TeamName_Axis->string,"MPUI_SPETSNAZ", 13))
                                        Q_strncpyz(teamname, "Spetsnaz", 32);
                                    else if(!Q_strncmp(g_TeamName_Axis->string,"MPUI_OPFOR", 10))
                                        Q_strncpyz(teamname, "Opfor", 32);
                                    else
                                        Q_strncpyz(teamname, g_TeamName_Axis->string, 32);

                                    break;

                                case TEAM_BLUE:
                                    if(!Q_strncmp(g_TeamName_Allies->string,"MPUI_MARINES", 12))
                                        Q_strncpyz(teamname, "Marines", 32);
                                    else if(!Q_strncmp(g_TeamName_Allies->string,"MPUI_SAS", 8))
                                        Q_strncpyz(teamname, "S.A.S.", 32);
                                    else
                                        Q_strncpyz(teamname, g_TeamName_Allies->string,32);

                                    break;

                                case TEAM_FREE:
                                    Q_strncpyz(teamname, "Free",32);
                                    break;
                                case TEAM_SPECTATOR:
                                    Q_strncpyz(teamname, "Spectator", 32);
                                    break;
                                default:
                                    *teamname = 0;
                            }
                        }else{
                            *team = 0;
                            *score = 0;
                            *kills = 0;
                            *deaths = 0;
                            *assists = 0;
                            *ping = 0;
                            *rank = 0;
                            *power = 0;
                            if(cl->state == CS_CONNECTED){
                                Q_strncpyz(teamname, "Connecting...", 32);
                            }else{
                                Q_strncpyz(teamname, "Loading...", 32);
                            }
                        }
                                                SV_SApiSteamIDTo64String(cl->steamid, ssti, sizeof(ssti));
                                                SV_SApiSteamIDTo64String(cl->steamid, psti, sizeof(psti));

                        XML_OpenTag(&xmlbase, "Client", 15, "CID",cid, "ColorName",cl->name, "DBID", ssti, "IP",NET_AdrToStringShort(&cl->netchan.remoteAddress), "ID", psti, "Score",score, "Kills",kills, "Deaths",deaths, "Assists",assists, "Ping", ping, "Team",team, "TeamName", teamname, "Updated", timestr, "power", power, "rank", rank);
                        XML_CloseTag(&xmlbase);
                }
            }

        XML_CloseTag(&xmlbase);
    XML_CloseTag(&xmlbase);

    FS_SV_WriteFile(sv_statusfile->string, outputbuffer, strlen(outputbuffer));

}


void SV_InitServerId(){
    int i;
    byte masterServerSecretBin[(MASTERSERVERSECRETLENGTH -1) / 2];
/*    int read;
    char buf[256];
    *buf = 0;
    fileHandle_t file;

    FS_SV_FOpenFileRead("server_id.dat", &file);
    if(!file){
        Com_Printf(CON_CHANNEL_SERVER,"Couldn't open server_id.dat for reading\n");
        return;
    }
    Com_Printf(CON_CHANNEL_SERVER, "Loading file server_id.dat\n");

    read = FS_ReadLine(buf,sizeof(buf),file);

    if(read == -1){
        Com_Printf(CON_CHANNEL_SERVER,"Can not read from server_id.dat\n");
        FS_FCloseFile(file);
        loadconfigfiles = qfalse;
        return;
    }


    psvs.masterServer_id = atoi(Info_ValueForKey(buf, "id"));
    Q_strncpyz(psvs.masterServer_challengepassword, Info_ValueForKey(buf, "challenge_password"), sizeof(psvs.masterServer_challengepassword));

    FS_FCloseFile(file);
*/

    Com_RandomBytes((byte*)&psvs.masterServer_id, sizeof(psvs.masterServer_id));
    psvs.masterServer_challengepassword[0] = '-';
    psvs.masterServer_challengepassword[1] = '1';
    psvs.masterServer_challengepassword[2] = '\0';
    Com_RandomBytes((byte*)masterServerSecretBin, sizeof(masterServerSecretBin));
    for (i=0; i < sizeof(masterServerSecretBin); ++i)
    {
        sprintf(&masterServerSecret[2*i], "%02x", masterServerSecretBin[i]);
    }
    masterServerSecret[sizeof(masterServerSecret) -1] = '\0';

}

void SV_InitCvarsOnce(void){
#ifdef CODOL_SERVER
    CODOL_NetworkInit();
#endif

    sv_paused = Cvar_RegisterBool("sv_paused", qfalse, CVAR_ROM, "True if the server is paused");
    sv_killserver = Cvar_RegisterBool("sv_killserver", qfalse, CVAR_ROM, "True if the server getting killed");
    sv_protocol = Cvar_RegisterInt("protocol", PROTOCOL_VERSION, PROTOCOL_VERSION, PROTOCOL_VERSION, 0x44, "Protocol version");
    sv_privateClients = Cvar_RegisterInt("sv_privateClients", 0, 0, 64, 4, "Maximum number of private clients allowed onto this server");
#ifdef CODOL_SERVER
    sv_hostname = Cvar_RegisterString("sv_hostname", "sh1x server", 5, "Host name of the server");
#else
    sv_hostname = Cvar_RegisterString("sv_hostname", "^5CoD4Host", 5, "Host name of the server");
#endif
#ifdef PUNKBUSTER
    sv_punkbuster = Cvar_RegisterBool("sv_punkbuster", qtrue, 0x15, "Enable PunkBuster on this server");
#endif

    sv_minPing = Cvar_RegisterInt("sv_minPing", 0, 0, 1000, 5, "Minimum allowed ping on the server");
    sv_maxPing = Cvar_RegisterInt("sv_maxPing", 0, 0, 1000, 5, "Maximum allowed ping on the server");
    sv_queryIgnoreMegs = Cvar_RegisterInt("sv_queryIgnoreMegs", 1, 0, 32, 0x11, "Number of megabytes of RAM to allocate for the querylimit IP-blacklist. 0 disables this feature");
    sv_queryIgnoreTime = Cvar_RegisterInt("sv_queryIgnoreTime", 2000, 100, 100000, 1, "How much milliseconds have to pass until another two queries are allowed");
    Cvar_RegisterBool("sv_disableClientConsole", qfalse, 4, "Disallow remote clients from accessing the client console");

    sv_privatePassword = Cvar_RegisterString("sv_privatePassword", "", 0, "Password for the private client slots");
    sv_rconPassword = Cvar_RegisterString("rcon_password", "", 0, "Password for the server remote control console");

    sv_allowDownload = Cvar_RegisterBool("sv_allowDownload", qtrue, 1, "Allow clients to download gamefiles from server");
    sv_maxDownloadRate = Cvar_RegisterInt("sv_maxDownloadRate", 1024, 128, 8192, 0, "Rate in kilobytes all clients can together receive when downloading from server");
    sv_wwwDownload = Cvar_RegisterBool("sv_wwwDownload", qfalse, 1, "Enable http download");
    sv_wwwBaseURL = Cvar_RegisterString("sv_wwwBaseURL", "", 1, "The base url to files for downloading from the HTTP-Server");
    sv_wwwDlDisconnected = Cvar_RegisterBool("sv_wwwDlDisconnected", qfalse, 1, "Should clients stay connected while downloading from a HTTP-Server?");

    sv_voice = Cvar_RegisterBool("sv_voice", qfalse, 0xd, "Allow serverside voice communication");
    sv_voiceQuality = Cvar_RegisterInt("sv_voiceQuality", 3, 0, 9, 8, "Voice quality");

    sv_cheats = Cvar_RegisterBool("sv_cheats", qfalse, 0x18, "Enable cheats on the server");
    sv_reconnectlimit = Cvar_RegisterInt("sv_reconnectlimit", 5, 0, 1800, 1, "Seconds to disallow a prior connected client to reconnect to the server");
    sv_padPackets = Cvar_RegisterInt("sv_padPackets", 0, 0, 0x7fffffff, 0, "How many nop-bytes to add to insert into each snapshot");

    sv_mapRotation = Cvar_RegisterString("sv_mapRotation", "", 0, "List of all maps server will play");
    sv_mapRotationCurrent = Cvar_RegisterString("sv_mapRotationCurrent", "", 0, "List of remaining maps server has to play");
    sv_nextmap = Cvar_RegisterString("nextmap", "", 0, "String to execute on map_rotate. This will override the default maprotation of CoD4 with the Quake3 style maprotation");
    sv_randomMapRotation = Cvar_RegisterBool("sv_randomMapRotation", qfalse, CVAR_ARCHIVE, "Mixes up maps in rotation when true");

    sv_timeout = Cvar_RegisterInt("sv_timeout", 40, 0, 1800, 0, "Seconds to keep a client on server without a new clientmessage");
    sv_connectTimeout = Cvar_RegisterInt("sv_connectTimeout", 90, 0, 1800, 0, "Seconds to wait for a client which is loading a map without a new clientmessage");
    sv_zombieTime = Cvar_RegisterInt("sv_zombieTime", 2, 0, 1800, 0, "Seconds to keep a disconnected client on server to transmit the last message");

    Cvar_RegisterBool("clientSideEffects", qtrue, 0x80, "Enable loading _fx.gsc files on the client");

    sv_modStats = Cvar_RegisterBool("ModStats", qtrue, 0, "Flag whether to use stats of mod (when running a mod) or to use stats of the Cod4 coregame");
    sv_authorizemode = Cvar_RegisterInt("sv_authorizemode", 1, -1, 1, CVAR_ARCHIVE, "How to authorize clients, 0=acceptall(No GUIDs) 1=accept no one with invalid GUID");
    sv_showasranked = Cvar_RegisterBool("sv_showasranked", qfalse, 0, "List the server in serverlist of ranked servers even when it is modded");
    sv_statusfile = Cvar_RegisterString("sv_statusfilename", "serverstatus.xml", CVAR_ARCHIVE, "Filename to write serverstatus to disk");
    g_mapstarttime = Cvar_RegisterString("g_mapStartTime", "", CVAR_SERVERINFO | CVAR_ROM, "Time when current map has started");
    g_friendlyPlayerCanBlock = Cvar_RegisterBool("g_friendlyPlayerCanBlock", qfalse, 0, "Flag whether friendly players can block each other");
    g_FFAPlayerCanBlock = Cvar_RegisterBool("g_FFAPlayerCanBlock", qtrue, 0, "Flag whether players in non team based games can block each other");
    sv_password = Cvar_RegisterString("g_password", "", CVAR_ARCHIVE, "Password which is required to join this server");
    g_motd = Cvar_RegisterString("g_motd", "", CVAR_ARCHIVE, "Message of the day, which getting shown to every player on his 1st spawn");
    sv_uptime = Cvar_RegisterString("uptime", "", CVAR_SERVERINFO | CVAR_ROM, "Time the server is running since last restart");
    sv_autodemorecord = Cvar_RegisterBool("sv_autodemorecord", qfalse, 0, "Automatically start from each connected client a demo.");
    sv_demoCompletedCmd = Cvar_RegisterString("sv_demoCompletedCmd", "", com_securemode ? CVAR_INIT : 0 , "This program will be executed when a demo has been completed. You have to specify an executable file located in fs_homepath/apps/. The arrived filename will be passed as argument.");
    sv_screenshotArrivedCmd = Cvar_RegisterString("sv_screenshotArrivedCmd", "", com_securemode ? CVAR_INIT : 0 , "This program will be executed when a new screenshot has arrived. You have to specify an executable file located in fs_homepath/apps/. The arrived filename will be passed as argument.");
    sv_mapDownloadCompletedCmd = Cvar_RegisterString("sv_mapDownloadCompletedCmd", "", com_securemode ? CVAR_INIT : 0 , "This program will be executed when a downloaded map was received. You have to specify an executable file located in fs_homepath/apps/. The arrived usermaps/mapname will be passed as argument.");
    sv_consayname = Cvar_RegisterString("sv_consayname", "^2Server: ^7", CVAR_ARCHIVE, "If the server broadcast text-messages this name will be used");
    sv_contellname = Cvar_RegisterString("sv_contellname", "^5Server^7->^5PM: ^7", CVAR_ARCHIVE, "If the server broadcast text-messages this name will be used");

    sv_master[0] = Cvar_RegisterString("sv_master1", "", 0, "A masterserver name");
    sv_master[1] = Cvar_RegisterString("sv_master2", "", 0, "A masterserver name");

    sv_masterservers = Cvar_RegisterString("sv_masterservers", "", 0, "Official used masterservers separated by ;");

    sv_g_gametype = Cvar_RegisterString("g_gametype", "war", 0x24, "Current game type");
    sv_mapname = Cvar_RegisterString("mapname", "", CVAR_ROM | CVAR_SERVERINFO, "Current map name");
#ifdef CODOL_SERVER
    /* IW4 rank scripts require the engine's XP scale; an absent dvar reads
     * as zero. T5 common.cpp also registers the normal default as one. */
    Cvar_RegisterInt("scr_xpscale", 1, 0, 4, 0,
        "Rank XP multiplier; zero disables XP persistence");
    codol_zoneType = Cvar_RegisterString("codol_zoneType", "mp", CVAR_LATCH,
        "CoDOL asset category: mp, coop or zm; distinct from g_gametype");
    codol_animlistMask = Cvar_RegisterInt("codol_animlistMask", 0, 0, 15, 0,
        "Animation classes at next full map load: human=1 dog=2 civilian=4 zombie=8; requires matching client assets");
    /* Not CVAR_LATCH: it is read once per spawn, from the value the lobby set
     * over rcon just before `map`, and an unset value means "none". */
    codol_sessionMap = Cvar_RegisterString("codol_sessionMap", "", 0,
        "CoDOL playlist/session map spelling for this match (e.g. coop_training_mp_killhouse_sh); the base level zone is still what `map` names and what goes on the wire");
#endif
#ifdef CODOL_SERVER
    sv_maxclients = Cvar_RegisterInt("sv_maxclients", 16, 1, CODOL_MAX_GAME_CLIENTS, CVAR_INIT | CVAR_SERVERINFO, "Maximum number of clients that can connect to a server");
#else
    sv_maxclients = Cvar_RegisterInt("sv_maxclients", 16, 1, 64, CVAR_INIT | CVAR_SERVERINFO, "Maximum number of clients that can connect to a server");
#endif
    sv_clientSideBullets = Cvar_RegisterBool("sv_clientSideBullets", qtrue, 8, "If true, clients will synthesize tracers and bullet impacts");
    sv_maxRate = Cvar_RegisterInt("sv_maxRate", 100000, 2500, 100000, 5, "Maximum allowed bitrate per client");
    sv_floodProtect = Cvar_RegisterInt("sv_floodprotect", 4, 0, 100000, 5, "Prevent malicious lagging by flooding the server with commands. Is the number of client commands allowed to process");
    sv_showcommands = Cvar_RegisterBool("sv_showcommands", qfalse, 0, "Print all client commands");
    sv_iwds = Cvar_RegisterString("sv_iwds", "", 0x48, "IWD server checksums");
    sv_iwdNames = Cvar_RegisterString("sv_iwdNames", "", 0x48, "Names of IWD files used by the server");
    sv_referencedIwds = Cvar_RegisterString("sv_referencedIwds", "", 0x48, "Checksums of all referenced IWD files");
    sv_referencedIwdNames = Cvar_RegisterString("sv_referencedIwdNames", "", 0x48, "Names of all referenced IWD files used by the server");
    sv_FFCheckSums = Cvar_RegisterString("sv_FFCheckSums", "", 0x48, "FastFile server checksums");
    sv_FFNames = Cvar_RegisterString("sv_FFNames", "", 0x48, "Names of FastFiles used by the server");
    sv_referencedFFCheckSums = Cvar_RegisterString("sv_referencedFFCheckSums", "", 0x48, "Checksums of all referenced FastFiles");
    sv_referencedFFNames = Cvar_RegisterString("sv_referencedFFNames", "", 0x48, "Names of all referenced FastFiles used by the server");
    sv_serverid = Cvar_RegisterInt("sv_serverid", 0, 0x80000000, 0x7fffffff, 0x48, "The current id of server to let client and server distinguish between gamestates");
    sv_pure = Cvar_RegisterBool("sv_pure", qtrue, 0xc, "Cannot use modified IWD files");
    sv_fps = Cvar_RegisterInt("sv_fps", 20, 1, 250, 0, "Server frames per second");
    sv_showAverageBPS = Cvar_RegisterBool("sv_showAverageBPS", qfalse, 0, "Show average bytes per second for net debugging");
    sv_botsPressAttackBtn = Cvar_RegisterBool("sv_botsPressAttackBtn", qtrue, 0, "Allow testclients to press attack button");
    sv_debugRate = Cvar_RegisterBool("sv_debugRate", qfalse, 0, "Enable snapshot rate debugging info");
    sv_debugReliableCmds = Cvar_RegisterBool("sv_debugReliableCmds", qfalse, 0, "Enable debugging information for reliable commands");
    sv_clientArchive = Cvar_RegisterBool("sv_clientArchive", qtrue, 0, "Have the clients archive data to save bandwidth on the server");
    sv_shownet = Cvar_RegisterInt("sv_shownet", -1, -1, 63, 0, "Enable network debugging for a client");
    sv_updatebackendname = Cvar_RegisterString("sv_updatebackendname", UPDATE_PROXYSERVER_NAME, CVAR_ARCHIVE, "Hostname for the used clientupdatebackend");
    sv_legacymode = Cvar_RegisterBool("sv_legacyguidmode", qfalse, CVAR_ARCHIVE, "outputs pbguid on status command and games_mp.log");
    sv_authtoken = Cvar_RegisterString("sv_authtoken", "", 0, "Token to register on masterserver");
    sv_disableChat = Cvar_RegisterBool("sv_disablechat", qfalse, CVAR_ARCHIVE, "Disable chat messages from clients");
}

void SV_TryLoadXAC();

void SV_Init(){
    SV_AddOperatorCommands();
    SV_InitCvarsOnce();
    SVC_RateLimitInit( );
    SV_InitBanlist();
    Init_CallVote();
    SV_InitServerId();
    SV_MasterHeartbeatInit();
    Com_RandomBytes((byte*)&psvs.randint, sizeof(psvs.randint));
    SV_InitSApi();
    SV_TryLoadXAC();
}


/*
===================
SV_CalcPings

Updates the cl->ping variables
===================
*/
void SV_CalcPings( void ) {
    int i, j;
    client_t    *cl;
    int total, count;
    int delta;

    for ( i = 0 ; i < sv_maxclients->integer ; i++ ) {
        cl = &svs.clients[i];

        if ( cl->state != CS_ACTIVE ) {
            cl->ping = -1;
            continue;
        }
        if ( !cl->gentity ) {
            cl->ping = -1;
            continue;
        }
        if ( cl->netchan.remoteAddress.type == NA_BOT ) {
            cl->ping = 0;
            cl->lastPacketTime = svs.time;
            continue;
        }

        total = 0;
        count = 0;
        for ( j = 0 ; j < PACKET_BACKUP ; j++ ) {
            if ( cl->frames[j].messageAcked == 0xFFFFFFFF ) {
                continue;
            }
            delta = cl->frames[j].messageAcked - cl->frames[j].messageSent;
            count++;
            total += delta;
        }
        if ( !count ) {
            cl->ping = 999;
        } else {
            cl->ping = total / count;
            if ( cl->ping > 999 ) {
                cl->ping = 999;
            }
        }
    }
}

/*
===============
SV_GetConfigstring

===============
*/
void SV_GetConfigstring( int index, char *buffer, int bufferSize ) {

    short strIndex;
    const char* cs;

    if ( bufferSize < 1 ) {
        Com_Error( ERR_DROP, "SV_GetConfigstring: bufferSize == %i", bufferSize );
    }
    if ( index < 0 || index >= MAX_CONFIGSTRINGS ) {
        Com_Error( ERR_DROP, "SV_GetConfigstring: bad index %i\n", index );
    }
    strIndex = SV_GetConfigstringIndex(index);

    cs = SL_ConvertToString(strIndex);

    Q_strncpyz( buffer, cs, bufferSize );
}

/* SV_GetConfigstringIndex
 * 0x08172FB0
 * T-Max: Should add array index check? 0 <= num < MAX_CONFIGSTRINGS
 */
int SV_GetConfigstringIndex(int num)
{
    return (int)sv.configstrings[num];
}

/* SV_GetModelConfigstringIndex
 * 0x080CAC42
 */
int SV_GetModelConfigstringIndex(int num)
{
    return SV_GetConfigstringIndex(num + 0x33E);
}

void SV_UpdateClientConfigInfo(client_t* cl)
{
    ++svs.configDataSequence;
    svs.changedConfigData[svs.configDataSequence % MAX_CONFIGDATACACHE] = cl - svs.clients;
}

typedef struct{
    int index;
    char* string;
    int unk1;
    int unk2;
}constConfigstring_t;

/*
===============

===============
*/

#ifdef CODOL_SERVER
int CODOL_RefreshServerPlayerNames(void)
{
    char tokens[CODOL_PLAYERNAME_SLOTS][64];
    const char *names[CODOL_PLAYERNAME_SLOTS];
    unsigned char changed[CODOL_PLAYERNAME_SLOTS];
    int slot, recipient, any = 0;
    codol_configstrings_t *bank = CODOL_ServerConfigstrings();
    for (slot = 0; slot < CODOL_PLAYERNAME_SLOTS; ++slot) {
        const char *old = CODOL_GetConfigstring(bank, CODOL_CS_PLAYERNAMES + slot);
        const char *name = slot < sv_maxclients->integer && svs.clients[slot].state >= CS_CONNECTED
            ? svs.clients[slot].name : NULL;
        CODOL_PlayerNameToken(tokens[slot], name); names[slot] = tokens[slot];
        changed[slot] = !old || strcmp(old, tokens[slot]);
        any |= changed[slot];
    }
    if (!any) return 1;
    if (!CODOL_SetPlayerNames(bank, CODOL_PLAYERNAME_SLOTS, names)) return 0;
    for (recipient = 0; recipient < sv_maxclients->integer; ++recipient) {
        client_t *target = &svs.clients[recipient];
        if (target->state < CS_PRIMED || !target->gamestateSent) continue;
        for (slot = 0; slot < CODOL_PLAYERNAME_SLOTS; ++slot) if (changed[slot])
            SV_SendServerCommandNoLoss(target, "d %u %s", CODOL_CS_PLAYERNAMES + slot, tokens[slot]);
    }
    return 1;
}

/* Re-send, after a gamestate, every configstring that an older "d" command
 * still in this client's reliable ring would overwrite.
 *
 * C1 keeps its server command sequence across a map change: commands queued
 * before the new gamestate that it had not yet executed on the old level run
 * after that gamestate, at the new level's first snapshot (CL_SetConfigstring
 * 0x487440 then applies each over the gamestate's value). The old level's
 * teardown queues such commands: SV_RemoveAllBots drops every bot, and the
 * forced snapshot in SV_SpawnServer publishes "d 1280+n " blanks for them. A
 * bot the level script re-added during the spawn's warm-up frames is named
 * only by the gamestate, so its stale blank won and the name stayed empty on
 * the scoreboard, the kill feed, the nameplate and the crosshair (C1 0x46ca39
 * copies CS[1280+clientIndex] into clientinfo+0xc, which 0x488af0 serves to
 * all of them) for the whole level. Measured on a live C1 (2026-09-28): slot 0
 * blank after every map change before this, intact after.
 *
 * Every index is handled the same way: take the last value the ring holds for
 * it, and where the new gamestate's effective value differs, record that
 * value as a deferred update. This includes the inherited fastfile constants:
 * a stale command from a different category can overwrite one even when the
 * override bank has no entry at that index. The update gets a later sequence than
 * every stale command, and the snapshot hold delivers it before C1's first
 * snapshot (CODOL_DeferredConfigstringsHoldSnapshot). The override bank is
 * exactly what SV_WriteGameState wrote, while the inherited bank represents
 * the new category's fastfile constants. A command C1 did execute on the old
 * level was reset by the gamestate
 * already; re-sending the gamestate's value for it is a no-op in C1, whose
 * only gate is strcmp(old, new). Indices neither bank carries (retained
 * producers that publish a raw "d" with no bank value) are left alone. */
void CODOL_ReassertConfigstringsAfterGamestate(client_t *client)
{
    static const char *last[CODOL_MAX_CONFIGSTRINGS];
    unsigned short touched[MAX_RELIABLE_COMMANDS];
    const codol_configstrings_t *bank = CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited = CODOL_ServerInheritedConfigstrings();
    char cmd[MAX_STRING_CHARS];
    int seq, first, count = 0, i, sent = 0;

    if (!client || client->netchan.remoteAddress.type == NA_BOT) return;
    /* C1 holds MAX_RELIABLE_COMMANDS (256) unexecuted commands; older ones
     * can no longer run. */
    first = client->reliableSequence - MAX_RELIABLE_COMMANDS + 1;
    if (first < 1) first = 1;
    for (seq = first; seq <= client->reliableSequence; ++seq) {
        const char *text = client->reliableCommands[seq & (MAX_RELIABLE_COMMANDS - 1)].command;
        char *end;
        unsigned long index;
        if (text[0] != 'd' || text[1] != ' ' || text[2] < '0' || text[2] > '9') continue;
        index = strtoul(text + 2, &end, 10);
        if ((*end != ' ' && *end) || index >= CODOL_MAX_CONFIGSTRINGS) continue;
        if (!last[index]) touched[count++] = (unsigned short)index;
        last[index] = *end ? end + 1 : end;
    }
    for (i = 0; i < count; ++i) {
        unsigned index = touched[i];
        const char *value = CODOL_GetEffectiveConfigstring(bank, inherited, index);
        const char *stale = last[index];
        last[index] = NULL;
        if (!value || !strcmp(value, stale)) continue;
        Com_sprintf(cmd, sizeof(cmd), "d %u %s", index, value);
        if (!CODOL_DeferConfigstringCommand(client, cmd))
            SV_SendServerCommandNoLoss(client, "%s", cmd);
        ++sent;
    }
    if (sent)
        Com_Printf(CON_CHANNEL_SERVER, "CoDOL gamestate: %s gets %d configstring(s) again that older commands would overwrite\n",
                   client->name, sent);
}
#endif

void SV_WriteGameState( msg_t* msg, client_t* cl ) {
#ifdef CODOL_SERVER
    if (!CODOL_SetServerId(sv_serverid->integer) || !CODOL_RefreshServerAssetNames() || !CODOL_RefreshServerMapConfigstrings() || !CODOL_RefreshServerPlayerNames() ||
        !CODOL_RefreshServerWeaponRegistry() || !CODOL_RefreshServerWeaponMappings()) {
        msg->overflowed = qtrue;
        return;
    }
    CODOL_WriteServerGamestate(msg, sv_mapname->string, codol_zoneType->string,
        sv_g_gametype->string, sv_maxclients->integer, cl->reliableSequence, cl - svs.clients, sv.checksumFeed,sv_hostname->string);
    return;
#endif

    int i, numConfigstrings, clnum;
    entityState_t nullstate, *base;
    snapshotInfo_t snapInfo;
    unsigned short strindex;

    MSG_WriteByte( msg, svc_gamestate );
    MSG_WriteLong( msg, cl->reliableSequence );
    MSG_WriteByte( msg, svc_configstring );

    for ( i = 0, numConfigstrings = 0; i < MAX_CONFIGSTRINGS ; i++) {

        strindex = SV_GetConfigstringIndex(i);
        if(strindex != 0)
        {
            numConfigstrings++;
        }
    }
    MSG_WriteLong(msg, numConfigstrings);

    for ( i = 0 ; i < MAX_CONFIGSTRINGS ; i++)
    {

        strindex = SV_GetConfigstringIndex(i);

        if(strindex == 0)
        {
            continue;
        }
        MSG_WriteLong(msg, i);
        MSG_WriteBigString(msg, SL_ConvertToString(strindex));
    }
    Com_Memset( &nullstate, 0, sizeof( nullstate ) );
    clnum = cl - svs.clients;
    // baselines
    for ( i = 0; i < MAX_GENTITIES ; i++ ) {
        base = &sv.svEntities[i].baseline.s;
        if ( !base->number ) {
            continue;
        }
        MSG_WriteByte( msg, svc_baseline );

        snapInfo.clnum = clnum;
        snapInfo.client = NULL;
        snapInfo.snapshotDeltaTime = 0xFFFFFFFF;
        snapInfo.fromBaseline = qtrue;
        snapInfo.archived = 0;

        MSG_WriteDeltaEntity( &snapInfo, msg, 0, &nullstate, base, qtrue );
    }

    for(i = 0, cl = svs.clients; i < sv_maxclients->integer; ++i, ++cl)
    {
        if(cl->state < CS_CONNECTED)
        {
            continue;
        }
        SV_WriteClientConfigInfo(msg, cl, -1);
    }

    //MSG_WriteByte( msg, svc_configdata );
    MSG_WriteByte( msg, svc_EOF );

}

/*
================
SV_RconStatusWrite
î
Used by rcon to retrive all serverdata as detailed as possible
================
*/
void SV_WriteRconStatus( msg_t* msg ) {

    //Reserve 19000 free bytes for msg_t struct

    int i;
    client_t    *cl;
    gclient_t *gclient;
    char infostring[MAX_INFO_STRING];
    mvabuf;
    char ssti[128];
    char psti[128];

    infostring[0] = 0;

    if(!com_sv_running->boolean)
            return;

    strcpy( infostring, Cvar_InfoString( CVAR_SERVERINFO | CVAR_NORESTART));
    // echo back the parameter to status. so master servers can use it as a challenge
    // to prevent timed spoofed reply packets that add ghost servers
    if(*sv_password->string)
        Info_SetValueForKey( infostring, "pswrd", "1");

    //Write teamnames
        if(!Q_strncmp(g_TeamName_Axis->string,"MPUI_SPETSNAZ", 13))
            Info_SetValueForKey( infostring, "axis", "Spetsnaz");
        else if(!Q_strncmp(g_TeamName_Axis->string,"MPUI_OPFOR", 10))
            Info_SetValueForKey( infostring, "axis", "Opfor");
        else
            Info_SetValueForKey( infostring, "axis", g_TeamName_Axis->string);

        if(!Q_strncmp(g_TeamName_Allies->string,"MPUI_MARINES", 12))
            Info_SetValueForKey( infostring, "allies", "Marines");
        else if(!Q_strncmp(g_TeamName_Allies->string,"MPUI_SAS", 8))
            Info_SetValueForKey( infostring, "allies", "S.A.S.");
        else
            Info_SetValueForKey( infostring, "allies", g_TeamName_Allies->string);

        Info_SetValueForKey( infostring, "svtime", va("%i", svs.time));

    //Writing general server info to msg (Reserve 1024 bytes)
    MSG_WriteString(msg, infostring);

    //Reserve 64 * 280 bytes = 18000
    //Writing clientinfo to msg
    for ( i = 0, gclient = level.clients ; i < sv_maxclients->integer ; i++, gclient++ ) {

        cl = &svs.clients[i];

        infostring[0] = 0;

        if ( cl->state >= CS_CONNECTED ) {
            MSG_WriteByte( msg, i );	//ClientIndex
            Info_SetValueForKey( infostring, "name", cl->name);
            SV_SApiSteamIDTo64String(cl->steamid, ssti, sizeof(ssti));
            Info_SetValueForKey( infostring, "steamid", ssti);
            SV_SApiSteamIDTo64String(cl->steamid, psti, sizeof(psti));
            Info_SetValueForKey( infostring, "playerid", psti);
            Info_SetValueForKey( infostring, "team", va("%i", gclient->sess.cs.team));
            Info_SetValueForKey( infostring, "score", va("%i", gclient->sess.score));
#ifdef CODOL_SERVER
            Info_SetValueForKey( infostring, "kills", va("%i", CODOL_ScoreInteger(gclient->sess.kills)));
#else
            Info_SetValueForKey( infostring, "kills", va("%i", gclient->sess.kills));
#endif
            Info_SetValueForKey( infostring, "deaths", va("%i", gclient->sess.deaths));
            Info_SetValueForKey( infostring, "assists", va("%i", gclient->sess.assists));
            Info_SetValueForKey( infostring, "ping", va("%i", cl->ping));

            if(cl->netchan.remoteAddress.type == NA_BOT)
                Info_SetValueForKey( infostring, "ipconn", "BOT");
            else
                Info_SetValueForKey( infostring, "ipconn", NET_AdrToConnectionString(&cl->netchan.remoteAddress));

            Info_SetValueForKey( infostring, "state", va("%i", cl->state));
            Info_SetValueForKey( infostring, "power", va("%i", cl->power));
            Info_SetValueForKey( infostring, "rate", va("%i", cl->rate));
            MSG_WriteString(msg, infostring);
        }
    }
    MSG_WriteByte( msg, -1 );	//Terminating ClientIndex
}



void SV_GetServerStaticHeader(){
    svs.nextCachedSnapshotFrames = svsHeader.nextCachedSnapshotFrames;
    svs.nextCachedSnapshotEntities = svsHeader.nextCachedSnapshotEntities;
    svs.nextCachedSnapshotClients = svsHeader.nextCachedSnapshotClients;
    svs.archivedEntityCount = svsHeader.archivedEntityCount;
    
    svsHeaderValid = 0;
}

void SV_SetServerStaticHeader()
{
    VectorCopy(svs.mapCenter, svsHeader.mapCenter);

    svsHeader.snapFlagServerBit = svs.snapFlagServerBit;
    svsHeader.time = svs.time;
    svsHeader.numSnapshotEntities = svs.numSnapshotEntities;
    svsHeader.numSnapshotClients = svs.numSnapshotClients;
    svsHeader.nextSnapshotEntities = svs.nextSnapshotEntities;
    svsHeader.nextSnapshotClients = svs.nextSnapshotClients;
    svsHeader.nextCachedSnapshotFrames = svs.nextCachedSnapshotFrames;
    svsHeader.nextArchivedSnapshotFrames = svs.nextArchivedSnapshotFrames;
    svsHeader.nextCachedSnapshotEntities = svs.nextCachedSnapshotEntities;
    svsHeader.nextCachedSnapshotClients = svs.nextCachedSnapshotClients;
    svsHeader.num_entities = sv.num_entities;
    svsHeader.clients = svs.clients;
    svsHeader.snapshotEntities = svs.snapshotEntities;
    svsHeader.snapshotClients = svs.snapshotClients;
    svsHeader.svEntities = sv.svEntities;

    svsHeader.cachedSnapshotEntities = svs.cachedSnapshotEntities;
    svsHeader.cachedSnapshotClients = svs.cachedSnapshotClients;
    svsHeader.archivedSnapshotBuffer = svs.archivedSnapshotBuffer;
    svsHeader.cachedSnapshotFrames = svs.cachedSnapshotFrames;

    svsHeader.maxclients = sv_maxclients->integer;
    svsHeader.fps = sv_fps->integer;
    svsHeader.gentitySize = sv.gentitySize;
    svsHeader.clientArchive = sv_clientArchive->integer;

    svsHeader.gentities = sv.gentities;
    svsHeader.firstClientState = G_GetClientState( 0 );
    svsHeader.firstPlayerState = G_GetPlayerState( 0 );
    svsHeader.clientSize = G_GetClientSize();

    svsHeader.numCachedSnapshotEntities = svs.numCachedSnapshotEntities;
    svsHeader.numCachedSnapshotClients = svs.numCachedSnapshotClients;
    svsHeader.archivedEntityCount = svs.archivedEntityCount;

    svsHeaderValid = 1;
}


void SV_InitSnapshot()
{
  svs.nextSnapshotEntities = 0;
  svs.nextSnapshotClients = 0;
  //sv.inFrame = 0;
}

void SV_InitArchivedSnapshot()
{
#ifdef CODOL_SERVER
  /* The cached-snapshot ring is being rewound; its CoDOL extension blocks
   * describe states that no longer exist. */
  CODOL_PlayerStateExtClearArchive();
  CODOL_ClearArchivedClientAbilities();
  CODOL_EntityStateExtClearArchive();
#endif
  svs.nextArchivedSnapshotFrames = 0;
  svs.nextArchivedSnapshotBuffer = 0;
  svs.nextCachedSnapshotEntities = 0;
  svs.nextCachedSnapshotClients = 0;
  svs.nextCachedSnapshotFrames = 0;
  svs.numCachedSnapshotEntities = sizeof(svs.cachedSnapshotEntities)/sizeof(svs.cachedSnapshotEntities[0]);
  svs.numCachedSnapshotClients = sizeof(svs.cachedSnapshotClients)/sizeof(svs.cachedSnapshotClients[0]);
}

void SV_RunFrame(){
    SV_ResetSkeletonCache();
    G_RunFrame(svs.time);
}


int SV_ClientAuthMode(){

    return sv_authorizemode->integer;

}

const char* SV_GetMessageOfTheDay(){

    return g_motd->string;

}


qboolean SV_FriendlyPlayerCanBlock(){

    return g_friendlyPlayerCanBlock->boolean;

}

qboolean SV_FFAPlayerCanBlock(){

    return g_FFAPlayerCanBlock->boolean;

}

//Few custom added things which should happen if we load a new level or restart a level
void SV_PreLevelLoad(){
    Com_UpdateRealtime();
    time_t realtime = Com_GetRealtime();
    char *timestr = ctime(&realtime);
    timestr[strlen(timestr)-1]= 0;

    Cvar_SetString(g_mapstarttime, timestr);

    if(!onExitLevelExecuted)
    {
        PHandler_Event(PLUGINS_ONEXITLEVEL, NULL);
    }
    onExitLevelExecuted = qfalse;

    SV_RemoveAllBots();

    FS_ShutdownIwdPureCheckReferences();

    NV_LoadConfig();

    HL2Rcon_EventLevelStart();
}

void SV_PostLevelLoad(){
    PHandler_Event(PLUGINS_ONSPAWNSERVER, NULL);
    sv.frameusec = 1000000 / sv_fps->integer;
}

#ifndef CODOL_SERVER
/* IW4OL client extension metadata. C1 uses its native fastfile/asset
 * namespaces and does not consume this cod<protocol> extension payload. */
void SV_BuildXAssetCSString()
{
    char cs[MAX_STRING_CHARS];
    char list[MAX_STRING_CHARS];
    char turrets[16];

    DB_BuildOverallocatedXAssetList(list, sizeof(list));

    turrets[0] = 0;
    if(DB_DiscardBspWeapons())
    {
        strcpy(turrets, "nobspweapon=1 ");
    }
    Com_sprintf(cs, sizeof(cs), "cod%d %s%s", PROTOCOL_VERSION, list, turrets);
    SV_SetConfigstring(2, cs);
}
#endif

void SV_LoadLevel(const char* levelname)
{
    char mapname[MAX_QPATH];

    Q_strncpyz(mapname, levelname, sizeof(mapname));
    FS_ConvertPath(mapname);
    SV_PreLevelLoad();
    SV_SpawnServer(mapname);

#ifndef CODOL_SERVER
    SV_BuildXAssetCSString();
    //Temporarily
    cvar_t* sv_wantediwdheaders = Cvar_RegisterString("sv_wantediwdheaders", "", 0, "developmental only");
    cvar_t* sv_wantediwdchecksums = Cvar_RegisterString("sv_wantediwdchecksums", "", 0, "developmental only");
    SV_SetConfigstring(CS_IWDHEADERS, sv_wantediwdheaders->string);
    //"localized_british_iw00 localized_korean_iw00 localized_taiwanese_iw00 localized_japanese_iw00 localized_chinese_iw00 localized_thai_iw00 localized_leet_iw00 localized_czech_iw00 localized_english_iw0 localized_french_iw0 localized_german_iw0 localized_italian_iw0 localized_spanish_iw0 localized_polish_iw0 localized_russian_iw0 localized_chinese_iw0");
    SV_SetConfigstring(CS_IWDCHECKSUMHEADERS, sv_wantediwdchecksums->string);
#endif

    SV_CalculateChecksums();
    SV_PostLevelLoad();
}


/*
==================
SV_Map

Restart the server on a different map
==================
*/
qboolean SV_Map( const char *levelname ) {
    char        *map;
    char mapname[MAX_QPATH];
    char expanded[MAX_QPATH];
    char mapname_loadff[MAX_QPATH];

    map = FS_GetMapBaseName(levelname);
    Q_strncpyz(mapname, map, sizeof(mapname));
    Q_strlwr(mapname);

#ifdef CODOL_SERVER
    /* The native mount uses codol_zonePath; it does not load IW3 .d3dbsp
     * files or the client's separate loading-screen fastfile. */
    if(!DB_FileExists(mapname, 0)) {
        Com_PrintError(CON_CHANNEL_SERVER,"Can't find CoDOL map archive %s\n",mapname);
        return qfalse;
    }
    /* A coop session zone is mounted beside the level zone. Check it here,
     * while the current level still runs: once SV_LoadLevel has torn that
     * down, a missing zone is a fatal ERR_DROP that leaves the server dead
     * (VPS 2026-09-27: coop_survival_mp_afghan, a mode no zone ships). */
    {
        const char *session = SV_CoDOLSessionMapName();
        if(session && *session && Q_stricmp(session, mapname) && !DB_FileExists(session, 0)) {
            Com_PrintError(CON_CHANNEL_SERVER,
                "Can't find CoDOL session archive %s for %s; keeping the current match\n", session, mapname);
            Cvar_SetStringByName("codol_sessionMap", sv_mapname->string);
            return qfalse;
        }
    }
#else
    if(!useFastFile->boolean)
    {
        Com_sprintf(expanded, sizeof(expanded), "maps/mp/%s.d3dbsp", mapname);
        if ( FS_ReadFile( expanded, NULL ) == -1 ) {
            Com_PrintError(CON_CHANNEL_SERVER, "Can't find map %s\n", expanded );
            return qfalse;
        }
    }

    if(!DB_FileExists(mapname, 0) && (!fs_gameDirVar->string[0] || !DB_FileExists(mapname, 2))){
        Com_PrintError(CON_CHANNEL_SERVER,"Can't find map %s\n", mapname);
        if(!fs_gameDirVar->string[0])
            Com_PrintError(CON_CHANNEL_SERVER,"A mod is required to run custom maps\n");
        return qfalse;
    }
    Com_sprintf(mapname_loadff, sizeof(mapname_loadff), "%s_load", mapname);
    if(!DB_FileExists(mapname_loadff, 0) && !DB_FileExists(mapname_loadff, 2))
    {
        Com_PrintError(CON_CHANNEL_SERVER,"Can't find file %s.ff\n", mapname_loadff);
        return qfalse;
    }
#endif
//	Cbuf_ExecuteBuffer(0, 0, "selectStringTableEntryInDvar mp/didyouknow.csv 0 didyouknow");

    SV_LoadLevel(mapname);
    return qtrue;
}


void SV_PreFastRestart(){
    PHandler_Event(PLUGINS_ONPREFASTRESTART, NULL);
}
void SV_PostFastRestart(){
    PHandler_Event(PLUGINS_ONPOSTFASTRESTART, NULL);
}


void __cdecl SV_ReconnectClients(int savepersist)
{
    int i;
    client_t* client;
    const char  *denied;
    char cmd[128];

    // connect and begin all the clients
    for ( i = 0, client = svs.clients; i < sv_maxclients->integer ; i++, client++ ) {
        if(client->state < CS_PRIMED)
        {
            client->gamestateSent = 0;
        }
        // send the new gamestate to all connected clients
        if ( client->state < CS_CONNECTED ) {
            continue;
        }


        if ( client->netchan.remoteAddress.type != NA_BOT ) {
#ifdef CODOL_SERVER
            /* C1 k/x dispatch to CG_MapRestart467980 with preserve=1/0.
             * The zero branch467bf0 clears scoreboard and round UI state;
             * CL_GetServerCommand also handles both before CG dispatch. */
            Com_sprintf(cmd, sizeof(cmd), "%c", savepersist != 0 ? 'k' : 'x');
#else
            Com_sprintf(cmd, sizeof(cmd), "%c", savepersist != 0 ? 'n' : 'B');
#endif
            SV_AddServerCommand(client, 1, cmd);
        }

        // connect the client again, without the firstTime flag
        denied = ClientConnect(i, client->scriptId);
        if(denied){
            SV_DropClient(client, denied);
            Com_Printf(CON_CHANNEL_SERVER,"SV_MapRestart: dropped client %i - denied!\n", i);
            continue;
        }


        if(client->state == CS_ACTIVE){
            SV_ClientEnterWorld( client, &client->lastUsercmd );
        }
    }
}


/*
================
SV_MapRestart

Completely restarts a level, but doesn't send a new gamestate to the clients.
This allows fair starts with variable load times.
================
*/
void SV_MapRestart( qboolean fastRestart ){

    int i;
    client_t    *client;

    // make sure server is running
    if ( !com_sv_running->boolean ) {
        Com_Printf(CON_CHANNEL_SERVER, "Server is not running.\n" );
        return;
    }

    // DHM - Nerve :: Check for invalid gametype
    SV_SetGametype();
    if(Q_stricmp(sv.gametype, sv_g_gametype->string)){
        fastRestart = qfalse; //No fastrestart if we have changed gametypes
    }
    Q_strncpyz(sv.gametype, sv_g_gametype->string, sizeof(sv.gametype));
    int pers = G_GetSavePersist();


    if(!fastRestart)
    {
        G_SetSavePersist(0);
        SV_LoadLevel(sv_mapname->string);
        return;
    }

    if(com_frameTime == sv.start_frameTime)
        return;

    SV_PreFastRestart();

    // connect and begin all the clients
    for ( client = svs.clients, i = 0 ; i < sv_maxclients->integer ; i++, client++ ) {

        if ( client->state < CS_CONNECTED ) {
            continue;
        }

        if ( client->netchan.remoteAddress.type == NA_BOT ) {
            continue;
        }

        // add the map_restart command
//		NET_OutOfBandPrint( NS_SERVER, &client->netchan.remoteAddress, "fastrestart" ); //Replaced

#ifdef CODOL_SERVER
        /* C1 handles map restart at the client layer: index table 0x4878D8
         * sends both k (preserve 1) and x (preserve 0) to 0x487892. IW3's 'm'
         * is SND_StopMusic on C1 (4696ee), so a fast restart never reached the
         * client. A fast restart preserves state, so it is k. */
        SV_SendServerCommandNoLoss( client, "%c", 'k' );
#else
        SV_SendServerCommandNoLoss( client, "%c", 'm' );
#endif
    }

/*    SV_InitCvars();*/
    SV_InitArchivedSnapshot();
    svs.snapFlagServerBit ^= 4;

    SV_GenerateServerId(qfalse); //Short restart

    //sv.inFrame = 0;

    sv.state = SS_LOADING;
//    sv.inFrame = 0;
    sv.restarting = qtrue;

    PHandler_Event(PLUGINS_ONPREGAMERESTART, pers);
    SV_RestartGameProgs(pers);
    PHandler_Event(PLUGINS_ONPOSTGAMERESTART, pers);
#ifndef CODOL_SERVER
    SV_BuildXAssetCSString();
#endif

/*    
    // run a few frames to allow everything to settle
    for ( i = 0 ; i < 3 ; i++ ) {
        svs.time += 100;
        SV_RunFrame();
    }
*/
    sv.state = SS_GAME; //Has to be called before reconnecting clients? Crash after ClientConnect then DropClient?

    SV_ReconnectClients(pers);

    // reset all the vm data in place without changing memory allocation
    // note that we do NOT set sv.state = SS_LOADING, so configstrings that
    // had been changed from their default values will generate broadcast updates

    sv.restarting = qfalse;
    SV_PostFastRestart();
}



/*
==================
SV_CheckTimeouts

If a packet has not been received from a client for timeout->integer
seconds, drop the conneciton.  Server time is used instead of
realtime to avoid dropping the local client while debugging.

When a client is normally dropped, the client_t goes into a zombie state
for a few seconds to make sure any final reliable message gets resent
if necessary
==================
*/
#define SV_MAXCS_CONNECTEDTIME 16
#define MAX_UPDATETIMEOUT 30000

void SV_CheckTimeouts( void ) {

    int i;
    client_t    *cl;
    int primeddroppoint;
    int connectdroppoint;
    int activedroppoint;
    int zombiepoint;

    activedroppoint = svs.time - 1000 * sv_timeout->integer;
    primeddroppoint = svs.time - 1000 * sv_connectTimeout->integer;
    connectdroppoint = svs.time - 1000 * SV_MAXCS_CONNECTEDTIME;
    zombiepoint = svs.time - 1000 * sv_zombieTime->integer;

    for ( i = 0,cl = svs.clients ; i < sv_maxclients->integer ; i++,cl++ ) {
#ifdef CODOL_SERVER
        /* Native bots generate commands locally; no remote packets can
         * refresh their transport timeout, including during map startup. */
        if ( cl->state >= CS_CONNECTED && cl->netchan.remoteAddress.type == NA_BOT ) {
            cl->lastPacketTime = svs.time;
            cl->timeoutCount = 0;
            continue;
        }
#endif
        // message times may be wrong across a changelevel
        if ( cl->lastPacketTime > svs.time ) {
            cl->lastPacketTime = svs.time;
        }

        if ( cl->state == CS_ZOMBIE && cl->lastPacketTime < zombiepoint ) {
            // using the client id cause the cl->name is empty at this point
            if(cl->needupdate && cl->lastPacketTime + MAX_UPDATETIMEOUT > svs.time)
            {
                return;
            }

            Com_Printf(CON_CHANNEL_SERVER, "Going from CS_ZOMBIE to CS_FREE for client %d\n", i );
            cl->state = CS_FREE;    // can now be reused
            continue;
        }

        if(cl->state == CS_ACTIVE && cl->lastPacketTime < activedroppoint){
            // wait several frames so a debugger session doesn't
            // cause a timeout
            if ( ++cl->timeoutCount > 5 ) {
                SV_DropClient( cl, "EXE_TIMEDOUT" );
                cl->state = CS_FREE;    // don't bother with zombie state
            }
        } else if ( cl->state == CS_CONNECTED && cl->lastPacketTime < connectdroppoint) {
            if ( ++cl->timeoutCount > 5 ) {
                SV_DropClient( cl, "EXE_TIMEDOUT" );
                cl->state = CS_FREE;    // don't bother with zombie state
            }
        } else if ( cl->state == CS_PRIMED && cl->lastPacketTime < primeddroppoint ) {
            // wait several frames so a debugger session doesn't
            // cause a timeout
            if ( ++cl->timeoutCount > 5 ) {
                SV_DropClient( cl, "EXE_TIMEDOUT" );
                cl->state = CS_FREE;    // don't bother with zombie state
            }
        } else {
            cl->timeoutCount = 0;
        }
    }
}

/*
==================
SV_CheckPaused
==================
*/
qboolean SV_CheckPaused( void ) {
    client_t    *cl;
    int i;

#ifndef DEDICATEDONLY
    if ( !cl_paused->boolean ) {
        return qfalse;
    }
#endif
    // only pause if there is not a single client connected
    for ( i = 0,cl = svs.clients ; i < sv_maxclients->integer ; i++,cl++ ) {
        if ( cl->state >= CS_ZOMBIE && cl->netchan.remoteAddress.type != NA_BOT ) {
            if ( sv_paused->boolean ) {
                Cvar_SetBool( sv_paused, qfalse );
            }
            return qfalse;
        }
    }
    if ( !sv_paused->boolean ) {
        Cvar_SetBool( sv_paused, qtrue );
    }
    return qtrue;
}



void SV_SetConfigValueForKey(int start, int max, const char *key, const char *value)
{
#ifdef CODOL_SERVER
  /* CVAR_CONFIG is a semantic dvar publication, not an IW3 array write.
   * C1 pairs names24..223 with values224..423. Sending legacy20/128
   * slots overwrote unrelated inherited names and weapon-bob values. */
  if (start == 20 && max == 128) {
    if (!CODOL_PublishReplicatedDvar(key, value))
      Com_Error(ERR_DROP, "CoDOL replicated dvar publication failed: %s", key);
    return;
  }
#endif
  int v4;
  signed int ccsi;
  int i;

  if ( start < 821 ){
    v4 = SL_FindString(key);
  }else{
    v4 = SL_FindLowercaseString(key);
  }
  ccsi = CCS_GetConstConfigStringIndex(value);

  if ( ccsi < 0 )
  {
    i = 0;
    for(i = 0; i < max; ++i)
    {
        if ( SV_GetConfigstringIndex(start + i) == sv.emptyConfigString )
        {
            break;
        }

        if ( v4 == SV_GetConfigstringIndex(start + i) )
        {
            break;
        }
    }

    if(SV_GetConfigstringIndex(start + i) == sv.emptyConfigString)
    {
        SV_SetConfigstring(i + start, key);
    }

  }else{

    i = CCS_GetConfigStringNumForConstIndex(ccsi);
    //constantConfigStrings[ccsi].index;
    if ( i >= start && i < max + start )
    {
      SV_SetConfigstring(i + start, key);
    }
  }

  if ( i == max )
  {
    Com_Printf(CON_CHANNEL_SERVER,"Overflow at config string start value of %i: key values printed below\n", start);
    for(i = 0; i < max; ++i)
    {
        Com_Printf(CON_CHANNEL_SERVER,"%i: %i ( %s )\n", i + start, SV_GetConfigstringIndex(start + i), SL_ConvertToString(SV_GetConfigstringIndex(start + i)));
    }
    Com_Error(ERR_FATAL, "SV_SetConfigValueForKey: overflow");
  }
  SV_SetConfigstring(max + start + i, (char *)value);
}



void SV_SetSystemInfoConfig(void)
{
  char buf[8192];

#ifdef CODOL_SERVER
  /* fs_game is a category carrier here, never a mod directory.  Consume a
   * pending token before it can reach a systeminfo string: the value C1 would
   * see must stay byte-identical to an mp match's, which is empty. */
  FS_CoDOLNormalizeGameDir();
#endif
  Cvar_InfoString_Big(CVAR_SYSTEMINFO, buf, sizeof(buf));

  if ( !fs_gameDirVar->string[0] )
  {
    if ( strlen(buf) + 10 <= 1024 )
    {
        Q_strncat(buf, 1024, "\\fs_game\\\\");
    }
    else
    {
        Com_Printf(CON_CHANNEL_SERVER,"Info string length exceeded\nkey: fs_game\nInfo string:\n%s\n", buf);
    }
  }

  SV_SetConfigstring(1, buf);
  cvar_modifiedFlags &= ~CVAR_SYSTEMINFO;
}


typedef struct
{
    int start;
    int max;
    int bit_flags;
}svConfigCvarInfo_t;


void SV_SetConfigCvar(const cvar_t *var, void* varg)
{
  const char *value;
  svConfigCvarInfo_t *arg;

  arg = (svConfigCvarInfo_t *)varg;

  if ( var->flags & arg->bit_flags )
  {
    value = Cvar_DisplayableValue(var);
    SV_SetConfigValueForKey(arg->start, arg->max, var->name, value);
  }
}

void SV_SetConfig(int start, int max, int bit)
{
  svConfigCvarInfo_t arg;

  arg.start = start;
  arg.max = max;
  arg.bit_flags = bit;
  Cvar_ForEach(SV_SetConfigCvar, &arg);
}

void SV_BotUserMove(client_t *client)
{
    signed int num;
    usercmd_t ucmd = { 0 };
    vec2_t move_pos;
    gentity_t *ent;
    int i;
    float distance;

    if(!client->gentity)
        return;

    num = client - svs.clients;
    ucmd.serverTime = svs.time;

    ent = SV_GentityNum(num);
#ifdef CODOL_SERVER
    {
        int botCommand=CODOL_BotBuildCommand(client,&ucmd);
        if(botCommand) {
            if(botCommand==1) {
                client->deltaMessage=client->netchan.outgoingSequence-1;
                SV_ClientThink(client,&ucmd);
            }
            return; /* 2: a goal notification deleted/reused the receiver. */
        }
    }
#endif

    CODOL_UsercmdSetWeapon(&ucmd, g_botai[num].weapon);

    if ( level.clients[num].sess.archiveTime == 0 )
    {
        ucmd.buttons = g_botai[num].buttons;

        /* Apply movement. */
        if (g_botai[num].doMove)
        {
            /* forwardmove is moving on X axis. */
            /* leftmove is moving on Y axis.    */

            /* Calculate movement origin */
            vec2_copy(move_pos, g_botai[num].moveTo);
            vec2_substract(move_pos, ent->r.currentOrigin);
            /* Com_Printf(CON_CHANNEL_SERVER,"move_pos: (%g, %g) ", move_pos[0], move_pos[1]); */
            distance = vec2_length(move_pos);
            g_botai[num].doMove = distance > 7.0 ? 1 : 0;
            /* Rotate vector according to current client pitch angle. */
            vec2_rotate(move_pos, -ent->r.currentAngles[1]);
            /* Limit vector components to 127. */
            vec2_multiply(move_pos, 127 / vec2_maxabs(move_pos));
            /* Round components to integer values. */
            vec2_floor(move_pos);
            /* Invert second component to fit movement requirements. */
            move_pos[1] = -move_pos[1];
            /* Copy result to actual move command. */
            ucmd.forwardmove = ((int)move_pos[0]) & 0xFF;
            ucmd.rightmove    = ((int)move_pos[1]) & 0xFF;

            //Com_Printf(CON_CHANNEL_SERVER,"val: (%3d, %3d), distance: %f ", ucmd.forwardmove, ucmd.rightmove, distance);
            //Com_Printf(CON_CHANNEL_SERVER,"speed: (%d, %d)", ucmd.forwardmove, ucmd.leftmove);
            //Com_Printf(CON_CHANNEL_SERVER,"origin: (%3.3f, %3.3f, %3.3f)", ent->r.currentOrigin[0], ent->r.currentOrigin[1], ent->r.currentOrigin[2]);
            //Com_Printf(CON_CHANNEL_SERVER,"\n");

            /* Notify only once */
            if (!g_botai[num].doMove)
            {
                Scr_Notify(ent, scr_const.movedone, 0);
                Com_DPrintf(CON_CHANNEL_SERVER,"Bot movement done at (%3.3f, %3.3f)\n",
                            ent->r.currentOrigin[0], ent->r.currentOrigin[1]);
            }

        }

        /* Apply rotation. */
        VectorCopy(ent->client->sess.cmd.angles, ucmd.angles);
        if(g_botai[num].rotIterCount)
        {
            --g_botai[num].rotIterCount;
            for(i = 0; i < 3; ++i)
            {
                if(i < 2)
                {
                    ucmd.angles[i] += g_botai[num].rotFrac[i];
                }
                if(ucmd.angles[i] < 0){
                    ucmd.angles[i] = 0xFFFF + ucmd.angles[i];
                }else if(ucmd.angles[i] > 0xFFFF){
                    ucmd.angles[i] -= 0xFFFF;
                }
            }
            /* Notify only once */
            if (!g_botai[num].rotIterCount)
                Scr_Notify(ent, scr_const.rotatedone, 0);
        }
    }

    if (shouldSpamUseButton(ent))
        ucmd.buttons |= KEY_MASK_USE | KEY_MASK_USERELOAD;

    client->deltaMessage = client->netchan.outgoingSequence - 1;
#ifdef CODOL_SERVER
    CODOL_StageBotWeaponInput((unsigned)num);
#endif
    SV_ClientThink(client, &ucmd);
}


void SV_UpdateBots()
{
    int i;
    client_t* cl;

    SV_ResetSkeletonCache();

    for(i = 0, cl = svs.clients; i < sv_maxclients->integer; ++i, ++cl)
    {
        if(cl->state >= CS_CONNECTED &&
           cl->netchan.remoteAddress.type == NA_BOT)
            SV_BotUserMove(cl);
    }
}



/*
==================
SV_PreFrame
==================
*/
void SV_PreFrame()
{
  SV_UpdateBots();
  if ( cvar_modifiedFlags & 0x404 )
  {
    SV_SetConfigstring(0, Cvar_InfoString(CVAR_SERVERINFO));
    cvar_modifiedFlags &= ~0x404;
  }

  if ( cvar_modifiedFlags & CVAR_SYSTEMINFO )
  {
    SV_SetSystemInfoConfig();
  }

  if ( cvar_modifiedFlags & 256 )
  {
    SV_SetConfig(20, 128, 256);
    cvar_modifiedFlags &= ~256;
  }
  SV_ClientCalcFramerate();

}





/*
==================
SV_FrameMsec
Return time in millseconds until processing of the next server frame.
==================
*/
unsigned int SV_FrameUsec()
{
    if(sv_fps)
    {
        unsigned int frameUsec;

        frameUsec = 1000000 / sv_fps->integer;

        if(frameUsec < sv.timeResidual)
            return 0;
        else
            return frameUsec - sv.timeResidual;
    }
    else
        return 1;
}


/*
spawnerrortest_t e_spawns[64];
#include <math.h>
*/
/*
==================
SV_Frame

Player movement occurs as a result of packet events, which
happen before SV_Frame is called
==================
*/
__optimize3 __regparm1 qboolean SV_Frame( unsigned int usec ) {
    unsigned int frameUsec;
    char mapname[MAX_QPATH];
    static qboolean underattack = qfalse;
    mvabuf;

    if ( !com_sv_running->boolean ) {
        Sys_SleepUSec(20000);
        return qtrue;
    }


    // allow pause if only the local client is connected
/*	if ( SV_CheckPaused() ) {
        SV_MasterHeartbeat( HEARTBEAT_GAME );//Still send heartbeats
        CL_WritePacket( &svs.authserver );
        CL_WritePacket( &svs.scrMaster );
        return;
    }
*/
    // if it isn't time for the next frame, do nothing
    frameUsec = sv.frameusec * com_timescale->value;

    // don't let it scale below 1ms
    if(frameUsec < 1000)
    {
        frameUsec = 1000;
    }
    sv.timeResidual += usec;

    if ( sv.timeResidual < frameUsec ) {
        // NET_Sleep will give the OS time slices until either get a packet
        // or time enough for a server frame has gone by
        underattack = NET_Sleep( frameUsec - sv.timeResidual );
        return qfalse;
    }

    if(underattack)
        NET_Clear();

    SV_PreFrame( );

    // run the game simulation in chunks
    while ( sv.timeResidual >= frameUsec ) {
        sv.timeResidual -= frameUsec;
        div_t svtimeinc = div(frameUsec + svs.timeResidual, 1000);

        svs.time += svtimeinc.quot;
        svs.timeResidual = svtimeinc.rem;
        // let everything in the world think and move
        G_RunFrame( svs.time );
    }

    SV_RunSApiFrame();
    SV_RunFrameXAC();

#ifdef CODOL_SERVER
    /* Team scores reach C1 both as reliable C/D commands and as
     * configstrings 5 and 6; the retained engine writes neither
     * configstring. Publishing here, before the messages go out, keeps a
     * late joiner's gamestate and the live HUD in step. No-op when
     * nothing changed. */
    /* Only while a game is actually running: both walk level.clients and the
     * configstring bank, neither of which is meaningful while the server is
     * still loading a level. */
    if (sv.state == SS_GAME) {
        CODOL_PublishTeamScores();
        /* The player's own score reaches C1's HUD only as the incremental
         * "E <client> <score>" command; without it the readout is whatever
         * the last whole scoreboard said. See codol_scoreboard_sender.c. */
        CODOL_PublishPlayerScores();
        CODOL_RefreshWeaponHud();
        /* In-match rank/XP reaches the C1 client's own secure-profile copy
         * only through its 'K' command; see codol_profile_push.h. */
        CODOL_PushSecureProfiles();
    }
    {
        /* Keep the extended player-state switch live, so the two field
         * families added by the wire audit can be taken out and put back
         * without a restart while they are still unverified against C1. */
        static cvar_t *extended;
        extern int codol_publish_extended_ps;
        if (!extended) extended = Cvar_FindVar("codol_publishExtendedPlayerState");
        if (extended) codol_publish_extended_ps = extended->boolean;
    }
#endif

    // send messages back to the clients
    SV_SendClientMessages();

    Scr_SetLoading(0);

    // update ping based on the all received frames
    SV_CalcPings();

    // check timeouts
    SV_CheckTimeouts();

    // send a heartbeat to the master if needed
    SV_MasterHeartbeat( HEARTBEAT_GAME );


/*
    for(i = 0; i < sv_maxclients->integer; ++i)
    {
        if(svs.clients[i].state < CS_ACTIVE)
        {
            continue;
        }
        if(fabs(svs.clients[i].gentity->r.currentAngles[0] - e_spawns[i].direction1[0]) > 0.1||
        fabs(svs.clients[i].gentity->r.currentAngles[1] - e_spawns[i].direction1[1]) > 0.1 ||
        fabs(svs.clients[i].gentity->r.currentAngles[2] - e_spawns[i].direction1[2]) > 0.1)
        {
            Com_Printf(CON_CHANNEL_SERVER,"^1Debug Spawn angles changed: ^7ent->r.currentAngles changed new: %.2f, %.2f, %.2f\n",
            svs.clients[i].gentity->r.currentAngles[0],
            svs.clients[i].gentity->r.currentAngles[1],
            svs.clients[i].gentity->r.currentAngles[2]);
            Com_Printf(CON_CHANNEL_SERVER,"^1Old angles: ^7ent->r.currentAngles: %.2f, %.2f, %.2f\n",
            e_spawns[i].direction1[0],
            e_spawns[i].direction1[1],
            e_spawns[i].direction1[2]);


            e_spawns[i].direction1[0] = svs.clients[i].gentity->r.currentAngles[0];
            e_spawns[i].direction1[1] = svs.clients[i].gentity->r.currentAngles[1];
            e_spawns[i].direction1[2] = svs.clients[i].gentity->r.currentAngles[2];
        }

        if(fabs(svs.clients[i].gentity->client->ps.viewangles[0] != e_spawns[i].direction2[0]) > 0.1 ||
        fabs(svs.clients[i].gentity->client->ps.viewangles[1] != e_spawns[i].direction2[1]) > 0.1 ||
        fabs(svs.clients[i].gentity->client->ps.viewangles[2] != e_spawns[i].direction2[2]) > 0.1)
        {
            Com_Printf(CON_CHANNEL_SERVER,"^1Debug Spawn angles changed: ^7ent->client->ps.viewangles changed new: %.2f, %.2f, %.2f\n",
            svs.clients[i].gentity->client->ps.viewangles[0],
            svs.clients[i].gentity->client->ps.viewangles[1],
            svs.clients[i].gentity->client->ps.viewangles[2]);
            Com_Printf(CON_CHANNEL_SERVER,"^1Old angles: ^7ent->client->ps.viewangles: %.2f, %.2f, %.2f\n",
            e_spawns[i].direction2[0],
            e_spawns[i].direction2[1],
            e_spawns[i].direction2[2]);

            e_spawns[i].direction2[0] = svs.clients[i].gentity->client->ps.viewangles[0];
            e_spawns[i].direction2[1] = svs.clients[i].gentity->client->ps.viewangles[1];
            e_spawns[i].direction2[2] = svs.clients[i].gentity->client->ps.viewangles[2];

        }

    }

*/

#ifdef PUNKBUSTER
    PbServerProcessEvents( 0 );
#endif
    // if time is about to hit the 32nd bit, kick all clients
    // and clear sv.time, rather
    // than checking for negative time wraparound everywhere.
    // 2giga-milliseconds = 23 days, so it won't be too often
    if ( svs.time > 0x70000000 ) {
        Q_strncpyz( mapname, sv_mapname->string, sizeof(mapname) );
        SV_Shutdown( "EXE_SERVERRESTARTTIMEWRAP" );
        Com_Restart( );
        // TTimo
        // show_bug.cgi?id=388
        // there won't be a map_restart if you have shut down the server
        // since it doesn't restart a non-running server
        // instead, re-run the current map
        SV_Map( mapname );
        return qtrue;
    }

    // this can happen considerably earlier when lots of clients play and the map doesn't change
    if ( svs.nextSnapshotEntities >= 0x7FFFFFFE - svs.numSnapshotEntities ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15numSnapshotEntities wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }

    if ( svs.nextSnapshotClients >= 0x7FFFFFFE - svs.numSnapshotClients ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15numSnapshotClients wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }

    if ( svs.nextCachedSnapshotEntities >= 0x7FFFBFFD ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15nextCachedSnapshotEntities wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }

    if ( svs.nextCachedSnapshotClients >= 0x7FFFEFFD ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15nextCachedSnapshotClients wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }


    if ( svs.nextArchivedSnapshotFrames >= 0x7FFFFB4D ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15nextArchivedSnapshotFrames wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }

    if ( svs.nextArchivedSnapshotBuffer >= 0x7DFFFFFD ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15nextArchivedSnapshotBuffer wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }

    if ( svs.nextCachedSnapshotFrames >= 0x7FFFFDFD ) {
        Q_strncpyz( mapname, sv_mapname->string, MAX_QPATH );
        SV_Shutdown( "EXE_SERVERRESTARTMISC\x15svs.nextCachedSnapshotFrames wrapping" );
        Com_Restart( );
        // TTimo see above
        SV_Map( mapname );
        return qtrue;
    }
    SetAnimCheck(com_animCheck->boolean);

    if( svs.time > svs.frameNextSecond){	//This runs each second
            svs.frameNextSecond = svs.time+1000;

            // the menu kills the server with this cvar
            if ( sv_killserver->boolean ) {
                SV_Shutdown( "Server was killed.\n" );
                Cvar_SetBool( sv_killserver, qfalse );
                return qtrue;
            }

            if(svs.time > svs.frameNextTenSeconds){	//This runs each 10 seconds
            svs.frameNextTenSeconds = svs.time+10000;

            int d, h, m;
            int uptime;

            uptime = Sys_Seconds();
            d = uptime/(60*60*24);
    //		uptime = uptime%(60*60*24);
            h = uptime/(60*60);
    //		uptime = uptime%(60*60);
            m = uptime/60;

            if(h < 4)
                Cvar_SetString(sv_uptime, va("%i minutes", m));
            else if(d < 3)
                Cvar_SetString(sv_uptime, va("%i hours", h));
            else
                Cvar_SetString(sv_uptime, va("%i days", d));

            serverStatus_Write();

            PHandler_Event(PLUGINS_ONTENSECONDS, NULL);	// Plugin event
    /*		if(svs.time > svs.nextsecret){
                svs.nextsecret = svs.time+80000;
                Com_RandomBytes((byte*)&svs.secret,sizeof(int));
            }*/

    }
    }

    return qtrue;
}


void SV_SayToPlayers(int clnum, int team, char* text)
{

    client_t *cl;

    if(clnum >= 0 && clnum < 64){
        SV_SendServerCommand(&svs.clients[clnum], SV_CHAT_CMD " \"%s\"", text);
        return;
    }
    if(team == -1)
    {
        SV_SendServerCommand(NULL, SV_CHAT_CMD " \"%s\"", text);
        return;
    }
    for(cl = svs.clients, clnum = 0; clnum < sv_maxclients->integer; clnum++){

        if(cl->state < CS_ACTIVE)
            continue;

        if(team != level.clients[clnum].sess.cs.team)
            continue;

        SV_SendServerCommand(cl, SV_CHAT_CMD " \"%s\"", text);
    }
}


qboolean SV_UseUids()
{
    return psvs.useuids;
}

const char* SV_GetMapRotation()
{
    return sv_mapRotation->string;
}

const char* SV_GetNextMap()
{
    return sv_nextmap->string;
}


void SV_ShowClientUnAckCommands( client_t *client )
{
    int i;

    Com_Printf(CON_CHANNEL_SERVER,"-- Unacknowledged Server Commands for client %i:%s --\n", client - svs.clients, client->name);

    for ( i = client->reliableAcknowledge + 1; i <= client->reliableSequence; ++i )
    {
        Com_Printf(CON_CHANNEL_SERVER,"cmd %5d: %8d: %s\n", i, client->reliableCommands[i & (MAX_RELIABLE_COMMANDS -1)].cmdTime,
                   client->reliableCommands[i & (MAX_RELIABLE_COMMANDS -1)].command );
    }

    Com_Printf(CON_CHANNEL_SERVER,"-----------------------------------------------------\n");
}


void SV_CalculateChecksums()
{
    int i;
    char filename[MAX_OSPATH];
    //char* str;
    int len, crc32;

    Com_Printf(CON_CHANNEL_SERVER,"^4Calculate referenced files checksums...\n");
    Cmd_TokenizeString(sv_referencedIwdNames->string);

    for(i = 0; i < Cmd_Argc(); ++i)
    {
        Com_sprintf(filename, sizeof(filename), "%s.iwd", Cmd_Argv(i));
        len = FS_CalculateChecksumForFile(filename, &crc32);
        Com_Printf(CON_CHANNEL_SERVER,"^4CRC32 for %s is %x Len %d\n", filename, crc32, len);
    }
    Cmd_EndTokenizedString();

    Cmd_TokenizeString(sv_referencedFFNames->string);

    for(i = 0; i < Cmd_Argc(); ++i)
    {

        DB_GetQPathForZone(Cmd_Argv(i), sizeof(filename), filename);

        if((len = FS_CalculateChecksumForFile(filename, &crc32)) <= 0)
        {
            Com_PrintError(CON_CHANNEL_SERVER,"file for loaded zone '%s' not found\n", Cmd_Argv(i));
        }else{
            Com_Printf(CON_CHANNEL_SERVER,"^4CRC32 for %s is %x Len %d\n", filename, crc32, len);
        }
    }

    Cmd_EndTokenizedString();
}


void SV_WriteChecksumInfo(msg_t* msg, const char* filename)
{
    MSG_WriteLong(msg, 0);
    msg->cursize += FS_WriteChecksumInfo(filename, msg->data + msg->cursize, msg->maxsize - msg->cursize);
}


/*
===============
SV_SetConfigstring

===============
*/
void SV_SetConfigstring( int index, const char *val ) {
    int len, i;
#ifndef CODOL_SERVER
    int maxChunkSize = MAX_STRING_CHARS - 24;
#endif
    client_t    *client;
    uint16_t ccs;
#ifndef CODOL_SERVER
    char buf[MAX_STRING_CHARS];
    char cmd;
#endif

    if ( index < 0 || index >= MAX_CONFIGSTRINGS ) {
        Com_Error( ERR_DROP, "SV_SetConfigstring: bad index %i\n", index );
        return;
    }

    if ( !val ) {
        val = "";
    }

    // don't bother broadcasting an update if no change
    if ( !strcmp( val, SL_ConvertToString(SV_GetConfigstringIndex(index)) ) )
    {
        return;
    }

    // change the string in sv
    SL_RemoveRefToString( SV_GetConfigstringIndex(index) );
    if(index <= 820)
    {
        ccs = SL_GetString(val, 0);
    }else{
        ccs = SL_GetLowercaseString(val, 0);
    }

    sv.configstrings[index] = ccs;


    // send it to all the clients if we aren't
    // spawning a new server
    if ( sv.state != SS_GAME && !sv.restarting )
    {
        return;
    }
#ifdef CODOL_SERVER
    {
        int published=CODOL_PublishAssetConfigstring(index);
        if(published) {
            if(published<0) Com_Error(ERR_DROP,"Invalid CoDOL asset configstring %d",index);
            return;
        }
    }
    if(index==0) {
        if(!CODOL_SetServerInfo(sv_mapname->string,sv_g_gametype->string,sv_maxclients->integer,sv_hostname->string)) {
            Com_Error(ERR_DROP,"Invalid CoDOL serverinfo");
            return;
        }
        val=CODOL_GetConfigstring(CODOL_ServerConfigstrings(),0);
    }
    /* C1's native sender5d30e0 bounds the value to1015 bytes and emits
     * exactly one d command. Its CL_GetServerCommand487730 does not
     * reassemble IW3 x/y/z; x instead enters its control/reset handler.
     * Validate the translated wire value, not the retained IW3 storage. */
    len = strlen(val);
    if(len > CODOL_CONFIGSTRING_VALUE_CHARS) {
        Com_Error(ERR_DROP, "CoDOL configstring %i exceeds %i bytes", index,
            CODOL_CONFIGSTRING_VALUE_CHARS);
        return;
    }
    for(i = 0, client = svs.clients; i < sv_maxclients->integer; ++i, ++client) {
        if(client->state >= CS_PRIMED && client->gamestateSent)
            SV_SendServerCommandNoLoss(client, "d %i %s", index, val);
    }
#else

    sprintf(buf, "%i", index);
    maxChunkSize = MAX_STRING_CHARS - 4 - strlen(buf);
    len = strlen( val );

    // send the data to all relevent clients
    for ( i = 0, client = svs.clients; i < sv_maxclients->integer ; i++, client++ )
    {
        if ( client->state < CS_PRIMED ) {
            continue;
        }

        if ( len >= maxChunkSize ) {
            int sent = 0;
            int remaining = len;


            while ( remaining > 0 ) {
                if ( sent == 0 ) {
                    cmd = 'x';
                } else if ( remaining < maxChunkSize )    {
                    cmd = 'z';
                } else {
                    cmd = 'y';
                }
                Q_strncpyz( buf, &val[sent], maxChunkSize );

                SV_SendServerCommandNoLoss( client, "%c %i %s", cmd, index, buf );

                sent += ( maxChunkSize - 1 );
                remaining -= ( maxChunkSize - 1 );
            }
        } else {
            // standard cs, just send it
            cmd = 'd';
            SV_SendServerCommandNoLoss( client, "%c %i %s", cmd, index, val );
        }
    }
#endif
}


void SV_GenerateServerId(qboolean longrestart)
{
    int serverid;
    int playcount;

    if(longrestart)
    {
        sv.start_frameTime = com_frameTime;
    }

    playcount = sv_serverid->integer & 0x000000ff;

    ++playcount;

    serverid = (sv.start_frameTime & 0xffffff00) | (playcount & 0x000000ff);

    Cvar_SetInt(sv_serverid, serverid);
#ifdef CODOL_SERVER
    if(!CODOL_PublishServerId(serverid))
        Com_Error(ERR_DROP, "Cannot publish CoDOL server ID");
#endif

}


/*
===============
SV_Startup

Called when a host starts a map when it wasn't running
one before.  Successive map or map_restart commands will
NOT cause this to be called, unless the game is exited to
the menu system first.
===============
*/
void SV_Startup( void ) {

    if ( svs.initialized ) {
        Com_Error( ERR_FATAL, "SV_Startup: svs.initialized" );
    }

    // RF, avoid trying to allocate large chunk on a fragmented zone
/*
    svs.clients = calloc( sizeof( client_t ) * sv_maxclients->integer, 1 );
    if ( !svs.clients ) {
        Com_Error( ERR_FATAL, "SV_Startup: unable to allocate svs.clients" );
    }
    //svs.clients = Z_Malloc (sizeof(client_t) * sv_maxclients->integer );
*/
/*
    if ( com_dedicated->integer ) {
        svs.numSnapshotEntities = sv_maxclients->integer * PACKET_BACKUP * 64;
    } else {
        // we don't need nearly as many when playing locally
        svs.numSnapshotEntities = sv_maxclients->integer * 4 * 64;
    }
*/
    svs.numSnapshotEntities = 0x2A000;
    svs.numSnapshotClients = 32 * sv_maxclients->integer * sv_maxclients->integer;
    svs.initialized = qtrue;

    //1st OOBProfilepacket would get time = svs.time

    Cvar_SetBool( com_sv_running, 1 );
}


/*
================
SV_CreateBaseline

Entity baselines are used to compress non-delta messages
to the clients -- only the fields that differ from the
baseline will be transmitted
================
*/
void SV_CreateBaseline( void ) {
    gentity_t *svent;
    int entnum;

    for ( entnum = 1; entnum < sv.num_entities ; entnum++ ) {
        svent = SV_GentityNum( entnum );
        if ( !svent->r.linked ) {
            continue;
        }
        svent->s.number = entnum;
        //
        // take current state as baseline
        //
        sv.svEntities[entnum].baseline.s = svent->s;

        sv.svEntities[entnum].baseline.r.svFlags = svent->r.svFlags;

        sv.svEntities[entnum].baseline.r.clientMask[0] = svent->r.clientMask[0];
        sv.svEntities[entnum].baseline.r.clientMask[1] = svent->r.clientMask[1];

        VectorCopy(svent->r.absmin, sv.svEntities[entnum].baseline.r.absmin);
        VectorCopy(svent->r.absmax, sv.svEntities[entnum].baseline.r.absmax);

        if ( svent->s.clientNum >= 64 )
        {
          svent->s.clientNum = 64;
        }
    }
}




void SV_SaveSystemInfo()
{
    SV_SetSystemInfoConfig();
    SV_SetConfigstring(0, Dvar_InfoString(0, 1028));

    cvar_modifiedFlags &= ~ (CVAR_SERVERINFO | 1024);

    SV_SetConfig(20, 128, 256);

    cvar_modifiedFlags &= ~256;
    //cvar_modifiedFlags &= ~CVAR_WOLFINFO;
}

void SV_ChangeMaxClients()
{
    //No change. At least now
}


void SV_InitXAC();
/* Fragmented testing: 0x8174A74 jmp to 08174E98 (SV_RunFrame(...)) */


#ifdef CODOL_SERVER
/*
============================================================================
CoDOL asset-category resolution

The category (mp | coop | zm) selects the gametype zones that mount, the
mp/constConfigStrings_<cat>.csv namespace, the constant-configstring CRC in the
gamestate and the script set that compiles.  It is resolved from scratch on
every spawn, in this precedence:

  1. fs_game, this match's explicit carrier from the lobby.  It is the only
     input that can say "coop" for an mp_* level zone, because a coop match
     loads the mp_* level with common_gametype_coop.
  2. codol_zoneType written since the last promotion, i.e. latchedString still
     disagreeing with string.  That is precisely "the lobby set it for THIS
     match" -- once a spawn promotes the latch the two are equal again, so a
     leftover from the previous match can never look explicit.
  3. The map name, which proves the category for zm_* and coop_* spellings.
  4. "mp".

The previous match's value deliberately never wins.  It used to, by default,
and it killed the server: with codol_zoneType left at "mp" from an earlier
match, `map zm_prototype_sh` (a console/exitLevel map change, no rcon
dispatch) hit the mismatch guard in CODOL_LoadMapArchives, which sv_main turned
into Com_Error(ERR_DROP) -- "Server crashed" (MEASURED, qconsole log around
'Server: zm_prototype_sh').  The map name is a FALLBACK that auto-selects, not
a veto.

A genuine contradiction between an explicit category and the map name is
corrected and announced rather than made fatal, for the same reason: ERR_DROP
here ends a running match and drops the connected client, whereas a correction
loads the set the client itself will pick from the map name.
============================================================================
*/

/* The category the map NAME proves, or NULL when it cannot decide.  Mirrors
 * C1 0x612850 for the two prefixes that are unambiguous, and deliberately does
 * NOT claim "mp" for an mp_* zone: a coop match legitimately pairs an mp_*
 * level zone with common_gametype_coop. */
static const char *SV_CoDOLCategoryProvenByMapName(const char *map)
{
    if(!map || !*map)
        return NULL;
    if(!Q_stricmpn(map, "zm", 2))
        return "zm";
    if(!Q_stricmpn(map, "coop", 4))
        return "coop";
    return NULL;
}

/* Force a value onto codol_zoneType so that BOTH string and latchedString end
 * up holding it.  Cvar_SetVariant early-outs when var->string already matches
 * (cvar.c, CVAR_STRING case), which would leave a disagreeing latchedString
 * behind for the re-registration below to promote -- the exact opposite of
 * what was asked for.  Moving the value away first makes the real set land. */
static void SV_CoDOLForceZoneType(const char *category)
{
    if(!codol_zoneType)
        return;
    if(codol_zoneType->latchedString && Q_stricmp(codol_zoneType->latchedString, category))
        Cvar_SetString(codol_zoneType, "");
    Cvar_SetString(codol_zoneType, category);
}

static void SV_CoDOLResolveAssetCategory(const char *mapname)
{
    const char *explicitCat = NULL;
    const char *source = "";
    const char *proven;
    const char *resolved;

    if(!codol_zoneType)
        return;

    /* (1) fs_game.  FS_CoDOLNormalizeGameDir has already emptied the dvar; the
     * token is held for exactly one map load. */
    FS_CoDOLNormalizeGameDir();
    explicitCat = FS_CoDOLConsumeGameCategory();
    if(explicitCat)
    {
        source = "fs_game";
    }
    /* (2) codol_zoneType written for this match but not yet promoted. */
    else if(codol_zoneType->latchedString && codol_zoneType->string &&
            Q_stricmp(codol_zoneType->latchedString, codol_zoneType->string) &&
            FS_CoDOLCategoryToken(codol_zoneType->latchedString))
    {
        explicitCat = FS_CoDOLCategoryToken(codol_zoneType->latchedString);
        source = "codol_zoneType";
    }

    proven = SV_CoDOLCategoryProvenByMapName(mapname);

    if(explicitCat)
    {
        resolved = explicitCat;
    }
    else
    {
        /* (3) then (4).  Never the previous match's value. */
        resolved = proven ? proven : "mp";
        source = proven ? "map name" : "default";
    }

    /* Contradictions.  An mp_* level zone with category coop is NOT one: that
     * pairing is how every coop match ships. */
    if(proven && Q_stricmp(resolved, proven))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL asset category: %s asked for '%s' but '%s' is a '%s' map -- the client "
            "derives '%s' from the map name and would disagree with us on the zone chain, "
            "the constant-configstring namespace and fs_crc. Loading '%s'.\n",
            source, resolved, mapname, proven, proven, proven);
        resolved = proven;
        source = "map name (corrected)";
    }
    else if(!proven && !Q_stricmp(resolved, "zm"))
    {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL asset category: %s asked for 'zm' but '%s' is not a zm_* map; zm content "
            "lives only under zm_* level zones. Loading 'mp'.\n", source, mapname);
        resolved = "mp";
        source = "map name (corrected)";
    }

    Com_Printf(CON_CHANNEL_SERVER, "CoDOL asset category: %s (from %s) for map %s\n",
        resolved, source, mapname && *mapname ? mapname : "?");

    SV_CoDOLForceZoneType(resolved);
}
#endif

void SV_SpawnServer(const char *mapname)
{
  int savedPersist;
  char bspfilename[64];
  const char* dropreason;
  XZoneInfo zoneinfo;
  char outChkSums[8192];
  char outPathNames[8192];
  int i, checksum;
  client_t* cl;

    if(svs.sysrestartmessage[0])
    {
        Sys_Restart(svs.sysrestartmessage);
        return;
    }

    /* A load that spins must not hold the server silently forever: see the
     * map-load watchdog in sys_main.c (VPS 2026-09-27, zm_prototype_sh). */
    {
        cvar_t *loadWatchdog = Cvar_RegisterInt("sys_loadWatchdog", 90, 0, 3600, 0,
            "Seconds a map load may run without finishing before the server records the main thread's stack and exits so it can be restarted (0 = off)");
        Sys_LoadWatchdogArm(mapname, loadWatchdog->integer);
    }

#ifdef _LAGDEBUG
    Com_DPrintfLogfile("SV_SpawnServer Begin\n");
#endif

  Com_SyncThreads();
  Sys_BeginLoadThreadPriorities();

#ifdef CODOL_SERVER
  /* codol_zoneType decides which gametype zones mount, which
   * mp/constConfigStrings_<type>.csv installs, and which script set compiles,
   * all of which are read further down in this function.  It is CVAR_LATCH, so
   * the lobby's `set codol_zoneType zm` over rcon only writes latchedString --
   * Cvar_Set_f passes force=qfalse (cvar.c:1727) and Cvar_SetVariant leaves
   * var->string alone for a latched var (cvar.c:825-829).  Registration is the
   * engine's own promotion point: Cvar_Register takes the latched value with
   * force=qtrue (cvar.c:686).  g_gametype gets exactly this treatment once per
   * map from GScr_LoadGameTypeScript, which is why it takes effect and this
   * one, registered once in SV_InitCvarsOnce, silently did not: a live server
   * handed `zm` would have mounted common_gametype_mp against a zm map.
   * A map spawn is the restart the latch is waiting for.
   *
   * The resolve below now decides the value first -- from fs_game, from a
   * latch the lobby wrote for THIS match, or from the map name -- and forces
   * string and latchedString to agree, so this registration promotes exactly
   * what was resolved and nothing older.  It must stay ahead of FS_Restart and
   * of CODOL_LoadMapArchives, both further down in this function. */
  SV_CoDOLResolveAssetCategory(mapname);
  Cvar_RegisterString("codol_zoneType", "mp", CVAR_LATCH,
      "CoDOL asset category: mp, coop or zm; distinct from g_gametype");
#endif

#ifndef DEDICATEDONLY
  char loadffname[128];

  if ( useFastFile->boolean && !com_dedicated->integer )
  {
    //DB_AddUserMapDir(mapname); //Done by FS_Startup
    DB_ResetZoneSize(0);
    Com_sprintf(loadffname, sizeof(loadffname), "%s_load", mapname);
    zoneinfo.name = loadffname;
    zoneinfo.allocFlags = 32;
    zoneinfo.freeFlags = 96;
    DB_LoadXAssets(&zoneinfo, 1u, 0);
  }
#endif
  Scr_ParseGameTypeList();
  SV_SetGametype();

#ifndef DEDICATEDONLY
  CL_InitLoad(mapname, sv_g_gametype->string);
#endif

  if ( useFastFile->boolean )
  {
    DB_SyncXAssets();
    DB_UpdateDebugZone();
  }

  savedPersist = 0;
  if ( com_sv_running->boolean )
  {
    savedPersist = G_GetSavePersist();

        for(i = 0, cl = svs.clients; i < sv_maxclients->integer; ++i, cl++)
        {
            if(cl->demorecording)
            {
                SV_StopRecord(cl);
                cl->demorecording = qtrue; //Making a new demo later when server is spawned
                char shortdmname[1024];
                int demonamelen = strlen(cl->demoName);
                if(demonamelen < 15 )
                {
                    cl->demoName[0] = 0;
                }else{
                    Q_strncpyz(shortdmname, cl->demoName + 6, sizeof(cl->demoName)); //Remove demos/
                    shortdmname[demonamelen -6 -5 -4] = 0;
                    Q_strncpyz(cl->demoName, shortdmname, sizeof(cl->demoName)); //remove .dm_1
                }
            }

            if ( cl->state < CS_PRIMED )
            {
                continue;
            }
#ifdef CODOL_SERVER
            /* C1 connectionless handler496e9b checks the server address,
             * reads map and gametype as separate lines, enters connection
             * state5 and calls the loading handler499560. Reliable l is
             * an audio command in C1, not the IW3 map-loading notice.
             * The second line is the zone category, not the gametype: C1
             * passes it straight to its zone-list builder 0x4CCDF0 (measured
             * live 2026-09-28: 0x499450("combat") on a map_restart), which
             * only tests "zm" and "coop"; the gamestate names the same
             * category from codol_zoneType, resolved above for this map. */
            if(cl->netchan.remoteAddress.type != NA_BOT)
                NET_OutOfBandPrint(NS_SERVER, &cl->netchan.remoteAddress,
                    "loadingnewmap\n%s\n%s\n", mapname,
                    codol_zoneType && codol_zoneType->string && *codol_zoneType->string ?
                        codol_zoneType->string : "mp");
#else
            SV_SendServerCommandNoLoss( cl, "%c \"%s\" \"%s\"", 'l', mapname, sv_g_gametype->string );
#endif
            // force a snapshot to be sent
            cl->nextSnapshotTime = -1;
            SV_SendClientSnapshot( cl );
        }
    Sys_SleepUSec(250000);
  }
  Cvar_SetStringByName("mapname", mapname);
#ifndef DEDICATEDONLY
  CL_MapLoading();
  CL_ShutdownAll();
#endif
  Sys_LoadWatchdogPhase("shutting down the previous game");
  SV_ShutdownGameProgs();
  Com_Printf(CON_CHANNEL_SERVER,"------ Server Initialization ------\n");
  Com_Printf(CON_CHANNEL_SERVER,"Server: %s\n", mapname);
  Sys_LoadWatchdogPhase("clearing the server and mounting the map");

  SV_ClearServer(); //Inline on MACOS_X

  if ( !useFastFile->boolean )
  {
    FS_Shutdown(qtrue);
    FS_ClearPakReferences( 0 ); //FS_ClearIwdReferences();
  }
  Com_Restart();
  if ( com_sv_running->boolean )
  {
    SV_ChangeMaxClients();
  }
  else
  {
    SV_Startup();// Inline on MACOS_X
  }
  Q_strncpyz(sv.gametype, sv_g_gametype->string, sizeof(sv.gametype));

    // get a new checksum feed and restart the file system
    srand( Sys_MillisecondsRaw() );
    sv.checksumFeed = ( ( (int) rand() << 16 ) ^ rand() ) ^ Sys_Milliseconds();
#ifdef CODOL_SERVER
    /* sv is cleared per spawn; keep the feed a client's stale first cp still
     * names (SV_VerifyPaks_f) for its log line. */
    codol_previous_checksum_feed = codol_current_checksum_feed;
    codol_current_checksum_feed = (unsigned)sv.checksumFeed;
#endif

    // DO_LIGHT_DEDICATED
    // only comment out when you need a new pure checksum string and it's associated random feed
    Com_Printf(CON_CHANNEL_SERVER,"SV_SpawnServer checksum feed: %p\n", sv.checksumFeed);

    FS_Restart( sv.checksumFeed );


  if ( !useFastFile->boolean )
  {
    Com_GetBspFilename(bspfilename, 64, mapname);
    SV_SetExpectedHunkUsage(bspfilename);
  }
#ifndef DEDICATEDONLY
  CL_StartLoading( );
#endif
#ifndef CODOL_SERVER
  if ( useFastFile->boolean )
#endif
  {
    /* CoDOL map archives and inherited configstrings are required regardless
     * of the retained IW3 loose-file toggle. */
    //DB_AddUserMapDir(mapname); //Done by FS_Startup
    zoneinfo.name = mapname;
    zoneinfo.allocFlags = 8;
    zoneinfo.freeFlags = 8;
#ifdef CODOL_SERVER
    /* Changing category means the previous category's gametype zones and its
     * script set must go before the new ones mount; nothing else in the
     * process retires them.  The asset layer owns that teardown and installs
     * itself through SV_SetCoDOLCategoryTeardown. */
    /* A same-category change to a DIFFERENT map must run the same teardown:
     * CODOL_LoadMapArchives retires the outgoing map's group without freeing
     * it (its data may still be reachable from composed weapons), and nothing
     * else ever released it, so every zm_prototype -> zm_asylum style change
     * left another full map resident. Measured on 2026-09-22: a probe grew
     * from 0.7 GB to 2.1 GB over five zombie map changes. A restart of the
     * same map keeps its reuse fast path: the mount compares names and skips. */
    if(codol_loadedZoneType[0] &&
       (Q_stricmp(codol_loadedZoneType, codol_zoneType->string) ||
        (codol_loadedMapName[0] && Q_stricmp(codol_loadedMapName, mapname))))
    {
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL asset %s change %s/%s -> %s/%s: retiring the previous gametype zones and scripts\n",
            Q_stricmp(codol_loadedZoneType, codol_zoneType->string) ? "category" : "map",
            codol_loadedZoneType, codol_loadedMapName[0] ? codol_loadedMapName : "-",
            codol_zoneType->string, mapname);
        if(codol_categoryTeardown)
            codol_categoryTeardown(codol_loadedZoneType, codol_zoneType->string);
        else
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL asset category change with no teardown installed: the %s gametype zones stay resident\n",
                codol_loadedZoneType);
    }
    /* A coop match carries two map spellings: the playlist zone the lobby knows
     * (coop_training_mp_killhouse_sh) and the level zone that goes on the wire
     * and is what `map` named (mp_killhouse_sh).  Hand the first one over
     * before the mount; the mount still keys off `mapname`. */
    if(codol_sessionMapInstaller)
        codol_sessionMapInstaller(SV_CoDOLSessionMapName());
    if(!CODOL_LoadMapArchives(mapname,codol_zoneType->string))
        Com_Error(ERR_DROP,"CoDOL map archive loading failed: %s",mapname);
    Q_strncpyz(codol_loadedZoneType, codol_zoneType->string, sizeof(codol_loadedZoneType));
    Q_strncpyz(codol_loadedMapName, mapname, sizeof(codol_loadedMapName));
    {
        const codol_engine_table_t *constants=NULL;
        const char *table_name=va("mp/constConfigStrings_%s.csv",codol_zoneType->string);
        if(!CODOL_SetServerMapIdentity(mapname,codol_zoneType->string) ||
           CODOL_LoadEngineStringTable(table_name,&constants)!=1 || constants->columnCount!=2 ||
           !CODOL_SetServerInheritedConfigstrings(codol_zoneType->string,(size_t)constants->rowCount,constants->values)) {
            Com_Error(ERR_DROP,"CoDOL inherited configstring initialization failed: %s",table_name);
            return;
        }
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL inherited configstrings installed: %d (%s)\n",constants->rowCount,codol_zoneType->string);
        if(!CODOL_InitializeServerWeaponConfigstrings(codol_zoneType->string)) {
            Com_Error(ERR_DROP,"CoDOL weapon configstrings: %s",CODOL_ServerWeaponRegistryError());
            return;
        }
        /* Resolve hand behavior from the definitions owned by the loaded archives.
         * Installing the dual-wield resolver also invalidates its cached flags. */
        CODOL_SetWeaponDualWieldResolver(CODOL_GetNativeWeaponDualWield);
        CODOL_SetWeaponRechamberDualWieldResolver(CODOL_GetNativeWeaponRechamberDualWield);
        CODOL_SetWeaponSpinUpResolver(CODOL_GetNativeWeaponSpinUp);
        CODOL_SetWeaponDetonateTriggerResolver(CODOL_GetNativeWeaponDetonateTrigger);
        CODOL_SetWeaponRequiresGroundResolver(CODOL_GetNativeWeaponRequiresGround);
        CODOL_SetWeaponHoldPinResolver(CODOL_GetNativeWeaponHoldPin);
        /* Capture once: every later gamestate and this registry replay must
         * use the same class mask, even if the configuration changes mid-map.
         * Archives are mounted before any animlist rawfile is requested. */
        CODOL_ResetModelAnimations();
        {
            /* The mask says which actor animation classes C1 registers at map
             * load. MEASURED at C1 0x0040840b-0x0040847a: five trees indexed
             * by one bit each, ebx starting at 1 and rol'd per iteration --
             * 0x01 generic_human, 0x02 dog, 0x04 generic_human,
             * 0x08 generic_human, 0x10 zombie_dog. Bit 0x08 is the humanoid
             * actor class and also pulls common_zombie.animlist, whose
             * =generic_human group carries every ai_zombie_* animation, so it
             * is the one bit a zombies match needs. C1 clears a class bit
             * whose animlist fails to load, so an unsupported class degrades
             * rather than breaking.
             *
             * Derive the category's requirement from the species table rather
             * than making the operator remember a number per game mode: the
             * launcher's historical default (2, dog) is right for mp and
             * silently wrong for zm. An operator who sets the dvar explicitly
             * still wins -- we only warn if their value omits a bit the
             * mounted category's species need. */
            unsigned mask = (unsigned)codol_animlistMask->integer;
            unsigned needed = CODOL_ActorSpeciesAnimListMask(codol_zoneType->string);
            /* "Unset" is the registered default 0, NOT !->modified: MEASURED
             * live 2026-09-20, Cvar_RegisterInt leaves ->modified set, so the
             * derive branch never ran and an mp boot warned that mask 0x0
             * omits the dog bit -- i.e. this check disabled the very thing it
             * was added to supply. A mask of 0 registers no actor animation
             * classes at all, which is never what an operator wants; any
             * deliberate value is non-zero and still wins below. */
            if(mask == 0 && needed != 0) {
                Com_Printf(CON_CHANNEL_SERVER,
                    "CoDOL animation classes: %s needs mask 0x%x; using it in place of the default 0x%x\n",
                    codol_zoneType->string, needed, mask);
                mask = needed;
            } else if(needed & ~mask) {
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "CoDOL animation classes: codol_animlistMask 0x%x omits 0x%x, which the %s species need; "
                    "those actors will not animate\n", mask, needed & ~mask, codol_zoneType->string);
            }
            if(!CODOL_SetServerAnimListFlags(mask)) {
                Com_Error(ERR_DROP,"CoDOL invalid animation class mask");
                return;
            }
        }
        if(CODOL_LoadClientAnimTrees(mapname,CODOL_ServerAnimListFlags(),NULL)<0) {
            Com_Error(ERR_DROP,"CoDOL animation list rawfile could not be loaded");
            return;
        }
        /* The waypoint graph belongs to the map, so load it here rather
         * than from maps/mp/gametypes/_codol_bots::init(): that script is
         * threaded by _gamelogic, which only the mp gametypes run, so a zm
         * or coop map used to inherit the previous map's nodes and plan
         * actor routes over coordinates from a different level
         * (docs/CODOL_ZOMBIE_SPAWN_20260921.md).  No CSV is the normal case
         * outside mp; an empty graph is what the actor mover needs to fall
         * back to a straight line. */
        {
            int nodes=CODOL_BotNavLoadForMap(mapname);
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL waypoint graph: %d nodes for %s (%s)\n",
                nodes, mapname, nodes ? "waypoints/<map>_wp.csv" :
                "no CSV for this map; actors steer straight at their goal");
        }
    }
#else
    DB_LoadXAssets(&zoneinfo, 1u, 0);
#endif
  }
  sv.emptyConfigString = SL_GetString("", 0);

  // allocate empty config strings
  for ( i = 0 ; i < MAX_CONFIGSTRINGS ; i++ ) {
    sv.configstrings[i] = SL_GetString("", 0);
  }

  Cvar_ClearFlagsForEach(1024); //CVAR_NORESTART? Probably not Cvar_ResetScriptInfo();


  SV_InitArchivedSnapshot();
  SV_InitSnapshot();
  svs.snapFlagServerBit ^= 4u;

//  Cvar_SetString(nextmap, "map_restart");
#ifndef DEDICATEDONLY
  Cvar_SetInt(cl_paused, 0);
#endif

  Com_GetBspFilename(bspfilename, sizeof(bspfilename), mapname);
#ifndef CODOL_SERVER
  if ( !useFastFile->boolean )
  {
    Com_LoadBsp(bspfilename);
  }
#endif
  CM_LoadMap(bspfilename, &checksum);
  Com_LoadWorld(bspfilename);
#ifndef CODOL_SERVER
  if ( !useFastFile->boolean )
  {
    Com_UnloadBsp();
  }
#endif
  CM_LinkWorld();
  SV_GenerateServerId(qtrue); //Long restart

  sv.state = SS_LOADING;
#ifndef CODOL_SERVER
  if ( !useFastFile->boolean )
  {
    Com_LoadSoundAliases(bspfilename, "all_mp", 2u);
  }
#endif



  Sys_LoadWatchdogPhase("G_InitGame");
  SV_InitGameProgs(savedPersist);

  Sys_LoadWatchdogPhase("settling frames");
  for(i = 0; i < 3; ++i)
  {
    svs.time += 100;
    SV_RunFrame();
  }

  SV_CreateBaseline(); //inline in MACOS_X

    for(i = 0, cl = svs.clients; i < sv_maxclients->integer; ++i, ++cl)
    {
        if ( cl->state < CS_CONNECTED )
        {
            continue;
        }
#ifdef CODOL_SERVER
        /* SV_RemoveAllBots ran before this spawn, so any bot here was added
         * by the level script (_codol_bots.gsc addTestClient) during the
         * three warm-up SV_RunFrame calls above; SV_AddBotClient already ran
         * ClientConnect and SV_ClientEnterWorld for it. Re-running
         * ClientConnect here and demoting it to CS_CONNECTED left a bot
         * with no client to re-enter the world: SV_ClientThink never ran
         * ClientThink for it, so slot 0 sat at the spawn commandTime with
         * PMF_RESPAWNED for the whole match. (Re-entering it from here
         * instead duplicated the script connect state: two onPlayerSpawned
         * loops -> "already attached" fatal script error.) Bots need no
         * gamestate; leave them alone. */
        if ( cl->netchan.remoteAddress.type == NA_BOT )
        {
            continue;
        }
#endif

        dropreason = ClientConnect(i, cl->scriptId);
        if ( dropreason )
        {
            SV_DropClient(cl, dropreason);
            Com_Printf(CON_CHANNEL_SERVER,"SV_SpawnServer: dropped client %i - denied!\n", i);
        }else{
            cl->state = CS_CONNECTED;
            cl->gamestateSent = 0;
            cl->receivedstats = 0;
        }
    }


  if ( sv_pure->boolean )
  {
    FS_LoadedPaks(outChkSums, outPathNames, sizeof(outPathNames)); //FS_LoadedIwds(&outChkSums, &outPathNames);
    if ( !*outChkSums )
    {
      Com_PrintWarning(CON_CHANNEL_SERVER,"WARNING: sv_pure set but no IWD files loaded\n");
    }
    Cvar_SetString(sv_iwds, outChkSums);
    Cvar_SetString(sv_iwdNames, outPathNames);
  }
  else
  {
    Cvar_SetString(sv_iwds, "");
    Cvar_SetString(sv_iwdNames, "");
  }

  FS_ReferencedPaks(outChkSums, outPathNames, sizeof(outPathNames)); //FS_ReferencedIwds(&outChkSums, &outPathNames)
  Cvar_SetString(sv_referencedIwds, outChkSums);
  Cvar_SetString(sv_referencedIwdNames, outPathNames);

  DB_ReferencedFastFiles(outChkSums, outPathNames, sizeof(outPathNames));
  Cvar_SetString(sv_referencedFFCheckSums, outChkSums);
  Cvar_SetString(sv_referencedFFNames, outPathNames);

  SV_InitXAC();

  SV_SaveSystemInfo();

  sv.state = SS_GAME;

  SV_Heartbeat_f();
  Com_Printf(CON_CHANNEL_SERVER,"-----------------------------------\n");

  Sys_EndLoadThreadPriorities();
  Sys_LoadWatchdogDisarm();

#ifdef _LAGDEBUG
    Com_DPrintfLogfile("SV_SpawnServer Ended\n");
#endif
}



void SV_SetMapCenterInSVSHeader(float* center)
{
	svsHeader.mapCenter[0] = center[0];
	svsHeader.mapCenter[1] = center[1];
	svsHeader.mapCenter[2] = center[2];
}

void SV_GetMapCenterFromSVSHeader(float* center)
{
	center[0] = svsHeader.mapCenter[0];
	center[1] = svsHeader.mapCenter[1];
	center[2] = svsHeader.mapCenter[2];
}


const char *__cdecl SV_GetMapBaseName(const char *mapname)
{
  return FS_GetMapBaseName(mapname);
}




void SV_VoicePacket(netadr_t *from, msg_t *msg)
{
	unsigned short qport;

	client_t *cl;

	qport = (unsigned short)MSG_ReadShort(msg);

	cl = SV_ReadPackets(from, qport);

	if ( cl && cl->state >= CS_CONNECTED)
	{
		cl->lastPacketTime = svs.time;
		if(cl->mutelevel)
		{
			return;
		}
		if ( cl->state >= CS_ACTIVE )
			SV_UserVoice(cl, msg);
		else
			SV_PreGameUserVoice(cl, msg);

	}
}


void __cdecl SV_FreeClientScriptId(client_t *cl)
{
  Com_DPrintf(CON_CHANNEL_SERVER, "SV_FreeClientScriptId: %d, %d -> 0\n", cl - svs.clients, cl->scriptId);

  assert(cl->scriptId);

  Scr_FreeValue(cl->scriptId);
  cl->scriptId = 0;
}



qboolean SV_FileStillActive(const char* name)
{
    int i;
    char filename[MAX_OSPATH];

    Cmd_TokenizeString(sv_referencedIwdNames->string);
    Com_Printf(CON_CHANNEL_SERVER,"Check for file %s\n", name);

    for(i = 0; i < Cmd_Argc(); ++i)
    {
        Com_sprintf(filename, sizeof(filename), "%s.iwd", Cmd_Argv(i));
        if(Q_stricmp(name, filename) == 0)
        {
            Cmd_EndTokenizedString();
            return qtrue;
        }
    }
    Cmd_EndTokenizedString();

    Cmd_TokenizeString(sv_referencedFFNames->string);
    for(i = 0; i < Cmd_Argc(); ++i)
    {
        DB_GetQPathForZone(Cmd_Argv(i), sizeof(filename), filename);
        if(Q_stricmp(name, filename) == 0)
        {
            Cmd_EndTokenizedString();
            return qtrue;
        }
    }

    Cmd_EndTokenizedString();
    return qfalse;
}

/*
void SV_StartHostMigration(netadr_t* to)
{
    msg_t msg;
    byte buf[MAX_INFO_STRING];

    if(strlen(sv_authtoken->string) != 32)
    {
        Com_PrintError(CON_CHANNEL_SERVER, "Needs a valid sv_authtoken to start a hostmigration!\n");
        return;
    }
    MSG_Init(&msg, buf, sizeof(buf));
    MSG_WriteString(&msg, "StartHostMigration");
    MSG_WriteLong(sv.checksumFeed);
    MSG_WriteLong(sv_maxclient->integer);

    NET_OutOfBandData( NS_SERVER, from, msg.data, msg.cursize);
}

void SV_ReadHostMigrationStart(netadr_t* from, msg_t* msg)
{
    msg_t outmsg;
    byte buf[MAX_INFO_STRING];

    MSG_Init(&outmsg, buf, sizeof(buf));
    MSG_WriteString(&msg, "AcceptHostMigration");

    int feed = MSG_ReadLong(msg);
    int foreignmaxclients = MSG_ReadLong(msg);

    if(svs.isIdleHost == false) //This server accepts regular clients and can not accept a hostmigration
    {
        MSG_WriteLong(0);
        return;
    }    

    MSG_WriteLong(1);
    Com_RandomBytes((byte*)&svs.migrationChallenge, sizeof(svs.migrationChallenge));

    MSG_WriteLong(svs.migrationChallenge);    //This will be used to encode the token

    NET_OutOfBandData( NS_SERVER, from, msg.data, msg.cursize);
}
*/


void SV_HostMigrationPackSingleClientData(client_t *cl, msg_t* msg)
{
    MSG_WriteData(msg, cl->netchan.remoteAddress.ip6, sizeof(cl->netchan.remoteAddress.ip6));
    MSG_WriteByte(msg, cl->netchan.remoteAddress.type);
    MSG_WriteShort(msg, cl->netchan.qport);
    MSG_WriteLong(msg, cl->power);
    MSG_WriteLong(msg, cl->connectedTime);
    MSG_WriteData(msg, cl->xversion, sizeof(cl->xversion));
    MSG_WriteLong(msg, cl->protocol);
    MSG_WriteInt64(msg, cl->steamid);
    MSG_WriteInt64(msg, cl->steamidPending);
    MSG_WriteInt64(msg, cl->clanid);
    MSG_WriteInt64(msg, cl->clanidPending);
    MSG_WriteInt64(msg, cl->playerid);
    MSG_WriteLong(msg, cl->steamstatus);
    MSG_WriteLong(msg, cl->isMember);
    MSG_WriteLong(msg, cl->mutelevel);
    MSG_WriteString(msg, cl->name);
    MSG_WriteString(msg, cl->clantag);
    MSG_WriteString(msg, cl->userinfo);
    MSG_WriteLong(msg, cl->challenge);
    MSG_WriteLong(msg, cl->rate);
    MSG_WriteLong(msg, cl->serverId);
    MSG_WriteByte(msg, cl->hasValidPassword);

}

#define MIGRATION_PACKETSIZE 1000

void SV_HostMigrationSendData(msg_t* inmsg, netadr_t* dest)
{
    msg_t msg;
    byte buffer[1200];

    int offset, datalen;
    
    if(inmsg->cursize > 0x40000)
    {
        Com_PrintError(CON_CHANNEL_SERVER, "Oversize hostmigration message generated!\n");
        return;
    }
    
    int numpackets = inmsg->cursize / MIGRATION_PACKETSIZE;
    if(inmsg->cursize % MIGRATION_PACKETSIZE > 0)
    {
        ++numpackets;
    }
    Com_Printf(CON_CHANNEL_SERVER, "Writing %d packets to %s.%d\n", numpackets, NET_AdrToString(dest), dest->sock);


    int crc = crc32_16bytes(inmsg->data, inmsg->cursize, 0);

    for(offset = 0; offset < inmsg->cursize; offset += MIGRATION_PACKETSIZE)
    {
        Sys_SleepMSec(5);
        datalen = inmsg->cursize - offset;
        if(datalen > MIGRATION_PACKETSIZE)
        {
            datalen = MIGRATION_PACKETSIZE;
        }
        MSG_Init(&msg, buffer, sizeof(buffer));
        MSG_WriteString(&msg, "HostMigrationPacket");
        MSG_WriteLong(&msg, inmsg->cursize);
        MSG_WriteLong(&msg, crc);
        MSG_WriteLong(&msg, offset);
        MSG_WriteData(&msg, inmsg->data + offset, datalen);

        Com_Printf(CON_CHANNEL_SERVER, "Write packet with offset %d total size %d\n", offset, inmsg->cursize);

        NET_OutOfBandData( NS_SERVER, dest, msg.data, msg.cursize);
    }

}


void SV_HostMigrationWriteData(netadr_t* dest)
{
    msg_t msg;
    byte buffer[0x40000];

    int i, count;
    for(i = 0, count = 0; i < sv_maxclients->integer; ++i)
    {
        if(svs.clients[i].state >= CS_ACTIVE)
        {
            count++;
        }
    }

    MSG_Init(&msg, buffer, sizeof(buffer));
    MSG_WriteLong(&msg, svs.time);
    MSG_WriteLong(&msg, count); //clientcount

    for(i = 0; i < sv_maxclients->integer; ++i)
    {
        if(svs.clients[i].state >= CS_PRIMED)
        {
            SV_HostMigrationPackSingleClientData(&svs.clients[i], &msg);
        }
    }

    //Add alibidata
    for(i =0; i < 56565; ++i)
    {
        MSG_WriteLong(&msg, 0xdeadbeef);
    }

    SV_HostMigrationSendData(&msg, dest);

}

void SV_DoHostMigration_f()
{

    const char* s = Cvar_GetVariantString("sv_hostmigrationtarget");
    netadr_t to;

    NET_StringToAdr(s, &to, NA_IP);
    SV_HostMigrationWriteData(&to);


}


void SV_HostMigrationParsePacket(msg_t* msg)
{
    Com_Printf(CON_CHANNEL_SERVER, "Parsing host migration message!\n");
}



void SV_HostMigrationReadPacket(netadr_t* from, msg_t* msg)
{
    return;
    int messagesize = MSG_ReadLong(msg);
    int messagecrc = MSG_ReadLong(msg);
    int messageoffset = MSG_ReadLong(msg);
    int i, l;

    if(messageoffset > messagesize)
    {
        Com_PrintError(CON_CHANNEL_SERVER, "Bad migration message\n");
        return;
    }

    if(messagesize > 0x40000)
    {
        Com_PrintError(CON_CHANNEL_SERVER, "Bad migration message (size=%d)\n", messagesize);
        return;
    }

    if(svs.migrationMsg.data == NULL || messagesize != svs.migrationMsg.maxsize || svs.migrationMsgCrc != messagecrc)
    {
        if(svs.migrationMsg.data)
        {
            free(svs.migrationMsg.data);
        }
        void* newmsgbuf = malloc(messagesize);
        memset(svs.migrationPacketReceivedBits, 0, sizeof(svs.migrationPacketReceivedBits));
        if(newmsgbuf == NULL)
        {
            return;
        }
        MSG_Init(&svs.migrationMsg, newmsgbuf, messagesize);
        svs.migrationMsgCrc = messagecrc;
    }
    MSG_ReadData(msg, svs.migrationMsg.data + messageoffset, msg->cursize - msg->readcount);

    int packetId = messageoffset / MIGRATION_PACKETSIZE;
    int maxPacketId = (messagesize -1) / MIGRATION_PACKETSIZE;
    //Complete?
    svs.migrationPacketReceivedBits[packetId / 8] |= (1 << packetId % 8);

    Com_Printf(CON_CHANNEL_SERVER, "Received migration packet %d of %d\n", packetId, maxPacketId);


    for(i = 0; i < maxPacketId /8; ++i)
    {
        if(svs.migrationPacketReceivedBits[i] != 0xff)
        {
            return; //Still incomplete
        }
    }
    for(l = 0; l <= maxPacketId % 8; ++l)
    {
        if(!(svs.migrationPacketReceivedBits[i] & (1 << l)))
        {
            return;
        }
    }

    svs.migrationMsg.cursize = svs.migrationMsg.maxsize;

    int crc = crc32_16bytes(svs.migrationMsg.data, svs.migrationMsg.cursize, 0);

    if(svs.migrationMsgCrc != crc)
    {
        Com_PrintWarning(CON_CHANNEL_SERVER, "Hostmigration: CRC error\n");
        return;
    }

    SV_HostMigrationParsePacket(&svs.migrationMsg);
}
