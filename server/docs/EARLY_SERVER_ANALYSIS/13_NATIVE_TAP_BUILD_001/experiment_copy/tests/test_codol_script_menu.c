#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include "server.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>

gentity_t g_entities[MAX_GENTITIES];
serverStatic_t svs;
static gclient_t player;
static cvar_t maxclients;
cvar_t *sv_maxclients=&maxclients;

static const char *argument="menu";
static int parameters=1,errors,result=-1,recipient,game_sends,reads,updates;
static int update_recipients[8];
static char command[1100],update_commands[8][1100];

int Q_stricmp(const char *a,const char *b) { return strcasecmp(a,b); }
void Scr_ObjectError(const char *s) { assert(s); ++errors; }
void Scr_Error(const char *s) { assert(s); ++errors; }
char *Scr_GetString(unsigned i) { assert(!i); ++reads; return (char *)argument; }
int Scr_GetNumParam(void) { return parameters; }
void Scr_AddInt(int value) { result=value; }
void QDECL Com_DPrintf(conChannel_t channel,const char *format,...)
{ (void)channel; (void)format; }
int CODOL_RefreshMapSunSampleSize(void) { return 1; }
void CODOL_ResetMapSunSampleSize(void) {}
void SV_GameSendServerCommand(int client,int type,const char *text)
{
    assert(type==1 && strlen(text)<sizeof(command));
    recipient=client;
    strcpy(command,text);
    ++game_sends;
}
void QDECL SV_SendServerCommandNoLoss(client_t *client,const char *format,...)
{
    va_list args;
    assert(client>=svs.clients && client<svs.clients+maxclients.integer);
    assert(updates<(int)(sizeof(update_recipients)/sizeof(update_recipients[0])));
    update_recipients[updates]=(int)(client-svs.clients);
    va_start(args,format);
    assert(vsnprintf(update_commands[updates],sizeof(update_commands[updates]),format,args)>0);
    va_end(args);
    ++updates;
}
static void expect_update(int index,int client,const char *text)
{
    assert(index<updates && update_recipients[index]==client);
    assert(!strcmp(update_commands[index],text));
}

int main(void)
{
    scr_entref_t ref={3,0};
    char menu_index[16],second_index[16];
    const char *cells[4];
    int previous;

    snprintf(menu_index,sizeof(menu_index),"%u",CODOL_CS_MENUS);
    snprintf(second_index,sizeof(second_index),"%u",CODOL_CS_MENUS+1);
    cells[0]=menu_index; cells[1]="menu";
    cells[2]=second_index; cells[3]="already";
    assert(CODOL_SetServerInheritedConfigstrings("mp",2,cells));
    assert(!strcmp(CODOL_ServerMenuName(0),"menu"));
    assert(!strcmp(CODOL_ServerMenuName(1),"already"));
    assert(CODOL_ServerMenuName(CODOL_MENU_SLOTS)==NULL);

    g_entities[3].client=&player;
    CODOL_Scr_OpenPopupMenu(ref);
    assert(result==0 && !game_sends && !reads);
    player.sess.connected=CON_CONNECTED;
    CODOL_Scr_OpenPopupMenu(ref);
    assert(result==1 && recipient==3 && !strcmp(command,"u 0"));
    CODOL_Scr_ClosePopupMenu(ref); assert(!strcmp(command,"v 0"));
    CODOL_Scr_OpenMenu(ref); assert(!strcmp(command,"q 0"));
    CODOL_Scr_OpenMenuNoMouse(ref); assert(!strcmp(command,"q 0 1"));
    previous=game_sends;
    CODOL_Scr_CloseMenu(ref);
    assert(game_sends==previous+2 && !strcmp(command,"r 0"));
    parameters=0; previous=game_sends;
    CODOL_Scr_CloseMenu(ref);
    assert(game_sends==previous+2 && !strcmp(command,"r"));
    CODOL_Scr_CloseInGameMenu(ref); assert(!strcmp(command,"H"));

    maxclients.integer=4;
    svs.clients[0].state=CS_ACTIVE; svs.clients[0].gamestateSent=qtrue;
    svs.clients[1].state=CS_PRIMED; svs.clients[1].gamestateSent=qtrue;
    svs.clients[2].state=CS_PRIMED; svs.clients[2].gamestateSent=qfalse;
    svs.clients[3].state=CS_CONNECTED; svs.clients[3].gamestateSent=qtrue;
    parameters=1;
    argument="MENU";
    CODOL_Scr_PrecacheMenu(); assert(!updates);
    argument="new_menu";
    CODOL_Scr_PrecacheMenu();
    assert(updates==2 && !strcmp(CODOL_ServerMenuName(2),"new_menu"));
    expect_update(0,0,"d 4245 new_menu");
    expect_update(1,1,"d 4245 new_menu");
    CODOL_Scr_ClosePopupMenu(ref); assert(!strcmp(command,"v 2"));

    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),CODOL_CS_MENUS,""));
    assert(!strcmp(CODOL_ServerMenuName(0),""));
    argument="replacement";
    CODOL_Scr_PrecacheMenu();
    assert(updates==4 && !strcmp(CODOL_ServerMenuName(0),"replacement"));
    expect_update(2,0,"d 4243 replacement");
    expect_update(3,1,"d 4243 replacement");
    previous=updates; argument="REPLACEMENT";
    CODOL_Scr_PrecacheMenu(); assert(updates==previous);

    previous=game_sends; argument="menu";
    CODOL_Scr_ClosePopupMenu(ref); assert(errors==1 && game_sends==previous);
    argument="bad\nname";
    CODOL_Scr_PrecacheMenu(); assert(errors==2 && updates==4);
    ref.classnum=1;
    CODOL_Scr_ClosePopupMenu(ref); assert(errors==3 && game_sends==previous);
    ref.classnum=0; ref.entnum=4;
    CODOL_Scr_ClosePopupMenu(ref); assert(errors==4 && game_sends==previous);

    CODOL_ResetServerConfigstrings();
    puts("PASS: production menu lookup, client gated precache, and native menu commands");
}
