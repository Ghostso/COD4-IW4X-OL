#ifndef CODOL_ZONE_PATH_H
#define CODOL_ZONE_PATH_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Name is an archive basename, without extension. Explicit directory overrides
 * the installation/language path. Output is unchanged on failure. */
int CODOL_ZoneFilePath(const char *base,const char *language,const char *directory,
                       const char *name,char *out,size_t capacity);
#ifdef __cplusplus
}
#endif
#endif
