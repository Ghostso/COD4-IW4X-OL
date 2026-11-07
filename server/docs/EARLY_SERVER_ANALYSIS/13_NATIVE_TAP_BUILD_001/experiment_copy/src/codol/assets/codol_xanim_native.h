#ifndef CODOL_XANIM_NATIVE_H
#define CODOL_XANIM_NATIVE_H
#include "codol_assets.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
struct XAnimParts;
typedef struct {
    struct XAnimParts *parts;
    void *storage;
    size_t size;
} codol_native_xanim_t;
/* Constructs owned payloads, including translation and quat2 delta tracks.
 * CoDOL quat4 tracks remain unsupported and reject conversion. Native SL
 * handles are borrowed and must outlive the result. No global publication or
 * compressed-stream compatibility claim. Zero/prior out; atomic replacement. */
int CODOL_BuildNativeXAnim(const codol_mounted_xanim_t *,const codol_xanim_handles_t *,codol_native_xanim_t *);
void CODOL_FreeNativeXAnim(codol_native_xanim_t *);
/* Borrowed until full archive unmount, including retired archive generations.
 * The string provider/context must remain valid until then. Atomic output. */
int CODOL_LoadMountedNativeXAnim(const char *,codol_xanim_string_acquire_t,
    codol_xanim_string_release_t,void *,const struct XAnimParts **);
int CODOL_LoadEngineNativeXAnim(const char *,const struct XAnimParts **);
/* Diagnostic: resolves the persistent asset through DB lookup and evaluates
 * five finite-transform samples with an identity map; no client pose comparison. */
int CODOL_CheckEngineXAnim(const char *,unsigned *bones);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
