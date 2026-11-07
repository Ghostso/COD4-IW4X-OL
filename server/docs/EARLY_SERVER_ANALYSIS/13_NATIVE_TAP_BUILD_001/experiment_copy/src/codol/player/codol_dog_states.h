#ifndef CODOL_DOG_STATES_H
#define CODOL_DOG_STATES_H
struct DObj_s;
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_DogStateIndex(const char *name);
/* Clip binding against the loaded C1 dog tree, cached per tree. `missing`
 * names the first clip the tree does not declare when binding fails. */
int CODOL_DogClipBindings(unsigned tree,const unsigned **refs,const char **missing);
void CODOL_DogClipBindingsReset(void);
/* Table introspection, for the offline mapping test and diagnostics. */
const char *CODOL_DogClipName(unsigned index);
unsigned CODOL_DogClipCount(void);
const char *CODOL_DogStateName(unsigned index);
unsigned CODOL_DogStateCount(void);
int CODOL_DogStateApply(struct DObj_s *,unsigned entity,unsigned generation,unsigned tree,unsigned time,
    int state,int previous,int entering,float rate,float lean,float aimUp,float aimLeft);
#ifdef __cplusplus
}
#endif
#endif
