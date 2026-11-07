#include "codol_script_source.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static void write_file(const char *path,const char *data,size_t length)
{
    FILE *file=fopen(path,"wb"); assert(file);
    assert(fwrite(data,1,length,file)==length && !fclose(file));
}
int main(void)
{
    char root[]="/tmp/codol-source-XXXXXX",mp[256],overlay[256],native_overlay[256],common[256],variant[256],override[256];
    char *data=NULL; size_t length=0;
    assert(mkdtemp(root));
    snprintf(mp,sizeof(mp),"%s/mp",root); snprintf(overlay,sizeof(overlay),"%s/overlay",root);
    snprintf(native_overlay,sizeof(native_overlay),"%s/native",root);
    assert(!mkdir(mp,0700) && !mkdir(overlay,0700) && !mkdir(native_overlay,0700));
    snprintf(common,sizeof(common),"%s/test.gsc",root);
    snprintf(variant,sizeof(variant),"%s/mp/test.gsc",root);
    snprintf(override,sizeof(override),"%s/overlay/test.gsc",root);
    write_file(common,"common",6);
    assert(CODOL_ReadScriptSource(root,overlay,"test.gsc",&data,&length)==1 && length==6 && !strcmp(data,"common")); free(data);
    write_file(variant,"multiplayer",11);
    assert(CODOL_ReadScriptSource(root,overlay,"test.gsc",&data,&length)==1 && !strcmp(data,"multiplayer")); free(data);
    write_file(override,"overlay",7);
    assert(CODOL_ReadScriptSource(root,overlay,"test.gsc",&data,&length)==1 && !strcmp(data,"overlay")); free(data);
    {
        char native[256];
        snprintf(native,sizeof(native),"%s/test.gsc",native_overlay);
        write_file(native,"native",6);
        assert(CODOL_ReadScriptSourceWithNativeOverlay(root,overlay,native_overlay,
            "test.gsc",&data,&length)==1 && length==6 && !strcmp(data,"native"));
        free(data);
        write_file(native,"a\0b",3); data=(char *)1; length=99;
        assert(CODOL_ReadScriptSourceWithNativeOverlay(root,overlay,native_overlay,
            "test.gsc",&data,&length)==-1 && data==(char *)1 && length==99);
        write_file(native,"native",6);
        /* Per-asset-category root: <native_overlay>/<zone_type>/<name> wins over
         * <native_overlay>/<name>, so a zm or coop match compiles its own
         * gametype, callback and level scripts under the shared module names. */
        {
            char category[256],scoped[256];
            snprintf(category,sizeof(category),"%s/zm",native_overlay);
            assert(!mkdir(category,0700));
            snprintf(scoped,sizeof(scoped),"%s/test.gsc",category);
            /* No file yet: the category layer misses and the order is the
             * multiplayer one. */
            assert(CODOL_ReadScriptSourceWithNativeOverlayForZone(root,overlay,native_overlay,
                "zm","test.gsc",&data,&length)==1 && !strcmp(data,"native")); free(data);
            write_file(scoped,"zombies",7);
            assert(CODOL_ReadScriptSourceWithNativeOverlayForZone(root,overlay,native_overlay,
                "zm","test.gsc",&data,&length)==1 && !strcmp(data,"zombies")); free(data);
            /* Another category, and the no-category callers, never see it. */
            assert(CODOL_ReadScriptSourceWithNativeOverlayForZone(root,overlay,native_overlay,
                "coop","test.gsc",&data,&length)==1 && !strcmp(data,"native")); free(data);
            assert(CODOL_ReadScriptSourceWithNativeOverlay(root,overlay,native_overlay,
                "test.gsc",&data,&length)==1 && !strcmp(data,"native")); free(data);
            /* A category name that is not plain lowercase cannot build a path. */
            {
                const char *rejected[]={"","..","zm/","ZM","zm1"};
                for(unsigned i=0;i<sizeof(rejected)/sizeof(*rejected);++i) {
                    assert(CODOL_ReadScriptSourceWithNativeOverlayForZone(root,overlay,native_overlay,
                        rejected[i],"test.gsc",&data,&length)==1 && !strcmp(data,"native"));
                    free(data);
                }
            }
            assert(!unlink(scoped) && !rmdir(category));
        }
        assert(!unlink(native));
    }
    data=(char *)1; length=99; write_file(override,"a\0b",3);
    assert(CODOL_ReadScriptSource(root,overlay,"test.gsc",&data,&length)==-1 && data==(char *)1 && length==99);
    assert(CODOL_ReadScriptSource(root,overlay,"missing.gsc",&data,&length)==0 && data==(char *)1 && length==99);
    const char *bad[]={"../test.gsc","/test.gsc","a/../test.gsc","a\\test.gsc","C:test.gsc","a//test.gsc"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);++i)
        assert(CODOL_ReadScriptSource(root,overlay,bad[i],&data,&length)==-1 && data==(char *)1);
    assert(!unlink(override) && !unlink(variant) && !unlink(common));
    {
        char dir[256],exported[256],canonical[256];
        snprintf(dir,sizeof(dir),"%s/character",root);assert(!mkdir(dir,0700));
        snprintf(exported,sizeof(exported),"%s/character/charactermp_character_us_army_lmg.gsc",root);
        snprintf(canonical,sizeof(canonical),"%s/character/mp_character_us_army_lmg.gsc",root);
        write_file(exported,"export body",11);
        assert(CODOL_ReadScriptSource(root,overlay,"character/mp_character_us_army_lmg.gsc",&data,&length)==1);
        assert(!strcmp(data,"export body"));free(data);
        write_file(canonical,"canonical",9);
        assert(CODOL_ReadScriptSource(root,overlay,"character/mp_character_us_army_lmg.gsc",&data,&length)==1);
        assert(!strcmp(data,"canonical"));free(data);
        write_file(canonical,"a\0b",3);data=(char *)1;length=99;
        assert(CODOL_ReadScriptSource(root,overlay,"character/mp_character_us_army_lmg.gsc",&data,&length)==-1);
        assert(data==(char *)1 && length==99);
        assert(CODOL_ReadScriptSource(root,overlay,"character/mp_character_other.gsc",&data,&length)==0);
        assert(!unlink(canonical) && !unlink(exported));
        snprintf(exported,sizeof(exported),"%s/character/character_us_army_smg_b.gsc",root);
        write_file(exported,"smg body",8);
        assert(CODOL_ReadScriptSource(root,overlay,"character/mp_character_us_army_smg_b.gsc",&data,&length)==1);
        assert(!strcmp(data,"smg body"));free(data);
        assert(!unlink(exported) && !rmdir(dir));
    }
    {
        const char damaged[]="// THIS FILE IS AUTOGENERATED, DO NOT MODIFY\n\nmain().{..a[0] = \"head_militia_a_wht\";..return a;.}";
        char dir[256],file[256];size_t i;
        snprintf(dir,sizeof(dir),"%s/xmodelalias",root);assert(!mkdir(dir,0700));
        snprintf(file,sizeof(file),"%s/xmodelalias/alias_opforce_militia_heads_wht.gsc",root);
        write_file(file,damaged,sizeof(damaged)-1);
        assert(CODOL_ReadScriptSource(root,overlay,"xmodelalias/alias_opforce_militia_heads_wht.gsc",&data,&length)==1);
        assert(length==sizeof(damaged)-1);
        for(i=0;i<length;++i)assert(data[i]==(damaged[i]=='.' ? ' ' : damaged[i]));
        free(data);
        write_file(file,"main().{}",9);
        assert(CODOL_ReadScriptSource(root,overlay,"xmodelalias/alias_opforce_militia_heads_wht.gsc",&data,&length)==1);
        assert(!strcmp(data,"main().{}"));free(data);
        assert(!unlink(file) && !rmdir(dir));
    }
    assert(!rmdir(native_overlay) && !rmdir(overlay) && !rmdir(mp) && !rmdir(root));
    puts("PASS: native script roots, overlay precedence, binary rejection and atomic failure");
}
