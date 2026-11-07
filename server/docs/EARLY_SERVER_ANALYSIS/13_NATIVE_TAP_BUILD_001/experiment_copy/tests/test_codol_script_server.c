#include "scr_vm_functions.h"
#include "qcommon.h"
#include "sys_cod4defs.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
gentity_t g_entities[MAX_GENTITIES];
level_locals_t level;
static gclient_t clients[MAX_CLIENTS];
static unsigned length, pending, slots[MAX_CLIENTS];
static int integer;
static time_t now;
void Scr_MakeArray(void) { length = pending = 0; }
void Scr_AddEntity(gentity_t *e) { assert(!pending && length < MAX_CLIENTS); slots[length] = e - g_entities; pending = 1; }
void Scr_AddArray(void) { assert(pending); ++length; pending = 0; }
void Scr_AddInt(int value) { integer = value; }
/* The GSC match record expects the short C1 build version. */
void Scr_AddString(const char *s) { assert(strcmp(s, "1.1.1.13") == 0); }
time_t Com_GetRealtime(void) { return now; }
int Sys_GetBuild(void) { return 12345; }
int main(void)
{
    level.maxclients = 4;
    for (int i = 0; i < 4; ++i) {
        g_entities[i].client = &clients[i]; g_entities[i].r.inuse = 1;
        clients[i].sess.connected = CON_CONNECTED;
    }
    clients[1].sess.connected = CON_CONNECTING;
    g_entities[2].r.inuse = 0;
    CODOL_Scr_GetPlayers(); assert(length == 2 && slots[0] == 0 && slots[1] == 3);
    g_entities[0].client = NULL;
    CODOL_Scr_GetPlayers(); assert(length == 1 && slots[0] == 3);
    level.maxclients = 0; CODOL_Scr_GetPlayers(); assert(length == 0);
    level.maxclients = MAX_CLIENTS + 100; CODOL_Scr_GetPlayers(); assert(length == 1);
    now = 1780000000; CODOL_Scr_GetSystemTime(); assert(integer == 1780000000);
    now = (time_t)(uint32_t)0x80000000u; CODOL_Scr_GetSystemTime(); assert(integer == INT32_MIN);
    CODOL_Scr_GetBuildNumber(); assert(integer == 12345);
    CODOL_Scr_GetBuildVersion();
    puts("PASS: native player selection, bounded slots, Unix epoch and server build identity");
}
