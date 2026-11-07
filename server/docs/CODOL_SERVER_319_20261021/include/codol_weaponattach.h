#ifndef CODOL_WEAPONATTACH_H
#define CODOL_WEAPONATTACH_H
#include <stdbool.h>
#include <stdint.h>
#include "codol_weapondefs.h"
typedef struct { uint8_t type,index; uint16_t flags; uint16_t field_offset; uint32_t value; } codol_weaponattach_entry_t;
typedef struct { const char *name; int count; const codol_weaponattach_entry_t *entries; } codol_weaponattach_t;
extern const codol_weaponattach_t codol_weaponattach_scalar[];
extern const int codol_weaponattach_scalar_count;
const codol_weaponattach_t *codol_weaponattach_find(const char *name);
typedef struct { int applied; int skipped; } codol_weaponattach_result_t;
bool codol_weaponattach_apply_ex(codol_weapondef_t *def, const codol_weaponattach_t *attach,
                                codol_weaponattach_result_t *result);
bool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *attach);
#endif
