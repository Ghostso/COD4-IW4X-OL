/* Weapon HUD icon overrides and HUD splash notifications.
 * See codol_script_hud_notifications.h for the IW4/C1 provenance of the slot
 * table, the playerState field, the material index space and the client
 * command. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_script_hud_notifications.h"
#include <string.h>

/* The slot vocabulary is C1's, in C1's order (slot table 0x00cd3958, constants
 * initialised at 0x00577ae0). IW4's six names are this list without
 * tertiaryoffhand and actionslot5, in the same relative order, so a script
 * written against IW4 names resolves to the same client slots. Both engines
 * compare interned script strings, which is an exact, case-sensitive match. */
static const char *const hud_icon_slot_names[CODOL_HUD_ICON_OVERRIDE_SLOTS] = {
    "primaryoffhand",
    "secondaryoffhand",
    "tertiaryoffhand",
    "actionslot1",
    "actionslot2",
    "actionslot3",
    "actionslot4",
    "actionslot5"
};

int CODOL_WeaponHudIconOverrideSlot(const char *name)
{
    unsigned slot;
    if (!name) return -1;
    for (slot = 0; slot < CODOL_HUD_ICON_OVERRIDE_SLOTS; ++slot)
        if (!strcmp(name, hud_icon_slot_names[slot])) return (int)slot;
    return -1;
}

const char *CODOL_WeaponHudIconOverrideSlotName(unsigned slot)
{
    return slot < CODOL_HUD_ICON_OVERRIDE_SLOTS ? hud_icon_slot_names[slot] : NULL;
}

/* Field lookup by measured offset, as the other player overlays do. */
static int put_player(codol_player_fields_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    const codol_player_field_t *field;
    for (i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        field = CODOL_PlayerField(i);
        if (!field) return 0;
        if (field->offset == offset) { out->field[i] = value; return 1; }
    }
    return 0;
}

int CODOL_OverlayPlayerWeaponHudIcons(codol_player_fields_t *wire,
    const unsigned slots[CODOL_HUD_ICON_OVERRIDE_SLOTS])
{
    codol_player_fields_t out;
    unsigned slot;
    if (!wire || !slots) return 0;
    out = *wire;
    for (slot = 0; slot < CODOL_HUD_ICON_OVERRIDE_SLOTS; ++slot) {
        /* Zero is a real value and the common one: it is what a client with no
         * override carries and what "none" stores, and C1's consumer draws
         * nothing for it. Anything the ten-bit field cannot carry is a producer
         * that did not use the material bank. */
        if (slots[slot] > CODOL_HUD_ICON_OVERRIDE_MAX) return 0;
        if (!put_player(&out, CODOL_HUD_ICON_OVERRIDE_FIELD + 4u * slot, slots[slot])) return 0;
    }
    *wire = out;
    return 1;
}

#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "codol_playerstate_ext.h"
#include "codol_assets.h"
#include "cscr_stringlist.h"
#include "qcommon_io.h"
#include <stdio.h>

/* Retained cdecl routines. G_MaterialIndex is _g_utils_mp.asm:1469:
 * G_FindConfigstringIndex(name, CS_MATERIALS, MAX_MATERIALS, level.initializing,
 * "material"), i.e. a native index relative to CS_MATERIALS, 0 for an empty
 * name, and the engines' own "material \"%s\" not precached" script error when
 * allocation is closed - the same contract C1's 0x00570290 has.
 *
 * It normalises the name itself, after the scr_const.none comparison: the
 * retained routine strcpy's into a frame buffer and calls Q_strlwr, and C1
 * 0x00570290 lower-cases in place over 'A'..'Z'. So the method passes the
 * script string through unchanged. The retained copy is an unbounded strcpy
 * into a 0x48-byte frame buffer, where C1 uses a 0x40-bounded copy
 * (0x00ada54e), so the caller bounds the name instead of letting a long one
 * smash the retained frame. */
extern int G_MaterialIndex(const char *name);
extern void StringTable_GetAsset(const char *name, const codol_engine_table_t **table);
/* The bound C1 gives the same copy. */
#define CODOL_HUD_ICON_MATERIAL_NAME_MAX 0x40

/* The captured half of the array lives in the playerState extension, written
 * only by the publisher in codol_hud_icon_overrides.c. */
_Static_assert(CODOL_PS_HUD_ICON_SLOTS == CODOL_HUD_ICON_OVERRIDE_SLOTS,
    "the captured playerState array must hold every C1 hud icon slot");

/* Native material configstring index -> the material's name. NULL when the
 * index names nothing: index 0 (no override) or a configstring the bank never
 * filled. The getter, not this helper, decides what to answer for each. */
static const char *hud_icon_material_name(unsigned native)
{
    unsigned handle;
    const char *name;
    if (!native || native >= MAX_MATERIALS) return NULL;
    handle = (unsigned)SV_GetConfigstringIndex((int)(CS_MATERIALS + native));
    if (!handle || handle == sv.emptyConfigString) return NULL;
    name = SL_ConvertToString(handle);
    return (name && *name) ? name : NULL;
}

int CODOL_OverlayServerWeaponHudIcons(codol_player_fields_t *wire, const playerState_t *ps)
{
    uint16_t native[CODOL_HUD_ICON_OVERRIDE_SLOTS];
    unsigned slots[CODOL_HUD_ICON_OVERRIDE_SLOTS];
    unsigned slot;
    if (!wire || !ps) return 0;
    /* From the state being serialized, never from the script store or the live
     * client: an archived or followed playerState publishes the copy that was
     * taken with it, the same way IW4 gets it for free by having published the
     * array into ps+0x470..0x484 before the state was captured. */
    if (!CODOL_PlayerStateHudIconOverridesRead(ps, native)) return 0;
    for (slot = 0; slot < CODOL_HUD_ICON_OVERRIDE_SLOTS; ++slot) {
        int mapped;
        if (!native[slot]) { slots[slot] = 0; continue; }
        /* The bank is refreshed and published by codol_sv_assets.c, and
         * SV_SetConfigstring reaches it through CODOL_PublishAssetConfigstring
         * as soon as the setter allocates the material, so a recorded index
         * without a CoDOL slot means the bank is exhausted or was reset under
         * the state. Fail the frame instead of drawing another material. */
        mapped = CODOL_ServerMaterialToWire(native[slot]);
        if (mapped <= 0 || mapped > CODOL_HUD_ICON_OVERRIDE_MAX) return 0;
        slots[slot] = (unsigned)mapped;
    }
    return CODOL_OverlayPlayerWeaponHudIcons(wire, slots);
}

int CODOL_HudSplashRowNum(const char *name)
{
    const codol_engine_table_t *table = NULL;
    int row;
    if (!name || !*name) return -1;
    StringTable_GetAsset(CODOL_HUD_SPLASH_TABLE, &table);
    if (!table || table->columnCount <= CODOL_HUD_SPLASH_KEY_COLUMN) return -1;
    /* C1 0x0061ed00 and IW4 0x004ac180 both walk rows backwards and compare
     * case-insensitively, so a later duplicate row overrides an earlier one. */
    for (row = table->rowCount - 1; row >= 0; --row) {
        const char *cell = table->values[(size_t)row * table->columnCount +
                                         CODOL_HUD_SPLASH_KEY_COLUMN];
        if (cell && !Q_stricmp(name, cell)) return row;
    }
    return -1;
}

/* Both builtins take the same receiver checks in both engines: an entref whose
 * class is not an entity is "not an entity", and an entity without a client is
 * "entity %i is not a player". */
static gentity_t *hud_notification_player(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity"); return NULL;
    }
    if (!g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return NULL;
    }
    return &g_entities[ref.entnum];
}

/* The slot argument of both methods, at the argument position the engines
 * report in their parameter error. */
static int hud_icon_slot_argument(unsigned param)
{
    const char *name = Scr_GetString(param);
    int slot = CODOL_WeaponHudIconOverrideSlot(name);
    if (slot < 0)
        Scr_ParamError((int)param,
            va("\"%s\" is not a valid weapon hud icon type to override", name ? name : ""));
    return slot;
}

/* IW4 0x005f57c0 / C1 0x00549580. One argument, the slot name; returns the
 * material name the slot carries, or "none" when it carries nothing.
 *
 * Both engines read the script-owned client array (IW4 0x005f5857 through
 * ent->client + 0x3264, C1 0x0054973f through ent->client + 0x35ac), never a
 * playerState - which is why a following spectator still reads its own
 * overrides here rather than the followed player's. */
void CODOL_Scr_GetWeaponHudIconOverride(scr_entref_t ref)
{
    gentity_t *player = hud_notification_player(ref);
    const char *name;
    int slot;
    unsigned native;
    if (!player) return;
    slot = hud_icon_slot_argument(0);
    if (slot < 0) return;
    native = CODOL_GetClientHudIconOverride((unsigned)ref.entnum, (unsigned)slot);
    /* IW4 0x005f5868 and C1 0x00549751 answer the interned constant "none" for
     * a slot holding 0, and otherwise the material configstring's own name -
     * which, for an index whose configstring is empty, is the empty string. */
    if (!native) { Scr_AddString("none"); return; }
    name = hud_icon_material_name(native);
    Scr_AddString(name ? name : "");
}

/* IW4 0x005f56d0 / C1 0x00549300. Slot name, material name; "none" clears. */
void CODOL_Scr_SetWeaponHudIconOverride(scr_entref_t ref)
{
    gentity_t *player = hud_notification_player(ref);
    const char *material;
    int slot, native;
    if (!player) return;
    /* Both engines read the two arguments unconditionally: a missing one is the
     * VM's own "parameter %d does not exist", raised by the retained
     * Scr_GetConstString (_scr_vm.asm:6961) exactly as C1 0x005cc960 raises it.
     * Nothing here duplicates that check with different wording. */
    slot = hud_icon_slot_argument(0);
    if (slot < 0) return;
    material = Scr_GetString(1);
    if (!material) return;
    /* scr_const.none stores 0 without touching the material bank, exactly as
     * IW4 0x005f577a and C1 0x00549539 do; the comparison is against the
     * interned script string, so it is exact and case-sensitive, and it happens
     * before any normalisation. Every other name goes through G_MaterialIndex,
     * which lower-cases it, allocates and publishes the configstring, and
     * raises the engines' own not-precached script error when it may not. */
    if (strcmp(material, "none")) {
        if (strlen(material) >= CODOL_HUD_ICON_MATERIAL_NAME_MAX) {
            Scr_ParamError(1, "weapon hud icon material name is too long");
            return;
        }
        native = G_MaterialIndex(material);
    } else {
        native = 0;
    }
    if (native < 0 || native >= MAX_MATERIALS) {
        Scr_ParamError(1, va("\"%s\" could not be registered as a hud icon material", material));
        return;
    }
    /* The store is the client's, as in both references: the setter never
     * touches a playerState, and the per-frame publisher is what puts the
     * array into the state a snapshot captures. */
    if (!CODOL_SetClientHudIconOverride((unsigned)ref.entnum, (unsigned)slot,
                                        (unsigned)native))
        Scr_Error("this player cannot carry weapon hud icon overrides");
}

/* <player> setClientSubtitle( <localized string>, <seconds> )
 *
 * C1's timed-subtitle command is ']' (0x4694d2): argv[1] is a duration in
 * milliseconds, argv[2] is a localized string reference resolved through
 * 0x448e10, and the two are handed to the subtitle display at 0x44e830.
 *
 * The CoDOL gametype library calls this for deathstreak captions, where the
 * alpha0022 overlay routed it to its Python host instead. Sending the client
 * command directly is the native equivalent: no host, no bridge.
 *
 * The string travels quoted, so a quote inside it would end the token early
 * and shift every following argument. Localized references never contain one;
 * reject rather than truncate if one appears. */
void CODOL_Scr_SetClientSubtitle(scr_entref_t ref)
{
    gentity_t *player = hud_notification_player(ref);
    const char *text;
    char command[MAX_STRING_CHARS];
    double seconds;
    int milliseconds;
    if (!player) return;
    text = Scr_GetString(0);
    if (!text) { Scr_ParamError(0, "setClientSubtitle needs a localized string"); return; }
    if (strchr(text, '"') || strchr(text, '\n') || strchr(text, '\r')) {
        Scr_ParamError(0, "setClientSubtitle text cannot contain a quote or a newline");
        return;
    }
    /* Both a float and an int are accepted: the scripts pass whole seconds,
     * but a fractional caption length is meaningful on the wire. */
    seconds = Scr_GetNumParam() > 1 ? (double)Scr_GetFloat(1) : 0.0;
    if (!(seconds >= 0.0) || seconds > 60.0) {
        Scr_ParamError(1, "setClientSubtitle duration must be between 0 and 60 seconds");
        return;
    }
    milliseconds = (int)(seconds * 1000.0 + 0.5);
    if (snprintf(command, sizeof(command), "] %i \"%s\"", milliseconds, text) >= (int)sizeof(command)) {
        Scr_ParamError(0, "setClientSubtitle text is too long");
        return;
    }
    SV_GameSendServerCommand(player->s.number, 0, command);
}

/* <player> setActionSlotHelp( <action slot 1..8> )
 *
 * Names the action slot C1 substitutes for [{ACTION_SLOT_HELP}] in this
 * player's HUD text (see codol_script_hud_notifications.h). No IW4/IW5
 * counterpart: their killstreak splashes carry no key. The value rides the
 * player's clientState, so it must be set before the splash that uses it. */
static unsigned char action_slot_help[MAX_CLIENTS];
unsigned CODOL_ClientActionSlotHelp(unsigned client)
{
    return client < MAX_CLIENTS ? action_slot_help[client] : 0;
}
void CODOL_Scr_SetActionSlotHelp(scr_entref_t ref)
{
    gentity_t *player = hud_notification_player(ref);
    int slot;
    if (!player) return;
    slot = Scr_GetInt(0);
    /* Three bits on the wire hold slot - 1. */
    if (slot < 1 || slot > 8) {
        Scr_ParamError(0, va("setActionSlotHelp slot %i must be 1..8", slot));
        return;
    }
    if (player->s.number >= 0 && player->s.number < MAX_CLIENTS)
        action_slot_help[player->s.number] = (unsigned char)slot;
}

/* IW4 0x005df430 / C1 0x0051e530. Splash name, slot 0..4, optional duration. */
void CODOL_Scr_ShowHudSplash(scr_entref_t ref)
{
    gentity_t *player = hud_notification_player(ref);
    const char *name;
    char command[64];
    int slot, duration, row;
    if (!player) return;
    /* Name and slot are read unconditionally, as both engines do; the VM
     * raises its own "parameter %d does not exist" for a missing one. */
    name = Scr_GetString(0);
    slot = Scr_GetInt(1);
    /* Both engines compare unsigned, so a negative slot fails here too. */
    if ((unsigned)slot >= CODOL_HUD_SPLASH_SLOTS) {
        Scr_Error("Invalid slot number specified for ShowHudSplash"); return;
    }
    duration = Scr_GetNumParam() > 2 ? Scr_GetInt(2) : 0;
    row = CODOL_HudSplashRowNum(name);
    if (row < 0) {
        /* C1's table lookup reports exactly this and returns -1, and both
         * engines then send the -1 on. The C1 client feeds the row straight
         * into StringTable_GetColumnValueForRow (0x0061ee90), which returns
         * NULL for an out-of-range row, and into atof - so transmitting -1
         * dereferences NULL on the client. Report it and send nothing. */
        Com_PrintWarning(CON_CHANNEL_SERVER, "Unable to find '%s' in column %i of table %s\n",
                         name ? name : "", CODOL_HUD_SPLASH_KEY_COLUMN, CODOL_HUD_SPLASH_TABLE);
        return;
    }
    /* C1 0x0051e631 formats "%c %i %i %i" with 'w', the slot, the row and the
     * duration, and sends it to that one client; its CG_ServerCommand switch
     * (0x00469320) dispatches 'w' to CG_ShowSplash. */
    if (snprintf(command, sizeof(command), "%c %i %i %i",
                 CODOL_HUD_SPLASH_COMMAND, slot, row, duration) >= (int)sizeof(command)) return;
    SV_GameSendServerCommand(player->s.number, 0, command);
}
#endif
