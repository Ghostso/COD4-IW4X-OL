/* C1's own contents and surface-flag definitions.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * PROVENANCE: read out of C1.exe 1.1.1.13 (ImageBase 0x400000) from the
 * material `infoParms` table at file offset 0x008cd8a8..0x008cddbc (VA
 * 0x00ccf6a8, .data), 65 records
 * of 20 bytes: { const char *name; int clearSolid; int surfaceFlags;
 * int contents; int pad }.  Not inferred, not copied from IW3 headers.
 *
 * WHY THIS FILE EXISTS.  Before it, this tree had no contents or surface-flag
 * definitions for this engine at all -- the only CONTENTS_* symbols anywhere
 * were legacy Quake/BSPC ones under src/botlib/ and src/bspc/, unrelated.  So
 * every collision mask in the server was an unsourced magic number while the
 * project's mandate is to match C1.  A wrong mask includes or excludes a whole
 * CLASS of volume, which presents as extra solid in one place and missing solid
 * in another -- exactly the symptom pair under investigation.
 *
 * `clearSolid` in the table means the material REMOVES CONTENTS_SOLID.  That is
 * why there is no "solid" infoParm: solid is the default, and clip materials
 * clear it.  A surface with, say, contents 0x08031640 therefore has NO solid
 * bit and is a clip volume, not world solid.
 */
#ifndef CODOL_COLLISION_FLAGS_H
#define CODOL_COLLISION_FLAGS_H

/* ---- contents ---------------------------------------------------------- */
#define CODOL_CONTENTS_SOLID            0x00000001u /* default; cleared by clip materials */
#define CODOL_CONTENTS_FOLIAGE          0x00000002u /* "foliage",  clearSolid */
#define CODOL_CONTENTS_AICLIPALLOWDEATH 0x00000004u /* "aiclipallowdeath", clearSolid */
#define CODOL_CONTENTS_GLASS            0x00000010u /* "glass",    clearSolid */
#define CODOL_CONTENTS_WATER            0x00000020u /* "water",    clearSolid */
#define CODOL_CONTENTS_CANSHOOTCLIP     0x00000040u /* "canshootclip" */
#define CODOL_CONTENTS_CLIPMISSILE      0x00000080u /* "clipmissile",  clearSolid */
#define CODOL_CONTENTS_VEHICLECLIP      0x00000200u /* "vehicleclip",  clearSolid */
#define CODOL_CONTENTS_ITEMCLIP         0x00000400u /* "itemclip",     clearSolid */
#define CODOL_CONTENTS_SKY              0x00000800u /* "sky" */
#define CODOL_CONTENTS_AI_NOSIGHT       0x00001000u /* "ai_nosight",   clearSolid */
#define CODOL_CONTENTS_CLIPSHOT         0x00002000u /* "clipshot",     clearSolid */
#define CODOL_CONTENTS_PLAYERCLIP       0x00010000u /* "playerclip",   clearSolid */
#define CODOL_CONTENTS_MONSTERCLIP      0x00020000u /* "monsterclip",  clearSolid */
#define CODOL_CONTENTS_MANTLE           0x01000000u /* "mantleOn"/"mantleOver" */
#define CODOL_CONTENTS_DETAIL           0x08000000u /* "detail" */
#define CODOL_CONTENTS_STRUCTURAL       0x10000000u /* "structural" */
#define CODOL_CONTENTS_NODROP           0x80000000u /* "nodrop",       clearSolid */

/* THREE bits appear in trace masks that no material in the table can author.
 * They are engine-internal contents set at runtime on entities, which is why
 * no infoParm produces them -- and it is also why they are invisible to world
 * geometry: measured on mp_storm_spring, each occurs in 0 brushes, 0 leaf
 * contents and 0 materials (tests/test_codol_assets.c --contents).
 *   0x00004000  unnamed
 *   0x00800000  unnamed
 *   0x02000000  unnamed  (note: 0x02000000 IS "mantleOn" in SURFACE flags,
 *                         a different field -- an easy confusion to make)
 * Their individual meanings are still NOT established -- do not guess them.
 * What IS established is the mask that carries them. C1 builds the player
 * trace mask at 0x0050cbc1 as
 *   cmp [ebx+4],8 / setl dl / dec edx / and edx,0xfdffc000 / add edx,0x2814011
 * giving 0x02814011 when that field is < 8 and 0x00800011 otherwise. The
 * constant 0x02810011 this port used occurs NOWHERE in C1.exe; 0x02814011
 * occurs at 20 sites. Both branches were one bit out and are now fixed in
 * _g_active_mp.asm and _bg_pmove.asm. */

/* ---- surface flags ----------------------------------------------------- */
#define CODOL_SURF_NODAMAGE             0x00000001u
#define CODOL_SURF_SLICK                0x00000002u
#define CODOL_SURF_SKY                  0x00000004u
#define CODOL_SURF_LADDER               0x00000008u
#define CODOL_SURF_NOIMPACT             0x00000010u
#define CODOL_SURF_NOMARKS              0x00000020u
#define CODOL_SURF_NODRAW               0x00000080u
#define CODOL_SURF_NOPENETRATE          0x00000100u
#define CODOL_SURF_STAIRS               0x00000200u
#define CODOL_SURF_NOLIGHTMAP           0x00000400u
#define CODOL_SURF_SOFT                 0x00001000u
#define CODOL_SURF_NOSTEPS              0x00002000u
#define CODOL_SURF_NONSOLID             0x00004000u
#define CODOL_SURF_NODLIGHT             0x00020000u
#define CODOL_SURF_NOCASTSHADOW         0x00040000u
#define CODOL_SURF_MANTLEON             0x02000000u
#define CODOL_SURF_MANTLEOVER           0x04000000u
#define CODOL_SURF_PORTAL               0x80000000u

/* Surface TYPE occupies bits 20..24, i.e. (surfaceFlags >> 20) & 31.
 * CODOL_PM_FootstepsC1 and PM_CrashLand already use exactly that shift and
 * mask; this table confirms it. Index 0 is the unnamed default. */
#define CODOL_SURF_TYPE_SHIFT           20
#define CODOL_SURF_TYPE_MASK            0x1fu
#define CODOL_SURF_TYPE(sf) (((unsigned)(sf) >> CODOL_SURF_TYPE_SHIFT) & CODOL_SURF_TYPE_MASK)
enum {
    CODOL_SURFTYPE_DEFAULT = 0,  CODOL_SURFTYPE_BARK = 1,
    CODOL_SURFTYPE_BRICK = 2,    CODOL_SURFTYPE_CARPET = 3,
    CODOL_SURFTYPE_CLOTH = 4,    CODOL_SURFTYPE_CONCRETE = 5,
    CODOL_SURFTYPE_DIRT = 6,     CODOL_SURFTYPE_FLESH = 7,
    CODOL_SURFTYPE_FOLIAGE = 8,  CODOL_SURFTYPE_GLASS = 9,
    CODOL_SURFTYPE_GRASS = 10,   CODOL_SURFTYPE_GRAVEL = 11,
    CODOL_SURFTYPE_ICE = 12,     CODOL_SURFTYPE_METAL = 13,
    CODOL_SURFTYPE_MUD = 14,     CODOL_SURFTYPE_PAPER = 15,
    CODOL_SURFTYPE_PLASTER = 16, CODOL_SURFTYPE_ROCK = 17,
    CODOL_SURFTYPE_SAND = 18,    CODOL_SURFTYPE_SNOW = 19,
    CODOL_SURFTYPE_WATER = 20,   CODOL_SURFTYPE_WOOD = 21,
    CODOL_SURFTYPE_ASPHALT = 22, CODOL_SURFTYPE_CERAMIC = 23,
    CODOL_SURFTYPE_PLASTIC = 24, CODOL_SURFTYPE_RUBBER = 25,
    CODOL_SURFTYPE_CUSHION = 26, CODOL_SURFTYPE_FRUIT = 27,
    CODOL_SURFTYPE_PAINTEDMETAL = 28, CODOL_SURFTYPE_RIOTSHIELD = 29,
    CODOL_SURFTYPE_SLUSH = 30
};

#endif
