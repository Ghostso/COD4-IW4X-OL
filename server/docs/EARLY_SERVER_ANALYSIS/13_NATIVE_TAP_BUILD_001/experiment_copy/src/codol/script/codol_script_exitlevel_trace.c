/* exitLevel: the match-end leave, plus a developer trace of the call site.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "scr_vm_functions.h"
#include "cscr_parser.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include "server.h"
#include "cvar.h"
#include "codol_profile_push.h"
void GScr_ExitLevel(void);

/* Returning a CoDOL client to the lobby.
 *
 * A retail dedicated server rotates the map and the client follows it. A C1
 * client did not come from a server browser: it came from the Demonware lobby
 * and expects to go back there for its after-action report, so the match has
 * to end with an explicit leave.
 *
 * `t` is the only server-sendable leave, and it never reaches cgame. C1's
 * client layer dispatches the first character of every reliable command
 * through the table at 0x4878D8 indexed by `c - 'd'`, so `t` (index 16)
 * selects entry 2 of the jump table at 0x4878C8, which is 0x48782E. That arm
 * raises Com_Error(4, "EXE_SERVER_DISCONNECTED") when the command carries no
 * argument, and otherwise hands Cmd_Argv(1) to CL_Disconnect at 0x4960E0,
 * which compares it against "EXE_MATCHENDED" at 0xc47D30 and raises the benign
 * front-end notice instead of an error. The same table takes `d`, `k` and `x`
 * before cgame sees them. `disconnect` and `disconnectforoutro` are client-only
 * console commands and cannot be reached from the server.
 *
 * The results hold happens before this point: IW4's endGame already opens the
 * summary through setClientDvar("ui_opensummary", 1) - `ui_opensummary` is one
 * of the seven names on C1's own `s` whitelist - sends the final scoreboard,
 * and waits several seconds before calling exitLevel. So no extra menu command
 * is sent from here; `q 14` (mp_eog_summary) would only duplicate it.
 *
 * PROFILE REFRESH AND THE NORMAL MATCH-END REASON
 *
 * The reason string is also what decides whether the player's career page is
 * still showing last week's numbers.
 *
 * C1 caches the secure profile in one buffer (0x0205C598) behind two flags,
 * 0x06C3D3D9 and 0x06C3D3DC. Its per-frame Demonware tick (0x004D8EE0, reached
 * from 0x006FF0A9) re-fetches the profile - DW 10/3 GETFILE "mpdata_s",
 * through 0x004D9900 - whenever it finds BOTH flags zero and the lobby
 * connected; the completion at 0x004D9200 -> 0x004D98E0 sets them again.
 * GetRank (0x0058EFE0) and the whole Scaleform career view read
 * 0x0205C59C = that buffer + 4, synchronously, on draw. So a client that
 * clears those flags picks up a freshly written mpdata_s about 200 ms later,
 * with no relogin and nothing for the server to push.
 *
 * CL_HandleDisconnect (0x004960E0) clears them
 * (0x00496283/0x0049628A, when the cls.state captured at 0x004960F6 is >= 8),
 * and it does so only AFTER comparing the reason against a bypass list.
 * "EXE_MATCHENDED" is on that list: it matches at 0x00496114, jumps to
 * 0x00496116 and raises the silent level-5 notice without reaching the
 * invalidation. The other bypassed strings are
 * EXE_MIGRATIONABORTED, EXE_MIGRATION_IN_PROGRESS, hostquit,
 * EXE_PLAYERKICKED*, roundsdone and XBOXLIVE_SIGNINCHANGED.
 *
 * Any other reason falls through to 0x0049627D, invalidates, and raises
 * Com_Error(4, loc("EXE_SERVERDISCONNECTREASON") + loc(reason)).
 * EXE_MATCHEND_PARTNER_LEAVE (0x00C47E14) was previously used to invalidate
 * the cache, but it produces a false level-4 partner-left popup. The C1 'K'
 * command writes directly into that same cached secure record. The regular
 * per-frame profile push sends rank/XP edits during play; a forced push here
 * queues any last edits before the reliable 't EXE_MATCHENDED'. Both commands
 * use the same ordered reliable stream. The normal reason then returns the
 * client quietly without depending on profile invalidation.
 *
 * match_report.json is written at "gameended" (codol_script_matchdata.c)
 * before exitLevel runs; the lobby folds it independently for persistence.
 * C1 must still verify the popup, summary, and class/career values live.
 *
 * Not considered: patching C1 at 0x00496114 to skip the bypass. This server
 * does not modify the client. */
#define CODOL_MATCH_END_REASON "EXE_MATCHENDED"

static cvar_t *codol_exitToLobby;

void CODOL_Scr_ExitLevel(void)
{
    int i;

    if (com_developer && com_developer->integer) {
        Com_Printf(CON_CHANNEL_SERVER, "exitLevel called from script:\n");
        if (gScrVmPub.function_frame) Scr_PrintPrevCodePos(CON_CHANNEL_SERVER, gScrVmPub.function_frame->fs.pos, 0);
    }

    if (!codol_exitToLobby)
        codol_exitToLobby = Cvar_RegisterBool("codol_exitToLobby", qtrue, 0,
            "Return clients to the lobby at match end with t \"" CODOL_MATCH_END_REASON "\"; "
            "disable to keep them connected for a map rotation instead");

    if (codol_exitToLobby->boolean && svs.clients && sv_maxclients) {
        int sent = 0;
        /* GSC has finished the match report and all rank writes.  Flush the
         * secure record through C1's reliable K command before its reliable t
         * leave, including edits still inside the regular 250 ms batch. */
        CODOL_FlushSecureProfiles();
        for (i = 0; i < sv_maxclients->integer; ++i) {
            client_t *client = &svs.clients[i];
            if (client->state < CS_PRIMED || !client->gamestateSent) continue;
            if (client->netchan.remoteAddress.type == NA_BOT) continue;
            SV_SendServerCommandNoLoss(client, "t \"" CODOL_MATCH_END_REASON "\"");
            ++sent;
        }
        if (sent) Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL match end: returned %d client(s) to the lobby with \"%s\" "
            "(final secure profile flushed before the normal match-ended leave)\n",
            sent, CODOL_MATCH_END_REASON);
    }

    GScr_ExitLevel();
}
