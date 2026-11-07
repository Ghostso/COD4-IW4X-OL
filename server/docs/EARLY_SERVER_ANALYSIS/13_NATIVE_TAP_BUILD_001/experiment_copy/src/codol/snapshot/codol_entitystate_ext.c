/* Entity event epoch. See codol_entitystate_ext.h for the producers, the
 * storages and the record format. */
#include "codol_entitystate_ext.h"
/* Types only: the storage bases arrive through the seam, so this file
 * references no engine global and links in isolation. */
#include "g_shared.h"
#include "server.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

_Static_assert(offsetof(gentity_t, s) == 0, "gentity starts with its entityState");
_Static_assert(offsetof(archivedEntity_t, s) == 0, "archived entity starts with its entityState");

/* The CoDOL entity wire carries numbers 0..ENTITYNUM_WORLD-1; the writer
 * rejects anything above, so only those live slots can ever be serialized. */
#define CODOL_ES_EXT_LIVE ((unsigned)ENTITYNUM_WORLD)
#define CODOL_ES_EXT_SNAPSHOT \
    (sizeof(((serverStatic_t *)0)->snapshotEntities) / sizeof(entityState_t))
#define CODOL_ES_EXT_ARCHIVE \
    (sizeof(((serverStatic_t *)0)->cachedSnapshotEntities) / sizeof(archivedEntity_t))

static codol_es_ext_t live_ext[CODOL_ES_EXT_LIVE];
static codol_es_ext_t snapshot_ext[CODOL_ES_EXT_SNAPSHOT];
static codol_es_ext_t archive_ext[CODOL_ES_EXT_ARCHIVE];
static const codol_es_ext_t unknown_ext;
static unsigned misses;
static unsigned desyncs;

static void miss(const entityState_t *es)
{
    if (!misses++)
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL entityState extension: untracked entityState storage %p "
            "(entity %d type %d counter %d); its event history is unknown\n",
            (const void *)es,es->number,es->eType,es->eventSequence);
}

static void desync(const entityState_t *es, unsigned counter, uint32_t epoch)
{
    if (!desyncs++)
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL entityState extension: event epoch %u does not match "
            "entityState %p counter %u; event history cannot be serialized\n",
            (unsigned)epoch, (const void *)es, counter);
}

static codol_es_ext_t *resolve(const entityState_t *es)
{
    uintptr_t p = (uintptr_t)es, base;
    unsigned count = 0;
    size_t i;
    const gentity_t *live;
    const entityState_t *snapshot;
    const archivedEntity_t *archive;
    if (!es) return NULL;
    live = CODOL_EntityStateExtLiveBase(&count);
    if (live && count) {
        if (count > CODOL_ES_EXT_LIVE) count = CODOL_ES_EXT_LIVE;
        base = (uintptr_t)live;
        if (p >= base && p < base + (uintptr_t)count * sizeof(gentity_t)) {
            i = (size_t)((p - base) / sizeof(gentity_t));
            if (i < count && &live[i].s == es) return &live_ext[i];
        }
    }
    snapshot = CODOL_EntityStateExtSnapshotBase(&count);
    if (snapshot && count) {
        if (count > CODOL_ES_EXT_SNAPSHOT) count = CODOL_ES_EXT_SNAPSHOT;
        base = (uintptr_t)snapshot;
        if (p >= base && p < base + (uintptr_t)count * sizeof(entityState_t)) {
            i = (size_t)((p - base) / sizeof(entityState_t));
            if (i < count && &snapshot[i] == es) return &snapshot_ext[i];
        }
    }
    archive = CODOL_EntityStateExtArchiveBase(&count);
    if (archive && count) {
        if (count > CODOL_ES_EXT_ARCHIVE) count = CODOL_ES_EXT_ARCHIVE;
        base = (uintptr_t)archive;
        if (p >= base && p < base + (uintptr_t)count * sizeof(archivedEntity_t)) {
            i = (size_t)((p - base) / sizeof(archivedEntity_t));
            if (i < count && &archive[i].s == es) return &archive_ext[i];
        }
    }
    return NULL;
}

void CODOL_EntityStateEventAdded(entityState_t *es)
{
    codol_es_ext_t *ext = resolve(es);
    if (!ext) { miss(es); return; }
    if (!ext->known) { ext->epoch = 0; ext->known = 1; }
    ++ext->epoch;
}

void CODOL_EntityStatePrimaryWeaponCaptured(entityState_t *es, unsigned primary, int resolved)
{
    codol_es_ext_t *ext = resolve(es);
    if (!ext) { miss(es); return; }
    if (!resolved || primary > 0xffffu) {
        ext->primary_known = 0;
        ext->primary_weapon = 0;
        ext->held_offhand = 0;
        return;
    }
    ext->primary_weapon = (uint16_t)primary;
    ext->primary_known = 1;
}

void CODOL_EntityStateHeldOffhandCaptured(entityState_t *es, unsigned weapon)
{
    codol_es_ext_t *ext = resolve(es);
    if (!ext) { miss(es); return; }
    ext->held_offhand = ext->primary_known && weapon <= 0xffffu ? (uint16_t)weapon : 0;
}

unsigned CODOL_EntityStateHeldOffhand(const entityState_t *es)
{
    const codol_es_ext_t *ext;
    if (!es) return 0;
    ext = resolve(es);
    return ext && ext->primary_known ? ext->held_offhand : 0;
}

int CODOL_EntityStatePrimaryWeapon(const entityState_t *es, unsigned *out)
{
    const codol_es_ext_t *ext;
    if (!es || !out) return 0;
    ext = resolve(es);
    if (!ext) { miss(es); return 0; }
    if (!ext->primary_known) return 0;
    *out = ext->primary_weapon;
    return 1;
}

uint32_t CODOL_EntityStateEventEpoch(const entityState_t *es)
{
    const codol_es_ext_t *ext = resolve(es);
    return (ext && ext->known) ? ext->epoch : 0;
}

void CODOL_EntityStateVehicleCaptured(entityState_t *es,unsigned instance,unsigned definition,int resolved)
{
    codol_es_ext_t *ext=resolve(es);
    if(!ext) { miss(es); return; }
    ext->vehicle_known=0;
    ext->vehicle_identity=0;
    if(!resolved || instance>=16 || !definition || definition>=32 ||
       (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE)) return;
    ext->vehicle_identity=(uint16_t)(instance | (definition<<4));
    ext->vehicle_known=1;
}
int CODOL_EntityStateVehicleIdentity(const entityState_t *es,unsigned *out)
{
    const codol_es_ext_t *ext;
    if(!es || !out || (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE)) return 0;
    ext=resolve(es);
    if(!ext) { miss(es); return 0; }
    if(!ext->vehicle_known) return 0;
    *out=ext->vehicle_identity;
    return 1;
}

int CODOL_EntityStateModelAnimCaptured(entityState_t *es,unsigned entry,unsigned tree)
{
    codol_es_ext_t *ext;
    if(!es || es->eType!=ET_SCRIPTMOVER || es->solid==SOLID_BMODEL ||
       entry>0xfffu || tree>15u || (!!entry!=!!tree)) return 0;
    ext=resolve(es);
    if(!ext) { miss(es); return 0; }
    ext->model_anim_entry=(uint16_t)entry;
    ext->model_anim_tree=(unsigned char)tree;
    ext->model_anim_known=1;
    return 1;
}

int CODOL_EntityStateModelAnim(const entityState_t *es,unsigned *entry,unsigned *tree)
{
    const codol_es_ext_t *ext;
    if(!es || !entry || !tree || es->eType!=ET_SCRIPTMOVER ||
       es->solid==SOLID_BMODEL) return 0;
    ext=resolve(es);
    if(!ext) { miss(es); return 0; }
    if(!ext->model_anim_known) return 0;
    *entry=ext->model_anim_entry;
    *tree=ext->model_anim_tree;
    return 1;
}

unsigned CODOL_EntityStateEventDesyncs(void)
{
    return desyncs;
}

int CODOL_EntityStateEventSequence(const entityState_t *es, unsigned *out)
{
    const codol_es_ext_t *ext;
    unsigned counter;
    if (!es || !out || es->eventSequence < 0 || es->eventSequence > 255) return 0;
    counter = (unsigned)es->eventSequence;
    ext = resolve(es);
    if (!ext) { miss(es); desync(es, counter, counter); return 0; }
    if (!ext->known) {
        /* Never had an event: that is a recorded zero, not a guess. Anything
         * else means a producer ran without the hook. */
        if (counter) { desync(es, counter, 0); return 0; }
        *out = 0;
        return 1;
    }
    if ((ext->epoch & 0xffu) != counter) { desync(es, counter, ext->epoch); return 0; }
    *out = ext->epoch & 2047u;
    return 1;
}

int CODOL_EntityStateLinkCaptured(entityState_t *es,unsigned info,const float origin[3],const float angles[3])
{
    codol_es_ext_t *ext; unsigned i;
    if(!es || !origin || !angles || info>>27 || (info&65535u)>ENTITYNUM_WORLD)return 0;
    for(i=0;i<3;++i)if(!isfinite(origin[i]) || !isfinite(angles[i]))return 0;
    ext=resolve(es);if(!ext)return 0;
    ext->link_info=info;
    memcpy(ext->link_origin,origin,sizeof(ext->link_origin));
    memcpy(ext->link_angles,angles,sizeof(ext->link_angles));
    return 1;
}
int CODOL_EntityStateLink(const entityState_t *es,unsigned *info,float origin[3],float angles[3])
{
    const codol_es_ext_t *ext=resolve(es);
    if(!ext || !info || !origin || !angles)return 0;
    *info=ext->link_info;
    memcpy(origin,ext->link_origin,sizeof(ext->link_origin));
    memcpy(angles,ext->link_angles,sizeof(ext->link_angles));
    return 1;
}

int CODOL_EntityStateSetHidePartBits(entityState_t *es,const uint32_t bits[8])
{
    codol_es_ext_t *ext;
    if(!es || !bits) return 0;
    memcpy(es->partBits,bits,sizeof(es->partBits));
    ext=resolve(es);
    if(!ext) { miss(es); return 0; }
    memcpy(ext->hide_upper,bits+4,sizeof(ext->hide_upper));
    return 1;
}

void CODOL_EntityStateHidePartBits(const entityState_t *es,uint32_t bits[8])
{
    const codol_es_ext_t *ext;
    if(!bits) return;
    memset(bits,0,8*sizeof(bits[0]));
    if(!es) return;
    memcpy(bits,es->partBits,sizeof(es->partBits));
    ext=resolve(es);
    if(ext) memcpy(bits+4,ext->hide_upper,sizeof(ext->hide_upper));
}

int CODOL_EntityStateExtCopy(const entityState_t *dst, const entityState_t *src)
{
    codol_es_ext_t *to = resolve(dst);
    const codol_es_ext_t *from = resolve(src);
    if (!to) return 0;
    if (!from) { miss(src); *to = unknown_ext; return 0; }
    *to = *from;
    return 1;
}

int CODOL_EntityStateExtClear(const entityState_t *es)
{
    codol_es_ext_t *ext = resolve(es);
    if (!ext) return 0;
    *ext = unknown_ext;
    return 1;
}

void CODOL_EntityStateExtClearEntity(unsigned number)
{
    /* A freed entity number starts a new history; captured snapshots and
     * archived frames keep the epoch they were taken with. */
    if (number < CODOL_ES_EXT_LIVE) live_ext[number] = unknown_ext;
}

void CODOL_EntityStateExtClearArchive(void)
{
    memset(archive_ext, 0, sizeof(archive_ext));
}

void CODOL_EntityStateExtClearAll(void)
{
    memset(live_ext, 0, sizeof(live_ext));
    memset(snapshot_ext, 0, sizeof(snapshot_ext));
    memset(archive_ext, 0, sizeof(archive_ext));
    misses = 0;
    desyncs = 0;
}

/* ---- archived-snapshot stream record -------------------------------------- */
static void write_value(msg_t *msg, const codol_es_ext_t *value, const codol_es_ext_t *baseline)
{
    codol_es_ext_t from = baseline ? *baseline : unknown_ext;
    codol_es_ext_t to = value ? *value : unknown_ext;
    uint32_t delta;
    if (!msg) return;
    if (to.known == from.known && to.epoch == from.epoch) { MSG_WriteBit0(msg); return; }
    MSG_WriteBit1(msg);
    MSG_WriteBits(msg, to.known ? 1 : 0, 1);
    if (!to.known) return;
    delta = to.epoch - from.epoch;
    if (from.known && delta >= 1 && delta <= 16) {
        MSG_WriteBit1(msg);
        MSG_WriteBits(msg, (int)(delta - 1), 4);
    } else {
        MSG_WriteBit0(msg);
        MSG_WriteBits(msg, (int)to.epoch, 32);
    }
}

/* The captured weapon pair, written as its own record after the epoch's so the
 * epoch framing above is untouched. */
static void write_primary(msg_t *msg, const codol_es_ext_t *value, const codol_es_ext_t *baseline)
{
    codol_es_ext_t from = baseline ? *baseline : unknown_ext;
    codol_es_ext_t to = value ? *value : unknown_ext;
    if (!msg) return;
    if (to.primary_known == from.primary_known &&
        to.primary_weapon == from.primary_weapon &&
        to.held_offhand == from.held_offhand) { MSG_WriteBit0(msg); return; }
    MSG_WriteBit1(msg);
    MSG_WriteBits(msg, to.primary_known ? 1 : 0, 1);
    if (!to.primary_known) return;
    MSG_WriteBits(msg, (int)to.primary_weapon, 16);
    MSG_WriteBits(msg, (int)to.held_offhand, 16);
}

static void write_vehicle(msg_t *msg,const codol_es_ext_t *value,const codol_es_ext_t *baseline)
{
    codol_es_ext_t from=baseline ? *baseline : unknown_ext;
    codol_es_ext_t to=value ? *value : unknown_ext;
    if(!msg) return;
    if(to.vehicle_known==from.vehicle_known && to.vehicle_identity==from.vehicle_identity) {
        MSG_WriteBit0(msg); return;
    }
    MSG_WriteBit1(msg);
    MSG_WriteBits(msg,to.vehicle_known ? 1 : 0,1);
    if(to.vehicle_known) MSG_WriteBits(msg,to.vehicle_identity,9);
}
/* Internal archive record, not a new client protocol field. */
static void write_model_anim(msg_t *msg,const codol_es_ext_t *value,const codol_es_ext_t *baseline)
{
    codol_es_ext_t from=baseline ? *baseline : unknown_ext;
    codol_es_ext_t to=value ? *value : unknown_ext;
    if(!msg) return;
    if(to.model_anim_known==from.model_anim_known &&
       to.model_anim_entry==from.model_anim_entry &&
       to.model_anim_tree==from.model_anim_tree) { MSG_WriteBit0(msg); return; }
    MSG_WriteBit1(msg);
    MSG_WriteBits(msg,to.model_anim_known ? 1 : 0,1);
    if(!to.model_anim_known) return;
    MSG_WriteBits(msg,to.model_anim_entry,12);
    MSG_WriteBits(msg,to.model_anim_tree,4);
}

static void write_link(msg_t *msg,const codol_es_ext_t *value,const codol_es_ext_t *baseline)
{
    const codol_es_ext_t *to=value ? value : &unknown_ext,*from=baseline ? baseline : &unknown_ext;
    unsigned i; uint32_t bits;
    if(!msg)return;
    if(to->link_info==from->link_info && !memcmp(to->link_origin,from->link_origin,sizeof(to->link_origin)) &&
       !memcmp(to->link_angles,from->link_angles,sizeof(to->link_angles))) { MSG_WriteBit0(msg);return; }
    MSG_WriteBit1(msg);MSG_WriteBits(msg,to->link_info,27);
    if(!(to->link_info&65535u))return;
    for(i=0;i<3;++i) {memcpy(&bits,to->link_origin+i,4);MSG_WriteBits(msg,bits,32);}
    for(i=0;i<3;++i) {memcpy(&bits,to->link_angles+i,4);MSG_WriteBits(msg,bits,32);}
}

static void write_hide(msg_t *msg,const codol_es_ext_t *value,const codol_es_ext_t *baseline)
{
    const codol_es_ext_t *to=value ? value : &unknown_ext,*from=baseline ? baseline : &unknown_ext;
    unsigned i;
    if(!msg)return;
    if(!memcmp(to->hide_upper,from->hide_upper,sizeof(to->hide_upper))) { MSG_WriteBit0(msg);return; }
    MSG_WriteBit1(msg);
    for(i=0;i<4;++i)MSG_WriteBits(msg,to->hide_upper[i],32);
}

void CODOL_EntityStateExtWrite(msg_t *msg, const entityState_t *es, const entityState_t *baseline)
{
    const codol_es_ext_t *value = resolve(es), *base = resolve(baseline);
    write_value(msg, value, base);
    write_primary(msg, value, base);
    write_vehicle(msg, value, base);
    write_model_anim(msg, value, base);
    write_link(msg, value, base);
    write_hide(msg, value, base);
}

void CODOL_EntityStateExtWriteEntity(msg_t *msg, unsigned number, const entityState_t *baseline)
{
    const codol_es_ext_t *value = number < CODOL_ES_EXT_LIVE ? &live_ext[number] : NULL;
    const codol_es_ext_t *base = resolve(baseline);
    write_value(msg, value, base);
    write_primary(msg, value, base);
    write_vehicle(msg, value, base);
    write_model_anim(msg, value, base);
    write_link(msg, value, base);
    write_hide(msg, value, base);
}

void CODOL_EntityStateExtRead(msg_t *msg, const entityState_t *es, const entityState_t *baseline)
{
    const codol_es_ext_t *base = resolve(baseline);
    codol_es_ext_t value = base ? *base : unknown_ext;
    codol_es_ext_t *to;
    int changed, known, failed = 0;
    if (!msg) return;
    changed = MSG_ReadBit(msg);
    if (changed < 0 || msg->overflowed) {
        failed = 1;
    } else if (changed) {
        known = MSG_ReadBits(msg, 1);
        if (msg->overflowed || known < 0) {
            failed = 1;
        } else if (!known) {
            value.known = 0;
            value.epoch = 0;
        } else {
            int shortform = MSG_ReadBit(msg);
            if (shortform < 0 || msg->overflowed) {
                failed = 1;
            } else if (shortform) {
                int step = MSG_ReadBits(msg, 4);
                if (msg->overflowed || step < 0 || !(base && base->known)) failed = 1;
                else { value.epoch = base->epoch + (uint32_t)step + 1u; value.known = 1; }
            } else {
                uint32_t epoch = (uint32_t)MSG_ReadBits(msg, 32);
                if (msg->overflowed) failed = 1;
                else { value.epoch = epoch; value.known = 1; }
            }
        }
    }
    if (!failed) {
        /* The pair's record, in the order the writer emitted it. */
        int changed_primary = MSG_ReadBit(msg);
        if (changed_primary < 0 || msg->overflowed) {
            failed = 1;
        } else if (changed_primary) {
            int captured = MSG_ReadBits(msg, 1);
            if (msg->overflowed || captured < 0) {
                failed = 1;
            } else if (!captured) {
                value.primary_known = 0;
                value.primary_weapon = 0;
                value.held_offhand = 0;
            } else {
                int weapon = MSG_ReadBits(msg, 16);
                int held = MSG_ReadBits(msg, 16);
                if (msg->overflowed || weapon < 0 || held < 0) failed = 1;
                else {
                    value.primary_weapon = (uint16_t)weapon; value.primary_known = 1;
                    value.held_offhand = (uint16_t)held;
                }
            }
        }
    }
    if(!failed) {
        int changed_vehicle=MSG_ReadBit(msg);
        if(changed_vehicle<0 || msg->overflowed) failed=1;
        else if(changed_vehicle) {
            int captured=MSG_ReadBits(msg,1);
            if(captured<0 || msg->overflowed) failed=1;
            else if(!captured) { value.vehicle_known=0; value.vehicle_identity=0; }
            else {
                int identity=MSG_ReadBits(msg,9);
                if(identity<0 || msg->overflowed || !(identity>>4)) failed=1;
                else { value.vehicle_known=1; value.vehicle_identity=(uint16_t)identity; }
            }
        }
        if(!failed && value.vehicle_known && (!es ||
            (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE))) failed=1;
    }
    if(!failed) {
        int changed_anim=MSG_ReadBit(msg);
        if(changed_anim<0 || msg->overflowed) failed=1;
        else if(changed_anim) {
            int captured=MSG_ReadBits(msg,1);
            if(captured<0 || msg->overflowed) failed=1;
            else if(!captured) {
                value.model_anim_known=0;
                value.model_anim_entry=0;
                value.model_anim_tree=0;
            } else {
                int entry=MSG_ReadBits(msg,12);
                int tree=MSG_ReadBits(msg,4);
                if(entry<0 || tree<0 || msg->overflowed || (!!entry!=!!tree)) failed=1;
                else {
                    value.model_anim_known=1;
                    value.model_anim_entry=(uint16_t)entry;
                    value.model_anim_tree=(unsigned char)tree;
                }
            }
        }
        if(!failed && value.model_anim_known && (!es ||
           es->eType!=ET_SCRIPTMOVER || es->solid==SOLID_BMODEL)) failed=1;
    }
    if(!failed) {
        int changed_link=MSG_ReadBit(msg);
        if(changed_link<0 || msg->overflowed)failed=1;
        else if(changed_link) {
            unsigned i; uint32_t bits;
            int info=MSG_ReadBits(msg,27);
            if(info<0 || msg->overflowed || ((unsigned)info&65535u)>ENTITYNUM_WORLD)failed=1;
            else {
                value.link_info=(unsigned)info;
                memset(value.link_origin,0,sizeof(value.link_origin));
                memset(value.link_angles,0,sizeof(value.link_angles));
                if(info&65535u) {
                    for(i=0;i<3;++i) {bits=(uint32_t)MSG_ReadBits(msg,32);memcpy(value.link_origin+i,&bits,4);}
                    for(i=0;i<3;++i) {bits=(uint32_t)MSG_ReadBits(msg,32);memcpy(value.link_angles+i,&bits,4);}
                    for(i=0;i<3;++i)if(!isfinite(value.link_origin[i]) || !isfinite(value.link_angles[i]))failed=1;
                    if(msg->overflowed)failed=1;
                }
            }
        }
    }
    if(!failed) {
        int changed_hide=MSG_ReadBit(msg);
        if(changed_hide<0 || msg->overflowed)failed=1;
        else if(changed_hide) {
            unsigned i;
            for(i=0;i<4;++i)value.hide_upper[i]=(uint32_t)MSG_ReadBits(msg,32);
            if(msg->overflowed)failed=1;
        }
    }
    if (!failed && value.known && es && es->eventSequence >= 0 && es->eventSequence <= 255 &&
        (value.epoch & 0xffu) != (unsigned)es->eventSequence) {
        /* The record was written beside this very entity state; halves that
         * disagree mean the stream is out of step. */
        desync(es, (unsigned)es->eventSequence, value.epoch);
        failed = 1;
    }
    if (failed) { msg->overflowed = 1; value = unknown_ext; }
    to = resolve(es);
    if (to) *to = value;
}
