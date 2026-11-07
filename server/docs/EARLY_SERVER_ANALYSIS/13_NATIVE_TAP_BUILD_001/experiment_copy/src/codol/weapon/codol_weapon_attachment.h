/* CoDOL weaponattach overrides (asset type 43).
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_WEAPON_ATTACHMENT_H
#define CODOL_WEAPON_ATTACHMENT_H
#include "codol_assets.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Entry kinds, from C1's field switch 0x420afe and its own log strings.
 * Kinds below 0x10 carry a string value that begins with an optional
 * "[<op>]"/"[f<op>]" prefix (parser 0x41ee30); every other kind stores the
 * serialized dword unchanged (0x42098d), except the hide-tag kind. The three
 * unnamed asset kinds are named after their C1 resolver, because nothing in
 * the shipped data or the client names them: 0xb 0xa77b50, 0xc 0xa78170,
 * 0xe 0x61e820. Kind 0xd trims a ".map" suffix from the expanded value and
 * then writes no field at all (0x420e60); that is the whole handler. */
enum {
    CODOL_ATTACH_TEXT_0=0,        /* Four identical char* handlers, 0x420d80. */
    CODOL_ATTACH_TEXT_1=1, CODOL_ATTACH_TEXT_2=2, CODOL_ATTACH_TEXT_3=3,
    CODOL_ATTACH_INT=4,           /* "int",    0x420b63 */
    CODOL_ATTACH_QBOOL=5,         /* "qbool",  0x420b45, four bool bytes */
    CODOL_ATTACH_BOOL=6,          /* "bool",   0x420b0e, one byte */
    CODOL_ATTACH_FLOAT=7,         /* "float",  0x420bd5 */
    CODOL_ATTACH_INCHES=8,        /* "inches", 0x420ce0, value * 17.6 */
    CODOL_ATTACH_MILLISECONDS=9,  /* "ms",     0x420c63, value * 1000, to int */
    CODOL_ATTACH_EFFECT=0xa,      /* DB_FindXAssetHeader(30), 0x420df6 */
    CODOL_ATTACH_ASSET_A77B50=0xb, CODOL_ATTACH_ASSET_A78170=0xc,
    CODOL_ATTACH_MAP=0xd, CODOL_ATTACH_ASSET_61E820=0xe,
    CODOL_ATTACH_ASSET_TYPE40=0xf, /* DB_FindXAssetHeader(40), 0x420daa */
    CODOL_ATTACH_TEXT_LIMIT=0x10, /* First kind whose value is not a string. */
    CODOL_ATTACH_HIDE_TAG=0x27    /* Appends to the 32 tags at +0x3c, 0x420930 */
};
typedef struct {
    uint32_t offset,type,value; /* Serialized {u32,u32,u32}; loader 0x4c3d00. */
    const char *text;           /* Borrowed; non-null exactly for string kinds. */
} codol_weapon_attachment_entry_t;
typedef struct {
    codol_asset_t asset;
    const char *name;                         /* Borrowed archive string. */
    codol_weapon_attachment_entry_t *entries; /* Owned array, count elements. */
    uint32_t count;
} codol_weapon_attachment_t;
/* Reads one mounted type-43 definition: the 12-byte header {name, count,
 * entries} and its count 12-byte entries, with every string-kind value
 * resolved against the defining archive. Strings borrow archive lifetime, the
 * entry array is owned. A count without an entry array, an entry array without
 * a count, a string kind whose value reference does not resolve, or any extent
 * the asset does not cover rejects the whole definition; nothing is written
 * unless the read succeeds. 1 ready, 0 no such attachment, -1 malformed. */
int CODOL_ReadWeaponAttachment(const char *,codol_weapon_attachment_t *);
void CODOL_FreeWeaponAttachment(codol_weapon_attachment_t *);
enum { CODOL_WEAPON_SOURCE_HEADER=0xbfc, CODOL_WEAPON_SOURCE_TAGS=32 };
typedef struct {
    uint32_t offset;
    const char *name; /* Borrowed mounted name, or owned when overridden. */
    char *owned;
} codol_weapon_source_name_t;
/* An owned copy of one weapon's serialized CoDOL source image, carrying the
 * resolved name of every pointer slot the mounted readers expose and the 32
 * resolved hide tags. Attachment overrides are applied to this, never to a
 * native WeaponDef: C1's entry offsets address the CoDOL source layout, whose
 * fields do not correspond to IW3's struct. Scalar overrides land in data;
 * string and asset-name overrides land in names, because the corresponding
 * image dwords are serialized references, not pointers, and rewriting one
 * would break the inline traversal every mounted reader depends on. */
typedef struct {
    uint8_t *data;                    /* Owned copy of the mounted asset bytes. */
    size_t size,dependency_offset;    /* Unmoved: no override rewrites inline data. */
    const char *base;                 /* Borrowed mounted internal name. */
    char context[64];                 /* C1 <w> token: base without "_mp". */
    codol_weapon_source_name_t *names;
    size_t name_count;
    const char *sound_arrays[2][31]; /* Borrowed resolved array entries. */
    codol_weapon_model_t models[11];
    codol_weapon_effects_t effects;
    codol_weapon_tail_t tail; /* Borrowed graph data from this generation. */
    codol_weapon_visuals_t visuals;
    const char *hide_tags[CODOL_WEAPON_SOURCE_TAGS]; /* Borrowed or owned. */
    char *owned_tags[CODOL_WEAPON_SOURCE_TAGS];
    uint8_t *scalar;                  /* size bytes; 1 where a scalar may be written. */
} codol_weapon_source_image_t;
/* Deep-copies the mounted weapon's serialized image and resolves its name
 * slots and hide tags through the existing mounted readers. The image owns its
 * bytes and every override it later takes; the borrowed names it starts with
 * live as long as the defining archive, so an image must not outlive the mount
 * it was taken from. out must be zeroed or a prior image; failure preserves it.
 * 1 ready, 0 absent weapon, -1 malformed or unresolvable. */
int CODOL_BeginWeaponSourceImage(const char *,codol_weapon_source_image_t *);
void CODOL_FreeWeaponSourceImage(codol_weapon_source_image_t *);
/* Applies attachment definitions in C1's order (BG_BuildCustomWeaponDef
 * 0x421882..0x421a19): every entry is offered to the field filter 0x4208e0
 * first, which applies scalar, raw and hide-tag entries immediately and defers
 * the string operators; the deferred entries are then sorted with comparator
 * 0x420f10 and applied per offset group by 0x4210c0, which keeps one forced
 * entry, keeps one set entry, drops replaces that clash with a later replace,
 * and applies the rest in order. Original values are read from the unmodified
 * image and current values from the partially applied one, exactly as C1 reads
 * its +0x94 base pointer and its +0x98 copy.
 * The transaction is atomic: any malformed entry leaves the image untouched.
 * A kind whose value string is empty, or whose operator prefix yields an empty
 * operand, is ignored without a write, as in C1; a string operator on a scalar
 * kind uses the operand, as in C1. A scalar write that would land on a pointer
 * slot, on the hide-tag array or outside the image is rejected instead: those
 * are pointers in C1's relocated definition and serialized references here.
 * 1 applied, -1 rejected. */
int CODOL_ApplyWeaponAttachments(codol_weapon_source_image_t *,
    const codol_weapon_attachment_t *const *,unsigned);
/* Resolved name for one source pointer slot, after overrides. 1 found, 0 not a
 * slot this image resolves; *out may be null for a null slot. */
int CODOL_WeaponSourceName(const codol_weapon_source_image_t *,unsigned,const char **);
/* The 32 tags in slot order, with C1's appends. Absent slots stay null. */
int CODOL_WeaponSourceHideTags(const codol_weapon_source_image_t *,codol_weapon_hide_tags_t *);
/* A mounted view over the patched image for the existing native converters.
 * The four leading strings come from the name table, so an overridden internal
 * name is what the converters see. The view borrows the image; dependency
 * offsets are unchanged because no override ever moves inline data. */
int CODOL_WeaponSourceView(const codol_weapon_source_image_t *,codol_mounted_weapon_t *);
/* Resolved dependencies from this image, including name overrides. These
 * borrow image lifetime; they do not re-read a possibly replaced base asset.
 * dependency_offset is zero: these are resolved views, not traversal cursors. */
int CODOL_WeaponSourceAnimations(const codol_weapon_source_image_t *,codol_weapon_animations_t *);
int CODOL_WeaponSourceAmmoNames(const codol_weapon_source_image_t *,codol_weapon_ammo_names_t *);
int CODOL_WeaponSourceSounds(const codol_weapon_source_image_t *,codol_weapon_sounds_t *);
/* Model returns 0 for a null slot without changing out, 1 for a named slot,
 * -1 for invalid input. Effects preserves both slots, including nulls. */
int CODOL_WeaponSourceModel(const codol_weapon_source_image_t *,unsigned,codol_weapon_model_t *);
int CODOL_WeaponSourceEffects(const codol_weapon_source_image_t *,codol_weapon_effects_t *);
/* Changed asset names invalidate the old asset bytes; the native loader must
 * resolve the returned name before using an asset dependency. Graph arrays
 * remain borrowed from this image's original archive generation. */
int CODOL_WeaponSourceTail(const codol_weapon_source_image_t *,codol_weapon_tail_t *);
int CODOL_WeaponSourceVisuals(const codol_weapon_source_image_t *,codol_weapon_visuals_t *);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
