#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_sv_state.h"
#include "server.h"
#include <stdio.h>
#include <string.h>

static int find_menu(const char *name)
{
    unsigned slot;
    if(!name || !*name) return -1;
    for(slot=0;slot<CODOL_MENU_SLOTS;++slot) {
        const char *candidate=CODOL_ServerMenuName(slot);
        if(candidate && !Q_stricmp(candidate,name)) return (int)slot;
    }
    return -1;
}
static gentity_t *menu_player(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) { Scr_ObjectError("Not an entity"); return NULL; }
    if(!g_entities[ref.entnum].client) { Scr_ObjectError("Entity is not a player"); return NULL; }
    return &g_entities[ref.entnum];
}
void CODOL_Scr_PrecacheMenu(void)
{
    const char *name=Scr_GetString(0),*p; unsigned slot; int client;
    if(!name || !*name || strlen(name)>MAX_STRING_CHARS-32) { Scr_Error("Invalid menu name"); return; }
    for(p=name;*p;++p) if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') {
        Scr_Error("Invalid menu name"); return;
    }
    if(find_menu(name)>=0) return;
    for(slot=0;slot<CODOL_MENU_SLOTS;++slot) {
        const char *existing=CODOL_ServerMenuName(slot);
        if(existing && *existing) continue;
        if(!CODOL_SetConfigstring(CODOL_ServerConfigstrings(),CODOL_CS_MENUS+slot,name)) {
            Scr_Error("Could not register menu"); return;
        }
        Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL precached menu slot %u: %s\n",slot,name);
        /* Initial gamestate reads the saved override. Only clients that have
         * received one need this reliable update, before subsequent q/u/v
         * commands resolve the menu slot in C1's4243..4274 bank. */
        if(!svs.clients || !sv_maxclients) return;
        for(client=0;client<sv_maxclients->integer;++client) {
            client_t *target=&svs.clients[client];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_MENUS+slot,name);
        }
        return;
    }
    Scr_Error("Too many precached menus");
}
static void indexed_menu(scr_entref_t ref,char operation,int no_mouse)
{
    gentity_t *entity=menu_player(ref); int slot; char command[32];
    if(!entity) return;
    if(entity->client->sess.connected!=CON_CONNECTED) { Scr_AddInt(0); return; }
    slot=find_menu(Scr_GetString(0));
    if(slot<0) { Scr_Error("Menu was not precached"); return; }
    snprintf(command,sizeof(command),no_mouse ? "%c %i 1" : "%c %i",operation,slot);
    SV_GameSendServerCommand(ref.entnum,1,command); Scr_AddInt(1);
}
void CODOL_Scr_OpenMenu(scr_entref_t ref) { indexed_menu(ref,'q',0); }
void CODOL_Scr_OpenMenuNoMouse(scr_entref_t ref) { indexed_menu(ref,'q',1); }
void CODOL_Scr_OpenPopupMenu(scr_entref_t ref) { indexed_menu(ref,'u',0); }
/* IW4's closePopupMenu takes no menu: the bare "v" closes whatever popup is
 * up. A menu name is accepted too, for scripts that pass one. */
void CODOL_Scr_ClosePopupMenu(scr_entref_t ref)
{
    gentity_t *entity;
    if(Scr_GetNumParam()) { indexed_menu(ref,'v',0); return; }
    entity=menu_player(ref);
    if(!entity) return;
    if(entity->client->sess.connected!=CON_CONNECTED) { Scr_AddInt(0); return; }
    SV_GameSendServerCommand(ref.entnum,1,"v"); Scr_AddInt(1);
}
/* C1 tears a script menu down in two passes, so one "r" is not a full close.
 * The 'r' handler (0x00468060) validates the slot and then always takes the
 * close-everything tail at 0x004680F9, which for menu mode 6 calls 0x005F4F20:
 *
 *   top = Menus_TopVisible(0x00606E00)
 *   if (top)  { if (!anyVisibleFullScreen(0x00606FB0)) clearOpenMenuList(); }
 *   else      { if (keyCatchers & 0x10) keyCatchers &= ~0x10; }
 *
 * i.e. pass one empties the open-menu list (which is what C1's own HUD
 * predicate ShouldDrawHud/HudFade tests) and pass two releases KEYCATCH_UI,
 * which is what draws the UI cursor over the game (UI_Refresh 0x005ECE96..
 * 0x005ECEF7 requires that bit).  Emitting only the first leaves the cursor up
 * until the player happens to press a key (UI_KeyEvent 0x005F38AC).  Both
 * passes are no-ops when nothing is open and when a fullscreen menu is up, and
 * the Scaleform close at 0x006B7D60 returns immediately on the second pass, so
 * the pair is safe to send unconditionally.
 *
 * Both passes only reach the client because SV_AddServerCommand's IW3
 * replacement scan (sv_main.c sub_530FC0) skips 'q' and 'r'; it used to fold
 * the second identical unsent 'r' into the first, so the wire carried one.
 *
 * C1 ignores the slot argument beyond validating it, so closeMenu("x") and
 * closeMenu() do the same thing; the name is still resolved so a script typo
 * is reported instead of silently closing everything. */
void CODOL_Scr_CloseMenu(scr_entref_t ref)
{
    char command[32]; int slot;
    if(!menu_player(ref)) return;
    if(!Scr_GetNumParam()) {
        SV_GameSendServerCommand(ref.entnum,1,"r");
        SV_GameSendServerCommand(ref.entnum,1,"r");
        return;
    }
    slot=find_menu(Scr_GetString(0));
    if(slot<0) { Scr_Error("Menu was not precached"); return; }
    snprintf(command,sizeof(command),"r %i",slot);
    SV_GameSendServerCommand(ref.entnum,1,command);
    SV_GameSendServerCommand(ref.entnum,1,command);
}
void CODOL_Scr_CloseInGameMenu(scr_entref_t ref)
{
    if(menu_player(ref)) SV_GameSendServerCommand(ref.entnum,1,"H");
}
#endif
