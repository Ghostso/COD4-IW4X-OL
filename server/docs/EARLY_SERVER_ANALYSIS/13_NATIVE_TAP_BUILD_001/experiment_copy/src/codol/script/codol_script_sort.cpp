#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "cscr_variable.h"
#include "cscr_stringlist.h"
#include <cmath>
#include <cstdlib>
/* Existing retained field evaluator supports both script structs and entities. */
extern "C" VariableValue Scr_FindVariableField(unsigned int parent,unsigned int name);
static VariableValue read_origin(unsigned object,unsigned name)
{
    /* GetEntityFieldValue uses the VM evaluation stack and requires zero
     * input/output counts. A builtin still owns its arguments here; preserve
     * that frame rather than clearing or releasing the caller's array. */
    VariableValue *top=gScrVmPub.top;
    unsigned in=gScrVmPub.inparamcount,out=gScrVmPub.outparamcount;
    gScrVmPub.inparamcount=0;gScrVmPub.outparamcount=0;
    VariableValue result=Scr_FindVariableField(object,name);
    gScrVmPub.top=top;gScrVmPub.inparamcount=in;gScrVmPub.outparamcount=out;
    return result;
}
struct distance_entry {unsigned object,order;float distance;};
static int compare_distance(const void *a,const void *b)
{
    const distance_entry *x=(const distance_entry *)a,*y=(const distance_entry *)b;
    if(x->distance<y->distance)return -1;
    if(x->distance>y->distance)return 1;
    return x->order<y->order ? -1:x->order>y->order;
}
extern "C" void CODOL_Scr_SortByDistance(void)
{
    distance_entry entries[2048];float origin[3];unsigned count=0;
    unsigned array=Scr_GetObject(0),name;const char *error=NULL;
    if(Scr_GetObjectType(array)!=VAR_ARRAY){Scr_Error("sortByDistance requires an array");return;}
    if(GetArraySize(array)>2048){Scr_Error("sortByDistance exceeds 2048 objects");return;}
    Scr_GetVector(1,origin);
    for(unsigned k=0;k<3;++k)if(!std::isfinite(origin[k])) {
        Scr_Error("sortByDistance requires a finite origin");return;
    }
    name=SL_GetCanonicalString("origin");
    for(unsigned child=FindFirstSibling(array);child;child=FindNextSibling(child)) {
        unsigned object,type;VariableValue value;float delta[3],distance=0;
        if(count==2048 || GetValueType(child)!=VAR_POINTER) {error="sortByDistance requires object entries";break;}
        object=GetVariableValueAddress(child)->pointerValue;type=Scr_GetObjectType(object);
        if(type!=VAR_OBJECT && type!=VAR_ENTITY && type!=VAR_DEAD_ENTITY) {error="sortByDistance entry cannot have an origin";break;}
        value=read_origin(object,name);
        if(value.type!=VAR_VECTOR)error="sortByDistance entry has no vector origin";
        else for(unsigned k=0;k<3;++k) {
            if(!std::isfinite(value.u.vectorValue[k]))error="sortByDistance entry has a nonfinite origin";
            delta[k]=origin[k]-value.u.vectorValue[k];
            distance+=delta[k]*delta[k];
        }
        RemoveRefToValue(value.type,value.u);
        if(error)break;
        entries[count]={object,count,distance};++count;
    }
    if(error){Scr_Error(error);return;}
    /* IW4 compares squared float distances; tie ordering is unspecified there.
     * Preserve traversal order for equal distances here. Input stays untouched. */
    qsort(entries,count,sizeof(entries[0]),compare_distance);
    Scr_MakeArray();
    for(unsigned i=0;i<count;++i){Scr_AddObject(entries[i].object);Scr_AddArray();}
}
#endif
