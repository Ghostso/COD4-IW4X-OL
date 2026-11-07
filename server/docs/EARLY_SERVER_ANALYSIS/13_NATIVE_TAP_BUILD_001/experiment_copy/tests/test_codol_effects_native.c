#include "codol_effects_native.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put(uint8_t *p,uint32_t n) { memcpy(p,&n,4); }
int main(void)
{
    uint8_t records[3][260]={{0}},velocity[96]={7},samples[48]={9};
    char name[]="fx",sound[]="sound"; int material,model_a,model_b;
    const void *material_binding[]={&material},*model_bindings[]={&model_a,&model_b};
    codol_effect_visual_t visuals[4]={{0}};
    codol_effect_element_t elements[3]={{0}};
    codol_effect_source_t source={0}; codol_effect_bindings_t bindings[3]={{0}};
    FxEffectDef nested={0}; codol_native_effect_t native={0},saved; unsigned i;
    source.prefix.name=name; source.prefix.flags=1; source.prefix.total_size=12345;
    source.prefix.counts[1]=source.prefix.count=3; source.elements=elements;
    for(i=0;i<3;++i) { elements[i].record=records[i]; records[i][177]=1; put(records[i]+188,UINT32_MAX); }
    for(i=0;i<4;++i) visuals[i].reference=UINT32_MAX;
    elements[0].visual_count=1; elements[0].visuals=visuals;
    elements[0].velocity_count=elements[0].visual_sample_count=1;
    elements[0].velocity_samples=velocity; elements[0].visual_samples=samples;
    put(records[0]+180,UINT32_MAX); put(records[0]+184,UINT32_MAX); put(records[0]+216,UINT32_MAX);
    elements[0].effect_names[0]="nested"; bindings[0].effects[0]=&nested;
    bindings[0].visuals=material_binding; bindings[0].visual_count=1;
    records[1][176]=9; records[1][177]=2; elements[1].visual_count=2; elements[1].visuals=visuals+1;
    bindings[1].visuals=model_bindings; bindings[1].visual_count=2;
    records[2][176]=12; elements[2].visual_count=1; elements[2].visuals=visuals+3; visuals[3].string=sound;
    assert(CODOL_BuildNativeEffect(&source,bindings,&native)); saved=native;
    assert(native.effect->totalSize==(int)native.size && native.source_total_size==12345 && native.effect->elemDefCountOneShot==3);
    assert(!strcmp(native.effect->name,"fx") && native.effect->name!=name);
    assert(native.effect->elemDefs[0].elemType==0 && native.effect->elemDefs[1].elemType==5 && native.effect->elemDefs[2].elemType==8);
    assert(native.effect->elemDefs[0].visuals==&material && native.effect->elemDefs[0].effectRefs[0]==&nested);
    assert(((void **)native.effect->elemDefs[1].visuals)[1]==&model_b);
    assert(native.effect->elemDefs[0].velSamples!=velocity && ((uint8_t *)native.effect->elemDefs[0].velSamples)[0]==7);
    assert(native.effect->elemDefs[0].visSamples!=samples && ((uint8_t *)native.effect->elemDefs[0].visSamples)[0]==9);
    assert(native.effect->elemDefs[2].visuals!=sound && !strcmp(native.effect->elemDefs[2].visuals,"sound"));
    records[0][176]=6;
    assert(CODOL_BuildNativeEffect(&source,bindings,&native));
    assert(native.effect->elemDefs[0].elemType==4 && native.effect->elemDefs[0].visuals==&material);
    assert(native.effect->elemDefs[0].effectRefs[0]==&nested);
    assert(native.effect->elemDefs[0].velSamples!=velocity && ((uint8_t *)native.effect->elemDefs[0].velSamples)[0]==7);
    assert(native.effect->elemDefs[0].visSamples!=samples && ((uint8_t *)native.effect->elemDefs[0].visSamples)[0]==9);
    saved=native; put(records[0]+244,UINT32_MAX);
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    put(records[0]+244,0);
    records[0][176]=1;
    assert(CODOL_BuildNativeEffect(&source,bindings,&native));
    assert(native.effect->elemDefs[0].elemType==1 && native.effect->elemDefs[0].visuals==&material);
    assert(!memcmp(native.effect->elemDefs[0].velSamples,velocity,sizeof(velocity)));
    assert(!memcmp(native.effect->elemDefs[0].visSamples,samples,sizeof(samples)));
    assert(native.effect->elemDefs[0].effectRefs[0]==&nested);
    records[0][176]=3;
    assert(CODOL_BuildNativeEffect(&source,bindings,&native)); saved=native;
    assert(native.effect->elemDefs[0].elemType==2);
    assert(native.effect->elemDefs[0].visuals==&material);
    assert(!memcmp(native.effect->elemDefs[0].velSamples,velocity,sizeof(velocity)));
    assert(!memcmp(native.effect->elemDefs[0].visSamples,samples,sizeof(samples)));
    assert(native.effect->elemDefs[0].effectRefs[0]==&nested);
    bindings[0].visuals=NULL;
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(saved)));
    bindings[0].visuals=material_binding;
    put(records[0]+244,1);
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(saved)));
    put(records[0]+244,0);
    records[2][176]=8;
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    records[2][176]=12; put(records[2]+252,1);
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    put(records[2]+252,0); bindings[1].visual_count=1;
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    bindings[1].visual_count=2; bindings[0].effects[0]=NULL;
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    bindings[0].effects[0]=&nested; elements[0].velocity_count=2;
    assert(!CODOL_BuildNativeEffect(&source,bindings,&native) && !memcmp(&saved,&native,sizeof(native)));
    elements[0].velocity_count=1; name[0]='F'; sound[0]='S'; velocity[0]=1;
    assert(!strcmp(native.effect->name,"fx") && !strcmp(native.effect->elemDefs[2].visuals,"sound"));
    assert(((uint8_t *)native.effect->elemDefs[0].velSamples)[0]==7);
    assert(CODOL_BuildNativeEffect(&source,bindings,&native) && !strcmp(native.effect->name,"Fx"));
    CODOL_FreeNativeEffect(&native); CODOL_FreeNativeEffect(&native);
    {
        uint8_t record[260]={0}; codol_effect_element_t element={0};
        codol_effect_visual_t marks[4]={{0}}; const void *materials[4]={&material,NULL,&model_a,&model_b};
        codol_effect_bindings_t binding={materials,4,{0}};
        codol_effect_source_t decal={0}; unsigned count;
        record[176]=13; put(record+188,UINT32_MAX);
        for(i=0;i<4;++i) marks[i].reference=materials[i] ? UINT32_MAX : 0;
        element.record=record; element.visuals=marks;
        decal.prefix.name="decal"; decal.prefix.count=decal.prefix.counts[1]=1; decal.elements=&element;
        for(count=1;count<=2;++count) {
            record[177]=count; element.visual_count=binding.visual_count=2*count;
            assert(CODOL_BuildNativeEffect(&decal,&binding,&native)); saved=native;
            assert(native.effect->elemDefs[0].elemType==9 && native.effect->elemDefs[0].visualCount==count);
            assert(native.effect->elemDefs[0].visuals!=materials);
            assert(!memcmp(native.effect->elemDefs[0].visuals,materials,2*count*sizeof(void *)));
            --binding.visual_count;
            assert(!CODOL_BuildNativeEffect(&decal,&binding,&native) && !memcmp(&saved,&native,sizeof(saved)));
            ++binding.visual_count; materials[1]=&material;
            assert(!CODOL_BuildNativeEffect(&decal,&binding,&native) && !memcmp(&saved,&native,sizeof(saved)));
            materials[1]=NULL;
        }
        memset(marks,0,sizeof(marks)); memset(materials,0,sizeof(materials));
        assert(((const void **)native.effect->elemDefs[0].visuals)[2]==&model_a);
        put(record+188,0); element.visual_count=binding.visual_count=0;
        assert(CODOL_BuildNativeEffect(&decal,&binding,&native) && !native.effect->elemDefs[0].visuals);
        CODOL_FreeNativeEffect(&native);
    }
    {
        uint8_t record[260]={0}; codol_effect_element_t element={0};
        codol_effect_visual_t visuals[2]={{0}}; const void *targets[2]={NULL,NULL};
        codol_effect_bindings_t binding={targets,1,{0}}; codol_effect_source_t source={0};
        source.prefix.name="light-runner"; source.prefix.count=source.prefix.counts[1]=1; source.elements=&element;
        element.record=record; element.visual_count=1; element.visuals=visuals; record[176]=10;
        assert(CODOL_BuildNativeEffect(&source,&binding,&native)); saved=native;
        assert(native.effect->elemDefs[0].elemType==6 && !native.effect->elemDefs[0].visuals);
        put(record+188,1); visuals[0].reference=1; targets[0]=&nested;
        assert(!CODOL_BuildNativeEffect(&source,&binding,&native) && !memcmp(&saved,&native,sizeof(saved)));
        record[176]=14; record[177]=1; visuals[0].string="child";
        assert(CODOL_BuildNativeEffect(&source,&binding,&native));
        assert(native.effect->elemDefs[0].elemType==10 && native.effect->elemDefs[0].visuals==&nested);
        record[177]=2; element.visual_count=binding.visual_count=2;
        assert(CODOL_BuildNativeEffect(&source,&binding,&native)); saved=native;
        assert(((void **)native.effect->elemDefs[0].visuals)[0]==&nested && !((void **)native.effect->elemDefs[0].visuals)[1]);
        visuals[0].string=NULL;
        assert(!CODOL_BuildNativeEffect(&source,&binding,&native) && !memcmp(&saved,&native,sizeof(saved)));
        CODOL_FreeNativeEffect(&native);
    }
    puts("PASS: native FX layout, type translation, owned samples/strings and binding failures");
    return 0;
}
