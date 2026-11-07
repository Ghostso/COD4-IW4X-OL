/* Exercise the lobby-visible status after a dropped map and during a match. */
#include "server.h"
#include "cvar.h"
#include "qcommon_io.h"
#include "codol_connect.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

server_t sv;
serverStatic_t svs;
static cvar_t running_var, maxclients_var, map_var, session_var, gametype_var, zone_var;
cvar_t *com_sv_running=&running_var, *sv_maxclients=&maxclients_var;
static char status_line[2048];

cvar_t *Cvar_FindVar(const char *name)
{
    if (!strcmp(name,"mapname")) return &map_var;
    if (!strcmp(name,"codol_sessionMap")) return &session_var;
    if (!strcmp(name,"g_gametype")) return &gametype_var;
    if (!strcmp(name,"codol_zoneType")) return &zone_var;
    return NULL;
}
uint64_t CODOL_ClientConnectIdentity(unsigned client)
{
    return client==0 ? UINT64_C(0x9d8f2a1b3c4d5e6f) : 0;
}
void Com_Printf(conChannel_t channel,const char *format,...)
{
    va_list args;
    assert(channel==CON_CHANNEL_DONT_FILTER);
    va_start(args,format);
    vsnprintf(status_line,sizeof(status_line),format,args);
    va_end(args);
}
void CODOL_MatchStatus_f(void);
static void has(const char *field)
{
    if (!strstr(status_line,field)) {
        fprintf(stderr,"missing '%s' from %s",field,status_line);
        assert(0);
    }
}
int main(void)
{
    map_var.string="mp_rust";
    session_var.string="mp_rust";
    gametype_var.string="dm";
    zone_var.string="mp";
    maxclients_var.integer=3;
    svs.clients[0].state=CS_CONNECTED;
    svs.clients[0].netchan.remoteAddress.type=NA_IP;
    svs.clients[1].state=CS_CONNECTED;
    svs.clients[1].netchan.remoteAddress.type=NA_BOT;

    /* ERR_DROP invokes SV_Shutdown, but the mapname cvar retains the old map. */
    running_var.integer=0;
    sv.state=SS_DEAD;
    CODOL_MatchStatus_f();
    has("map=none "); has("session_map=none "); has("running=0 ");
    has("humans=0 "); has("bots=0 "); has("maxclients=0 "); has("uids=-\n");

    /* A cvar alone must not declare the server ready during map load. */
    running_var.integer=1;
    sv.state=SS_LOADING;
    CODOL_MatchStatus_f();
    has("map=none "); has("running=0 "); has("humans=0 ");

    sv.state=SS_GAME;
    CODOL_MatchStatus_f();
    has("map=mp_rust "); has("session_map=mp_rust "); has("running=1 ");
    has("humans=1 "); has("bots=1 "); has("maxclients=3 ");
    has("uids=9d8f2a1b3c4d5e6f\n");
    puts("PASS: match status hides stale maps and reports live seats");
    return 0;
}
