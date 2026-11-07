/* Bounded MapEnts stream reader; collision relocation supplies its position. */
#include "codol_assets.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>
static uint32_t read32(const uint8_t *p)
{ return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static unsigned read16(const uint8_t *p) { return (unsigned)p[0] | (unsigned)p[1]<<8; }
static float read_float(const uint8_t *p) { float f; memcpy(&f,p,4); return f; }
void CODOL_FreeTriggerModel(codol_trigger_model_t *model)
{
    if(!model) return;
    for(unsigned i=0;i<model->hull_count;++i) free(model->hulls[i].planes);
    free(model->hulls); memset(model,0,sizeof(*model));
}
int CODOL_ReadTriggerModel(const codol_map_entities_t *source,unsigned index,codol_trigger_model_t *out)
{
    codol_trigger_model_t result={0};
    size_t allocated=0;
    if(!source || !out || index>=source->model_count || !source->models ||
       !source->hulls || (source->slab_count && !source->slabs)) return 0;
    const uint8_t *model=source->models+(size_t)index*8;
    unsigned count=read16(model+4),first=read16(model+6);
    if(!count || first>source->hull_count || count>source->hull_count-first) return 0;
    memcpy(&result.contents,model,4);
    result.hulls=calloc(count,sizeof(*result.hulls));
    if(!result.hulls) return 0;
    result.hull_count=count;
    allocated=count*sizeof(*result.hulls);
    for(unsigned axis=0;axis<3;++axis) { result.mins[axis]=FLT_MAX; result.maxs[axis]=-FLT_MAX; }
    for(unsigned i=0;i<count;++i) {
        const uint8_t *h=source->hulls+(size_t)(first+i)*32;
        codol_trigger_hull_t *target=result.hulls+i;
        unsigned slabs=read16(h+28),start=read16(h+30);
        if(start>source->slab_count || slabs>source->slab_count-start) goto fail;
        memcpy(&target->contents,h+24,4);
        target->plane_count=6+slabs*2;
        if(target->plane_count>(CODOL_ASSET_LIMIT-allocated)/sizeof(*target->planes)) goto fail;
        allocated+=target->plane_count*sizeof(*target->planes);
        target->planes=calloc(target->plane_count,sizeof(*target->planes));
        if(!target->planes) goto fail;
        for(unsigned axis=0;axis<3;++axis) {
            float mid=read_float(h+axis*4),half=read_float(h+12+axis*4);
            if(!isfinite(mid) || !isfinite(half) || half<0) goto fail;
            target->mins[axis]=mid-half; target->maxs[axis]=mid+half;
            if(!isfinite(target->mins[axis]) || !isfinite(target->maxs[axis])) goto fail;
            if(target->mins[axis]<result.mins[axis]) result.mins[axis]=target->mins[axis];
            if(target->maxs[axis]>result.maxs[axis]) result.maxs[axis]=target->maxs[axis];
            target->planes[axis*2].normal[axis]=-1;
            target->planes[axis*2].distance=-target->mins[axis];
            target->planes[axis*2+1].normal[axis]=1;
            target->planes[axis*2+1].distance=target->maxs[axis];
        }
        for(unsigned j=0;j<slabs;++j) {
            const uint8_t *s=source->slabs+(size_t)(start+j)*20;
            double length=0; float n[3],mid=read_float(s+12),half=read_float(s+16);
            if(!isfinite(mid) || !isfinite(half) || half<0) goto fail;
            for(unsigned axis=0;axis<3;++axis) {
                n[axis]=read_float(s+axis*4);
                if(!isfinite(n[axis])) goto fail;
                length+=(double)n[axis]*n[axis];
            }
            if(!(length>0)) goto fail;
            length=sqrt(length);
            for(unsigned side=0;side<2;++side) {
                codol_trigger_plane_t *p=target->planes+6+j*2+side;
                double sign=side ? 1 : -1;
                for(unsigned axis=0;axis<3;++axis) p->normal[axis]=(float)(sign*n[axis]/length);
                p->distance=(float)((sign*mid+half)/length);
                if(!isfinite(p->distance)) goto fail;
            }
        }
    }
    CODOL_FreeTriggerModel(out); *out=result; return 1;
fail:
    CODOL_FreeTriggerModel(&result); return 0;
}
static int floats_valid(const uint8_t *p, unsigned count, unsigned first_nonnegative)
{
    unsigned i;
    for (i = 0; i < count; ++i) {
        float value;
        memcpy(&value, p+4*i, 4);
        if (!isfinite(value) || (i >= first_nonnegative && value < 0)) return 0;
    }
    return 1;
}
void CODOL_FreeMapEntities(codol_map_entities_t *e)
{ if (e) { free(e->storage); free(e->stages); memset(e, 0, sizeof(*e)); } }
/* MapEnts and AddonMapEnts are the same record; the addon one stops after the
 * trigger arrays.  MEASURED 2026-09-20 over the nine shipped coop addons
 * (docs/CODOL_ADDON_MAP_ENTS_20260920.md): 36-byte header, name pointer at +0
 * (0xFFFFFFFF/inline for all nine), entityString pointer at +4 (always
 * 0xFFFFFFFF), numEntityChars at +8, then count/pointer pairs for the trigger
 * models (8 bytes each), hulls (32) and slabs (20) filling +12..+35.  MapEnts
 * adds the stage pointer at +36 and the stage count byte at +40, making 44.
 * For every one of the nine, header + inline name + numEntityChars +
 * 8*models + 32*hulls + 20*slabs equals the asset extent exactly. */
static int read_map_entities(const void *data, size_t size, size_t header,
                             codol_map_entities_t *out)
{
    const uint8_t *bytes = data, *end;
    codol_map_entities_t result = {0};
    size_t position = header, name_size = 0, length, arrays[4], i;
    size_t stage_names[256] = {0};
    const unsigned strides[4] = {8, 32, 20, 20};
    uint32_t counts[4], references[4];
    if (!bytes || !out || size < header || size > CODOL_ASSET_LIMIT || read32(bytes+4) != UINT32_MAX) return 0;
    result.name_reference = read32(bytes);
    length = read32(bytes+8);
    if (result.name_reference == UINT32_MAX) {
        end = memchr(bytes+position, 0, size-position);
        if (!end) return 0;
        name_size = (size_t)(end-(bytes+position))+1; position += name_size;
    }
    if (!length || length > size-position || bytes[position+length-1] ||
        memchr(bytes+position, 0, length-1)) return 0;
    result.text_size = length;
    position += length;
    for (i = 0; i < 3; ++i) {
        counts[i] = read32(bytes+12+i*8); references[i] = read32(bytes+16+i*8);
    }
    if (header >= 44) { counts[3] = bytes[40]; references[3] = read32(bytes+36); }
    else { counts[3] = 0; references[3] = 0; }
    for (i = 0; i < 4; ++i) {
        if (counts[i] > (size-position)/strides[i] ||
            (counts[i] && references[i] != UINT32_MAX)) return 0;
        arrays[i] = position; position += (size_t)counts[i]*strides[i];
    }
    for (i = 0; i < counts[3]; ++i) {
        const uint8_t *stage = bytes+arrays[3]+20*i;
        unsigned trigger = read16(stage+16);
        if (!floats_valid(stage+4, 3, 3) || (trigger != 1024 && trigger >= counts[0])) return 0;
        if (read32(bytes+arrays[3]+20*i) == UINT32_MAX) {
            end = memchr(bytes+position, 0, size-position);
            if (!end) return 0;
            stage_names[i] = position; position = (size_t)(end-bytes)+1;
        }
    }
    for (i = 0; i < counts[0]; ++i) {
        const uint8_t *model = bytes+arrays[0]+8*i;
        if (read16(model+4)+read16(model+6) > counts[1]) return 0;
    }
    for (i = 0; i < counts[1]; ++i) {
        const uint8_t *hull = bytes+arrays[1]+32*i;
        if (!floats_valid(hull, 6, 3) || read16(hull+28)+read16(hull+30) > counts[2]) return 0;
    }
    for (i = 0; i < counts[2]; ++i)
        if (!floats_valid(bytes+arrays[2]+20*i, 5, 4)) return 0;
    result.storage = malloc(position-header);
    if (!result.storage) return 0;
    memcpy(result.storage, bytes+header, position-header);
    result.name = name_size ? (const char *)result.storage : NULL;
    result.text = (const char *)result.storage+name_size;
    result.consumed = position;
    result.model_count = counts[0]; result.hull_count = counts[1]; result.slab_count = counts[2];
    result.models = result.storage+(arrays[0]-header);
    result.hulls = result.storage+(arrays[1]-header);
    result.slabs = result.storage+(arrays[2]-header);
    result.stage_count = counts[3];
    if (counts[3]) {
        result.stages = calloc(counts[3], sizeof(*result.stages));
        if (!result.stages) { CODOL_FreeMapEntities(&result); return 0; }
    }
    for (i = 0; i < counts[3]; ++i) {
        const uint8_t *record = result.storage+(arrays[3]-header)+20*i;
        codol_map_stage_t *stage = &result.stages[i];
        stage->name_reference = read32(record);
        stage->name = stage_names[i] ? (const char *)result.storage+(stage_names[i]-header) : NULL;
        memcpy(stage->origin, record+4, sizeof(stage->origin));
        stage->trigger_index = (uint16_t)record[16] | (uint16_t)record[17]<<8;
        stage->sun_index = record[18];
    }
    *out = result; return 1;
}
int CODOL_ReadMapEntities(const void *data, size_t size, codol_map_entities_t *out)
{ return read_map_entities(data, size, 44, out); }
int CODOL_ReadAddonMapEntities(const void *data, size_t size, codol_map_entities_t *out)
{ return read_map_entities(data, size, 36, out); }

/* ---- addon composition -------------------------------------------------
 *
 * A coop zone ships no world assets at all -- no col_map_mp, com_map,
 * game_map_mp, gfx_map or map_ents -- only one addon_map_ents (MEASURED, see
 * docs/CODOL_ADDON_MAP_ENTS_20260920.md).  Its geometry is the base mp_* level
 * zone's, so the addon entities OVERLAY the base map_ents entity string rather
 * than replacing it: none of the nine addons carries a single "*N" brush-entity
 * reference while their base maps carry hundreds, and seven of the nine carry
 * no minimap_corner, so an addon cannot stand alone.  The addon's own leading
 * worldspawn is dropped: G_SpawnEntitiesFromString calls SP_worldspawn exactly
 * once, for the first parsed entity, and every addon worldspawn's
 * server-visible keys (northyaw, gravity, ambienttrack, message) are either
 * absent or identical to the base's -- two base maps carry a northyaw the
 * addon omits, so the base worldspawn has to stay entity 0.
 *
 * "?N" indexes the trigger model array of the MapEnts the entity came from, so
 * concatenating two entity strings has to bias every addon "?N" by the base's
 * trigger model count and append the addon's trigger models, hulls and slabs
 * after the base's.  One contiguous array then serves both halves and
 * CODOL_AppendNativeTriggers stays unchanged. */

static size_t decimal_length(uint32_t value)
{ size_t n = 1; while (value >= 10) { value /= 10; ++n; } return n; }

/* Rewrite every `"model" "?N"` in an addon entity string to `"?N+bias"`.
 *
 * MEASURED over all nine shipped addons: '?' occurs in the entity text ONLY as
 * that reference, always on a line of exactly that shape, once per trigger
 * model, with indices covering 0..model_count-1.  Anything else is refused
 * rather than guessed at -- a mis-rewrite silently rebinds a trigger volume to
 * the wrong brush.  `out` may be NULL to size the result first. */
static int rebase_trigger_refs(const char *body, size_t length, uint32_t bias,
                               uint32_t limit, char *out, size_t *written)
{
    static const char key[] = "\"model\" \"";
    const size_t key_length = sizeof(key)-1;
    size_t i = 0, w = 0;
    while (i < length) {
        uint32_t value = 0;
        size_t digits = 0, j, n;
        char text[12];
        if (body[i] != '?') { if (out) out[w] = body[i]; ++w; ++i; continue; }
        if (i <= key_length || memcmp(body+i-key_length, key, key_length) ||
            body[i-key_length-1] != '\n') return 0;
        for (j = i+1; j < length && body[j] >= '0' && body[j] <= '9'; ++j, ++digits) {
            if (value > (UINT32_MAX-9)/10) return 0;
            value = value*10 + (uint32_t)(body[j]-'0');
        }
        if (!digits || digits > 10 || j >= length || body[j] != '"') return 0;
        if (j+1 < length && body[j+1] != '\n') return 0;
        if (value >= limit || value > UINT32_MAX-bias) return 0;
        value += bias;
        n = decimal_length(value);
        if (out) {
            size_t k = n;
            out[w] = '?';
            while (k > 0) { text[--k] = (char)('0'+value%10); value /= 10; }
            memcpy(out+w+1, text, n);
        }
        w += 1+n;
        i = j;
    }
    *written = w; return 1;
}

static int contains_bytes(const char *haystack, size_t length, const char *needle, size_t needle_length)
{
    size_t i;
    if (needle_length > length) return 0;
    for (i = 0; i + needle_length <= length; ++i)
        if (haystack[i] == needle[0] && !memcmp(haystack+i, needle, needle_length)) return 1;
    return 0;
}

/* Byte range of the addon entity text to append: everything after a leading
 * worldspawn block.  Refuses anything that is not the measured
 * "{\n...\n}\n{\n...\n}" shape rather than appending a malformed tail. */
static int addon_overlay_body(const codol_map_entities_t *addon, const char **body, size_t *length)
{
    static const char world[] = "\"classname\" \"worldspawn\"";
    const char *text = addon->text, *newline;
    size_t total, offset;
    if (!text || addon->text_size < 2 || text[addon->text_size-1]) return 0;
    total = addon->text_size-1;
    if (total < 3 || text[0] != '{' || text[1] != '\n') return 0;
    newline = memchr(text, '\n', total);
    for (;;) {
        if (!newline) return 0;
        offset = (size_t)(newline-text);
        if (offset+2 < total && newline[1] == '}' && newline[2] == '\n') break;
        if (offset+2 == total && newline[1] == '}') { *body = text+total; *length = 0; return 1; }
        newline = memchr(newline+1, '\n', total-offset-1);
    }
    /* Only the first block is dropped, and only when it is the worldspawn. */
    if (!contains_bytes(text, offset, world, sizeof(world)-1)) { *body = text; *length = total; return 1; }
    *body = text+offset+3; *length = total-(offset+3);
    return 1;
}

int CODOL_MergeMapEntities(const codol_map_entities_t *base,
                           const codol_map_entities_t *addon,
                           codol_map_entities_t *out)
{
    codol_map_entities_t result = {0};
    const char *overlay; size_t overlay_length, rewritten = 0;
    size_t name_size, text_size, models, hulls, slabs, stage_names = 0, total, i, cursor;
    uint32_t limit;
    uint8_t *storage;
    if (!base || !addon || !out || !base->text || !base->text_size ||
        base->text[base->text_size-1] || addon->stage_count) return 0;
    if ((base->model_count && !base->models) || (base->hull_count && !base->hulls) ||
        (base->slab_count && !base->slabs) || (addon->model_count && !addon->models) ||
        (addon->hull_count && !addon->hulls) || (addon->slab_count && !addon->slabs)) return 0;
    if (!addon_overlay_body(addon, &overlay, &overlay_length)) return 0;
    limit = addon->model_count ? addon->model_count : 1;
    if (overlay_length &&
        !rebase_trigger_refs(overlay, overlay_length, base->model_count, limit, NULL, &rewritten)) return 0;
    if ((uint64_t)base->model_count+addon->model_count > 65535 ||
        (uint64_t)base->hull_count+addon->hull_count > 65535 ||
        (uint64_t)base->slab_count+addon->slab_count > 65535) return 0;
    name_size = base->name ? strlen(base->name)+1 : 0;
    /* base text without its NUL, one '\n' joiner, the rewritten overlay, NUL */
    text_size = overlay_length ? (base->text_size-1)+1+rewritten+1 : base->text_size;
    models = ((size_t)base->model_count+addon->model_count)*8;
    hulls  = ((size_t)base->hull_count+addon->hull_count)*32;
    slabs  = ((size_t)base->slab_count+addon->slab_count)*20;
    for (i = 0; i < base->stage_count; ++i)
        if (base->stages[i].name) stage_names += strlen(base->stages[i].name)+1;
    total = name_size+text_size+models+hulls+slabs+stage_names;
    if (!total || total > CODOL_ASSET_LIMIT) return 0;
    storage = malloc(total);
    if (!storage) return 0;
    cursor = name_size;
    if (name_size) memcpy(storage, base->name, name_size);
    memcpy(storage+cursor, base->text, base->text_size-1);
    if (overlay_length) {
        size_t produced = 0;
        storage[cursor+base->text_size-1] = '\n';
        if (!rebase_trigger_refs(overlay, overlay_length, base->model_count, limit,
                                 (char *)storage+cursor+base->text_size, &produced) ||
            produced != rewritten) { free(storage); return 0; }
    }
    storage[cursor+text_size-1] = 0;
    result.text = (const char *)storage+cursor;
    result.text_size = text_size;
    result.name = name_size ? (const char *)storage : NULL;
    result.name_reference = base->name_reference;
    cursor += text_size;
    result.models = storage+cursor;
    if (base->model_count) memcpy(storage+cursor, base->models, (size_t)base->model_count*8);
    for (i = 0; i < addon->model_count; ++i) {
        uint8_t *record = storage+cursor+((size_t)base->model_count+i)*8;
        unsigned first;
        memcpy(record, addon->models+i*8, 8);
        first = read16(record+6)+base->hull_count;
        record[6] = (uint8_t)(first&0xff); record[7] = (uint8_t)(first>>8);
    }
    cursor += models;
    result.hulls = storage+cursor;
    if (base->hull_count) memcpy(storage+cursor, base->hulls, (size_t)base->hull_count*32);
    for (i = 0; i < addon->hull_count; ++i) {
        uint8_t *record = storage+cursor+((size_t)base->hull_count+i)*32;
        unsigned start;
        memcpy(record, addon->hulls+i*32, 32);
        start = read16(record+30)+base->slab_count;
        record[30] = (uint8_t)(start&0xff); record[31] = (uint8_t)(start>>8);
    }
    cursor += hulls;
    result.slabs = storage+cursor;
    if (base->slab_count) memcpy(storage+cursor, base->slabs, (size_t)base->slab_count*20);
    if (addon->slab_count) memcpy(storage+cursor+(size_t)base->slab_count*20,
                                  addon->slabs, (size_t)addon->slab_count*20);
    cursor += slabs;
    result.model_count = base->model_count+addon->model_count;
    result.hull_count = base->hull_count+addon->hull_count;
    result.slab_count = base->slab_count+addon->slab_count;
    result.stage_count = base->stage_count;
    if (base->stage_count) {
        result.stages = calloc(base->stage_count, sizeof(*result.stages));
        if (!result.stages) { free(storage); return 0; }
        for (i = 0; i < base->stage_count; ++i) {
            result.stages[i] = base->stages[i];
            if (base->stages[i].name) {
                size_t n = strlen(base->stages[i].name)+1;
                memcpy(storage+cursor, base->stages[i].name, n);
                result.stages[i].name = (const char *)storage+cursor;
                cursor += n;
            }
        }
    }
    result.storage = storage;
    result.consumed = 0;
    CODOL_FreeMapEntities(out); *out = result; return 1;
}
