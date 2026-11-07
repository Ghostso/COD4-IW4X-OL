#include "codol_weapon_compose.h"
#include "codol_weapon_attachment.h"
#include "codol_xmodel_native.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ATTACHMENT_TABLE "mp/coWeaponAttachmentTable.csv"
#define MARKETPLACE_TABLE "mp/coMarketplaceItems.csv"
/* The three recipe tables C1's BG_CustomWeapon_LoadModelsAndTags (0x420320)
 * reads, in the spelling the zone stores them under. Table lookup is
 * case-insensitive and treats '\' as '/', so the case here is cosmetic.
 *   mp/coweapmodels/<weapon>.csv  4 cols: weapon, camoId, world, view
 *   mp/coweapitems/<group>.csv    6 cols: item, weapon, camoId, world, view, TAG
 *   mp/coweapitemswea.csv         per-weapon declared default slots */
#define BASE_MODEL_TABLE "mp/coweapmodels/%s.csv"
#define ITEM_MODEL_TABLE "mp/coweapitems/%s.csv"
#define CAMO_TABLE "mp/coweapitems/cam.csv"
#define DEFAULTS_TABLE "mp/coweapitemswea.csv"
/* C1 parses the name with Com_ParseString/Com_ParseInt, which treat any run of
 * whitespace as one separator. Numbers are plain decimal; the flag and each
 * variant are stored as bytes (0x4215f8, 0x421651). Two measured bounds apply
 * to the record C1 builds from the name: the name is copied into a 0x80-byte
 * field (0x4216a6) and the tag into a 0x10-byte field (0x4216d4). */
static int is_space(char c)
{ return c==' ' || c=='\t' || c=='\n' || c=='\r' || c=='\v' || c=='\f'; }
static const char *skip_spaces(const char *p)
{ while(is_space(*p))++p; return p; }
/* A whole decimal token: at least one digit, no sign, no radix prefix, within
 * the field's stored width, and terminated by whitespace or the end of the
 * name. "12x", "1+2" and a number run together with the next field are
 * rejected here instead of being accepted as their leading digits. */
static int parse_uint(const char **p,unsigned limit,unsigned *out)
{
    const char *s=skip_spaces(*p);unsigned value=0,digits=0;
    while(*s>='0' && *s<='9') {
        if(value>(0xffffffffu-(unsigned)(*s-'0'))/10u)return 0;
        value=value*10u+(unsigned)(*s-'0');
        ++s;++digits;
    }
    if(!digits || value>limit)return 0;
    if(*s && !is_space(*s))return 0;
    *p=s;*out=value;return 1;
}
/* The single spelling this producer emits and caches by: '*', tag, then each
 * number separated by one space. C1 accepts other spacings of the same fields,
 * and they resolve to this same weapon because the cache is keyed by this
 * rendering. No reordering, no deduplication and no other rewriting is done:
 * the accepted item/variant pairs keep the order the name gave them, which is
 * the order C1 stores them in (+0xc94/+0xd5c) and applies them in. */
static int render_canonical(const codol_composed_weapon_t *r,char *out,size_t size)
{
    unsigned i;int written;size_t offset;
    written=snprintf(out,size,"*%s %u %u",r->tag,r->base,r->flag);
    if(written<0 || (size_t)written>=size)return 0;
    offset=(size_t)written;
    for(i=0;i<r->count;++i) {
        written=snprintf(out+offset,size-offset," %u %u",r->items[i],r->variants[i]);
        if(written<0 || (size_t)written>=size-offset)return 0;
        offset+=(size_t)written;
    }
    return 1;
}
int CODOL_ParseComposedWeaponName(const char *name,codol_composed_weapon_t *out)
{
    codol_composed_weapon_t next;const char *p;size_t n;
    if(!name || !out)return -1;
    if(name[0]!='*')return 0;
    for(n=0;name[n];++n)if(n>=CODOL_COMPOSED_NAME_SIZE)return -1;
    memset(&next,0,sizeof(next));
    p=skip_spaces(name+1);
    for(n=0;p[n] && !is_space(p[n]);++n)
        if(n+1>=CODOL_COMPOSED_TAG_SIZE)return -1;
    if(!n)return -1;
    memcpy(next.tag,p,n);next.tag[n]=0;p+=n;
    if(!parse_uint(&p,0xffffu,&next.base) || !next.base)return -1;
    if(!parse_uint(&p,0xffu,&next.flag))return -1;
    for(;;) {
        unsigned item,variant;
        p=skip_spaces(p);
        if(!*p)break;
        if(next.count>=CODOL_COMPOSED_ATTACHMENTS)return -1;
        if(!parse_uint(&p,0xffffu,&item) || !item)return -1;
        /* C1 reads the variant with the same parser; a pair without one is a
         * malformed name here rather than a silent zero. */
        if(!parse_uint(&p,0xffu,&variant))return -1;
        next.items[next.count]=item;next.variants[next.count]=variant;++next.count;
    }
    if(!render_canonical(&next,next.canonical,sizeof(next.canonical)))return -1;
    *out=next;return 1;
}
int CODOL_CanonicalComposedWeaponName(const char *name,char *out,size_t size)
{
    codol_composed_weapon_t record;int status;size_t n;
    if(!out || !size)return -1;
    status=CODOL_ParseComposedWeaponName(name,&record);
    if(status!=1)return status;
    n=strlen(record.canonical)+1;
    if(n>size)return -1;
    memcpy(out,record.canonical,n);
    return 1;
}
/* Table order is only the fallback. The authoritative index -> name mapping is
 * the published registry: CODOL_InitializeServerWeaponConfigstrings walks the
 * same table but register_stock also registers each definition's partner names
 * (+0xb78/+0xb88) recursively, so a name's slot can differ from its ordinal in
 * the table. A client resolves a composed base index against the weapons it
 * holds, which are the slots the server published, so the registry wins
 * whenever it is up. */
int CODOL_ComposedWeaponBaseName(unsigned index,const char **name)
{
    const codol_engine_table_t *table=NULL;int r,q;unsigned next=2;
    if(!name)return -1;
#ifdef CODOL_SERVER
    {
        const char *registered=NULL;
        const codol_weapon_registry_t *registry=CODOL_ServerWeaponRegistry();
        if(CODOL_RegisteredWeaponName(registry,index,&registered)==1) {
            *name=registered;return 1;
        }
        if(registry) return 0;
    }
#endif
    if(!index){*name="none";return 1;}
    if(index==1){*name="defaultweapon_mp";return 1;}
    if(CODOL_LoadEngineStringTable(ATTACHMENT_TABLE,&table)!=1)return -1;
    if(!table || table->rowCount<0 || table->columnCount<1 ||
       (table->rowCount && !table->values))return -1;
    for(r=0;r<table->rowCount;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        int seen=0;
        if(!cells[0] || !*cells[0])continue;
        if(r) {
            const char *const *before=table->values+(size_t)(r-1)*table->columnCount;
            if(before[0] && *before[0] && !strcmp(before[0],cells[0]))continue;
        }
        for(q=0;q<r-1 && !seen;++q) {
            const char *const *earlier=table->values+(size_t)q*table->columnCount;
            seen=earlier[0] && *earlier[0] && !strcmp(earlier[0],cells[0]);
        }
        if(seen)continue;
        if(next==index){*name=cells[0];return 1;}
        ++next;
    }
    return 0;
}
/* The marketplace, bounded to the four columns every caller here reads:
 * 0 id, 1 name, 2 type, 3 group. */
static int marketplace(const codol_engine_table_t **out)
{
    const codol_engine_table_t *market=NULL;
    if(CODOL_LoadEngineStringTable(MARKETPLACE_TABLE,&market)!=1)return -1;
    if(!market || market->rowCount<0 || market->columnCount<4 ||
       (market->rowCount && !market->values))return -1;
    *out=market;return 1;
}
/* Immutable mounted-table indexes. Archive replacement/unmount clears these
 * even when no composed definition was built. Table identity is checked too,
 * so a newly resolved table never inherits an earlier table's row answers. */
typedef struct {
    const char *name,*group;
    unsigned ordinal;
} compose_market_name_t;
static const codol_engine_table_t *indexed_market;
static const char *const **market_ordinals;
static compose_market_name_t *market_names;
static unsigned market_ordinal_count,market_name_count;
#define COMPOSE_MODEL_CACHE_SIZE 256u
typedef struct {
    const codol_engine_table_t *table;
    unsigned camo;
    int row;
    char base[128],item[128];
} compose_model_cache_t;
static compose_model_cache_t model_cache[COMPOSE_MODEL_CACHE_SIZE];
static void reset_lookup_indexes(void)
{
    free(market_ordinals);free(market_names);
    market_ordinals=NULL;market_names=NULL;indexed_market=NULL;
    market_ordinal_count=market_name_count=0;
    memset(model_cache,0,sizeof(model_cache));
}
static int compare_market_names(const void *left,const void *right)
{
    const compose_market_name_t *a=left,*b=right;
    int order=strcmp(a->name,b->name);
    return order ? order : (a->ordinal>b->ordinal)-(a->ordinal<b->ordinal);
}
static int index_marketplace(const codol_engine_table_t *table)
{
    const char *const **ordinals;
    compose_market_name_t *names;
    unsigned n=0,k=0,named_ordinal=0;
    int row;
    if(indexed_market==table)return 1;
    if((size_t)table->rowCount>(size_t)-1/sizeof(*ordinals) ||
       (size_t)table->rowCount>(size_t)-1/sizeof(*names))return 0;
    ordinals=table->rowCount ? malloc((size_t)table->rowCount*sizeof(*ordinals)) : NULL;
    names=table->rowCount ? malloc((size_t)table->rowCount*sizeof(*names)) : NULL;
    if(table->rowCount && (!ordinals || !names)) {free(ordinals);free(names);return 0;}
    for(row=0;row<table->rowCount;++row) {
        const char *const *cells=table->values+(size_t)row*table->columnCount;
        if(!cells[2] || strcmp(cells[2],"wat"))continue;
        ordinals[n++]=cells;
        /* Keep the existing reverse API's treatment of null names exactly. */
        if(!cells[1])continue;
        ++named_ordinal;
        names[k++]=(compose_market_name_t){cells[1],cells[3] ? cells[3] : "",named_ordinal};
    }
    if(k>1)qsort(names,k,sizeof(*names),compare_market_names);
    free(market_ordinals);free(market_names);
    market_ordinals=ordinals;market_names=names;
    market_ordinal_count=n;market_name_count=k;indexed_market=table;
    return 1;
}
static compose_model_cache_t *model_cache_slot(const char *base,const char *item,unsigned camo)
{
    const unsigned char *p;unsigned hash=2166136261u;
    if(strlen(base)>=sizeof(model_cache[0].base) ||
       strlen(item)>=sizeof(model_cache[0].item))return NULL;
    for(p=(const unsigned char *)base;*p;++p)hash=(hash^*p)*16777619u;
    hash=(hash^0xffu)*16777619u;
    for(p=(const unsigned char *)item;*p;++p)hash=(hash^*p)*16777619u;
    return model_cache+((hash^camo)&(COMPOSE_MODEL_CACHE_SIZE-1));
}
int CODOL_ComposedAttachmentItem(unsigned index,const char **name,const char **group)
{
    const codol_engine_table_t *market=NULL;int r,status;unsigned ordinal=0;
    if(!index)return 0;
    status=marketplace(&market);if(status!=1)return status;
    if(index_marketplace(market)) {
        const char *const *cells;
        if(index>market_ordinal_count)return 0;
        cells=market_ordinals[index-1];
        if(!cells[1] || !*cells[1])return 0;
        if(name)*name=cells[1];
        if(group)*group=cells[3] ? cells[3] : "";
        return 1;
    }
    /* C1 numbers the attachment items by their position among the "wat" rows,
     * starting at one (0x41fa2e, 0x41fac0..0x41fb3d). */
    for(r=0;r<market->rowCount;++r) {
        const char *const *cells=market->values+(size_t)r*market->columnCount;
        if(!cells[2] || !*cells[2] || strcmp(cells[2],"wat"))continue;
        if(++ordinal!=index)continue;
        if(!cells[1] || !*cells[1])return 0;
        if(name)*name=cells[1];
        if(group)*group=cells[3] ? cells[3] : "";
        return 1;
    }
    return 0;
}
int CODOL_ComposedAttachmentItemName(unsigned index,const char **out)
{
    if(!out)return 0;
    return CODOL_ComposedAttachmentItem(index,out,NULL);
}
int CODOL_ComposedAttachmentItemIndex(const char *name,unsigned *index,const char **group)
{
    const codol_engine_table_t *market=NULL;int r,status;
    unsigned ordinal=0,resolved=0;const char *found=NULL;
    if(!name || !*name || !index)return 0;
    status=marketplace(&market);if(status!=1)return status;
    if(index_marketplace(market)) {
        unsigned lo=0,hi=market_name_count;
        /* upper_bound picks the final duplicate, preserving C1's last row. */
        while(lo<hi) {
            unsigned mid=lo+(hi-lo)/2;
            if(strcmp(market_names[mid].name,name)<=0)lo=mid+1;
            else hi=mid;
        }
        if(!lo || strcmp(market_names[lo-1].name,name))return 0;
        *index=market_names[lo-1].ordinal;
        if(group)*group=market_names[lo-1].group;
        return 1;
    }
    /* The same "wat" numbering read the other way round. C1's marketplace
     * lookups take the last matching row, so a name repeated across rows
     * resolves to its last one here too. */
    for(r=0;r<market->rowCount;++r) {
        const char *const *cells=market->values+(size_t)r*market->columnCount;
        if(!cells[1] || !cells[2] || !*cells[2] || strcmp(cells[2],"wat"))continue;
        ++ordinal;
        if(strcmp(cells[1],name))continue;
        resolved=ordinal;found=cells[3] ? cells[3] : "";
    }
    if(!resolved)return 0;
    *index=resolved;if(group)*group=found;
    return 1;
}
int CODOL_ComposedAttachmentGroup(const char *name,const char **group)
{
    unsigned index;
    return CODOL_ComposedAttachmentItemIndex(name,&index,group);
}
int CODOL_ComposedAttachmentVariant(const char *base_name,const char *item_name,unsigned *variant)
{
    const codol_engine_table_t *table=NULL;int r;
    if(!base_name || !*base_name || !item_name || !*item_name || !variant)return 0;
    if(CODOL_LoadEngineStringTable(ATTACHMENT_TABLE,&table)!=1)return -1;
    if(!table || table->rowCount<0 || table->columnCount<4 ||
       (table->rowCount && !table->values))return -1;
    /* Column 3 of the (weapon, item) row is the pair's <variant> byte, and the
     * presence of the row is the legality test: bg_attachIdx is only filled
     * for pairs this table lists (0x41fb59..0x41fc96), so an item with no row
     * here resolves to nothing on the client no matter what the name says. */
    for(r=0;r<table->rowCount;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        const char *value;unsigned parsed;
        if(!cells[0] || !cells[1] || strcmp(cells[0],base_name) ||
           strcmp(cells[1],item_name))continue;
        value=cells[3];
        if(!value || !*value){*variant=0;return 1;}
        parsed=0;
        for(;*value;++value) {
            if(*value<'0' || *value>'9')return 0;
            parsed=parsed*10u+(unsigned)(*value-'0');
            if(parsed>0xffu)return 0;
        }
        *variant=parsed;return 1;
    }
    return 0;
}
/* A recipe table named after one weapon or one item group. Both spellings are
 * built here so a group/weapon name from the mounted marketplace can never
 * overrun the buffer or escape the directory it belongs to. */
static int recipe_table(const char *format,const char *key,const codol_engine_table_t **out)
{
    char path[96];int written;const char *p;
    if(!key || !*key)return 0;
    for(p=key;*p;++p)
        if(*p=='/' || *p=='\\' || *p=='.' || *p<' ')return 0;
    written=snprintf(path,sizeof(path),format,key);
    if(written<0 || (size_t)written>=sizeof(path))return 0;
    return CODOL_LoadEngineStringTable(path,out);
}
int CODOL_ComposedBaseModelRow(const char *base_name,unsigned camo,
    const char **world,const char **view)
{
    const codol_engine_table_t *table=NULL;char key[8];int r,status;
    status=recipe_table(BASE_MODEL_TABLE,base_name,&table);
    /* No table for this weapon at all means "cannot check", which is what the
     * camo lift below needs to tell apart from "the row is not there". */
    if(status!=1 || !table || table->columnCount<4 || table->rowCount<0 ||
       (table->rowCount && !table->values))return -1;
    snprintf(key,sizeof(key),"%u",camo);
    for(r=0;r<table->rowCount;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        if(!cells[1] || strcmp(cells[1],key))continue;
        if(cells[0] && *cells[0] && strcmp(cells[0],base_name))continue;
        if(world)*world=cells[2];
        if(view)*view=cells[3];
        return 1;
    }
    return 0;
}
int CODOL_ComposedItemModelRow(const char *base_name,const char *item_name,
    const char *group,unsigned camo,const char **world,const char **view,const char **tag)
{
    const codol_engine_table_t *table=NULL;char key[8];int r,status,fallback=-1;
    compose_model_cache_t *cached;
    if(!base_name || !*base_name || !item_name || !*item_name)return 0;
    status=recipe_table(ITEM_MODEL_TABLE,group,&table);
    if(status!=1)return status;
    if(!table || table->rowCount<0 ||
       (table->rowCount && !table->values))return -1;
    /* A group table narrower than the six-column merge layout merges nothing.
     * cam.csv is the three-column camo-id table (the camo visual comes from
     * the composed header flag), and rof.csv ships two columns (item, weapon):
     * rof_akimbo on deserteagle/m9/usp/magnumncm/ranger. C1 does not reject
     * either: BG_CustomWeapon_LoadModelsAndTags (0x420320) reads columns 3, 4
     * and 5 through StringTable_GetColumnValueForRow (0x61ee90), which answers
     * "" for a column at or past columnCount (0x61ee9c jge 0x61ef07), so both
     * model cells are empty and the pair is skipped at 0x420502..0x420508.
     * The akimbo gun itself comes from the pair's weaponattach asset
     * (akimbo_de, akimbo_m9, ...), not from a model row. */
    if(table->columnCount<6)return 0;
    cached=model_cache_slot(base_name,item_name,camo);
    if(cached && cached->table==table && cached->camo==camo &&
       !strcmp(cached->base,base_name) && !strcmp(cached->item,item_name)) {
        fallback=cached->row;
        goto resolved_model_row;
    }
    snprintf(key,sizeof(key),"%u",camo);
    /* The client's row match (0x728060) is a scored best match, not an exact
     * one, and camo 0 is the universal fallback: most parts ship a row only
     * for camo 0 and it wins whenever the asked-for camo has none. */
    /* C1 calls 0x728060 with reverse=1 at 0x420484. Its strict
     * score comparison at 0x728416 retains the later row on a tie. */
    for(r=table->rowCount-1;r>=0;--r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        if(!cells[0] || !cells[1] || !cells[2] ||
           strcmp(cells[0],item_name) || strcmp(cells[1],base_name))continue;
        if(!strcmp(cells[2],key)) {
            fallback=r;
            break;
        }
        if(fallback<0 && !strcmp(cells[2],"0"))fallback=r;
    }
    if(cached) {
        cached->table=table;cached->camo=camo;cached->row=fallback;
        strcpy(cached->base,base_name);strcpy(cached->item,item_name);
    }
resolved_model_row:
    if(fallback<0)return 0;
    {
        const char *const *cells=table->values+(size_t)fallback*table->columnCount;
        if(world)*world=cells[3];
        if(view)*view=cells[4];
        if(tag)*tag=cells[5];
    }
    return 1;
}
int CODOL_ComposedAttachmentTag(const char *base_name,const char *item_name,
    const char *group,const char **tag)
{
    const char *found=NULL;int status;
    /* The tag is measured camo-invariant across every (weapon, item) pair the
     * recipe carries, so camo 0 with its own fallback answers for all of them.
     * An item with no row, or a row with no tag, merges nothing and can never
     * collide: every cam_* item is in that class, as are sco_none, hbs_normal
     * and gps_default. */
    status=CODOL_ComposedItemModelRow(base_name,item_name,group,0,NULL,NULL,&found);
    if(status!=1)return status;
    if(!found || !*found)return 0;
    if(tag)*tag=found;
    return 1;
}
int CODOL_ComposedLegalDefaultReplacement(const char *base_name,const char *group,
    const char **item,unsigned *index,unsigned *variant)
{
    const codol_engine_table_t *table=NULL;
    const char *best=NULL;unsigned best_index=0,best_variant=0;int best_score=-1;
    int r,status;
    if(!base_name || !*base_name || !group || !*group || !item || !index || !variant)return 0;
    status=CODOL_LoadEngineStringTable(ATTACHMENT_TABLE,&table);
    if(status!=1)return status;
    if(!table || table->rowCount<0 || table->columnCount<4 ||
       (table->rowCount && !table->values))return -1;
    for(r=0;r<table->rowCount;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        const char *candidate_group=NULL,*world=NULL,*view=NULL,*tag=NULL;
        unsigned candidate_index,candidate_variant;int score,model;
        if(!cells[0] || !cells[1] || strcmp(cells[0],base_name) || !*cells[1])continue;
        if(CODOL_ComposedAttachmentItemIndex(cells[1],&candidate_index,&candidate_group)!=1 ||
           !candidate_group || strcmp(candidate_group,group))continue;
        if(CODOL_ComposedAttachmentVariant(base_name,cells[1],&candidate_variant)!=1)continue;
        model=CODOL_ComposedItemModelRow(base_name,cells[1],candidate_group,0,&world,&view,&tag);
        if(model<0)return -1;
        if(model!=1 || ((!world || !*world) && (!view || !*view)))continue;
        /* Prefer the neutral/default variant, then names explicitly marked as
         * defaults. Stable table order breaks ties exactly as the client data
         * presents them. */
        score=(candidate_variant==0 ? 16 : 0) +
              (strstr(cells[1],"default") ? 8 : 0) +
              (tag && *tag ? 4 : 0) +
              (!strncmp(cells[1],group,strlen(group)) ? 2 : 0);
        if(score<=best_score)continue;
        best_score=score;best=cells[1];best_index=candidate_index;best_variant=candidate_variant;
    }
    if(!best)return 0;
    *item=best;*index=best_index;*variant=best_variant;return 1;
}
int CODOL_ComposedCamoId(const char *base_name,const char *cam_item,int variant,
    unsigned *camo,codol_camo_source_t *source)
{
    const codol_engine_table_t *table=NULL;int r,status;
    unsigned resolved=0,global=0;int have=0,have_global=0;
    codol_camo_source_t from=CODOL_CAMO_NONE;
    if(!camo || !base_name || !*base_name || !cam_item || !*cam_item)return 0;
    status=CODOL_LoadEngineStringTable(CAMO_TABLE,&table);
    if(status<0)return -1;
    if(status==1 && (!table || table->columnCount<3 || table->rowCount<0 ||
       (table->rowCount && !table->values)))return -1;
    /* mp/coweapitems/cam.csv is the table the client itself scores every cam_*
     * pair against, and its column 2 is the coweapmodels row space. The pair's
     * coWeaponAttachmentTable column 3 is a different number - a write-only
     * variant byte, zero for every premium camo - and is only the last resort
     * for an item this table does not list at all. */
    if(status==1) for(r=0;r<table->rowCount && !have;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        const char *value;unsigned parsed=0;
        if(!cells[0] || !cells[2] || strcmp(cells[0],cam_item))continue;
        for(value=cells[2];*value;++value) {
            if(*value<'0' || *value>'9'){parsed=0;break;}
            parsed=parsed*10u+(unsigned)(*value-'0');
            if(parsed>0xffu){parsed=0;break;}
        }
        if(cells[1] && !strcmp(cells[1],base_name)){resolved=parsed;have=1;break;}
        if(!have_global){global=parsed;have_global=1;}
    }
    if(have)from=CODOL_CAMO_ITEM_TABLE;
    else if(have_global){resolved=global;from=CODOL_CAMO_ITEM_TABLE_GLOBAL;}
    else if(variant>=0 && variant<=0xff){resolved=(unsigned)variant;from=CODOL_CAMO_ATTACH_COLUMN;}
    if(!resolved){*camo=0;if(source)*source=from;return 1;}
    /* An id whose mp/coweapmodels/<weapon>.csv row does not exist degrades to
     * zero, so the client is never asked for a base gun mesh that is not
     * there. A weapon with no table at all cannot be checked and keeps the id. */
    if(CODOL_ComposedBaseModelRow(base_name,resolved,NULL,NULL)==0) {
        *camo=0;if(source)*source=CODOL_CAMO_NO_MODEL_ROW;return 1;
    }
    *camo=resolved;if(source)*source=from;
    return 1;
}
/* mp/coweapitemswea.csv carries, per weapon, a run of (slot, defaultItem,
 * flag) groups. The patch zone's copy is 57 columns wide (5 header, 5 stats,
 * fifteen groups, a row index and an event flag) and supersedes the base
 * zone's narrower one, so the group run is located structurally rather than at
 * a fixed offset: a group column is a slot label followed by a marketplace
 * "wat" item. The slot need not equal the item group (hbs uses sra_hbs). The stride between the group
 * columns is what says whether a third, flag column exists. */
static int wat_group_of(const codol_engine_table_t *market,const char *name,const char **group)
{
    int r,found=0;
    for(r=0;r<market->rowCount;++r) {
        const char *const *cells=market->values+(size_t)r*market->columnCount;
        if(!cells[1] || !cells[2] || strcmp(cells[2],"wat") || strcmp(cells[1],name))continue;
        *group=cells[3] ? cells[3] : "";found=1;
    }
    return found;
}
static int default_group_column(const codol_engine_table_t *table,
    const codol_engine_table_t *market,int row,int column)
{
    const char *const *cells=table->values+(size_t)row*table->columnCount;
    const char *group=NULL;
    if(column+1>=table->columnCount)return 0;
    if(!cells[column] || !*cells[column] || !cells[column+1] || !*cells[column+1])return 0;
    if(!wat_group_of(market,cells[column+1],&group))return 0;
    return group && *group;
}
/* Group-column stride, learned from the first rows that show two of them.
 * Sixteen rows is far more than the widest weapon record needs and bounds the
 * marketplace walks this costs. */
static int default_stride(const codol_engine_table_t *table,const codol_engine_table_t *market)
{
    int row,column,previous,stride=0,rows=table->rowCount<16 ? table->rowCount : 16;
    for(row=0;row<rows;++row) {
        previous=-1;
        for(column=0;column+1<table->columnCount;++column) {
            if(!default_group_column(table,market,row,column))continue;
            if(previous>=0 && (!stride || column-previous<stride))stride=column-previous;
            previous=column;
        }
        if(stride==2 || stride==3)break;
    }
    return stride;
}
int CODOL_WeaponDeclaredDefaults(const char *base_name,codol_weapon_default_slot_t *out,
    unsigned max,unsigned *count)
{
    const codol_engine_table_t *table=NULL,*market=NULL;
    int status,row,column,found=-1,stride;unsigned n=0;
    if(!base_name || !*base_name || !count || (max && !out))return 0;
    status=CODOL_LoadEngineStringTable(DEFAULTS_TABLE,&table);
    if(status!=1)return status;
    if(!table || table->rowCount<0 || table->columnCount<2 ||
       (table->rowCount && !table->values))return -1;
    status=marketplace(&market);if(status!=1)return status;
    /* The weapon name is in the record's header columns. Weapon names are
     * distinct from every other cell the header carries, so the first header
     * column that holds this name is the record's key column. */
    for(column=0;column<table->columnCount && column<5 && found<0;++column)
        for(row=0;row<table->rowCount;++row) {
            const char *const *cells=table->values+(size_t)row*table->columnCount;
            if(cells[column] && !strcmp(cells[column],base_name)){found=row;break;}
        }
    if(found<0){*count=0;return 0;}
    stride=default_stride(table,market);
    if(!stride)return -1;
    for(column=0;column+1<table->columnCount;++column) {
        const char *const *cells=table->values+(size_t)found*table->columnCount;
        if(!default_group_column(table,market,found,column))continue;
        /* Only a group whose flag is exactly "y" is this weapon's declared
         * default. A layout with no flag column declares every group it lists. */
        if(stride>2) {
            const char *flag=column+2<table->columnCount ? cells[column+2] : NULL;
            if(!flag || (*flag!='y' && *flag!='Y') || flag[1])continue;
        }
        if(n<max){out[n].slot=cells[column];out[n].item=cells[column+1];}
        ++n;
        column+=stride-1;
    }
    *count=n;
    return n<=max ? 1 : -1;
}
int CODOL_ComposedAttachmentAssetName(const char *base_name,unsigned item_index,const char **out)
{
    const codol_engine_table_t *table=NULL;const char *item=NULL;int r,status;
    if(!out || !base_name || !*base_name)return -1;
    status=CODOL_ComposedAttachmentItemName(item_index,&item);
    if(status!=1)return status;
    if(CODOL_LoadEngineStringTable(ATTACHMENT_TABLE,&table)!=1)return -1;
    if(!table || table->rowCount<0 || table->columnCount<3 ||
       (table->rowCount && !table->values))return -1;
    /* C1 walks rows forward and overwrites this pair's bg_attachIdx entry
     * at 0x41fc96. Empty asset cells are skipped at 0x41fc6b..0x41fc72,
     * preserving the previous entry. Resolve the last nonempty match here
     * so native attachment effects agree with the client's final mapping. */
    for(r=table->rowCount-1;r>=0;--r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        if(!cells[0] || !cells[1] || strcmp(cells[0],base_name) || strcmp(cells[1],item))continue;
        if(!cells[2] || !*cells[2])continue;
        *out=cells[2];return 1;
    }
    return 0;
}
/* One owned entry per composed name. Each retains its adjusted source image,
 * converted core and graphs, acquired tag refs and stable sound bindings.
 * Native models, effects, animations and aliases borrow mounted archives.
 *
 * Two lists, mirroring the archive registry: entries built against the current
 * mount, and entries retired when their archives were replaced. Retired
 * entries are never freed at retirement, because live native code holds their
 * definition pointers exactly as it holds the retired archives' own weapon
 * cores; both are released together at unmount. Name lookups only ever see the
 * current list, so a replacement mount rebuilds against the new assets, while
 * definition-pointer lookups walk both, in the same generation order the
 * archive query walk uses. */
typedef struct composed_entry {
    struct composed_entry *next;
    char *name;
    codol_composed_weapon_t record;
    codol_native_weapon_core_t core;
    codol_weapon_source_image_t image;
    codol_weapon_hide_tag_handles_t owned_tags;
    codol_weapon_sound_bindings_t sounds;
    const struct WeaponDef *base;
    int adjusted; /* 1 once attachment overrides were applied to the source. */
    /* The mp/coweapmodels/<base>.csv row this name's flag selects: the CoDOL
     * runtime art the client assembles the composed gun from. Borrowed from
     * the mounted recipe table; null when the weapon has no table or the flag
     * has no row, which is the same thing the client would find. */
    const char *base_world_model,*base_view_model;
} composed_entry_t;
static composed_entry_t *composed,*retired_composed;
static char compose_error[192];
const char *CODOL_ComposedWeaponError(void){ return compose_error; }
static composed_entry_t *find_by_name(const char *name)
{
    composed_entry_t *e;
    for(e=composed;e;e=e->next)if(!strcmp(e->name,name))return e;
    return NULL;
}
static composed_entry_t *find_by_definition(const struct WeaponDef *definition)
{
    composed_entry_t *e;unsigned generation;
    if(!definition)return NULL;
    for(generation=0;generation<2;++generation)
        for(e=generation ? retired_composed : composed;e;e=e->next)
            if(definition==&e->core.definition)return e;
    return NULL;
}
/* Read every attachment definition this name carries, in its own order, and
 * apply them to the image as one transaction. The attachment module owns both
 * the type-43 reader and C1's grouped ordering; this only resolves which
 * definitions belong to the pair (base weapon, attachment item) and hands them
 * over together, because the ordering rules span the whole set. */
static int apply_attachments(const codol_composed_weapon_t *record,const char *base_name,
    codol_weapon_source_image_t *image)
{
    codol_weapon_attachment_t loaded[CODOL_COMPOSED_ATTACHMENTS];
    const codol_weapon_attachment_t *pointers[CODOL_COMPOSED_ATTACHMENTS];
    unsigned i,count=0;int status=1;
    memset(loaded,0,sizeof(loaded));
    for(i=0;i<record->count;++i) {
        const char *asset=NULL;
        int found=CODOL_ComposedAttachmentAssetName(base_name,record->items[i],&asset);
        if(found<0){status=-1;break;}
        /* A pair with no row for this weapon resolves to no attachment, which
         * is what bg_attachIdx holds for it; C1 keeps the item in the record
         * and resolves nothing. It is not an error and nothing is invented. */
        if(found!=1)continue;
        if(CODOL_ReadWeaponAttachment(asset,&loaded[count])!=1){status=-1;break;}
        pointers[count]=&loaded[count];++count;
    }
    if(status==1 && count && CODOL_ApplyWeaponAttachments(image,pointers,count)!=1)status=-1;
    for(i=0;i<count;++i)CODOL_FreeWeaponAttachment(&loaded[i]);
    return status;
}
static int load_composed_with_base(const char *name,const char *base_name,const struct WeaponDef **out)
{
    composed_entry_t *entry;codol_composed_weapon_t record;
    const struct WeaponDef *base=NULL;codol_weapon_source_image_t image={0};
    const XModel *world_model=NULL,*view_model=NULL;
    int status;size_t n;
    if(!name || !out || !base_name || !*base_name || base_name[0]=='*')return -1;
    status=CODOL_ParseComposedWeaponName(name,&record);
    if(status!=1)return status;
    /* Identity is the canonical spelling, so the same weapon written with
     * different spacing resolves to one definition and one published slot. */
    entry=find_by_name(record.canonical);
    if(entry){
        if(strcmp(entry->image.base,base_name)) return -1;
        *out=&entry->core.definition;return 1;
    }
    /* The base must exist as a real mounted weapon; a composed name over an
     * unknown base is rejected instead of resolving to something else. */
    if(CODOL_LoadMountedNativeWeapon(base_name,CODOL_LoadEngineWeaponCore,&base)!=1)return -1;
    entry=calloc(1,sizeof(*entry));if(!entry)return -1;
    n=strlen(record.canonical)+1;
    entry->name=malloc(n);
    if(!entry->name){free(entry);return -1;}
    memcpy(entry->name,record.canonical,n);
    /* Take the base's serialized image, apply this name's attachments to it as
     * one transaction, and convert the patched image. The overrides address the
     * CoDOL source layout, which is why they are applied here and not to a
     * converted WeaponDef. */
    if(CODOL_BeginWeaponSourceImage(base_name,&image)!=1) {
        snprintf(compose_error,sizeof(compose_error),
            "%s: base weapon %s has no readable source image",record.canonical,base_name);
        free(entry->name);free(entry);return -1;
    }
    status=apply_attachments(&record,base_name,&image);
    if(status!=1)
        snprintf(compose_error,sizeof(compose_error),
            "%s: attachment definitions for %s were rejected",record.canonical,base_name);
    else if(CODOL_LoadEngineWeaponCoreFromImage(&image,&entry->owned_tags,
              &entry->sounds,&entry->core)!=1) {
        status=-1;
        snprintf(compose_error,sizeof(compose_error),
            "%s: the patched source image did not convert",record.canonical);
    }
    else if(CODOL_ComposedBaseModelRow(base_name,record.flag,
              &entry->base_world_model,&entry->base_view_model)!=1 ||
            !entry->base_world_model || !*entry->base_world_model ||
            !entry->base_view_model || !*entry->base_view_model) {
        status=-1;
        snprintf(compose_error,sizeof(compose_error),
            "%s: %s camo %u has no complete base-model recipe",
            record.canonical,base_name,record.flag);
    }
    else if(CODOL_LoadEnginePhysicsXModel(entry->base_world_model,&world_model)!=1 || !world_model ||
            CODOL_LoadEnginePhysicsXModel(entry->base_view_model,&view_model)!=1 || !view_model ||
            !CODOL_BindNativeComposedWeaponModels(world_model,view_model,&entry->core)) {
        status=-1;
        snprintf(compose_error,sizeof(compose_error),
            "%s: recipe models %s / %s did not resolve",
            record.canonical,entry->base_world_model,entry->base_view_model);
    }
    if(status!=1) {
        CODOL_FreeNativeWeaponCore(&entry->core);
        CODOL_ReleaseEngineWeaponHideTags(&entry->owned_tags);
        CODOL_FreeWeaponSourceImage(&image);
        free(entry->name);free(entry);return -1;
    }
    compose_error[0]=0;
    entry->adjusted=1;
    /* C1 0x421712: the copy's internal name is the composed name itself. */
    entry->core.definition.szInternalName=entry->name;
    entry->record=record;
    /* The selected recipe names and their native model bindings were resolved
     * transactionally above; publishing a definition without them would make
     * G_GivePlayerWeapon reject the composed weapon. */
    /* Transfer the image without moving its allocations. The core borrows
     * adjusted names from it until this generation is finally released. */
    entry->image=image;
    entry->base=base;
    entry->next=composed;composed=entry;
    *out=&entry->core.definition;
    return 1;
}
int CODOL_LoadComposedWeapon(const char *name,const struct WeaponDef **out)
{
    codol_composed_weapon_t record; const char *base_name; int status;
    if(!out) return -1;
    status=CODOL_ParseComposedWeaponName(name,&record);
    if(status!=1) return status;
    if(CODOL_ComposedWeaponBaseName(record.base,&base_name)!=1) return -1;
    return load_composed_with_base(name,base_name,out);
}
int CODOL_RegisterComposedWeaponKeys(codol_weapon_registry_t *registry,unsigned wire,const char *name)
{
    codol_composed_weapon_t record; const char *base_name;
    const struct WeaponDef *definition; composed_entry_t *entry;
    codol_weapon_ammo_names_t ammo;
    if(!registry || CODOL_ParseComposedWeaponName(name,&record)!=1 ||
       strcmp(name,record.canonical) || record.base>=wire ||
       CODOL_RegisteredWeaponName(registry,record.base,&base_name)!=1 ||
       load_composed_with_base(name,base_name,&definition)!=1) return 0;
    entry=find_by_definition(definition);
    if(!entry || entry->image.size<CODOL_WEAPON_SOURCE_HEADER ||
       CODOL_WeaponSourceAmmoNames(&entry->image,&ammo)!=1) return 0;
    return CODOL_RegisterWeaponKeys(registry,wire,name,ammo.ammo,ammo.clip,
        entry->image.data[0xbbc],entry->image.data[0x560],(int)record.base);
}
int CODOL_ComposedWeaponRecord(const struct WeaponDef *definition,const codol_composed_weapon_t **out)
{
    composed_entry_t *e=find_by_definition(definition);
    if(!e || !out)return 0;
    *out=&e->record;return 1;
}
int CODOL_ComposedWeaponTail(const char *name,codol_weapon_tail_t *out)
{
    composed_entry_t *entry;
    if(!name || !out) return -1;
    entry=find_by_name(name);
    return entry ? CODOL_WeaponSourceTail(&entry->image,out) : 0;
}
int CODOL_ComposedWeaponBaseDefinition(const struct WeaponDef *definition,const struct WeaponDef **out)
{
    composed_entry_t *e=find_by_definition(definition);
    if(!e || !out || !e->base)return 0;
    /* The base definition was resolved in the same call that built this core,
     * so it belongs to the same archive generation and stays alive for exactly
     * as long: both are released only when every archive is unmounted. */
    *out=e->base;return 1;
}
int CODOL_ComposedWeaponBaseArt(const struct WeaponDef *definition,
    const char **world,const char **view)
{
    composed_entry_t *e=find_by_definition(definition);
    if(!e)return 0;
    if(world)*world=e->base_world_model;
    if(view)*view=e->base_view_model;
    return e->base_view_model || e->base_world_model ? 1 : 0;
}
const codol_native_weapon_core_t *CODOL_ComposedWeaponCore(const struct WeaponDef *definition)
{
    composed_entry_t *e=find_by_definition(definition);
    return e ? &e->core : NULL;
}
int CODOL_ComposedWeaponAdjusted(const struct WeaponDef *definition,int *out)
{
    composed_entry_t *e=find_by_definition(definition);
    if(!e || !out)return 0;
    *out=e->adjusted;return 1;
}
void CODOL_RetireComposedWeapons(void)
{
    composed_entry_t *e;
    reset_lookup_indexes();
    if(!composed)return;
    for(e=composed;e->next;e=e->next) {}
    e->next=retired_composed;retired_composed=composed;composed=NULL;
}
void CODOL_ResetComposedWeapons(void)
{
    unsigned generation;
    reset_lookup_indexes();
    for(generation=0;generation<2;++generation) {
        composed_entry_t **list=generation ? &retired_composed : &composed;
        while(*list) {
            composed_entry_t *e=*list;*list=e->next;
            CODOL_FreeNativeWeaponCore(&e->core);
            CODOL_ReleaseEngineWeaponHideTags(&e->owned_tags);
            CODOL_FreeWeaponSourceImage(&e->image);
            free(e->name);free(e);
        }
    }
}
