/* CoDOL cursor-hint publication: what the retained IW3 use scan decided, in the
 * C1 playerState representation.
 *
 * Native Player_UpdateCursorHints (src/asmsource/_player_use_mp.asm) publishes
 * three fields: ps+0x5a0 cursorHint, ps+0x5a4 cursorHintString, ps+0x5a8
 * cursorHintEntIndex. C1 keeps the same three in its own playerState at 0x208,
 * 0x20c and 0x210 plus a fourth one-bit field at 0x214, and reads all four in
 * one place (0x456080, the client-side hint update) into cg+0xbf058/68/6c.
 *
 * The hint value is an enum with a weapon tail in both engines:
 *   0                 no hint
 *   1 HINT_NOICON     C1 0x456859 draws text only, no icon lookup
 *   2 HINT_ACTIVATE   C1 0x456862 draws text only, no icon lookup
 *   3 HINT_HEALTH     C1 0x4569ac falls back to the "+activate" prompt with no
 *                     hint string; icon from the hint table 0x16d4554
 *   4 HINT_FRIENDLY   C1 icon table only
 *   4 + weapon        weapon hint; C1 0x456886..0x45689b accepts 5..0x2c0 and
 *                     reads weapondefs[hint-4] through 0x150d710, which is the
 *                     ordinary weapondef table 0x150d720 biased by four
 *                     entries (0x5764f7 indexes 0x150d720 by a plain weapon).
 * The native names come from the engine's own hintStrings table
 * (src/asmsource/_g_mover.asm:1373, indices 0..4) and the native weapon tail
 * from Player_UpdateCursorHints writing weapon+4 (asm lines 348-356 and the
 * item case at _500). The two enums agree on 0..4 and on the +4 weapon bias;
 * they do not agree on the weapon numbering, on the "no entity" value, and C1
 * has one field native never produced. That is what this adapter converts.
 *
 * Resolution and translation are separate. The caller must supply the wire
 * weapon binding belonging to this state; reading today's mutable weapon map
 * while serializing an archived snapshot would reinterpret an old hint.
 * Neither helper accesses a live weapon map or a live player entity.
 */
#ifndef CODOL_USEHINT_WIRE_H
#define CODOL_USEHINT_WIRE_H
#include "player.h"
#include "codol_playerstate.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

enum {
    CODOL_USEHINT_KIND_NONE = 0,
    CODOL_USEHINT_KIND_ICON = 1,   /* Published unchanged; both enums share 1..4. */
    CODOL_USEHINT_KIND_WEAPON = 2  /* Published as wire weapon + 4. */
};
/* HINT_NOICON..HINT_FRIENDLY: the populated part of hintStrings. */
#define CODOL_USEHINT_ICON_MAX 4
/* C1 0x45688f rejects a hint above 0x2c0, so the last usable weapon is 700 -
 * the same 700-weapon namespace the entity adapters use for variant packing. */
#define CODOL_USEHINT_WEAPON_MAX 700
/* C1 0x456992/0x457019 require a non-negative string before fetching text. */
#define CODOL_USEHINT_STRING_NONE (-1)

typedef struct {
    unsigned char known;     /* Zero means never captured; publishing is refused. */
    unsigned char kind;      /* codol_usehint_kind. */
    unsigned char alternate; /* ps+0x214; see CODOL_UseHintAlternate below. */
    unsigned char alternate_known; /* Leave the incoming field when unknown. */
    unsigned short icon;     /* KIND_ICON: 1..4. Zero otherwise. */
    unsigned short weapon;   /* KIND_WEAPON: wire weapon 1..700. Zero otherwise. */
    short string;            /* -1, or a hint-string slot 0..31 in bank 584. */
    unsigned short entity;   /* Wire entity number; 2047 is "none". */
} codol_use_hint_t;

void CODOL_ClearUseHint(codol_use_hint_t *hint);
/* Playing-frame publisher; archive/spectator copies carry its binding. */
void CODOL_CaptureClientUseHint(unsigned client);
int CODOL_UseHintValid(const codol_use_hint_t *hint);
/* Resolve named fields from this playerState. For cursorHint>4, wire_weapon
 * must be the binding for native weapon cursorHint-4 captured with that state.
 * Other hint kinds ignore wire_weapon. Rejects an invalid wire weapon, string
 * slot, or entity number. Capture/archive integration is still outstanding. */
int CODOL_ResolveEngineUseHint(codol_use_hint_t *out, const playerState_t *ps,
                             int wire_weapon);
/* Pure translation into wire fields 0x208/0x20c/0x210/0x214. No weapon map,
 * configstring, entity or client lookup. Field214 is written only when its
 * producer supplied a known value; other fields commit together or not at all. */
int CODOL_OverlayUseHint(codol_player_fields_t *wire, const codol_use_hint_t *hint);
/* ps+0x214 selects between the two icon-drawing branches of C1's hint draw
 * (0x456ba9 and 0x456ec9 test cg+0xbf06c, which 0x456080 copies from it). No
 * C1 server-side producer for it has been located and the retained playerState
 * has no counterpart, so resolution leaves it unknown and overlay preserves
 * the incoming field. This setter exists so a
 * producer that is identified later has one place to write, instead of the
 * value being invented inside the translator. */
int CODOL_UseHintAlternate(codol_use_hint_t *hint, int alternate);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
