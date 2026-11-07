#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include "g_public.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
void CODOL_GetNodeField(unsigned, int, int);
int CODOL_SetNodeField(unsigned, int, int);
int CODOL_IsStoredPathNode(const char *);
void Com_Error(int level, const char *text, ...) { (void)level; (void)text; assert(0); }
static unsigned cursor, resets, fields, errors, outputs, count, entity;
static int duplicate, empty;
static float vector[3], number;
static char string[128];
static const char *args[2];
int Q_stricmp(const char *a, const char *b) { return strcasecmp(a, b); }
void G_ResetEntityParsePoint(void) { cursor = 0; ++resets; }
static void pair(SpawnVar *v, const char *key, const char *value)
{
    unsigned i = v->numSpawnVars++;
    v->spawnVars[i].key = v->spawnVarChars + v->numSpawnVarChars;
    strcpy(v->spawnVarChars + v->numSpawnVarChars, key); v->numSpawnVarChars += strlen(key)+1;
    v->spawnVars[i].value = v->spawnVarChars + v->numSpawnVarChars;
    strcpy(v->spawnVarChars + v->numSpawnVarChars, value); v->numSpawnVarChars += strlen(value)+1;
}
qboolean G_ParseSpawnVars(SpawnVar *v)
{
    memset(v, 0, sizeof(*v));
    if (empty || cursor == 3) return qfalse;
    pair(v, "classname", cursor == 0 ? "worldspawn" : cursor == 1 ? "node_pathnode" : "node_cover_left");
    pair(v, "targetname", cursor == 1 || duplicate ? "start" : "end");
    pair(v, "origin", "1 2 3"); pair(v, "angles", "0 90 0");
    pair(v, "target", "end"); pair(v, "speed", "12.5");
    pair(v, "lookahead", "nan"); pair(v, "spawnflags", "4");
    ++cursor; return qtrue;
}
void Scr_AddClassField(unsigned c, const char *n, unsigned offset) { assert(c == 2 && n && offset < 10); ++fields; }
char *Scr_GetString(unsigned i) { assert(i < 2); return (char *)args[i]; }
void Scr_MakeArray(void) { count = 0; }
void Scr_AddArray(void) { ++count; }
void Scr_AddEntityNum(int i, unsigned c) { assert(c == 2 && i >= 0 && i < 2); entity = i; ++outputs; }
void Scr_Error(const char *s) { assert(s && *s); ++errors; }
void Scr_ObjectError(const char *s) { Scr_Error(s); }
/* The builtins report a bad argument through the VM's parameter-error path
 * and format the message with va. Both belong to the VM this harness does not
 * link, so they join the error stubs above and count the same way. */
void Scr_ParamError(int index,const char *s) { (void)index; Scr_Error(s); }
char *va(const char *fmt,...)
{
    static char text[1024];
    va_list argptr;
    va_start(argptr,fmt);
    vsnprintf(text,sizeof(text),fmt,argptr);
    va_end(argptr);
    return text;
}
void Scr_AddString(const char *s) { assert(strlen(s) < sizeof(string)); strcpy(string, s); ++outputs; }
void Scr_AddFloat(float f) { number = f; ++outputs; }
void Scr_AddInt(int i) { number = i; ++outputs; }
void Scr_AddVector(const float *v) { memcpy(vector, v, sizeof(vector)); ++outputs; }
int main(void)
{
    CODOL_InitPathNodes(); assert(resets == 2 && fields == 9 && cursor == 0);
    args[0] = "start"; args[1] = "targetname";
    CODOL_Scr_GetNode(); assert(outputs == 1 && entity == 0);
    CODOL_GetNodeField(2, 0, 5); assert(vector[0] == 1 && vector[1] == 2 && vector[2] == 3);
    CODOL_GetNodeField(2, 0, 1); assert(strcmp(string, "end") == 0);
    CODOL_GetNodeField(2, 0, 7); assert(number == 4);
    unsigned before = outputs;
    CODOL_GetNodeField(2, 0, 3); assert(outputs == before);
    /* animscript is field 8 and is a real field the spawn record does not
     * carry, so it answers with nothing and reports nothing. Field 9 is past
     * the end of the table and is the error. */
    CODOL_GetNodeField(2, 0, 8); assert(outputs == before && !errors);
    CODOL_GetNodeField(2, 0, 9); assert(outputs == before && errors == 1);
    assert(CODOL_IsStoredPathNode("node_pathnode") && CODOL_IsStoredPathNode("node_cover_left"));
    assert(!CODOL_IsStoredPathNode("worldspawn") && !CODOL_IsStoredPathNode("info_vehicle_node"));
    args[0] = "START"; CODOL_Scr_GetNode(); assert(outputs == before);
    args[0] = "missing"; CODOL_Scr_GetNode(); assert(outputs == before);
    CODOL_Scr_GetNodeArray(); assert(count == 0);
    args[0] = "end"; args[1] = "target";
    CODOL_Scr_GetNodeArray(); assert(count == 2);
    before = outputs; CODOL_Scr_GetNode(); assert(outputs == before && errors == 2);
    CODOL_Scr_GetAllPathNodes(); assert(count == 2);
    CODOL_GetNodeField(2, 2, 0); assert(errors == 3);
    CODOL_SetNodeField(2, 0, 0); assert(errors == 4);
    empty = 1; CODOL_InitPathNodes(); CODOL_Scr_GetAllPathNodes(); assert(count == 0);
    CODOL_ClearPathNodes(); CODOL_ClearPathNodes();
    puts("PASS: native path node ownership, class/fields, map filtering, lookup/misses, duplicate rejection and reset");
}
