#include "codol_character_variant.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    const char *cells[]={"part","model","m tf urb","part_tf_m_00",
                         "PART","model","f sc des","part_sc_f_wht"};
    codol_engine_table_t parts={"parts",4,2,cells};int allowed=99;
    assert(CODOL_CharacterSlot7Allowed(&parts,"part",&allowed) && allowed==1);
    cells[7]="part_sc_f_99";
    assert(CODOL_CharacterSlot7Allowed(&parts,"part",&allowed) && allowed==0);
    cells[7]="part_sc_f_";
    assert(CODOL_CharacterSlot7Allowed(&parts,"part",&allowed) && allowed==1);
    cells[7]="part";
    assert(CODOL_CharacterSlot7Allowed(&parts,"part",&allowed) && allowed==0);
    assert(CODOL_CharacterSlot7Allowed(&parts,"missing",&allowed) && allowed==0);
    cells[7]=NULL;allowed=99;
    assert(!CODOL_CharacterSlot7Allowed(&parts,"part",&allowed) && allowed==99);
    puts("PASS: C1 raw-row visibility, numeric suffix, exact-length terminator and malformed data");
}
