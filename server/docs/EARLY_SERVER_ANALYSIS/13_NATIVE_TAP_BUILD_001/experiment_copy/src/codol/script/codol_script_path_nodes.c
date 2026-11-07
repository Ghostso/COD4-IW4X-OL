#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include "g_public.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

/* Native VM class 2 already exists. Keep records separate from g_entities;
 * path nodes are script objects, not networked game entities. Connectivity
 * is not inferred from positions or fabricated for navigation queries. */
#define NODE_CLASS 2
/* C1 node spawn 0x6f96bd rejects the next node at count 0x2000. */
#define NODE_LIMIT 8192
static SpawnVar *nodes[NODE_LIMIT];
static unsigned node_count;
static int initialized;
static const struct { const char *name; unsigned type; } fields[] = {
    {"targetname", VAR_STRING}, {"target", VAR_STRING},
    {"script_linkname", VAR_STRING}, {"script_noteworthy", VAR_STRING},
    {"classname", VAR_STRING}, {"origin", VAR_VECTOR}, {"angles", VAR_VECTOR},
    {"spawnflags", VAR_INTEGER},
    /* C1 field table 0xcccf08: short script-string at node+0x0e, generic
     * getter (field type 5). The owned spawn record retains its source value. */
    {"animscript", VAR_STRING}
};

static const char *value(const SpawnVar *record, const char *key)
{
    int i;
    for (i = 0; i < record->numSpawnVars; ++i)
        if (!Q_stricmp(record->spawnVars[i].key, key)) return record->spawnVars[i].value;
    return NULL;
}
void CODOL_ClearPathNodes(void)
{
    unsigned i;
    for (i = 0; i < node_count; ++i) { free(nodes[i]); nodes[i] = NULL; }
    node_count = 0; initialized = 0;
}
void CODOL_InitPathNodes(void)
{
    SpawnVar parsed;
    unsigned i;
    CODOL_ClearPathNodes();
    for (i = 0; i < sizeof(fields)/sizeof(*fields); ++i)
        Scr_AddClassField(NODE_CLASS, fields[i].name, i);
    G_ResetEntityParsePoint();
    while (G_ParseSpawnVars(&parsed)) {
        const char *classname = value(&parsed, "classname");
        SpawnVar *copy;
        int pair;
        if (!classname || strncmp(classname, "node_", 5)) continue;
        if (node_count == NODE_LIMIT || !(copy = malloc(sizeof(*copy)))) {
            G_ResetEntityParsePoint(); CODOL_ClearPathNodes();
            Scr_Error("Could not allocate native path nodes"); return;
        }
        memcpy(copy, &parsed, sizeof(*copy));
        for (pair = 0; pair < copy->numSpawnVars; ++pair) {
            copy->spawnVars[pair].key = copy->spawnVarChars +
                (parsed.spawnVars[pair].key - parsed.spawnVarChars);
            copy->spawnVars[pair].value = copy->spawnVarChars +
                (parsed.spawnVars[pair].value - parsed.spawnVarChars);
        }
        nodes[node_count++] = copy;
    }
    /* The normal entity spawn pass must still read the entire map. */
    G_ResetEntityParsePoint();
    initialized = 1;
}

int CODOL_IsStoredPathNode(const char *classname)
{
    if (!classname || strncmp(classname, "node_", 5)) return 0;
    if (!initialized) {
        Com_Error(ERR_DROP, "Path nodes must be initialized before entity spawning");
        return 0;
    }
    return 1;
}

static void lookup(int array, int all)
{
    const char *wanted = NULL, *key = NULL;
    unsigned i;
    int found = -1;
    if (!all) {
        /* C1 resolves the lookup key against its native class-field table,
         * not the arbitrary key/value pairs in the map entity string.
         * GetNode 0x6f9928/0x6f9943 returns undefined for unknown keys;
         * GetNodeArray 0x6f9ae1/0x6f9afc reports parameter 1 instead.
         * Both reject native non-string fields before searching any nodes. */
        static const char *const string_keys[] = {
            "targetname", "target", "animscript", "script_linkname",
            "script_noteworthy"
        };
        static const char *const other_keys[] = {
            "origin", "angles", "radius", "minusedistsq", "spawnflags", "type"
        };
        int recognized = 0;
        wanted = Scr_GetString(0);
        key = Scr_GetString(1);
        for (i = 0; i < sizeof(string_keys)/sizeof(*string_keys); ++i)
            if (!strcmp(key, string_keys[i])) { recognized = 1; break; }
        if (!recognized) {
            for (i = 0; i < sizeof(other_keys)/sizeof(*other_keys); ++i)
                if (!strcmp(key, other_keys[i])) {
                    Scr_ParamError(1, "key is not internally a string");
                    return;
                }
            if (array)
                Scr_ParamError(1, va("key '%s' does not internally belong to nodes", key));
            return;
        }
    }
    if (array) Scr_MakeArray();
    for (i = 0; i < node_count; ++i) {
        const char *candidate = all ? NULL : value(nodes[i], key);
        if (!all && (!candidate || strcmp(candidate, wanted))) continue;
        if (array) { Scr_AddEntityNum(i, NODE_CLASS); Scr_AddArray(); }
        else {
            if (found >= 0) { Scr_Error("getnode matches more than one node"); return; }
            found = (int)i;
        }
    }
    if (!array && found >= 0) Scr_AddEntityNum(found, NODE_CLASS);
    /* No return value is the VM's undefined value on a genuine miss. */
}
void CODOL_Scr_GetNode(void) { lookup(0, 0); }
void CODOL_Scr_GetNodeArray(void) { lookup(1, 0); }
void CODOL_Scr_GetAllPathNodes(void) { lookup(1, 1); }

void CODOL_GetNodeField(unsigned classnum, int index, int field)
{
    const char *text;
    float vector[3];
    double number;
    char *end;
    if (classnum != NODE_CLASS || index < 0 || (unsigned)index >= node_count ||
        field < 0 || (unsigned)field >= sizeof(fields)/sizeof(*fields)) {
        Scr_ObjectError("Invalid path node field"); return;
    }
    text = value(nodes[index], fields[field].name);
    if (!text) return;
    if (fields[field].type == VAR_STRING) { Scr_AddString(text); return; }
    if (fields[field].type == VAR_VECTOR) {
        char extra;
        if (sscanf(text, "%f %f %f %c", &vector[0], &vector[1], &vector[2], &extra) != 3 ||
            !isfinite(vector[0]) || !isfinite(vector[1]) || !isfinite(vector[2])) {
            Scr_Error("Malformed path node vector"); return;
        }
        Scr_AddVector(vector); return;
    }
    number = strtod(text, &end);
    while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') ++end;
    if (end == text || *end || !isfinite(number)) { Scr_Error("Malformed path node number"); return; }
    if (fields[field].type == VAR_INTEGER) {
        if (number < -2147483648.0 || number > 2147483647.0 || floor(number) != number) {
            Scr_Error("Invalid path node integer"); return;
        }
        Scr_AddInt((int)number);
    } else {
        float f = (float)number;
        if (!isfinite(f)) { Scr_Error("Path node number out of range"); return; }
        Scr_AddFloat(f);
    }
}
int CODOL_SetNodeField(unsigned classnum, int index, int field)
{
    /* C1 class-2 assignment 0x56b6ce raises the named read-only error
     * (string 0xc7a61c). T5 Scr_SetPathnodeField 0x921e80 validates node/field then calls
     * 0x921ef0, which unconditionally raises the named read-only error
     * (string 0xd37aa0). Built-in node fields are not dynamic GSC fields;
     * GScr_SetDynamicPathnodeField has a separate path at 0x922070. */
    if (classnum != NODE_CLASS || index < 0 || (unsigned)index >= node_count ||
        field < 0 || (unsigned)field >= sizeof(fields)/sizeof(*fields)) {
        Scr_ObjectError("Invalid path node field"); return 1;
    }
    Scr_Error(va("pathnode property '%s' is read-only", fields[field].name));
    return 1;
}
/* Native actor goal consumer: return the same stored class-2 origin as the
 * VM getter, without touching VM arguments or manufacturing BSP links. */
int CODOL_PathNodeOrigin(unsigned index, float *origin)
{
    const char *text;
    char extra;
    if (!initialized || index >= node_count || !origin) return 0;
    text = value(nodes[index], "origin");
    return text && sscanf(text, "%f %f %f %c", &origin[0], &origin[1],
        &origin[2], &extra) == 3 && isfinite(origin[0]) &&
        isfinite(origin[1]) && isfinite(origin[2]);
}
/* Read-only census for the native graph builder (codol_bot_nav.c): how many
 * node_* records the entity string carried and one raw key of each. */
unsigned CODOL_PathNodeCount(void) { return initialized ? node_count : 0; }
const char *CODOL_PathNodeValue(unsigned index, const char *key)
{
    return initialized && index < node_count && key ? value(nodes[index], key) : NULL;
}
#endif
