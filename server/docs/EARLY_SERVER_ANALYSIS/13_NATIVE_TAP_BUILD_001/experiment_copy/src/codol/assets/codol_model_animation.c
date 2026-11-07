/* See codol_model_animation.h for the measured IW4 contract, the measured C1
 * consumer and registry, and the exact bounds of what this module publishes. */
#include "codol_model_animation.h"
#include "codol_assets.h"
#include "q_shared.h"
#include "xassets/xanims.h"

#include <string.h>

/* Registered names are asset names; the retained script string list bounds
 * them well below this. */
#define CODOL_MP_ANIM_NAME_CHARS 128

/* Retained script animtree access.
 *
 * Scr_GetAnims(id) is a plain read of gScrAnimPub+0x20c + id*4
 * (src/asmsource/_scr_animtree.asm:593), i.e. xanim_lookup[1][id], and its ids
 * are the 1-based ids Scr_UsingTreeInternal hands out (asm:473..479). It is
 * declared here rather than through cscr_animtree.h, whose scrAnimPub_t has a
 * C++ bool member.
 *
 * The tree count and the per-tree name live in the two asm objects below.
 * Both are globals of the retained assembly (asm:53, asm:68); they are
 * declared as bytes so this file does not have to restate a C++ struct, with
 * the offsets the same file measures:
 *   gScrAnimPub  +0x00c xanim_lookup[0][128]   +0x20c xanim_lookup[1][128]
 *                +0x40c xanim_num[2]           +0x414 animTreeIndex
 *   gScrAnimGlob +0x008 using_xanim_lookup[2][128], u16 variable ids,
 *                       written at asm:478 as [realm*128 + id]
 */
extern XAnim_s *Scr_GetAnims(unsigned int index);
extern void Scr_FindAnim(const char *tree_name, const char *anim_name,
                         uint32_t *anim, int user);
extern const char *XAnimGetAnimDebugName(XAnim_s *anims, unsigned int animIndex);
extern const char *SL_ConvertToString(unsigned int stringValue);
extern unsigned int GetVariableName(unsigned int id);
extern unsigned char gScrAnimPub[];
extern unsigned char gScrAnimGlob[];

#define CODOL_ANIM_TREE_COUNTS ((const unsigned int *)(gScrAnimPub + 0x40c))
#define CODOL_ANIM_TREE_NAMES ((const uint16_t *)(gScrAnimGlob + 0x008))

typedef struct {
    char name[CODOL_MP_ANIM_NAME_CHARS];
    unsigned used;
} codol_mp_anim_slot_t;

/* C1 408203 uses strncpy(...,63), then40820b writes byte63 to zero.
 * The local therefore retains up to63 characters plus the terminator. */
#define CODOL_CLIENT_TREE_NAME_CHARS 64

typedef struct {
    char name[CODOL_CLIENT_TREE_NAME_CHARS];
    unsigned char used;
} codol_client_tree_t;

static codol_mp_anim_slot_t s_bank[CODOL_MP_ANIM_SLOTS];
/* Ordered exactly as the client registers them: the id of s_client_trees[i]
 * is i + 1, because Scr_UsingTreeInternal hands out ++count[realm]. The table
 * is the full realm size, not the 15 the wire can carry, so a tree that lands
 * past 15 still consumes its id and shifts nothing. */
static codol_client_tree_t s_client_trees[CODOL_MODEL_ANIM_TREES];
static unsigned s_client_tree_count;
/* C1 0x408220's bgs->animData.animRefCount, replayed only for its effect on
 * registration: at 0x800 the append path is skipped, and with it the
 * Scr_UsingTreeInternal call, so a later list stops producing ids. */
static unsigned s_animlist_entries;
typedef struct {
    char tree[CODOL_CLIENT_TREE_NAME_CHARS];
    char anim[CODOL_MP_ANIM_NAME_CHARS];
    uint32_t resolved;
} codol_animlist_ref_t;
/* Scr_FindAnim keeps the output pointer until animtree construction, so these
 * references need map lifetime rather than parser-stack lifetime. */
static codol_animlist_ref_t s_animlist_refs[CODOL_ANIMLIST_MAX_ENTRIES];
static codol_model_anim_t s_entities[CODOL_MODEL_ANIMATION_ENTITIES];
static unsigned s_entity_trees[CODOL_MODEL_ANIMATION_ENTITIES];

static int valid_name(const char *name)
{
    if(!name || !*name) return 0;
    return strlen(name) + 1 <= CODOL_MP_ANIM_NAME_CHARS;
}

/* Canonical comparison follows C1 5cb860 and the retained
 * CreateCanonicalFilename, without allocating script-string references. */
static char fold(char c)
{
    if(c >= 'A' && c <= 'Z') return (char)(c - 'A' + 'a');
    if(c == '\\') return '/';
    return c;
}

static const char *skip_separators(const char *s)
{
    while(*s == '\\' || *s == '/') s++;
    return s;
}

static char canonical_next(const char **cursor)
{
    const char *s = *cursor;
    char c;
    for(;;) {
        c = *s;
        if(!c) { *cursor = s; return 0; }
        s++;
        /* Both implementations restart their separator-skipping loop after
         * control characters, and after emitting a single slash. Spaces are
         * retained. A trailing slash is retained too. */
        if((unsigned char)c < ' ') { s = skip_separators(s); continue; }
        c = fold(c);
        if(c == '/') s = skip_separators(s);
        *cursor = s;
        return c;
    }
}

static int same_name(const char *a, const char *b)
{
    char left, right;
    if(!a || !b) return 0;
    a = skip_separators(a);
    b = skip_separators(b);
    do {
        left = canonical_next(&a);
        right = canonical_next(&b);
        if(left != right) return 0;
    } while(left);
    return 1;
}

void CODOL_ResetModelAnimations(void)
{
    memset(s_bank, 0, sizeof(s_bank));
    memset(s_client_trees, 0, sizeof(s_client_trees));
    s_client_tree_count = 0;
    s_animlist_entries = 0;
    memset(s_animlist_refs, 0, sizeof(s_animlist_refs));
    memset(s_entities, 0, sizeof(s_entities));
    memset(s_entity_trees, 0, sizeof(s_entity_trees));
}

/* --- precache bank ---------------------------------------------------- */

int CODOL_RegisterMpAnimName(const char *name)
{
    unsigned slot;
    if(!valid_name(name)) return -1;
    /* IW4's G_FindConfigstringIndex scans from 1 and stops at the first empty
     * slot; a repeated name resolves to the slot it already owns. */
    for(slot = 1; slot < CODOL_MP_ANIM_SLOTS; slot++) {
        if(!s_bank[slot].used) break;
        if(!strcmp(s_bank[slot].name, name)) return (int)slot;
    }
    if(slot >= CODOL_MP_ANIM_SLOTS) return -1; /* "overflow mp anim" */
    memcpy(s_bank[slot].name, name, strlen(name) + 1);
    s_bank[slot].used = 1;
    return (int)slot;
}

int CODOL_FindMpAnimName(const char *name)
{
    unsigned slot;
    if(!valid_name(name)) return 0;
    for(slot = 1; slot < CODOL_MP_ANIM_SLOTS; slot++) {
        if(!s_bank[slot].used) break;
        if(!strcmp(s_bank[slot].name, name)) return (int)slot;
    }
    return 0;
}

const char *CODOL_MpAnimName(unsigned slot)
{
    if(!slot || slot >= CODOL_MP_ANIM_SLOTS || !s_bank[slot].used) return NULL;
    return s_bank[slot].name;
}

/* --- retained animtree registry --------------------------------------- */

unsigned CODOL_ServerAnimTreeCount(void)
{
    unsigned count = CODOL_ANIM_TREE_COUNTS[CODOL_MODEL_ANIM_SERVER_REALM];
    /* The registry has 128 realm-local slots; a larger count would mean the
     * layout assumed here is not the one in memory, so nothing is read. */
    if(count >= CODOL_MODEL_ANIM_TREES) return 0;
    return count;
}

/* Canonical server animtree names, copied out while the compiler's variable
 * objects are still alive.
 *
 * MEASURED 2026-09-20: XAnim_s->debugName is DEVELOPER-ONLY.
 * XAnimCreateAnims (src/asmsource/_xanim.asm:10883) allocates the XAnim_s and
 * initialises only ->size; ->debugName (offset 0) and ->debugAnimNames
 * (offset 8) are written exclusively inside the
 * "cmp byte [g_anim_developer], 0 / jnz" arm, and XAnimInit (:13183) latches
 * g_anim_developer from com_developer once at startup. bin/START-CODOL-SERVER.cmd
 * defaults CODOL_DEVELOPER=0, so on a production launch EVERY tree is built
 * with a NULL debugName and the old body below answered NULL for all of them.
 *
 * That is why the dogs killstreak never spawned: the "dog" scan in
 * CODOL_ActorPrepareAnimation matched nothing and refused every spawn, while
 * the same code worked under bin/START-CRASH-TEST.cmd, which defaults
 * CODOL_DEVELOPER=1. The feature had never worked on a production launch --
 * the test harness was hiding the defect.
 *
 * The name a tree was registered under lives in the compiler's
 * using_xanim_lookup table (CODOL_ANIM_TREE_NAMES), which is what
 * Scr_LoadAnimTreeAtIndex and CODOL_RegisterServerAnimListReferences below
 * already use, and it does not depend on a developer flag. Those variable
 * objects do not survive the load -- Scr_EndLoadAnimTrees ClearObject()s the
 * container and runs SL_ShutdownSystem(2), recycling the ids -- so the names
 * are snapshotted once at the end of script loading. */
static char s_server_tree_names[CODOL_MODEL_ANIM_TREES][CODOL_CLIENT_TREE_NAME_CHARS];
static unsigned s_server_tree_name_count;

void CODOL_SnapshotServerAnimTreeNames(void)
{
    unsigned count = CODOL_ServerAnimTreeCount(), i;
    memset(s_server_tree_names, 0, sizeof(s_server_tree_names));
    s_server_tree_name_count = 0;
    for(i = 1; i <= count && i < CODOL_MODEL_ANIM_TREES; ++i) {
        unsigned variable = CODOL_ANIM_TREE_NAMES[
            CODOL_MODEL_ANIM_SERVER_REALM * CODOL_MODEL_ANIM_TREES + i];
        unsigned handle = variable ? GetVariableName(variable) : 0;
        const char *name = handle ? SL_ConvertToString(handle) : NULL;
        if(!name || !*name) continue;
        Q_strncpyz(s_server_tree_names[i], name, CODOL_CLIENT_TREE_NAME_CHARS);
    }
    s_server_tree_name_count = count;
}

const char *CODOL_ServerAnimTreeName(unsigned server_tree)
{
    XAnim_s *anims;
    const char *name;
    if(!server_tree || server_tree > CODOL_ServerAnimTreeCount()) return NULL;
    /* The snapshot is the developer-independent answer; prefer it. */
    if(server_tree < CODOL_MODEL_ANIM_TREES &&
       server_tree <= s_server_tree_name_count &&
       s_server_tree_names[server_tree][0])
        return s_server_tree_names[server_tree];
    /* Fallback: a developer build still carries debugName, and a tree
     * registered after the snapshot (BG_LoadAnim's own "multiplayer") is only
     * reachable this way. */
    anims = Scr_GetAnims(server_tree);
    if(!anims) return NULL;
    name = anims->debugName;
    if(!name || !*name) return NULL;
    return name;
}

int CODOL_FindAnimInServerTree(unsigned server_tree, const char *name, unsigned *index)
{
    XAnim_s *anims;
    unsigned i;
    if(!valid_name(name)) return 0;
    if(!server_tree || server_tree > CODOL_ServerAnimTreeCount()) return 0;
    /* Scr_FindAnim writes (tree << 16) | index into every retained animlist
     * reference when the tree is built. This is available in production;
     * XAnim.debugAnimNames is developer metadata and may be NULL. */
    for(i = 0; i < s_animlist_entries; ++i) {
        uint32_t resolved = s_animlist_refs[i].resolved;
        if(!resolved || (resolved >> 16) != server_tree ||
           !same_name(s_animlist_refs[i].anim, name)) continue;
        if((resolved & 0xffffu) > CODOL_MODEL_ANIM_INDEX_MASK) return 0;
        if(index) *index = resolved & 0xffffu;
        return 1;
    }
    anims = Scr_GetAnims(server_tree);
    /* A registered tree that was never built has no entries to index. */
    if(!anims || !anims->size || !anims->debugAnimNames) return 0;
    for(i = 0; i < anims->size; i++) {
        const char *entry = XAnimGetAnimDebugName(anims, i);
        if(!entry || !same_name(entry, name)) continue;
        /* The wire carries 11 bits; a match the field cannot express is not a
         * usable answer, so it is refused rather than truncated. */
        if(i > CODOL_MODEL_ANIM_INDEX_MASK) return 0;
        if(index) *index = i;
        return 1;
    }
    return 0;
}

/* --- client correspondence -------------------------------------------- */

/* One '=' directive's worth of work: the id the client would hand this name,
 * assigning the next one when it is new. Returns 0 only when the realm's 128
 * slots are full, which is the point at which the client's own table would
 * overflow too. An empty name is a name here, because C1's per-file directive
 * buffer starts empty (0x4080ba) and an anim token before the first '='
 * registers whatever it holds: dropping it would shift every later id. */
static unsigned client_tree_register(const char *name)
{
    unsigned i;
    size_t len;
    if(!name) return 0;
    name = skip_separators(name);
    for(i = 0; i < s_client_tree_count; i++) {
        if(s_client_trees[i].used && same_name(s_client_trees[i].name, name)) return i + 1;
    }
    if(s_client_tree_count >= CODOL_MODEL_ANIM_TREES) return 0;
    len = strlen(name);
    if(len >= CODOL_CLIENT_TREE_NAME_CHARS) len = CODOL_CLIENT_TREE_NAME_CHARS - 1;
    memcpy(s_client_trees[s_client_tree_count].name, name, len);
    s_client_trees[s_client_tree_count].name[len] = '\0';
    s_client_trees[s_client_tree_count].used = 1;
    s_client_tree_count++;
    return s_client_tree_count;
}

/* C1 BeginParseSession627751 sets spaceDelimited (byte405) and clears
 * keepStringQuotes (406). Com_Parse627b72 therefore uses whitespace tokens;
 * its quoted arm627b1a..627b2b unescapes both quotes and backslashes. Keep
 * this reader bounded by the rawfile length as well as its NUL terminator. */
static const char *animlist_token(const char **pos, const char *end,
                                  char *out, size_t out_size)
{
    const char *p = *pos;
    size_t n = 0;
    for(;;) {
        while(p < end && *p && (unsigned char)*p <= ' ') p++;
        if(p >= end || !*p) { *pos = p; return NULL; }
        if(*p == '/' && p + 1 < end && p[1] == '/') {
            while(p < end && *p && *p != '\n') p++;
            continue;
        }
        if(*p == '/' && p + 1 < end && p[1] == '*') {
            p += 2;
            while(end - p >= 2 && *p && !(*p == '*' && p[1] == '/')) p++;
            if(end - p >= 2 && *p == '*' && p[1] == '/') p += 2;
            else { *pos = end; return NULL; }
            continue;
        }
        break;
    }
    if(*p == '"') {
        p++;
        while(p < end && *p && *p != '"') {
            char c = *p++;
            if(c == '\\' && p < end && (*p == '"' || *p == '\\')) c = *p++;
            if(n + 1 < out_size) out[n++] = c;
        }
        if(p < end && *p == '"') p++;
    } else {
        while(p < end && (unsigned char)*p > ' ') {
            if(n + 1 < out_size) out[n++] = *p;
            p++;
        }
    }
    out[n] = '\0';
    *pos = p;
    return out;
}

int CODOL_ParseAnimListClientTrees(const char *text, int length)
{
    /* C1 keeps the current directive in a per-file local that starts empty
     * (0x4080ba), so a directive does not carry across list files. */
    char tree[CODOL_CLIENT_TREE_NAME_CHARS];
    char token[1024]; /* C1 token cap627b42/627b80:1023 characters plus NUL. */
    const char *pos, *end;
    int registered = 0;
    if(!text || length <= 0) return 0;
    tree[0] = '\0';
    pos = text;
    end = text + length;
    while(animlist_token(&pos, end, token, sizeof(token))) {
        if(!token[0]) break; /* C1 loader4081ec..4081f0 ends on an empty token. */
        if(token[0] == '=') {
            /* 0x4081fb: the directive is the token past '=', and it consumes
             * no entry index. */
            size_t len = strlen(token + 1);
            if(len >= sizeof(tree)) len = sizeof(tree) - 1;
            memcpy(tree, token + 1, len);
            tree[len] = '\0';
            continue;
        }
        /* 0x408220: past the array bound nothing is appended and nothing is
         * registered. */
        if(s_animlist_entries >= CODOL_ANIMLIST_MAX_ENTRIES) break;
        if(!client_tree_register(tree)) return -1;
        {
            codol_animlist_ref_t *ref = &s_animlist_refs[s_animlist_entries];
            size_t tree_len = strlen(tree), anim_len = strlen(token);
            if(tree_len >= sizeof(ref->tree)) tree_len = sizeof(ref->tree) - 1;
            if(anim_len >= sizeof(ref->anim)) anim_len = sizeof(ref->anim) - 1;
            memcpy(ref->tree, tree, tree_len);
            ref->tree[tree_len] = '\0';
            memcpy(ref->anim, token, anim_len);
            ref->anim[anim_len] = '\0';
            ref->resolved = 0;
        }
        s_animlist_entries++;
        registered++;
    }
    return registered;
}

/* The rawfile bodies live in the mounted client zones, which is where the
 * client reads them from too (C1 0x4080cc looks the path up with
 * DB_FindXAssetHeader for rawfile, not through the filesystem). */
static int animlist_load_one(const char *list_name)
{
    const codol_engine_rawfile_t *raw = NULL;
    char path[CODOL_MP_ANIM_NAME_CHARS];
    size_t len;
    int status;
    if(!list_name || !*list_name) return 0;
    len = strlen(list_name);
    if(len + sizeof("animlists/.animlist") > sizeof(path)) return -1;
    memcpy(path, "animlists/", 10);
    memcpy(path + 10, list_name, len);
    memcpy(path + 10 + len, ".animlist", sizeof(".animlist"));
    status = CODOL_LoadEngineRawFile(path, &raw);
    /* An absent list is optional (C1 408112); an invalid mounted rawfile is
     * not absence. Skipping it would shift all subsequent tree identities. */
    if(status == 0) return 0;
    if(status != 1 || !raw || !raw->buffer || raw->len < 0) return -1;
    if(CODOL_ParseAnimListClientTrees(raw->buffer, raw->len) < 0) return -1;
    return 1;
}

int CODOL_LoadClientAnimTrees(const char *map_name, unsigned anim_flags,
                              unsigned *tree_count)
{
    static const char *const names[] = {
        "common", "common_actor_shared", "common_human", "common_dog",
        "common_civilian", "common_zombie"
    };
    static const unsigned masks[] = {
        0, CODOL_ANIMLIST_ACTOR_SHARED_MASK, CODOL_ANIMLIST_HUMAN,
        CODOL_ANIMLIST_DOG, CODOL_ANIMLIST_CIVILIAN, CODOL_ANIMLIST_ZOMBIE
    };
    int loaded = 0, status;
    unsigned i;

    memset(s_client_trees, 0, sizeof(s_client_trees));
    s_client_tree_count = 0;
    s_animlist_entries = 0;
    memset(s_animlist_refs, 0, sizeof(s_animlist_refs));

    /* C1 40831e..4083e3 order. Missing class lists clear their own bit in
     * C1, which cannot affect any later list's different bit. This registry
     * builder does not publish an effective actor-availability mask. */
    for(i=0;i<sizeof(names)/sizeof(names[0]);i++) {
        if(masks[i] && !(anim_flags & masks[i])) continue;
        status = animlist_load_one(names[i]);
        if(status < 0) goto invalid;
        loaded += status;
    }
    if(map_name && *map_name) {
        status = animlist_load_one(map_name);
        if(status < 0) goto invalid;
        loaded += status;
    }

    /* 0x450ba1, after the lists and before the loader: the client's own
     * "multiplayer" registration. It takes the next free id when no list
     * already claimed the name, so it is replayed here for the same reason -
     * to keep the ids of anything registered after it correct. */
    if(!client_tree_register("multiplayer")) goto invalid;

    if(tree_count) *tree_count = s_client_tree_count;
    return loaded;
invalid:
    memset(s_client_trees,0,sizeof(s_client_trees));
    s_client_tree_count = 0;
    s_animlist_entries = 0;
    memset(s_animlist_refs, 0, sizeof(s_animlist_refs));
    return -1;
}

unsigned CODOL_RegisterServerAnimListReferences(void)
{
    unsigned i, registered = 0;
    for(i = 0; i < s_animlist_entries; ++i) {
        codol_animlist_ref_t *ref = &s_animlist_refs[i];
        unsigned tree, count;
        int server_uses_tree = 0;
        /* C1 still consumes an entry before the first '=tree', but an empty
         * name is not a legal retained server tree. */
        if(!ref->tree[0] || !ref->anim[0]) continue;
        count = CODOL_ServerAnimTreeCount();
        for(tree = 1; tree <= count; ++tree) {
            unsigned variable = CODOL_ANIM_TREE_NAMES[
                CODOL_MODEL_ANIM_SERVER_REALM * CODOL_MODEL_ANIM_TREES + tree];
            unsigned handle = variable ? GetVariableName(variable) : 0;
            const char *name = handle ? SL_ConvertToString(handle) : NULL;
            if(name && same_name(name, ref->tree)) {
                server_uses_tree = 1;
                break;
            }
        }
        /* Client animlists also name client-only trees. Loading those in the
         * dedicated VM can demand XAnim assets intentionally absent from its
         * zones. Only augment trees already declared by server scripts. */
        if(!server_uses_tree) continue;
        ref->resolved = 0;
        Scr_FindAnim(ref->tree, ref->anim, &ref->resolved,
                     CODOL_MODEL_ANIM_SERVER_REALM);
        registered++;
    }
    return registered;
}

unsigned CODOL_ClientAnimTreeCount(void)
{
    return s_client_tree_count;
}

const char *CODOL_ClientAnimTreeName(unsigned client_tree)
{
    if(!client_tree || client_tree > s_client_tree_count) return NULL;
    if(!s_client_trees[client_tree - 1].used) return NULL;
    return s_client_trees[client_tree - 1].name;
}

int CODOL_BindClientAnimTree(const char *tree_name, unsigned client_tree)
{
    unsigned i;
    if(!valid_name(tree_name)) return 0;
    if(!client_tree || client_tree > CODOL_MODEL_ANIM_CLIENT_TREES) return 0;
    tree_name = skip_separators(tree_name);
    /* The same name at a second id, or a second name at this id, would make
     * publication depend on declaration order; both are refused. */
    for(i = 0; i < s_client_tree_count; i++) {
        if(s_client_trees[i].used && same_name(s_client_trees[i].name, tree_name)) {
            return i + 1 == client_tree;
        }
    }
    if(client_tree <= s_client_tree_count && s_client_trees[client_tree - 1].used) {
        return 0;
    }
    {
        size_t len = strlen(tree_name);
        if(len >= CODOL_CLIENT_TREE_NAME_CHARS) len = CODOL_CLIENT_TREE_NAME_CHARS - 1;
        memcpy(s_client_trees[client_tree - 1].name, tree_name, len);
        s_client_trees[client_tree - 1].name[len] = '\0';
        s_client_trees[client_tree - 1].used = 1;
    }
    /* An id declared past the end leaves the ids before it unnamed rather
     * than renumbering anything. */
    if(client_tree > s_client_tree_count) s_client_tree_count = client_tree;
    return 1;
}

int CODOL_ClientAnimTreeForServerTree(unsigned server_tree, unsigned *client_tree)
{
    const char *name = CODOL_ServerAnimTreeName(server_tree);
    unsigned i;
    if(!name) return 0;
    for(i = 0; i < s_client_tree_count; i++) {
        if(!s_client_trees[i].used) continue;
        if(!same_name(s_client_trees[i].name, name)) continue;
        /* Wire 0x094 is 4 bits: an id past 15 exists on the client but cannot
         * be named on the wire, so it is not an answer. */
        if(i + 1 > CODOL_MODEL_ANIM_CLIENT_TREES) return 0;
        if(client_tree) *client_tree = i + 1;
        return 1;
    }
    return 0;
}

unsigned CODOL_ClientAnimTreeBindingCount(void)
{
    return s_client_tree_count;
}

/* --- resolution -------------------------------------------------------- */

int CODOL_ResolveMpAnim(const char *name, unsigned server_tree, codol_model_anim_t *out)
{
    unsigned tree, index = 0, client = 0;
    unsigned found_tree = 0, found_index = 0, found_client = 0, matches = 0;
    if(!valid_name(name) || !out) return 0;

    /* Production XAnim trees may omit debugName/debugAnimNames. The animlist
     * producer already gives us both stable identities: Scr_FindAnim writes
     * the server tree/index into resolved, while ref->tree reproduces C1's
     * client tree registration name and therefore its 1-based wire id. */
    for(tree = 0; tree < s_animlist_entries; ++tree) {
        const codol_animlist_ref_t *ref = &s_animlist_refs[tree];
        uint32_t resolved = ref->resolved;
        unsigned resolved_tree, resolved_index, i, resolved_client = 0;
        if(!resolved || !same_name(ref->anim, name)) continue;
        resolved_tree = resolved >> 16;
        resolved_index = resolved & 0xffffu;
        if(server_tree && resolved_tree != server_tree) continue;
        if(!resolved_tree || resolved_index > CODOL_MODEL_ANIM_INDEX_MASK) continue;
        for(i = 0; i < s_client_tree_count; ++i) {
            if(s_client_trees[i].used && same_name(s_client_trees[i].name, ref->tree)) {
                resolved_client = i + 1;
                break;
            }
        }
        if(!resolved_client || resolved_client > CODOL_MODEL_ANIM_CLIENT_TREES) continue;
        if(matches && (found_tree != resolved_tree || found_index != resolved_index ||
                       found_client != resolved_client)) return 0;
        found_tree = resolved_tree;
        found_index = resolved_index;
        found_client = resolved_client;
        matches = 1;
    }
    if(matches == 1) {
        memset(out, 0, sizeof(*out));
        out->server_tree = found_tree;
        out->client_tree = found_client;
        out->index = found_index;
        out->active = 1;
        return 1;
    }

    if(server_tree) {
        if(!CODOL_ClientAnimTreeForServerTree(server_tree, &client)) return 0;
        if(!CODOL_FindAnimInServerTree(server_tree, name, &index)) return 0;
        found_tree = server_tree;
        found_index = index;
        found_client = client;
        matches = 1;
    } else {
        /* Only declared trees are searched, and the name has to be unique
         * among them: the same name may sit at different indices in different
         * trees, so a first match is not an answer. */
        unsigned count = CODOL_ServerAnimTreeCount();
        for(tree = 1; tree <= count; tree++) {
            if(!CODOL_ClientAnimTreeForServerTree(tree, &client)) continue;
            if(!CODOL_FindAnimInServerTree(tree, name, &index)) continue;
            matches++;
            if(matches > 1) return 0;
            found_tree = tree;
            found_index = index;
            found_client = client;
        }
    }
    if(matches != 1) return 0;

    memset(out, 0, sizeof(*out));
    out->server_tree = found_tree;
    out->client_tree = found_client;
    out->index = found_index;
    out->active = 1;
    return 1;
}

/* --- per-entity live intent -------------------------------------------- */

void CODOL_ResetEntityModelAnimation(unsigned entity)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return;
    memset(&s_entities[entity], 0, sizeof(s_entities[entity]));
    s_entity_trees[entity] = 0;
}

int CODOL_BindEntityAnimTree(unsigned entity, unsigned server_tree)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    if(server_tree && server_tree > CODOL_ServerAnimTreeCount()) return 0;
    s_entity_trees[entity] = server_tree;
    return 1;
}

unsigned CODOL_EntityAnimTree(unsigned entity)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    return s_entity_trees[entity];
}

int CODOL_PrepareModelAnimation(unsigned entity, unsigned slot, int start_time,
                                int variant, codol_model_anim_t *out)
{
    codol_model_anim_t resolved;
    const char *name;
    if(!out || entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    name = CODOL_MpAnimName(slot);
    if(!name) return 0;
    if(!CODOL_ResolveMpAnim(name, s_entity_trees[entity], &resolved)) return 0;
    /* The start consumer tests the entire packed word for zero. Refuse an
     * unencodable play before replacing the entity's previous animation. */
    if(!resolved.index && !variant) return 0;

    /* One animation per entity: a second play replaces the first, exactly as
     * the reference handler's two stores do. The sequence keeps the replay
     * visible to the server even though the pair did not change. */
    resolved.slot = slot;
    resolved.variant = variant ? 1u : 0u;
    resolved.start_time = start_time;
    resolved.sequence = s_entities[entity].sequence + 1;
    *out = resolved;
    return 1;
}

void CODOL_CommitModelAnimation(unsigned entity,const codol_model_anim_t *prepared)
{
    /* Only a successfully prepared value for this entity may be committed.
     * No resolution or allocation is allowed after its snapshot capture. */
    if(entity < CODOL_MODEL_ANIMATION_ENTITIES && prepared)
        s_entities[entity] = *prepared;
}

int CODOL_SetModelAnimation(unsigned entity,unsigned slot,int start_time,int variant)
{
    codol_model_anim_t prepared;
    if(!CODOL_PrepareModelAnimation(entity,slot,start_time,variant,&prepared)) return 0;
    CODOL_CommitModelAnimation(entity,&prepared);
    return 1;
}

int CODOL_ClearModelAnimation(unsigned entity)
{
    unsigned sequence;
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    /* The clear is a state transition, not a reset of the entity's history:
     * the tree binding and the play counter survive it. */
    sequence = s_entities[entity].sequence;
    memset(&s_entities[entity], 0, sizeof(s_entities[entity]));
    s_entities[entity].sequence = sequence;
    return 1;
}

int CODOL_ModelAnimationCaptureLive(unsigned entity, codol_model_anim_t *out)
{
    if(!out) return 0;
    memset(out, 0, sizeof(*out));
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    if(!s_entities[entity].active) return 0;
    *out = s_entities[entity];
    return 1;
}

int CODOL_ModelAnimationState(unsigned entity, unsigned *slot, int *start_time)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES || !slot || !start_time) return 0;
    if(!s_entities[entity].active) return 0;
    *slot = s_entities[entity].slot;
    *start_time = s_entities[entity].start_time;
    return 1;
}

const char *CODOL_ModelAnimationName(unsigned entity)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return NULL;
    if(!s_entities[entity].active) return NULL;
    return CODOL_MpAnimName(s_entities[entity].slot);
}

unsigned CODOL_ModelAnimationSequence(unsigned entity)
{
    if(entity >= CODOL_MODEL_ANIMATION_ENTITIES) return 0;
    return s_entities[entity].sequence;
}

/* --- wire encoding ------------------------------------------------------ */

int CODOL_ModelAnimationEncode(const codol_model_anim_t *state, uint32_t *wire060, uint32_t *wire094)
{
    uint32_t value;
    if(!state || !wire060 || !wire094) return 0;
    if(!state->active) return 0;
    if(!state->client_tree || state->client_tree > CODOL_MODEL_ANIM_CLIENT_TREES) return 0;
    if(state->index > CODOL_MODEL_ANIM_INDEX_MASK) return 0;
    value = state->index & CODOL_MODEL_ANIM_INDEX_MASK;
    if(state->variant) value |= CODOL_MODEL_ANIM_VARIANT_BIT;
    /* C1 43fd0e tests the whole field, not the index: index 0 without the
     * variant bit is indistinguishable from "no animation" on the wire, so it
     * is not published as if it were playable. */
    if(!value) return 0;
    *wire060 = value;
    *wire094 = state->client_tree;
    return 1;
}

void CODOL_ModelAnimationEncodeCleared(uint32_t *wire060, uint32_t *wire094)
{
    if(wire060) *wire060 = 0;
    if(wire094) *wire094 = 0;
}
