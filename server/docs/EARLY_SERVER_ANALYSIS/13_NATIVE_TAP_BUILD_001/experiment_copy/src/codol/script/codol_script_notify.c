#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "cscr_stringlist.h"
#include "codol_script_notify.h"
#include "codol_game.h"
#include <stdlib.h>
#include <string.h>
/* Retained VM routine, also used by IW4's notification delivery helper. */
extern int Scr_IsSystemActive(unsigned char system);

/* C1.exe 1.1.1.13, pointer table 00cd62c4. CL_SendActionNotify 499aa0
 * sends these one-based IDs. Keep this order separate from IW3 button bits. */
static const char *const actions[]={
    "+attack", "-attack", "+melee", "-melee", "+frag", "-frag",
    "+smoke", "-smoke", "+tact", "-tact", "+breath_sprint", "-breath_sprint",
    "+usereload", "-usereload", "+speed_throw", "-speed_throw",
    "+actionslot 1", "-actionslot 1", "+actionslot 2", "-actionslot 2",
    "+actionslot 3", "-actionslot 3", "+actionslot 4", "-actionslot 4",
    "+actionslot 5", "-actionslot 5", "+stance", "-stance",
    "+gostand", "-gostand", "+forward", "-forward", "+back", "-back",
    "+moveleft", "-moveleft", "+moveright", "-moveright",
    "+movedown", "-movedown", "+left", "-left", "+right", "-right",
    "+lookup", "-lookup", "+lookdown", "-lookdown", "+strafe", "-strafe",
    "+holdbreath", "-holdbreath", "+activate", "-activate",
    "+reload", "-reload", "+prone", "-prone", "+mlook", "-mlook",
    "+toggleads_throw", "-toggleads_throw", "+sprint", "-sprint",
    "+scores", "-scores", "+time", "-time", "+markerslot", "-markerslot",
    "togglemenu", "weapnext", "weapalt", "pause", "chatmodepublic",
    "chatmodeteam", "weapprev", "centerview", "toggletalk", "togglecrouch",
    "toggleprone", "goprone", "gocrouch", "toggleads", "leaveads"
};

/* IW4 457fa0: 256 total registrations, exact (player, command, event)
 * duplicates suppressed. Own text independently of VM string-table lifetime
 * so reset/disconnect can safely clear it before or after script shutdown. */
typedef struct {
    unsigned client;
    char *command, *event;
} command_notification_t;
static command_notification_t subscriptions[256];
static unsigned subscription_count;
static unsigned client_generation[MAX_CLIENTS];

void CODOL_ClearPlayerCommandNotifications(unsigned client)
{
    unsigned read,write=0;
    if(client<MAX_CLIENTS)++client_generation[client];
    for(read=0;read<subscription_count;++read) {
        if(subscriptions[read].client==client) {
            free(subscriptions[read].command);
            free(subscriptions[read].event);
        } else subscriptions[write++]=subscriptions[read];
    }
    memset(subscriptions+write,0,(subscription_count-write)*sizeof(*subscriptions));
    subscription_count=write;
}
void CODOL_ClearCommandNotifications(void)
{
    unsigned i;
    for(i=0;i<MAX_CLIENTS;++i)++client_generation[i];
    for(i=0;i<subscription_count;++i) {
        free(subscriptions[i].command);
        free(subscriptions[i].event);
    }
    memset(subscriptions,0,sizeof(subscriptions));
    subscription_count=0;
}

void CODOL_Scr_NotifyOnPlayerCommand(scr_entref_t ref)
{
    const char *event,*command;
    char *event_copy,*command_copy;
    unsigned i;
    size_t length;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError("NotifyOnPlayerCommand requires a player");return;
    }
    if(Scr_GetNumParam()!=2) {
        Scr_Error("NotifyOnPlayerCommand requires an event name and command");return;
    }
    event=Scr_GetString(0);
    command=Scr_GetString(1);
    for(i=0;i<subscription_count;++i)
        if(subscriptions[i].client==ref.entnum &&
           !Q_stricmp(subscriptions[i].command,command) &&
           !strcmp(subscriptions[i].event,event))return;
    if(subscription_count==256) {
        Scr_Error("Cannot register more than 256 player commands");return;
    }
    event_copy=malloc(strlen(event)+1);
    length=strlen(command);
    command_copy=malloc(length+1);
    if(!event_copy || !command_copy) {
        free(event_copy);free(command_copy);
        Scr_Error("Out of memory registering player command");return;
    }
    strcpy(event_copy,event);
    for(i=0;i<length;++i) {
        unsigned char c=(unsigned char)command[i];
        command_copy[i]=(char)(c>='A' && c<='Z' ? c+'a'-'A':c);
    }
    command_copy[length]=0;
    subscriptions[subscription_count++]=(command_notification_t){ref.entnum,command_copy,event_copy};
}

static unsigned action_number(const char *action_id)
{
    unsigned id=0;
    const unsigned char *cursor=(const unsigned char *)action_id;
    if(!cursor || !*cursor)return 0;
    /* Reject malformed IDs rather than letting atoi map a prefix to an action. */
    while(*cursor) {
        if(*cursor<'0' || *cursor>'9' || id>85)return 0;
        id=id*10+(*cursor++-'0');
    }
    return id && id<=sizeof(actions)/sizeof(actions[0]) ? id:0;
}
int CODOL_IsActionNotifyCommand(const char *command)
{
    return command && command[0]=='n' && command[1]==' ' && action_number(command+2)!=0;
}
static const char *notification_command(const char *action,char fallback[64])
{
    unsigned i;
    const char *space;
    size_t length;
    /* IW4 4ba760 first finds the full lowercase command in the VM string
     * table, then tries its first token only if that string does not exist.
     * Owned registrations count as interned even though their text is kept
     * independently of the retained VM allocator's lifetime. */
    if(SL_FindLowercaseString(action))return action;
    for(i=0;i<subscription_count;++i)
        if(!strcmp(subscriptions[i].command,action))return action;
    space=strchr(action,' ');
    if(!space)return action;
    length=(size_t)(space-action);
    if(length>=64)return action;
    memcpy(fallback,action,length);
    fallback[length]=0;
    return fallback;
}
void CODOL_HandleActionNotify(unsigned client,const char *action_id)
{
    unsigned id=action_number(action_id),i,count=0,generation;
    unsigned short notifications[256];
    const char *action;
    char fallback[64];
    if(!id || client>=MAX_CLIENTS || !g_entities[client].client)return;
    /* C1 IDs 17..26 are the five action-slot press/release pairs. Record
     * before dispatch so a script woken by this command sees the new state. */
    if(id>=17 && id<=26) {
        CODOL_RecordActionSlot(client,(id-17)/2,(id&1)!=0);
        if(g_entities[client].client->ps.locationSelectionInfo)
            CODOL_ClearActionSlotEdges(client);
    }
    if(!Scr_IsSystemActive(1))return;
    generation=client_generation[client];
    action=notification_command(actions[id-1],fallback);
    /* Snapshot event references: script notifications may register commands
     * or disconnect a player. Those mutations must not invalidate iteration. */
    for(i=0;i<subscription_count;++i)
        if(subscriptions[i].client==client && !strcmp(subscriptions[i].command,action))
            notifications[count++]=(unsigned short)SL_GetString(subscriptions[i].event,0);
    for(i=0;i<count;++i) {
        if(client_generation[client]==generation &&
           g_entities[client].client && g_entities[client].r.inuse && Scr_IsSystemActive(1))
            Scr_Notify(&g_entities[client],notifications[i],0);
        SL_RemoveRefToString(notifications[i]);
    }
}
#endif
