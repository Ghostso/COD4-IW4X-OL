/* getcurrentprimaryweapon, getcurrentweaponclipammo, isswitchingweapon.
 *
 * IW4 iw4x.exe registry records located by their name-string pointers:
 * getcurrentprimaryweapon 0x5d92d0, getcurrentweaponclipammo 0x5d93a0,
 * isswitchingweapon 0x5d9f20. Full disassembly of the three handlers is in
 * obj/claude-workers/weapon-state-evidence.txt and of their helpers
 * (0x44f9f0 session gate, 0x4bf750 hand argument, 0x48d170 per-hand clip
 * lookup) in obj/claude-workers/weapon-state-helpers.txt. The per-hand and
 * cached-primary state these read is implemented natively in
 * src/codol_weapon_state.c, which carries the CoDOL C1 provenance. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_weapon_state.h"
#include "xassets/weapondef.h"
#include <string.h>

static gclient_t *resolve_player(scr_entref_t ref)
{
    /* IW4 raises two different errors and this collapsed them into one, which
     * hid which of the two a script had actually done. A reference whose class
     * is not an entity is "not an entity"; an entity without a client is
     * "entity %i is not a player". Same split, and same wording, as
     * src/codol_script_hud_notifications.c already uses. */
    if(ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if(ref.entnum >= MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return NULL;
    }
    return g_entities[ref.entnum].client;
}

static const char *weapon_name(unsigned weapon)
{
    struct WeaponDef *def;
    if(!weapon || weapon >= (unsigned)BG_GetNumWeapons()) return "none";
    def = BG_GetWeaponDef((int)weapon);
    return def && def->szInternalName ? def->szInternalName : "none";
}

/* IW4 helper 0x4bf750, called with the script argument index (0 here, pushed
 * at 0x5d9408 and read as the helper's first parameter at 0x4bf758). It is an
 * optional argument: when Scr_GetNumParam (0x4b0e90) is not greater than the
 * index the helper returns hand 0 without consuming anything. Otherwise
 * Scr_GetConstString (0x494830) is compared against the precompiled 'right'
 * and 'left' constants (0x1aa2e8c and 0x1aa2e70 there, scr_const.right and
 * scr_const.left here), yielding 0 and 1; anything else raises
 * "weapon hand must be 'right' or 'left'" (message at 0x707824). */
static unsigned script_weapon_hand(unsigned index)
{
    unsigned short parameter;
    if((unsigned)Scr_GetNumParam() <= index) return 0;
    parameter = (unsigned short)Scr_GetConstString(index);
    if(parameter == scr_const.right) return 0;
    if(parameter == scr_const.left) return 1;
    Scr_ParamError((int)index, "weapon hand must be 'right' or 'left'");
    return 0;
}

/* IW4 0x5d92d0: require the session gate (0x44f9f0 tests client+0x311c == 0,
 * the playing session state) and a positive current weapon, then answer with
 * the cached primary when the current weapon's inventory type is alternate
 * mode (0x5d9350 compares the definition's inventory type against 3) and with
 * the current weapon otherwise. Both failure paths return the literal "none"
 * string (0x72e6f4). C1's BG_PlayerStateToEntityState makes the identical
 * choice at 0x40d0d7..0x40d0fd from ps+0x33c and ps+0x340. */
void CODOL_Scr_GetCurrentPrimaryWeapon(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    unsigned primary;
    if(!client) return;
    if(client->sess.sessionState != SESS_STATE_PLAYING) { Scr_AddString("none"); return; }
    if((int)client->ps.weapon <= 0) { Scr_AddString("none"); return; }
    if(!CODOL_WeaponStatePrimaryWeapon(&client->ps, &primary)) { Scr_AddString("none"); return; }
    Scr_AddString(weapon_name(primary));
}

/* IW4 0x5d93a0: no session gate (absent from this handler); an unsigned test
 * of the current weapon against zero returns integer 0 immediately, otherwise
 * the optional hand argument is resolved and 0x48d170 scans the fifteen
 * per-clip records for the weapon's own clip key, returning that record's
 * magazine for the requested hand. */
void CODOL_Scr_GetCurrentWeaponClipAmmo(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    unsigned hand;
    int ammo = 0;
    if(!client) return;
    if(!client->ps.weapon) { Scr_AddInt(0); return; }
    hand = script_weapon_hand(0);
    if(!CODOL_WeaponStateClipAmmo(&client->ps, client->ps.weapon, hand, &ammo)) ammo = 0;
    Scr_AddInt(ammo);
}

/* IW4 0x5d9f20 tests both hand weaponstates (client+0x1f8 and client+0x214)
 * against 1..5. Those are IW4's own enumerators: raise, alternate raise, drop,
 * quick drop and alternate drop. The retained IW3 machine has no separate
 * alternate drop state (PM_BeginWeaponChange writes 3 or 4 and marks the
 * alternate case with weapon animation 17), so the equivalent native set is
 * 1..4; 5 and 6 are firing and rechambering here. Both hands are consulted
 * through the native per-hand state. */
/* The three selected offhands, set as one set.
 *
 * There is no IW4 or T5 method to copy: IW4 carries only the offhand
 * primary/secondary *class* setters, which name a class for its own two-button
 * search, and CoDOL selects a *weapon* per slot instead. The shape follows the
 * reference server's own producer, alpha0022 equipment.py EquipmentState
 * set_class (line 419), which replaces all three from one loadout record; the
 * slot order is its SLOTS tuple, lethal/tactical/special (line 109), which is
 * the order of the buttons 0x4000/0x8000/0x10000 and of the player-state words
 * 0x32C/0x330/0x334.
 *
 * Three weapon-name arguments; "none" or "" empties a slot. C1 40c82a,
 * 40c83c and 40c84f accept an explicit selection in any slot; conventional
 * class grouping applies only to fallback selection. */
static int offhand_slot_argument(unsigned index, unsigned slot,unsigned *out)
{
    const char *name = Scr_GetString(index);
    int weapon, expected;
    if(!name || !*name || !strcmp(name, "none")) { *out=0; return 1; }
    weapon = (int)CODOL_WeaponStateWeaponForName(name);
    if(weapon <= 0) {
        Scr_ParamError((int)index, va("unknown weapon '%s'", name));
        return 0;
    }
    expected = CODOL_WeaponStateOffhandSlotForWeapon((unsigned)weapon);
    if(expected < 0) {
        Scr_ParamError((int)index,
            va("weapon '%s' is not offhand equipment for slot %u", name, slot));
        return 0;
    }
    *out=(unsigned)weapon; return 1;
}
void CODOL_Scr_SetOffhandEquipment(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    unsigned weapon[3];
    unsigned i;
    if(!client) return;
    if(Scr_GetNumParam() != 3) {
        Scr_Error("usage: setoffhandequipment(<lethal>, <tactical>, <special>)");
        return;
    }
    for(i = 0; i < 3; ++i) if(!offhand_slot_argument(i, i,weapon+i)) return;
    if(!CODOL_WeaponStateSetOffhandSlots(&client->ps, weapon))
        Scr_Error("setoffhandequipment: the selection could not be recorded");
}
/* The weapon in one slot, by the same order. Answers "none" for an empty slot
 * and for a state that never had a selection recorded, which is what such a
 * state can raise: nothing. */
void CODOL_Scr_GetOffhandEquipment(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    unsigned slot, weapon = 0;
    if(!client) return;
    if(Scr_GetNumParam() != 1) {
        Scr_Error("usage: getoffhandequipment(<slot>)");
        return;
    }
    slot = (unsigned)Scr_GetInt(0);
    if(slot >= 3) { Scr_ParamError(0, "offhand slot must be 0, 1 or 2"); return; }
    if(!CODOL_WeaponStateOffhandSlot(&client->ps, slot, &weapon)) weapon = 0;
    Scr_AddString(weapon_name(weapon));
}

void CODOL_Scr_IsSwitchingWeapon(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    if(!client) return;
    Scr_AddBool(CODOL_WeaponStateIsSwitching(&client->ps) != 0);
}

/* IW4 registry73c5c8 ->5d9e70. Same player receiver errors as the other
 * queries; no arguments consumed and integer0/1 returned by both paths. */
void CODOL_Scr_IsReloading(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    if(!client) return;
    Scr_AddInt(CODOL_WeaponStateIsReloading(&client->ps) ? 1 : 0);
}

/* IW4 method table73c5bc ->5d9df0: player receiver, no consumed arguments,
 * integer0/1 from stored dual-wield state, no session-state gate. */
void CODOL_Scr_IsDualWielding(scr_entref_t ref)
{
    gclient_t *client = resolve_player(ref);
    if(!client) return;
    Scr_AddInt(CODOL_WeaponStateIsDualWielding(&client->ps) ? 1 : 0);
}
#endif
