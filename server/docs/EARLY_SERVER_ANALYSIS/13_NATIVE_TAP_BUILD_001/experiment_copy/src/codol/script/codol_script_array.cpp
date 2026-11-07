#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "cscr_variable.h"

extern "C" VariableValue Scr_GetArrayIndexValue(unsigned int name);

static unsigned array_argument(unsigned index = 0)
{
    unsigned object = Scr_GetObject(index);
    if (Scr_GetObjectType(object) != VAR_ARRAY) {
        Scr_ParamError(index, "parameter must be an array"); return 0;
    }
    return object;
}

/* Decode the retained VM's key representation; do not import IW4's
 * string/object index boundaries into the IW3 variable allocator. */
static void add_key(unsigned child)
{
    if (!child) { Scr_AddUndefined(); return; }
    VariableValue key = Scr_GetArrayIndexValue(GetVariableName(child));
    switch (key.type) {
    case VAR_STRING: Scr_AddConstString(key.u.stringValue); break;
    case VAR_INTEGER: Scr_AddInt(key.u.intValue); break;
    case VAR_POINTER: Scr_AddObject(key.u.pointerValue); break;
    default: Scr_Error("invalid native array key"); break;
    }
}

/* IW4 5f4e00 -> 44b0d0: first sibling key, undefined for an empty array. */
extern "C" void CODOL_Scr_GetFirstArrayKey(void)
{
    unsigned object = array_argument();
    if (object) add_key(FindFirstSibling(object));
}

/* IW4 5f4e40 -> 4a02d0 -> 61c440 accepts integer/string lookup keys,
 * reports a missing key, and returns undefined after the final sibling. */
extern "C" void CODOL_Scr_GetNextArrayKey(void)
{
    unsigned object = array_argument(), child = 0;
    if (!object) return;
    switch (Scr_GetType(1)) {
    case VAR_INTEGER: {
        int key = Scr_GetInt(1);
        if (!IsValidArrayIndex(key)) {
            Scr_ParamError(1, "array index out of range"); return;
        }
        child = FindArrayVariable(object, key);
        break;
    }
    case VAR_STRING:
        child = FindVariable(object, (unsigned short)Scr_GetConstString(1));
        break;
    default:
        Scr_ParamError(1, "array key must be an integer or string"); return;
    }
    if (!child) { Scr_ParamError(1, "key does not exist in array"); return; }
    add_key(FindNextSibling(child));
}

/* T5 65f940, with point extraction at 642ea0. Both inputs are dense,
 * zero-indexed arrays. Validate/copy inputs before publishing any result. */
extern "C" void CODOL_Scr_Matrix4x4TransformPoints(void)
{
    float matrix[16], points[128][3];
    unsigned object = array_argument(0), count, child;
    if (!object) return;
    if (GetArraySize(object) != 16) {
        Scr_ParamError(0, "matrix must contain exactly 16 numbers"); return;
    }
    for (unsigned i = 0; i < 16; ++i) {
        child = FindArrayVariable(object, i);
        if (!child) { Scr_ParamError(0, "matrix indices must be 0 through 15"); return; }
        VariableUnion *value = GetVariableValueAddress(child);
        switch (GetValueType(child)) {
        case VAR_FLOAT: matrix[i] = value->floatValue; break;
        case VAR_INTEGER: matrix[i] = (float)value->intValue; break;
        default: Scr_ParamError(0, "matrix entries must be numbers"); return;
        }
    }
    object = array_argument(1);
    if (!object) return;
    count = GetArraySize(object);
    if (count > 128) { Scr_ParamError(1, "at most 128 points may be transformed"); return; }
    for (unsigned i = 0; i < count; ++i) {
        child = FindArrayVariable(object, i);
        if (!child || GetValueType(child) != VAR_VECTOR) {
            Scr_ParamError(1, "points must be a dense array of vectors"); return;
        }
        const float *point = GetVariableValueAddress(child)->vectorValue;
        for (unsigned axis = 0; axis < 3; ++axis) points[i][axis] = point[axis];
    }
    Scr_MakeArray();
    for (unsigned i = 0; i < count; ++i) {
        float result[3];
        for (unsigned axis = 0; axis < 3; ++axis) {
            /* This mixed indexing is deliberate: T5 uses 0/4/8 + 3,
             * 1/5/9 + 7, and 2/6/10 + 11. No perspective division. */
            result[axis] = points[i][0] * matrix[axis] +
                           points[i][1] * matrix[axis + 4] +
                           points[i][2] * matrix[axis + 8] + matrix[axis * 4 + 3];
        }
        Scr_AddVector(result);
        Scr_AddArray();
    }
}
#endif
