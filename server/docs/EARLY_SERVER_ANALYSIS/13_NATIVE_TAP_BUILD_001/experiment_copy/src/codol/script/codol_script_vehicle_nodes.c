#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include "g_public.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

/* Native VM class 3 already exists. Keep records separate from g_entities;
 * vehicle path nodes are script objects, not networked game entities. */
#define NODE_CLASS 3
#define NODE_LIMIT 16384
static SpawnVar *nodes[NODE_LIMIT];
static unsigned node_count;
static const struct { const char *name; unsigned type; } fields[] = {
    {"targetname", VAR_STRING}, {"target", VAR_STRING},
    {"script_linkname", VAR_STRING}, {"script_noteworthy", VAR_STRING},
    {"classname", VAR_STRING}, {"origin", VAR_VECTOR}, {"angles", VAR_VECTOR},
    {"speed", VAR_FLOAT}, {"lookahead", VAR_FLOAT}, {"spawnflags", VAR_INTEGER},
    {"model", VAR_STRING}
};

static const char *value(const SpawnVar *record, const char *key)
{
    int i;
    for (i = 0; i < record->numSpawnVars; ++i)
        if (!Q_stricmp(record->spawnVars[i].key, key)) return record->spawnVars[i].value;
    return NULL;
}
void CODOL_ClearVehicleNodes(void)
{
    unsigned i;
    for (i = 0; i < node_count; ++i) { free(nodes[i]); nodes[i] = NULL; }
    node_count = 0;
}
void CODOL_InitVehicleNodes(void)
{
    SpawnVar parsed;
    unsigned i;
    CODOL_ClearVehicleNodes();
    for (i = 0; i < sizeof(fields)/sizeof(*fields); ++i)
        Scr_AddClassField(NODE_CLASS, fields[i].name, i);
    G_ResetEntityParsePoint();
    while (G_ParseSpawnVars(&parsed)) {
        const char *classname = value(&parsed, "classname");
        SpawnVar *copy;
        int pair;
        if (!classname || (Q_stricmp(classname, "info_vehicle_node") &&
                           Q_stricmp(classname, "info_vehicle_node_rotate"))) continue;
        if (node_count == NODE_LIMIT || !(copy = malloc(sizeof(*copy)))) {
            G_ResetEntityParsePoint(); CODOL_ClearVehicleNodes();
            Scr_Error("Could not allocate native vehicle nodes"); return;
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
}

static void lookup(int array, int all)
{
    const char *wanted = NULL, *key = NULL;
    unsigned i;
    int found = -1;
    if (!all) { wanted = Scr_GetString(0); key = Scr_GetString(1); }
    if (array) Scr_MakeArray();
    for (i = 0; i < node_count; ++i) {
        const char *candidate = all ? NULL : value(nodes[i], key);
        if (!all && (!candidate || strcmp(candidate, wanted))) continue;
        if (array) { Scr_AddEntityNum(i, NODE_CLASS); Scr_AddArray(); }
        else {
            if (found >= 0) { Scr_Error("getvehiclenode matches more than one node"); return; }
            found = (int)i;
        }
    }
    if (!array && found >= 0) Scr_AddEntityNum(found, NODE_CLASS);
    /* No return value is the VM's undefined value on a genuine miss. */
}
void CODOL_Scr_GetVehicleNode(void) { lookup(0, 0); }
void CODOL_Scr_GetVehicleNodeArray(void) { lookup(1, 0); }
void CODOL_Scr_GetAllVehicleNodes(void) { lookup(1, 1); }

void CODOL_GetVehicleNodeField(unsigned classnum, int index, int field)
{
    const char *text;
    float vector[3];
    double number;
    char *end;
    if (classnum != NODE_CLASS || index < 0 || (unsigned)index >= node_count ||
        field < 0 || (unsigned)field >= sizeof(fields)/sizeof(*fields)) {
        Scr_ObjectError("Invalid vehicle node field"); return;
    }
    text = value(nodes[index], fields[field].name);
    if (!text) return;
    if (fields[field].type == VAR_STRING) { Scr_AddString(text); return; }
    if (fields[field].type == VAR_VECTOR) {
        char extra;
        if (sscanf(text, "%f %f %f %c", &vector[0], &vector[1], &vector[2], &extra) != 3 ||
            !isfinite(vector[0]) || !isfinite(vector[1]) || !isfinite(vector[2])) {
            Scr_Error("Malformed vehicle node vector"); return;
        }
        Scr_AddVector(vector); return;
    }
    number = strtod(text, &end);
    while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') ++end;
    if (end == text || *end || !isfinite(number)) { Scr_Error("Malformed vehicle node number"); return; }
    if (fields[field].type == VAR_INTEGER) {
        if (number < -2147483648.0 || number > 2147483647.0 || floor(number) != number) {
            Scr_Error("Invalid vehicle node integer"); return;
        }
        Scr_AddInt((int)number);
    } else {
        float f = (float)number;
        if (!isfinite(f)) { Scr_Error("Vehicle node number out of range"); return; }
        Scr_AddFloat(f);
    }
}
int CODOL_SetVehicleNodeField(unsigned classnum, int index, int field)
{
    /* This is the class-3 native-property assignment path. C1's object-field
     * dispatcher 0x56b660 sends it to 0x56b6f3, which unconditionally raises
     * string 0xc5cb30; IW4 0x4f20f0/0x4f2103 and T5 0x684ef0/0x684f40
     * have the same contract. There is no writable vehicle-node property
     * dispatch hidden behind this rejection. */
    (void)classnum; (void)index; (void)field;
    Scr_Error("vehicle node is read-only");
    return 1;
}
/* Read access for the native path follower (codol_script_vehicle_builtins.c). */
unsigned CODOL_VehicleNodeCount(void) { return node_count; }
const char *CODOL_VehicleNodeValue(unsigned index, const char *key)
{ return index < node_count ? value(nodes[index], key) : NULL; }
#endif
