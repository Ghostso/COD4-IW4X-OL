#ifndef CODOL_STREAM_MODEL_H
#define CODOL_STREAM_MODEL_H
#include "codol_xsurface.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* C1 1.1.1.13 streamed models/<name> container, not a fastfile stream.
 * Owned blocks map source blocks 0/1/2 to retained blocks 3/6/7. Relocated
 * words are encoded references, never host pointers. Root header is block 3.
 * Geometry decoding and publication are separate operations. */
typedef struct {
    uint8_t *storage[3];
    codol_model_block_t blocks[8];
} codol_stream_model_t;
int CODOL_ReadStreamModel(const uint8_t *,size_t,codol_stream_model_t *);
void CODOL_FreeStreamModel(codol_stream_model_t *);
/* Owned name and surface descriptors; array/tree references borrow the stream
 * blocks. Keep the stream alive until native geometry construction completes. */
int CODOL_ReadStreamModelSurfaces(const codol_stream_model_t *,codol_model_surfaces_t *);
/* Provider returns 1 with owned decoded blocks, 0 absent, -1 invalid. It must
 * leave output unchanged on failure. Configure before mounting; provider and
 * context must survive all mounts. Reconfiguration requires unmounting. */
typedef int (*codol_stream_model_loader_t)(void *,const char *,codol_stream_model_t *);
int CODOL_SetStreamModelLoader(codol_stream_model_loader_t,void *);
void CODOL_InitEngineStreamModels(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
