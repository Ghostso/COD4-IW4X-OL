#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include <assert.h>
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static float argument, result[3], vectors[2][3];
static unsigned count, errors, outputs, object_type = VAR_ARRAY, child_type = VAR_VECTOR;
float Scr_GetFloat(unsigned i) { assert(i == 0); return argument; }
unsigned Scr_GetObject(unsigned i) { assert(i == 0); return 7; }
unsigned Scr_GetObjectType(unsigned id) { assert(id == 7); return object_type; }
unsigned FindFirstSibling(unsigned id) { assert(id == 7); return count ? 11 : 0; }
unsigned FindNextSibling(unsigned id) { assert(id == 11 || id == 29); return id == 11 && count == 2 ? 29 : 0; }
unsigned GetValueType(unsigned id) { assert(id == 11 || id == 29); return child_type; }
union VariableUnion *GetVariableValueAddress(unsigned id)
{
    static union VariableUnion value;
    assert(id == 11 || id == 29);
    value.vectorValue = vectors[id == 29]; return &value;
}
void Scr_Error(const char *s) { assert(s && *s); ++errors; }
void Scr_AddFloat(float f) { result[0] = f; ++outputs; }
void Scr_AddVector(const float *v) { memcpy(result, v, sizeof(result)); ++outputs; }
int main(void)
{
    const float inputs[] = {-720, -540, -181, -180, 0, 180, 181, 540, 720};
    const float expected[] = {0, 180, 179, 180, 0, 180, -179, 180, 0};
    for (unsigned i = 0; i < sizeof(inputs)/sizeof(*inputs); ++i) {
        argument = inputs[i]; CODOL_Scr_AngleClamp180(); assert(result[0] == expected[i]);
    }
    unsigned before = outputs;
    argument = INFINITY; CODOL_Scr_AngleClamp180();
    argument = NAN; CODOL_Scr_AngleClamp180(); assert(outputs == before && errors == 2);
    CODOL_Scr_AveragePoint(); assert(result[0] == 0 && result[1] == 0 && result[2] == 0);
    count = 2; vectors[0][0] = 2; vectors[1][1] = 2;
    CODOL_Scr_AveragePoint(); assert(result[0] == 1 && result[1] == 1 && result[2] == 0);
    CODOL_Scr_AverageNormal(); assert(fabsf(result[0] - 0.70710678f) < 0.000001f && result[0] == result[1]);
    vectors[0][0] = FLT_MAX; vectors[1][0] = FLT_MAX; vectors[1][1] = 0;
    CODOL_Scr_AveragePoint(); assert(result[0] == FLT_MAX);
    CODOL_Scr_AverageNormal(); assert(result[0] == 1 && result[1] == 0);
    vectors[1][0] = -FLT_MAX;
    CODOL_Scr_AverageNormal(); assert(result[0] == 0 && result[1] == 0);
    before = outputs; vectors[0][0] = NAN;
    CODOL_Scr_AveragePoint(); child_type = VAR_INTEGER;
    CODOL_Scr_AveragePoint(); object_type = VAR_OBJECT;
    CODOL_Scr_AveragePoint(); assert(outputs == before && errors == 5);
    puts("PASS: native vector averages, sparse child iteration, large/cancelling vectors, angle boundaries and invalid input");
}
