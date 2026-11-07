#ifndef CODOL_MAP_CUSTOM_H
#define CODOL_MAP_CUSTOM_H
#include <stddef.h>
/* Query brace-delimited arena key/value records. 1=found, 0=absent,
 * -1=invalid. Bounded output is only changed for a found value. */
int CODOL_MapCustom(const char *data,size_t size,const char *map,const char *key,char *out,size_t capacity);
#endif
