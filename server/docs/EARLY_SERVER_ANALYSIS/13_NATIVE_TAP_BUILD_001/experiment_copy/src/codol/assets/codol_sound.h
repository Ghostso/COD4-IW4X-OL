/* Serialized CoDOL sound views. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SOUND_H
#define CODOL_SOUND_H
#include "codol_xmodel.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Structural evidence: C1 loaders 0x4b8750 (snd_alias_list_t, 12 bytes),
 * 0x4b84b0 (snd_alias_t, 108 bytes), 0x4b8240 (SoundFile, 12 bytes),
 * 0x4b8420 (SpeakerMap, 408 bytes), 0x4b82b0 (SndCurve, 136 bytes) and
 * 0x4b80b0 (LoadedSound, 48 bytes plus payload). Field roles are measured in
 * the C1 runtime and listed with codol_sound_native.h's conversion table;
 * unmeasured words are preserved here instead of being renamed by analogy. */
typedef struct {
    codol_asset_t asset;
    codol_model_block_t blocks[8];
} codol_sound_view_t;
/* Reference kinds the resolver must answer. Types 11/12/13 are asset
 * references and must return the winning definition's serialized view with its
 * owning archive's block views. CODOL_SOUND_SPAN is a deduplicated pointer into
 * reconstructed loader memory: the resolver returns the serialized span the
 * loader replayed there, which is how alias arrays and sound files whose
 * dependencies were written to the rewound scratch block stay readable. */
enum { CODOL_SOUND_SPAN=0 };
typedef int (*codol_sound_resolver_t)(void *context,unsigned type,uint32_t reference,
    codol_sound_view_t *out);
typedef struct {
    const char *name;
    /* Record +0x04 starts a forty-byte sound-info block, four bytes longer
     * than the retained AILSOUNDINFO. Field roles measured against the shipped
     * zones: +0x0c is the payload length and matches the replayed payload,
     * +0x10 is 44100/48000/32000/22050, +0x14 is 4 (ADPCM) or 16 (PCM),
     * +0x18 is 1 or 2 channels, +0x1c is a constant sentinel, +0x20 is the
     * sample count (twice the byte count for 4-bit ADPCM, half for 16-bit mono
     * PCM) and +0x24 is a 512/768/1024/2048 block size. */
    uint32_t format,data_length,rate,bits,channels,samples,block_size;
    uint32_t sentinel; /* record +0x1c, constant 0xffffffff in shipped data */
    const uint8_t *payload; /* borrowed serialized samples; NULL when absent */
} codol_loaded_sound_t;
typedef struct {
    const char *name;
    unsigned knot_count; /* 16-bit count at +4, C1 evaluator 0x7375b0 */
    float knots[16][2];  /* 8-byte pairs, interpolated by C1 0x618d80 */
} codol_sound_curve_t;
typedef struct {
    uint8_t is_default;
    const char *name;
    const uint8_t *channel_maps; /* borrowed 400 serialized bytes */
} codol_speaker_map_t;
typedef struct {
    uint8_t type,exists; /* C1 0x7384e0: 1 loaded, 2 streamed, 3 primed */
    const char *dir,*name; /* streamed and primed records */
    int has_loaded;
    codol_loaded_sound_t loaded;
} codol_sound_file_t;
typedef struct {
    /* Slot 0 alias name, 1 subtitle, 2 secondary alias, 3 chain alias and a
     * fifth CoDOL-only name with no IW3 field. */
    const char *names[5];
    int has_file;
    codol_sound_file_t file;
    int32_t sequence,start_delay;
    float volume[2],pitch[2],distance[2],probability;
    uint32_t flags;
    uint8_t priority; /* record +60 byte, compared against a global threshold */
    /* Scalars with no measured role, in record order:
     * +0x34, +0x40, +0x44, +0x4c, +0x50, +0x5c, +0x60, +0x64. */
    float unmeasured[8];
    int has_curve,has_speakers;
    codol_sound_curve_t curve;
    codol_speaker_map_t speakers;
    const uint8_t *record; /* borrowed 108 serialized bytes */
} codol_sound_alias_t;
typedef struct {
    const char *name;
    unsigned count;
    codol_sound_alias_t *aliases;
} codol_sound_alias_list_t;
/* Complete serialized traversal of a type 11 asset in loader order, including
 * sound files, loaded-sound payloads, curves and speaker maps. Owns only the
 * alias array; strings and payloads borrow the view's archive lifetime. No
 * serialized pointer is retained as an engine pointer. Deduplicated alias
 * arrays and sound files are replayed from the serialized span the resolver
 * returns for CODOL_SOUND_SPAN, so their loaded sounds and inline curves are
 * read from the archive image instead of rewound scratch memory.
 * out is zero/prior; failure preserves it. */
int CODOL_ReadSoundAliasList(const codol_sound_view_t *,codol_sound_resolver_t,void *,
    codol_sound_alias_list_t *);
void CODOL_FreeSoundAliasList(codol_sound_alias_list_t *);
/* Diagnostics for the engine error path: first hard failure line of the current
 * source lookup, reset by the engine weapon-sound loader. */
int CODOL_SoundSourceFailureLine(void);
void CODOL_ResetSoundSourceFailure(void);
void CODOL_SoundSourceFailureDetail(int *status,unsigned *type,uint32_t *reference);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)

#endif
