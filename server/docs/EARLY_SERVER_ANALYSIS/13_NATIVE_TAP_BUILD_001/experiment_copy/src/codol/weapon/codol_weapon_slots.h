/* The native weapon table width, in exactly one place.
 *
 * C1 1.1.1.13 registers 700 weapon definitions and there is no 128 anywhere on
 * its weapon path:
 *   bg_weaponDefs        0x0150D720   700 pointers; the next live global is at
 *                                     0x0150E210 = base + 0xAF0, no padding
 *   BG_ClearWeaponDefs   0x0041F570   memset(0x0150D720, 0, 0xAF0)
 *   CG_Init              0x00450ADC   walks 1..699 (cmp edi, 0x2bc)
 *   BG_RegisterWeaponDef 0x0041F640   appends with no cap
 *   CS_WEAPONS                        a 700-slot configstring window (5362..6061)
 *   entity field 0x098   0x0052FBC3   encodes weapon + 700*modelIndex - 700 is
 *                                     literally the modulus
 * The playerstate weapon fields are 10 bits, so 1023 is the encoding limit, but
 * 700 is what the client's table and configstring window can consume.
 *
 * The 128 this server used to have was entirely the retained IW3 playerState_t
 * layout: weapons/weaponold/weaponrechamber are 4 dwords each at 0x55c/0x56c/
 * 0x57c and weaponmodels is 128 bytes at 0x81c, inside a struct whose size
 * (0x2f64) cannot change because 521 retained-assembly sites address gclient_t
 * members past it. All four arrays now live in the playerState extension at
 * full width; the retained assembly reaches them through
 * src/asmsource/codol_weapon_bits.inc.
 *
 * ammo[128] / ammoclip[128] are NOT this domain and stay at 128: they are
 * indexed by def->iAmmoIndex / def->iClipIndex, a separate pool that weapons
 * share by name. C1 has no such limit: BG_ClearWeaponDefs (0x41F570) clears
 * four 700-pointer tables (defs 0x0150D720, clips 0x015106F8, shared caps
 * 0x0150CC30, ammo 0x0150FC08) and keeps ammo per weapon slot, not per pool
 * index. The retained pools (_bg_weapons.asm, 128 each) are therefore gated
 * by CODOL_AdmitWeaponPools, which refuses a definition that would need a
 * 129th entry instead of letting the unchecked append overwrite the next
 * pool's counter. Stock MP maps use about 105 of the 128.
 */
#ifndef CODOL_WEAPON_SLOTS_H
#define CODOL_WEAPON_SLOTS_H

/* The number itself already had a home: codol_configstrings.h states it for
 * the CS_WEAPONS window. Take it from there rather than writing 700 twice. */
#include "codol_configstrings.h"
/* 22 words. Spelled out rather than divided so that a width that is not a
 * multiple of 32 still gets a word for the remainder. */
#define CODOL_WEAPON_BIT_WORDS ((CODOL_WEAPON_SLOTS + 31u) / 32u)
/* Entries in each retained ammo / clip / shared-cap pool and in playerState
 * ammo[] / ammoclip[]. */
#define CODOL_NATIVE_AMMO_POOL 128u

/* Bits that hold one native weapon index wherever the server serializes it
 * for itself (the archived snapshot frames killcams and followed spectators
 * are rebuilt from, and the playerState extension records beside them). C1's
 * own playerstate weapon fields are 10 bits wide as well. */
#define CODOL_WEAPON_INDEX_BITS 10
#if CODOL_WEAPON_SLOTS > (1 << CODOL_WEAPON_INDEX_BITS)
#error "CODOL_WEAPON_INDEX_BITS cannot hold every native weapon index"
#endif

/* The item index: weapon + CODOL_ITEM_STRIDE * world-model variant. It indexes
 * bg_itemlist and is stored in gentity item[].index, an item's s.index and a
 * pickup missile's s.index. C1 builds it with a stride of 700 (0x0052FBC3
 * imul 0x2bc) and its client takes s+0x98 apart with the same divisor
 * (0x0043E94C), so the stride is the weapon table width; the retained IW3
 * stride of 128 cannot name a weapon above 127. The retained assembly uses
 * src/asmsource/codol_item_index.inc, which must agree with this. */
#define CODOL_ITEM_STRIDE CODOL_WEAPON_SLOTS
#define CODOL_ITEM_MODELS 16u
#define CODOL_ITEM_INDEX_BITS 14
#if CODOL_ITEM_STRIDE != 700
#error "codol_item_index.inc hard-codes the C1 item stride 700"
#endif
#if CODOL_ITEM_STRIDE * CODOL_ITEM_MODELS > (1 << CODOL_ITEM_INDEX_BITS)
#error "CODOL_ITEM_INDEX_BITS cannot hold every item index"
#endif
#define CODOL_ItemIndexWeapon(index) ((unsigned)(index) % CODOL_ITEM_STRIDE)
#define CODOL_ItemIndexModel(index) ((unsigned)(index) / CODOL_ITEM_STRIDE)

#endif
