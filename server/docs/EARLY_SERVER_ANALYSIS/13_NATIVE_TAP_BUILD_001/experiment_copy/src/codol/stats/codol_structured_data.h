#ifndef CODOL_STRUCTURED_DATA_H
#define CODOL_STRUCTURED_DATA_H
#include <stddef.h>
#include <stdint.h>
#pragma pack(push, 8)
/* A validated schema's logical-property -> storage map, in serialized LE32
 * form. Offsets are bytes except bool (type 2), which uses bit positions.
 * The caller owns the map and record for the duration of each operation. */
typedef struct {
    const uint8_t *offset_map;
    size_t offset_map_size;
    size_t record_size;
} codol_structured_layout_t;
/* Raw scalar bits, not GSC coercion: 0=int32, 1=byte, 2=bool, 8=float32,
 * 9=short. Float bits are preserved; short writes take the low 16 bits and
 * reads zero-extend (the VM adapter owns signed interpretation).
 * Other types reject. Byte writes require 0..255; bool input must be 0/1.
 * Failure preserves output/record; record capacity must cover the schema. */
int CODOL_StructuredReadScalar(const codol_structured_layout_t *,unsigned type,
    unsigned property,const uint8_t *record,size_t capacity,uint32_t *out);
int CODOL_StructuredWriteScalar(const codol_structured_layout_t *,unsigned type,
    unsigned property,uint8_t *record,size_t capacity,uint32_t value);
#pragma pack(pop)
#endif
