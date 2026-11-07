/* CoDOL vehicle definition registration/loading and configstring lifecycle.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_vehicle_assets.h"
#include "codol_vehicle_native.h"
#include "codol_sv_state.h"
#include "server.h"
#include "g_shared.h"
#include "qcommon_io.h"
#include <string.h>

/* Retained simulation records, defined by g_scr_vehicle.cpp as
 * struct vehicle_info_t s_vehicleInfos[32]. Only three fields are needed here,
 * so the record is addressed by offset instead of duplicating the layout.
 * _g_vehicles_mp.asm G_LoadVehicle proves the stride (0x270 memset/index
 * scaling), the name at the record start (strcpy of the requested name), the
 * six 64-byte sound names at0xe4 and their indices at0x264; the turret weapon
 * therefore occupies0x90..0xcf, immediately before the five turret span/rate
 * floats at0xd0..0xe3. VEH_ParseSpecificField writes the type at0x40. */
#define VEHICLE_INFO_STRIDE 0x270
#define VEHICLE_INFO_NAME 0x00
extern char s_vehicleInfos[];
extern short s_numVehicleInfos;

typedef struct {
    char name[64];  /* published name this binding was resolved from */
    int info;       /* retained record index, -1 while unloaded */
    int weapon;     /* turret weapon index registered with the definition */
    int resolved;   /* the named definition itself loaded, not a fallback */
} codol_vehicle_slot_t;
static codol_vehicle_slot_t vehicle_slots[CODOL_VEHICLE_SLOTS];

static char *vehicle_record(int info)
{
    return info >= 0 && info < CODOL_VEHICLE_SLOTS && info < s_numVehicleInfos ?
        s_vehicleInfos + (unsigned)info * VEHICLE_INFO_STRIDE : NULL;
}
static const char *record_name(int info)
{
    char *record = vehicle_record(info);
    return record ? record + VEHICLE_INFO_NAME : NULL;
}
/* Names travel in the gamestate string block and in "d <index> <value>"
 * reliable commands, so a name that cannot survive tokenization is invalid.
 * IW4's registrar takes the lowercase string identity for banks above0x457
 * (4af0e4 selects4c63e0 over434ee0), which includes the vehicle base0x665. */
static int canonical_name(const char *name, char out[64])
{
    size_t length = 0;
    while (name[length]) {
        unsigned char c = (unsigned char)name[length];
        if (length == 63 || c <= 32 || c == 127 || c == '"' || c == ';' || c == '\\') return 0;
        out[length] = c >= 'A' && c <= 'Z' ? (char)(c + 32) : (char)c;
        ++length;
    }
    out[length] = 0;
    return 1;
}
static const char *slot_value(unsigned slot)
{
    const char *value = CODOL_GetConfigstring(CODOL_ServerConfigstrings(),
        CODOL_CS_VEHICLES + slot);
    if (!value) value = CODOL_GetConfigstring(CODOL_ServerInheritedConfigstrings(),
        CODOL_CS_VEHICLES + slot);
    return value;
}
/* A binding survives only while its slot still names the same definition and
 * the retained record still holds it. G_VehiclesInit(0) clears
 * s_numVehicleInfos on every map load, so an unnoticed reset invalidates
 * bindings here instead of aliasing a slot onto another map's record. */
static codol_vehicle_slot_t *slot_binding(int slot)
{
    codol_vehicle_slot_t *binding;
    const char *value, *name;
    if (slot <= 0 || slot >= CODOL_VEHICLE_SLOTS) return NULL;
    binding = &vehicle_slots[slot];
    value = slot_value((unsigned)slot);
    if (!binding->name[0]) { binding->info = -1; return binding; }
    if (!value || strcmp(value, binding->name)) {
        memset(binding, 0, sizeof(*binding)); binding->info = -1; return binding;
    }
    name = record_name(binding->info);
    if (binding->info >= 0 && (!name || Q_stricmp(name, binding->name) ||
                             !CODOL_NativeVehicleDefinition(binding->info))) {
        binding->info = -1; binding->weapon = 0; binding->resolved = 0;
    }
    return binding;
}
void CODOL_ResetVehicleAssets(void)
{
    unsigned slot;
    CODOL_ResetNativeVehicles();
    memset(vehicle_slots, 0, sizeof(vehicle_slots));
    for(slot=0;slot<CODOL_VEHICLE_SLOTS;++slot) vehicle_slots[slot].info=-1;
}
static void publish_late(unsigned slot, const char *name)
{
    int client;
    if (!svs.clients || !sv_maxclients) return;
    for (client = 0; client < sv_maxclients->integer; ++client) {
        client_t *target = &svs.clients[client];
        if (target->state >= CS_PRIMED && target->gamestateSent)
            SV_SendServerCommandNoLoss(target, "d %u %s", CODOL_CS_VEHICLES + slot, name);
    }
}
static int register_name(const char *name, int create, int *out_slot)
{
    char canonical[64];
    unsigned slot, available = 0;
    if (!name) return -1;
    if (!*name) return 0; /* IW4 4af0c0 returns the reserved index for empty names. */
    if (!canonical_name(name, canonical)) return -1;
    for (slot = 1; slot < CODOL_VEHICLE_SLOTS; ++slot) {
        const char *current = slot_value(slot);
        if (current && *current && !strcmp(current, canonical)) { *out_slot = (int)slot; return (int)slot; }
        if (!available && (!current || !*current)) available = slot;
    }
    if (!create) return -1;
    /* Never overwrite a published slot: entities and archived snapshots keep
     * referring to a definition by its numeric slot. */
    if (!available) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "Exceeded limit of %d VehicleDef assets, cannot register '%s'\n",
            CODOL_VEHICLE_SLOTS - 1, canonical);
        return -1;
    }
    if (!CODOL_SetConfigstring(CODOL_ServerConfigstrings(),
            CODOL_CS_VEHICLES + available, canonical)) return -1;
    publish_late(available, canonical);
    *out_slot = (int)available;
    return (int)available;
}
int CODOL_RegisterVehicleName(const char *name, int create)
{
    int slot = 0;
    return register_name(name, create, &slot);
}
int CODOL_VehicleSlotForName(const char *name)
{
    return CODOL_RegisterVehicleName(name, 0);
}
const char *CODOL_VehicleName(int slot)
{
    const char *value;
    if (slot <= 0 || slot >= CODOL_VEHICLE_SLOTS) return NULL;
    value = slot_value((unsigned)slot);
    return value && *value ? value : NULL;
}
int CODOL_LoadVehicleDefinition(int slot)
{
    codol_vehicle_slot_t *binding = slot_binding(slot);
    const char *name = CODOL_VehicleName(slot), *loaded;
    int info;
    if (!binding || !name) return 0;
    /* IW4 443ac3 loads a slot at most once, keyed on its cached header. */
    if (binding->name[0] && binding->info >= 0) return binding->resolved;
    memset(binding, 0, sizeof(*binding));
    binding->info = -1;
    if (strlen(name) >= sizeof(binding->name)) return 0;
    strcpy(binding->name, name);
    /* Always resolve the mounted CoDOL definition. An existing text record
     * must not bypass archive conversion, and an invalid/missing VehicleDef
     * must not silently become defaultvehicle. The native installer owns
     * record capacity, conversion and weapon/sound registration. */
    info = CODOL_InstallNativeVehicleRecord(name);
    if (info < 0 || !CODOL_NativeVehicleDefinition(info)) return 0;
    loaded = record_name(info);
    binding->resolved = loaded && !Q_stricmp(loaded, name);
    if (!binding->resolved) return 0;
    binding->info = info;
    binding->weapon = CODOL_NativeVehicleTurretWeapon(info);
    return binding->resolved;
}
int CODOL_VehicleInfoIndex(int slot)
{
    codol_vehicle_slot_t *binding = slot_binding(slot);
    return binding ? binding->info : -1;
}
int CODOL_VehicleInfoForSpawn(const char *name)
{
    int slot = CODOL_RegisterVehicleName(name, level.initializing);
    if (slot > 0 && CODOL_LoadVehicleDefinition(slot)) {
        int info = CODOL_VehicleInfoIndex(slot);
        if (info >= 0) return info;
    }
    Com_Error(ERR_DROP, "Could not load native VehicleDef '%s' for spawn",
              name ? name : "");
    return -1;
}
int CODOL_VehicleTurretWeapon(int slot)
{
    codol_vehicle_slot_t *binding = slot_binding(slot);
    return binding ? binding->weapon : 0;
}
int CODOL_BindVehicleInfoIndex(int info_index)
{
    const char *name = record_name(info_index);
    int slot = 0;
    if (!name || !*name) return -1;
    if (register_name(name, 1, &slot) <= 0) return -1;
    /* A retained record alone is not proof of native CoDOL conversion. */
    if (!CODOL_LoadVehicleDefinition(slot) ||
        CODOL_VehicleInfoIndex(slot) != info_index) return -1;
    return slot;
}
#endif
