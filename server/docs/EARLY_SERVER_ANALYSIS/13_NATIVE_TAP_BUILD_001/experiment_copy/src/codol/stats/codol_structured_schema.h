#ifndef CODOL_STRUCTURED_SCHEMA_H
#define CODOL_STRUCTURED_SCHEMA_H
#include "codol_assets.h"
#include "codol_structured_data.h"
#pragma pack(push, 8)
typedef struct {uint32_t kind,index;} codol_structured_type_t;
typedef struct {const char *name; uint32_t value;} codol_structured_enum_member_t;
typedef struct {uint32_t count; codol_structured_enum_member_t *members;} codol_structured_enum_t;
typedef struct {
    const char *name; codol_structured_type_t type;
    uint32_t logical_index,extra[2];
} codol_structured_property_t;
typedef struct {
    uint32_t count,size,bit_offset,logical_count;
    codol_structured_property_t *properties;
} codol_structured_struct_t;
typedef struct {uint32_t count_or_enum; codol_structured_type_t element; uint32_t stride;} codol_structured_array_t;
typedef struct {
    uint32_t version,checksum,enum_count,struct_count,indexed_count,enum_array_count;
    codol_structured_type_t root;
    codol_structured_enum_t *enums;
    codol_structured_struct_t *structs;
    codol_structured_array_t *indexed_arrays,*enum_arrays;
    codol_structured_layout_t layout;
} codol_structured_definition_t;
typedef struct {const char *name; uint32_t count; codol_structured_definition_t *definitions;} codol_structured_schema_t;
/* A non-NULL name selects a field/enum; otherwise index selects an array item. */
typedef struct {const char *name; int32_t index;} codol_structured_path_t;
typedef struct {
    codol_structured_type_t type;
    uint32_t logical_index,mapped_address;
} codol_structured_field_t;
/* Resolve a complete scalar path with C1's lookup arithmetic. Validates every
 * visited type and final storage extent; preserves out on failure. Enum-array
 * indices follow 0x61f270 directly. Nested scoreboard semantics remain under
 * investigation; no inferred multiplication by serialized byte stride. */
int CODOL_ResolveStructuredField(const codol_structured_definition_t *,
    const codol_structured_path_t *,size_t count,codol_structured_field_t *out);
/* C1's structured-data result codes, numbered as its message table at
 * 0xccfcd8. Anything this resolver rejects that C1 does not classify (an
 * invalid definition, or a path ending on a struct/array rather than a value)
 * reports the type mismatch code. The change/set and value-range codes belong
 * to the write path and are never produced by resolution. */
enum {
    CODOL_STRUCTURED_OK = 0,
    CODOL_STRUCTURED_TYPE = 1,
    CODOL_STRUCTURED_BOUNDS = 2,
    CODOL_STRUCTURED_NAME = 3,
    CODOL_STRUCTURED_ENUM = 4,
    CODOL_STRUCTURED_CHANGED = 5,
    CODOL_STRUCTURED_UNCHANGED = 6,
    CODOL_STRUCTURED_BYTE_RANGE = 8,
    CODOL_STRUCTURED_STRING_LENGTH = 9
};
const char *CODOL_StructuredStatusText(int status);
/* Same resolution, plus the code above for the first failing path element.
 * status may be NULL; it is written on success and failure alike. */
int CODOL_ResolveStructuredFieldStatus(const codol_structured_definition_t *,
    const codol_structured_path_t *,size_t count,codol_structured_field_t *out,int *status);
/* String (3) and named enum (4) storage. Read borrows record/schema text.
 * Write rejects unknown enum names and strings without room for a terminator;
 * a shorter string preserves bytes after its terminator, as C1 does. */
int CODOL_StructuredReadText(const codol_structured_definition_t *,
    const codol_structured_path_t *,size_t,const uint8_t *,size_t,const char **out);
int CODOL_StructuredWriteText(const codol_structured_definition_t *,
    const codol_structured_path_t *,size_t,uint8_t *,size_t,const char *value);
/* Owns record arrays; strings and offset maps borrow asset/resolver lifetimes.
 * Requires inline record arrays; packed string references use resolver.
 * Exact stream boundary required. This validates stream structure, not every
 * type graph or field storage range. out must be zero/prior; failure atomic. */
int CODOL_ReadStructuredSchema(const codol_asset_t *,const char *(*resolver)(void *,uint32_t),
    void *context,codol_structured_schema_t *out);
void CODOL_FreeStructuredSchema(codol_structured_schema_t *);
int CODOL_LoadMountedStructuredSchema(const char *,codol_structured_schema_t *);
#pragma pack(pop)
#endif
