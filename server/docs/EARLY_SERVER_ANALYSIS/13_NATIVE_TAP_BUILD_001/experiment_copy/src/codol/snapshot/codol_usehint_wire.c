/* Cursor-hint capture and pure translation. See codol_usehint_wire.h. */
#include "codol_usehint_wire.h"
#include "codol_configstrings.h"
#include "codol_entities.h"
#include "entity.h"

/* C1 0x456886 starts the weapon range at 5, so hint 4 is HINT_FRIENDLY and
 * weapon 1 is hint 5. Native writes the same bias (asm _player_use_mp.asm:351
 * "add eax, 0x4" on the used entity's weapon, and _500 "lea edi, [eax+4]" on a
 * dropped item's weapon), so only the weapon number itself is translated. */
#define USEHINT_WEAPON_BIAS 4

static int hint_put(codol_player_fields_t *wire, unsigned offset, uint32_t value)
{
    unsigned i;

    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        const codol_player_field_t *field = CODOL_PlayerField(i);

        if(field && field->offset == offset) { wire->field[i] = value; return 1; }
    }
    return 0;
}

static int hint_string_valid(int string)
{
    return string == CODOL_USEHINT_STRING_NONE ||
           (string >= 0 && string < (int)CODOL_HINTSTRING_SLOTS);
}

void CODOL_ClearUseHint(codol_use_hint_t *hint)
{
    if(!hint) return;
    hint->known = 0;
    hint->kind = CODOL_USEHINT_KIND_NONE;
    hint->alternate = 0;
    hint->alternate_known = 0;
    hint->icon = 0;
    hint->weapon = 0;
    /* Neutral, not zero: string zero is hint-string slot zero and entity zero
     * is the first client. */
    hint->string = CODOL_USEHINT_STRING_NONE;
    hint->entity = CODOL_ENTITY_SENTINEL;
}

int CODOL_UseHintValid(const codol_use_hint_t *hint)
{
    if(!hint || !hint->known || hint->alternate_known > 1 || hint->alternate > 1) return 0;
    if(!hint_string_valid(hint->string) || hint->entity > CODOL_ENTITY_SENTINEL) return 0;
    switch(hint->kind) {
    case CODOL_USEHINT_KIND_NONE:
        return hint->icon == 0 && hint->weapon == 0;
    case CODOL_USEHINT_KIND_ICON:
        return hint->weapon == 0 && hint->icon >= 1 && hint->icon <= CODOL_USEHINT_ICON_MAX;
    case CODOL_USEHINT_KIND_WEAPON:
        return hint->icon == 0 && hint->weapon >= 1 && hint->weapon <= CODOL_USEHINT_WEAPON_MAX;
    default:
        return 0;
    }
}

int CODOL_UseHintAlternate(codol_use_hint_t *hint, int alternate)
{
    if(!hint || (alternate != 0 && alternate != 1)) return 0;
    hint->alternate = (unsigned char)alternate;
    hint->alternate_known = 1;
    return 1;
}

/* Native entity numbers are 11-bit with ENTITYNUM_NONE 2047 and
 * ENTITYNUM_WORLD 2046, the same pair C1 uses: its client compares against
 * 0x7ff (0x5764d4) before indexing its entity array. The entity adapters
 * publish the numbers unchanged, so this uses the same rule. */
static int capture_entity(unsigned short *out, int entity)
{
    if(entity == ENTITYNUM_NONE) { *out = CODOL_ENTITY_SENTINEL; return 1; }
    if(entity == ENTITYNUM_WORLD) { *out = CODOL_ENTITY_SENTINEL - 1; return 1; }
    if(entity < 0 || entity >= ENTITYNUM_WORLD) return 0;
    *out = (unsigned short)entity;
    return 1;
}

/* Both engines index one hint-string pool by this value: native
 * G_GetHintStringIndex (_g_scr_main_mp.asm:145672) hands out 0..31 and writes
 * configstring 0x115+slot, and C1 0x45629c reads the configstring offset table
 * at bank 584 + slot. codol_sv_assets.c republishes 0x115+slot as 584+slot, so
 * the number itself does not change. Native uses -1 for "no string"
 * (_player_use_mp.asm:_160 turns an entity's 0xff into -1), which is also what
 * C1's two non-negative tests want.
 *
 * A value outside the pool has no slot in bank 584 at all: publishing it would
 * make the client read an unrelated configstring, so it is refused. The only
 * native writer that could produce one is the mounted-weapon path
 * (_player_use_mp.asm:356) copying weapondef+0x7e8; that field's type is not
 * established here, so an out-of-range capture failure is the signal for it. */
static int capture_string(short *out, int string)
{
    if(!hint_string_valid(string)) return 0;
    *out = (short)string;
    return 1;
}

int CODOL_ResolveEngineUseHint(codol_use_hint_t *out, const playerState_t *ps,
                             int wire_weapon)
{
    codol_use_hint_t hint;

    if(!out || !ps) return 0;
    CODOL_ClearUseHint(&hint);
    hint.known = 1;
    /* Native clears only cursorHint each frame (_player_use_mp.asm:295) and
     * leaves the other two holding the previous hint's values. C1 returns from
     * 0x456080 before reading them when the hint is zero, so the stale pair is
     * dropped here instead of being serialized as a live-looking hint. */
    if(ps->cursorHint == 0) { *out = hint; return 1; }
    if(ps->cursorHint < 0) return 0;
    if(ps->cursorHint <= CODOL_USEHINT_ICON_MAX) {
        hint.kind = CODOL_USEHINT_KIND_ICON;
        hint.icon = (unsigned short)ps->cursorHint;
    } else {
        if(wire_weapon <= 0 || wire_weapon > CODOL_USEHINT_WEAPON_MAX) return 0;
        hint.kind = CODOL_USEHINT_KIND_WEAPON;
        hint.weapon = (unsigned short)wire_weapon;
    }
    if(!capture_string(&hint.string, ps->cursorHintString) ||
       !capture_entity(&hint.entity, ps->cursorHintEntIndex)) return 0;
    *out = hint;
    return 1;
}

int CODOL_OverlayUseHint(codol_player_fields_t *wire, const codol_use_hint_t *hint)
{
    codol_player_fields_t out;
    uint32_t value;

    if(!wire || !CODOL_UseHintValid(hint)) return 0;
    switch(hint->kind) {
    case CODOL_USEHINT_KIND_ICON: value = hint->icon; break;
    case CODOL_USEHINT_KIND_WEAPON: value = (uint32_t)hint->weapon + USEHINT_WEAPON_BIAS; break;
    default: value = 0; break;
    }
    out = *wire;
    /* 0x20c is a signed eight-bit field; the writer takes the two's-complement
     * word, as the other signed fields do (codol_engine_state.c:230). */
    if(!hint_put(&out, 0x208, value) ||
       !hint_put(&out, 0x20c, (uint32_t)(int32_t)hint->string) ||
       !hint_put(&out, 0x210, hint->entity)) return 0;
    if(hint->alternate_known &&
       !hint_put(&out, 0x214, hint->alternate ? UINT32_C(1) : UINT32_C(0))) return 0;
    *wire = out;
    return 1;
}
