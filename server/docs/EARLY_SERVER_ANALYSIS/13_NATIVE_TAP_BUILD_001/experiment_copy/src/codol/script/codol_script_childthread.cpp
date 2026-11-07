/*
 * codol_script_childthread.cpp -- native GSC "childthread" support.
 *
 * Substrate facts this module is built on, each read out of this tree's own
 * sources (file:line given) rather than assumed:
 *
 *  - ordinary call opcodes 0x50..0x53 build VAR_CHILD_THREAD *frames* through
 *    AllocChildThread(self, callerFrame) (cscr_variable.cpp:1045); thread calls
 *    0x54..0x57 build root threads through AllocThread(self)
 *    (cscr_variable.cpp:1027). "childthread" is neither, so it gets its own
 *    opcodes and its own allocator entry point.
 *  - AllocThread() leaves refCount == 0 and does NOT reference its self object;
 *    OP_endon adds that reference explicitly and Scr_KillEndonThread()
 *    (cscr_variable.cpp:2358) releases it.
 *  - OP_endon (0x7A, VM_ExecuteInternal_4050, _scr_vm.asm:3006..3067) performs
 *    TWO registrations, not one:
 *      a) marker = AllocThread(endoningFrame), filed as an object-keyed entry
 *         in object[OBJECT_ENDONLIST][notifyName]  (asm:3026..3043), then
 *         RemoveRefToObject(marker) drops the allocation reference, leaving the
 *         array key as the owner;
 *      b) gScrVarPub.pauseArrayId[endoningFrame][marker] = VAR_POINTER(object)
 *         via GetObjectVariable/GetArray/GetNewObjectVariable/SetNewVariableValue
 *         (asm:3044..3062), and Scr_SetThreadNotifyName(marker, notifyName)
 *         (asm:3063).
 *    Both stack operands are popped with "sub dword [gFs+0xc], 0x10" and no
 *    RemoveRefToValue (asm:3065): the string reference is transferred to the
 *    marker's notify name and the object reference is transferred to the
 *    VAR_POINTER stored in the pause array. SetNewVariableValue()
 *    (cscr_variable.cpp:2435) stores the union raw, so it takes no reference of
 *    its own. A native registration therefore has to *own* both references
 *    before handing them over.
 *  - Scr_KillThread(frameId) (cscr_variable.cpp:2376) walks
 *    pauseArrayId[frameId] and, per entry, calls VM_CancelNotify(pointerValue,
 *    marker) + Scr_KillEndonThread(marker) + RemoveObjectVariable(...), i.e. the
 *    engine itself unregisters every endon a dying frame had registered. That is
 *    why (b) is mandatory: with (a) alone, a childthread that ends before its
 *    parent leaves a marker in the parent's endon list pointing at a released
 *    frame id, and the engine has no record with which to remove it.
 *  - VM_Notify(object, name, params) (_scr_vm.asm:632) is the other half: per
 *    marker in object[OBJECT_ENDONLIST][name] it runs VM_CancelNotifyInternal,
 *    Scr_KillEndonThread, RemoveObjectVariable on the registering frame's pause
 *    entry (asm:985..1000) and VM_TerminateStack on the registering frame. So a
 *    correctly registered pair needs no teardown code of its own here: the
 *    engine handles both death orders. VM_CancelNotifyInternal calls
 *    Scr_RemoveThreadNotifyName (asm:212), which does SL_RemoveRefToString
 *    (cscr_variable.cpp:2714) -- that is what balances the transferred string
 *    reference, in both orders.
 *  - This draft no longer calls VM_Notify or installs a Scr_KillThread
 *    callback. Inherited registrations use native notification teardown.
 *
 * IW4 evidence for the construct itself is source-level only, and is recorded in
 * obj/claude-workers/childthread-repair-report.md: the IW4 and IW5 script
 * corpora under .../alpha0022/vendor use "childthread" in both receiverless and
 * receiver-qualified form, and af_chase_knife_fight_code.gsc:970 comments a
 * childthread entry point with "childthread acquires endons". No engine-level
 * definition of the construct was obtained from any binary: iw4x.exe, the Black
 * Ops dedicated server (which exports the full cscr_* symbol set, has
 * AllocChildThread, and has nothing else childthread-shaped) and C1.exe contain
 * no childthread symbol or string. The binding implemented here -- inheritance
 * of the caller frame chain's endon subscriptions -- is derived from the script
 * corpus, with the exact sites and the reasoning quoted at the head of layer 3
 * below. It is a derivation, not a measurement. The native source integration
 * is enabled by CODOL_CHILDTHREAD_ENABLED; builds and runtime verification are
 * still deferred during the missing-function writing pass.
 */

#include "q_shared.h"
#include "qcommon.h"
#include "scr_vm.h"
#include "cscr_variable.h"
#include "cscr_stringlist.h"
#include "codol_script_childthread.h"

#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#ifdef CODOL_SERVER
static_assert(OP_CoDOLChildThreadCall == OP_ScriptChildThreadCall &&
              OP_CoDOLChildThreadCallPointer == OP_ScriptChildThreadCallPointer &&
              OP_CoDOLMethodChildThreadCall == OP_ScriptMethodChildThreadCall &&
              OP_CoDOLMethodChildThreadCallPointer == OP_ScriptMethodChildThreadCallPointer &&
              OP_count == OP_ScriptMethodChildThreadCallPointer + 1,
              "CoDOL public opcode enum must match the childthread extension");
#endif

/* Reserved variable name of an object's endon list, as used by OP_endon. */
#define OBJECT_ENDONLIST 0x18000u

/* ====================================================================== */
/* layer 1: source recognition                                            */
/* ====================================================================== */

typedef struct
{
    int stmtStart;   /* receiver start, or keyword when the receiver may not be
                      * used as a match anchor (see CT_ReceiverAnchor)        */
    int keyword;
    int funcRef;     /* first byte of the function reference or of "[["       */
    int parenOffset; /* '(' of the argument list                              */
    int end;         /* one past the closing ')'                              */
    unsigned char form;
    unsigned char hasReceiver;
} childThreadSpan_t;

#define CT_FORM_LOCAL   0
#define CT_FORM_FAR     1
#define CT_FORM_POINTER 2

typedef struct
{
    char *name;
    childThreadSpan_t *spans;
    int count;
    int capacity;
} childThreadFile_t;

static childThreadFile_t *ct_files = NULL;
static int ct_fileCount = 0;
static int ct_fileCapacity = 0;
static int ct_currentFile = -1;

static int CT_FindFile(const char *filename)
{
    int i;

    for (i = 0; i < ct_fileCount; ++i)
    {
        if (ct_files[i].name && !Q_stricmp(ct_files[i].name, filename))
        {
            return i;
        }
    }
    return -1;
}

static void CT_FreeSpans(int file)
{
    if (ct_files[file].spans)
    {
        free(ct_files[file].spans);
        ct_files[file].spans = NULL;
    }
    ct_files[file].count = 0;
    ct_files[file].capacity = 0;
}

/* Returns the file slot for filename, growing the table. -1 on allocation
 * failure; there is no silent cap. */
static int CT_GetFile(const char *filename)
{
    childThreadFile_t *grown;
    int capacity;
    int i;

    i = CT_FindFile(filename);
    if (i >= 0)
    {
        return i;
    }
    if (ct_fileCount == ct_fileCapacity)
    {
        capacity = ct_fileCapacity ? ct_fileCapacity * 2 : 64;
        grown = (childThreadFile_t *)realloc(ct_files, capacity * sizeof(childThreadFile_t));
        if (!grown)
        {
            return -1;
        }
        memset(grown + ct_fileCapacity, 0, (capacity - ct_fileCapacity) * sizeof(childThreadFile_t));
        ct_files = grown;
        ct_fileCapacity = capacity;
    }
    i = ct_fileCount;
    ct_files[i].name = strdup(filename);
    if (!ct_files[i].name)
    {
        return -1;
    }
    ct_files[i].spans = NULL;
    ct_files[i].count = 0;
    ct_files[i].capacity = 0;
    ++ct_fileCount;
    return i;
}

static qboolean CT_AddSpan(int file, const childThreadSpan_t *span)
{
    childThreadSpan_t *grown;
    int capacity;

    if (ct_files[file].count == ct_files[file].capacity)
    {
        capacity = ct_files[file].capacity ? ct_files[file].capacity * 2 : 16;
        grown = (childThreadSpan_t *)realloc(ct_files[file].spans, capacity * sizeof(childThreadSpan_t));
        if (!grown)
        {
            return qfalse;
        }
        ct_files[file].spans = grown;
        ct_files[file].capacity = capacity;
    }
    ct_files[file].spans[ct_files[file].count++] = *span;
    return qtrue;
}

static qboolean CT_IsIdentStart(int c) { return (qboolean)(isalpha(c) || c == '_'); }
static qboolean CT_IsIdentChar(int c)  { return (qboolean)(isalnum(c) || c == '_'); }

static int CT_SkipTrivia(const char *buf, int len, int i)
{
    while (i < len)
    {
        if (buf[i] == ' ' || buf[i] == '\t' || buf[i] == '\r' || buf[i] == '\n' || buf[i] == '\f')
        {
            ++i;
            continue;
        }
        if (buf[i] == '/' && i + 1 < len && buf[i + 1] == '/')
        {
            i += 2;
            while (i < len && buf[i] != '\n')
            {
                ++i;
            }
            continue;
        }
        if (buf[i] == '/' && i + 1 < len && buf[i + 1] == '*')
        {
            i += 2;
            while (i + 1 < len && !(buf[i] == '*' && buf[i + 1] == '/'))
            {
                ++i;
            }
            i = (i + 1 < len) ? i + 2 : len;
            continue;
        }
        break;
    }
    return i;
}

static int CT_ScanFunctionRef(const char *buf, int len, int i, unsigned char *form)
{
    int last;

    *form = CT_FORM_LOCAL;
    if (i >= len || !CT_IsIdentStart((unsigned char)buf[i]))
    {
        return -1;
    }
    while (i < len && CT_IsIdentChar((unsigned char)buf[i]))
    {
        ++i;
    }
    for (;;)
    {
        last = i;
        if (i < len && buf[i] == '\\')
        {
            ++i;
            if (i >= len || !CT_IsIdentStart((unsigned char)buf[i]))
            {
                return -1;
            }
            while (i < len && CT_IsIdentChar((unsigned char)buf[i]))
            {
                ++i;
            }
            *form = CT_FORM_FAR;
            continue;
        }
        if (i + 1 < len && buf[i] == ':' && buf[i + 1] == ':')
        {
            i += 2;
            if (i >= len || !CT_IsIdentStart((unsigned char)buf[i]))
            {
                return -1;
            }
            while (i < len && CT_IsIdentChar((unsigned char)buf[i]))
            {
                ++i;
            }
            *form = CT_FORM_FAR;
            return i;
        }
        i = last;
        break;
    }
    return i;
}

static int CT_ScanArgumentList(const char *buf, int len, int i)
{
    int depth = 0;

    while (i < len)
    {
        if (buf[i] == '"')
        {
            ++i;
            while (i < len && buf[i] != '"')
            {
                i += (buf[i] == '\\') ? 2 : 1;
            }
            ++i;
            continue;
        }
        if (buf[i] == '/' && i + 1 < len && (buf[i + 1] == '/' || buf[i + 1] == '*'))
        {
            i = CT_SkipTrivia(buf, len, i);
            continue;
        }
        if (buf[i] == '(')
        {
            ++depth;
        }
        else if (buf[i] == ')')
        {
            --depth;
            if (!depth)
            {
                return i + 1;
            }
        }
        ++i;
    }
    return -1;
}

/* Walks back over the receiver expression. The result is used only to widen the
 * match window to the left, and only when the receiver text cannot itself
 * contain a thread-call node -- otherwise a nested "thread" call in the
 * receiver could be mistaken for this call. */
static int CT_ReceiverAnchor(const char *buf, int keyword, qboolean *hasReceiver)
{
    int i = keyword - 1;
    int depth = 0;
    int start = keyword;
    int p;

    *hasReceiver = qfalse;
    while (i >= 0 && (buf[i] == ' ' || buf[i] == '\t'))
    {
        --i;
    }
    if (i < 0 || buf[i] == ';' || buf[i] == '{' || buf[i] == '}' || buf[i] == '\n')
    {
        return keyword;
    }
    while (i >= 0)
    {
        if (buf[i] == ']' || buf[i] == ')')
        {
            ++depth;
            --i;
            continue;
        }
        if (buf[i] == '[' || buf[i] == '(')
        {
            if (!depth)
            {
                break;
            }
            --depth;
            --i;
            continue;
        }
        if (depth)
        {
            --i;
            continue;
        }
        if (CT_IsIdentChar((unsigned char)buf[i]) || buf[i] == '.' || buf[i] == '"')
        {
            start = i;
            --i;
            continue;
        }
        break;
    }
    if (start >= keyword)
    {
        return keyword;
    }
    *hasReceiver = qtrue;
    /* refuse the wider anchor when the receiver could hold a thread call */
    for (p = start; p + 6 <= keyword; ++p)
    {
        if (!Q_stricmpn(&buf[p], "thread", 6))
        {
            return keyword;
        }
    }
    return start;
}

qboolean Scr_ChildThread_SourceHasKeyword(const char *buf, int len)
{
    int i;

    if (!buf)
    {
        return qfalse;
    }
    for (i = 0; i + 11 <= len; ++i)
    {
        if ((buf[i] == 'c' || buf[i] == 'C') && !Q_stricmpn(&buf[i], "childthread", 11))
        {
            return qtrue;
        }
    }
    return qfalse;
}

qboolean Scr_ChildThread_LowerSource(const char *filename, char *buf, int len,
                                     const char **errMsg, int *errPos)
{
    childThreadSpan_t span;
    const char *dummyMsg;
    int dummyPos;
    int file;
    int i;
    int identEnd;
    int next;
    int refEnd;
    unsigned char form;
    qboolean hasReceiver;

    if (!errMsg)
    {
        errMsg = &dummyMsg;
    }
    if (!errPos)
    {
        errPos = &dummyPos;
    }
    *errMsg = NULL;
    *errPos = 0;

    if (!buf || len <= 0 || !filename)
    {
        return qtrue;
    }

    file = CT_GetFile(filename);
    if (file < 0)
    {
        *errMsg = "out of memory recording childthread calls";
        return qfalse;
    }
    CT_FreeSpans(file);
    ct_currentFile = file;

    for (i = 0; i < len;)
    {
        if (buf[i] == '"')
        {
            ++i;
            while (i < len && buf[i] != '"')
            {
                i += (buf[i] == '\\') ? 2 : 1;
            }
            ++i;
            continue;
        }
        if (buf[i] == '/' && i + 1 < len && (buf[i + 1] == '/' || buf[i + 1] == '*'))
        {
            i = CT_SkipTrivia(buf, len, i);
            continue;
        }
        if (!CT_IsIdentStart((unsigned char)buf[i]))
        {
            ++i;
            continue;
        }

        identEnd = i;
        while (identEnd < len && CT_IsIdentChar((unsigned char)buf[identEnd]))
        {
            ++identEnd;
        }
        if (identEnd - i != 11 || Q_stricmpn(&buf[i], "childthread", 11))
        {
            i = identEnd;
            continue;
        }
        if (i > 0 && (buf[i - 1] == '.' || buf[i - 1] == '\\' || buf[i - 1] == ':'))
        {
            i = identEnd; /* member or namespace component, not the keyword */
            continue;
        }

        if (!CODOL_CHILDTHREAD_ENABLED)
        {
            *errMsg = "childthread support is disabled";
            *errPos = i;
            CT_FreeSpans(file);
            return qfalse;
        }
        memset(&span, 0, sizeof(span));
        span.keyword = i;

        next = CT_SkipTrivia(buf, len, identEnd);
        span.funcRef = next;
        if (next + 1 < len && buf[next] == '[' && buf[next + 1] == '[')
        {
            form = CT_FORM_POINTER;
            next += 2;
            while (next + 1 < len && !(buf[next] == ']' && buf[next + 1] == ']'))
            {
                ++next;
            }
            if (next + 1 >= len)
            {
                *errMsg = "unterminated [[ ]] after childthread";
                *errPos = i;
                CT_FreeSpans(file);
                return qfalse;
            }
            refEnd = next + 2;
        }
        else
        {
            refEnd = CT_ScanFunctionRef(buf, len, next, &form);
            if (refEnd < 0)
            {
                *errMsg = "childthread must be followed by a function name or [[ ]]";
                *errPos = i;
                CT_FreeSpans(file);
                return qfalse;
            }
        }

        next = CT_SkipTrivia(buf, len, refEnd);
        if (next >= len || buf[next] != '(')
        {
            *errMsg = "childthread must be followed by a function call";
            *errPos = i;
            CT_FreeSpans(file);
            return qfalse;
        }
        span.parenOffset = next;
        span.end = CT_ScanArgumentList(buf, len, next);
        if (span.end < 0)
        {
            *errMsg = "unterminated argument list in childthread call";
            *errPos = i;
            CT_FreeSpans(file);
            return qfalse;
        }
        span.form = form;
        span.stmtStart = CT_ReceiverAnchor(buf, i, &hasReceiver);
        span.hasReceiver = (unsigned char)hasReceiver;

        if (!CT_AddSpan(file, &span))
        {
            *errMsg = "out of memory recording childthread calls";
            *errPos = i;
            CT_FreeSpans(file);
            return qfalse;
        }

        /* "childthread" -> "thread" + padding. Same byte length, so offsets,
         * lines and columns of the whole file are unchanged and the recorded
         * spans share the compiler's coordinate system. */
        memcpy(&buf[i], "thread", 6);
        memset(&buf[i + 6], ' ', 5);
        i = identEnd;
    }

    return qtrue;
}

void Scr_ChildThread_ClearFile(const char *filename)
{
    int file = CT_FindFile(filename);

    if (file >= 0)
    {
        CT_FreeSpans(file);
        if (ct_currentFile == file)
        {
            ct_currentFile = -1;
        }
    }
}

void Scr_ChildThread_ClearAll(void)
{
    int i;

    for (i = 0; i < ct_fileCount; ++i)
    {
        CT_FreeSpans(i);
        if (ct_files[i].name)
        {
            free(ct_files[i].name);
            ct_files[i].name = NULL;
        }
    }
    if (ct_files)
    {
        free(ct_files);
        ct_files = NULL;
    }
    ct_fileCount = 0;
    ct_fileCapacity = 0;
    ct_currentFile = -1;
}

/* ====================================================================== */
/* layer 2: compiler tagging                                              */
/* ====================================================================== */

/* Span tables are per file and MapOpcode sees only source offsets, so the
 * selection has to be right at every emit. LowerSource's own selection is NOT
 * enough: ScriptCompile (_scr_compiler.asm:10694) calls Scr_LoadScriptInternal
 * (asm:10913) for #include'd files, so a nested file is prepared -- selecting
 * itself -- in the middle of the including file's compilation, and nothing
 * restores the outer selection afterwards. The integration therefore re-selects
 * around ScriptCompile in Scr_LoadScriptInternal (scr_vm_main.c:1230..1240),
 * beside the gScrParserPub.scriptfilename save/restore already there and with
 * the same name. Without that, a thread call emitted after an include is matched
 * against the wrong file's spans. */
void Scr_ChildThread_BeginFile(const char *filename)
{
    ct_currentFile = filename ? CT_FindFile(filename) : -1;
}

qboolean Scr_ChildThread_IsChildOpcode(int opcode)
{
    return (qboolean)(opcode >= OP_ScriptChildThreadCall && opcode <= OP_ScriptMethodChildThreadCallPointer);
}

static qboolean CT_PositionSelects(const childThreadSpan_t *span, int pos)
{
    /* The window runs from the anchor to the '(' of the argument list. A call
     * nested in the arguments lies to the right of it, a call in the receiver
     * to the left of the keyword (and the anchor is only widened over a
     * receiver that provably contains no thread call), so no other thread-call
     * node can fall inside. */
    return (qboolean)(pos >= span->stmtStart && pos <= span->parenOffset);
}

int Scr_ChildThread_MapOpcode(int opcode, int callPos, int funcPos)
{
    const childThreadFile_t *f;
    const childThreadSpan_t *span;
    int best = -1;
    int bestWidth = 0;
    int width;
    int i;

    if (!CODOL_CHILDTHREAD_ENABLED)
    {
        return opcode; /* identity while the feature is not confirmed */
    }
    if (opcode < OP_ScriptThreadCall || opcode > OP_ScriptMethodThreadCallPointer)
    {
        return opcode;
    }
    if (ct_currentFile < 0)
    {
        return opcode;
    }

    f = &ct_files[ct_currentFile];
    for (i = 0; i < f->count; ++i)
    {
        span = &f->spans[i];
        if (!CT_PositionSelects(span, callPos) && !CT_PositionSelects(span, funcPos))
        {
            continue;
        }
        width = span->parenOffset - span->stmtStart;
        if (best < 0 || width < bestWidth)
        {
            best = i;
            bestWidth = width;
        }
    }
    if (best < 0)
    {
        return opcode;
    }
    return opcode + CHILDTHREAD_OPCODE_DELTA;
}

/* ====================================================================== */
/* layer 3: runtime lifetime -- inherited endon subscriptions              */
/* ====================================================================== */

/* WHAT A CHILDTHREAD IS, and why this is not a "bind to the caller's root
 * thread" implementation.
 *
 * Reference evidence (vendor GSC, read in this pass):
 *
 *  A. vendor/iw4/maps/af_chase_knife_fight_code.gsc:955..966
 *         create_dof_targetent()
 *         {
 *             level notify( "new_dof_targetent" );
 *             level endon( "new_dof_targetent" );
 *             level endon( "kill_dof_management" );
 *             ent = Spawn( "script_origin", ... );  ent endon( "death" );
 *             level.dof_targetent = ent;
 *             childthread dof_target_manager( ent );
 *             return ent;
 *         }
 *     and af_chase_knife_fight_code.gsc:970  "// childthread acquires endons"
 *     at the head of dof_target_manager, whose body is an unconditional
 *     while(1)/wait .05 loop with no endon and no exit of its own
 *     (af_chase_knife_fight_code.gsc:968..996).
 *
 *     The three endons are registered in create_dof_targetent's OWN frame and
 *     that frame returns on the next line. In this engine a normal function
 *     return runs Scr_KillThread(fs.localId) (_scr_vm.asm:3208..3215 and
 *     :3404..3411, both "GetSafeParentLocalId(fs.localId); Scr_KillThread(
 *     fs.localId)"), and Scr_KillThread walks pauseArrayId[frameId] and
 *     cancels + kills every endon marker that frame registered
 *     (cscr_variable.cpp:2392..2413). So the caller's own endons are gone
 *     microseconds after the childthread starts. For "kill_dof_management" to
 *     still stop dof_target_manager later (restore_dof(),
 *     af_chase_knife_fight_code.gsc:999..1005, and every blend_to_*_dof()
 *     which opens with level notify("kill_dof_management")), and for the next
 *     create_dof_targetent()'s leading level notify("new_dof_targetent") to
 *     stop the previous manager, the CHILD must hold its own copies of those
 *     registrations. Lifetime-linking the child to the caller's root thread
 *     cannot produce that behaviour: the notify would have nothing to hit.
 *
 *  B. Ancestor scope. vendor/iw4/maps/_utility.gsc:15583..15587
 *         create_blend( func, var1, var2, var3 )
 *         { ent = SpawnStruct(); ent childthread process_blend( func, self,
 *           var1, var2, var3 ); return ent; }
 *     create_blend registers no endon at all, and neither does
 *     process_blend (vendor/iw4/maps/_utility_code.gsc:1406..1445, a
 *     waittillframeend + for/wait .05 loop). Nor does its caller blend_dof()
 *     (_utility.gsc:15561..15565). The only endon in the chain is two frames
 *     up, e.g. blend_to_knife_dof() (af_chase_knife_fight_code.gsc:1042..1057)
 *     which does level notify("kill_dof_management"); level
 *     endon("kill_dof_management"); ... blend_dof(...). Those functions are the
 *     mutual-cancellation mechanism for DOF blends: each one notifies
 *     "kill_dof_management" to stop the blend that is already running. The
 *     running blend is the process_blend childthread, so it can only be
 *     stopped if it inherited an endon registered TWO frames above the
 *     childthread statement. Hence the inherited set is the effective set of
 *     the caller's whole frame chain, not just of fs.localId.
 *
 * What this module therefore implements: a childthread is an ordinary root
 * thread (AllocThread, exactly like a thread call) whose start replays, onto
 * itself, every endon registration currently held by the caller's frame chain
 * -- fs.localId, then each VAR_CHILD_THREAD parent via GetSafeParentLocalId
 * (cscr_variable.cpp:2455..2478), up to and including the root VAR_THREAD.
 * Each replay is byte-for-byte the work OP_endon does (_scr_vm.asm:3006..3067,
 * dissected in the file header), with the child as the endon-ing frame, so
 * from the moment it returns the child is indistinguishable from a thread that
 * had executed those endon statements itself. Every teardown order is then the
 * engine's own: Scr_KillThread(child) unregisters them if the child ends
 * first, VM_Notify kills the child if the object is notified first.
 *
 * Consequences that follow from this, and are NOT separate mechanisms:
 *   - the child outlives the frame that started it (A);
 *   - the child outlives the caller's root thread when that thread merely
 *     returns, and dies with it when that thread is ended by one of the
 *     inherited conditions;
 *   - no bookkeeping outside the variable system, no hook in Scr_KillThread,
 *     and no failure path that could hand the VM a partially bound thread.
 *
 *  C. Second, independent site for the same rule.
 *     vendor/iw4/maps/af_chase_waterfall.gsc:177..179
 *         level endon ( "clear_rapids_junk" );
 *         childthread rumbly_rocks_bumps();
 *     rumbly_rocks_bumps (af_chase_waterfall.gsc:1099..1112) is a bare while(1)
 *     with no endon and no exit, and clear_rapids_junk() (:79..81) is
 *     "level notify( "clear_rapids_junk" )", threaded at :894. Again the child
 *     can only be stopped through an endon it inherited from the caller.
 *
 *  D. START-TIME SNAPSHOT, not a live link. This is what the previous draft
 *     left open, and it is decided by a shipped IW5 script.
 *     vendor/iw5/maps/hamburg_tank_ai.gsc
 *         24  _id_7D9C()
 *         27      self notify( "stop_turret_attack_think_hamburg" );
 *         28      self endon( "stop_turret_attack_think_hamburg" );
 *         46      childthread _id_7DA7();
 *         73      self endon( "death" );
 *     with the child being
 *         _id_7DA7() { self waittill( "death" );
 *                      level.tanks = array_remove( level.tanks, self ); }
 *     Under a live link the child would carry self endon("death") -- an endon
 *     for exactly the notify it exists to wait for. VM_Notify (_scr_vm.asm:632)
 *     opens by resolving object[OBJECT_ENDONLIST][name] and, per marker, runs
 *     VM_CancelNotifyInternal + Scr_KillEndonThread + RemoveObjectVariable and
 *     terminates the registering frame's stack (asm:985..1000); under a live
 *     link that frame is the child, so the tank's removal from level.tanks --
 *     the sole purpose of the childthread -- would be killed by the death
 *     notify it is waiting for. Under the snapshot the child inherits only
 *     "stop_turret_attack_think_hamburg", i.e. the re-entrancy guard the
 *     function set up two lines earlier, and the cleanup runs.
 *     A full scan of the corpus (obj/claude-workers/childthread-finalize-scan.py,
 *     109 sites in vendor/iw4, iw5, iw4x, iw5_wii) finds three further sites
 *     with a later endon in the same function; all three are satisfied by the
 *     snapshot, and in the one whose child needs an endon at all (C) the
 *     operative registration is the one placed before the statement.
 *     So: live-link semantics contradicts shipped content, snapshot semantics is
 *     consistent with every site. That is an inconsistency argument, not a
 *     positive measurement -- it does not exclude some third rule that also fits.
 *
 * Not established:
 *   - no engine-side definition was obtained from any binary (see header). All
 *     of A..D is derived from shipped script behaviour.
 *   - whether IW additionally ends the child when the caller's root thread
 *     ends normally. Evidence A/B/C do not need it, and af_chase_knife_fight.gsc
 *     reuses level.dof_targetent across separate scene functions
 *     (:445,:512,:553,:666,:751,:927) while create_dof_targetent runs once,
 *     which argues against it; that is an argument, not a measurement.
 *   - nothing here has been assembled, compiled, linked or run.
 */

/* Type of an object id, screening 0. Scr_GetObjectType() (cscr_variable.cpp:
 * 2115) reads w.type & VAR_MASK and asserts only in debug builds that the entry
 * is not VAR_STAT_FREE; every id this module passes it comes either from
 * fs.localId, from GetSafeParentLocalId (which itself screens VAR_STAT_FREE,
 * cscr_variable.cpp:2459) or from a live pause-array key, so none of them can
 * be a freed slot at the point of the call. */
static unsigned int CT_ObjectType(unsigned int id)
{
    if (!id)
    {
        return VAR_UNDEFINED;
    }
    return Scr_GetObjectType(id);
}

static qboolean CT_IsLiveFrame(unsigned int id)
{
    unsigned int type;

    type = CT_ObjectType(id);
    /* VAR_THREAD..VAR_CHILD_THREAD; VAR_DEAD_THREAD is deliberately excluded. */
    return (qboolean)(type >= VAR_THREAD && type <= VAR_CHILD_THREAD);
}

/* An endon marker, as OP_endon builds it (_scr_vm.asm:3018..3025, :3063):
 * a freshly allocated thread whose self is the endon-ing frame, later retyped
 * to VAR_NOTIFY_THREAD by Scr_SetThreadNotifyName. pauseArrayId[frame] is
 * keyed by that marker id and valued with the endon-ed object
 * (asm:3044..3062).
 *
 * The key test "markerId != frameId" is not redundant: the waittill handler
 * (_scr_vm.asm:2925..2957) also writes a pauseArrayId entry, but it registers
 * fs.localId itself rather than a separate marker thread, so a suspended
 * waittill is excluded here. A childthread must inherit endon conditions, not
 * the caller's pending waittill. */
static qboolean CT_IsEndonMarker(unsigned int frameId, unsigned int markerId)
{
    if (!markerId || markerId == frameId)
    {
        return qfalse;
    }
    if (CT_ObjectType(markerId) != VAR_NOTIFY_THREAD)
    {
        return qfalse;
    }
    return (qboolean)(Scr_GetSelf(markerId) == frameId);
}

/* pauseArrayId[frameId] as an array object id, without creating it. */
static unsigned int CT_PauseObject(unsigned int frameId)
{
    unsigned int pauseVar;

    if (!gScrVarPub.pauseArrayId)
    {
        return 0;
    }
    pauseVar = FindObjectVariable(gScrVarPub.pauseArrayId, frameId);
    if (!pauseVar)
    {
        return 0;
    }
    return FindObject(pauseVar);
}

/* True when childRoot already carries an endon for exactly this (object, name)
 * pair. The same pair can legitimately appear in two frames of one chain
 * (a function that re-registers an endon its caller already holds); replaying
 * it twice would leave a second marker that the first notify's
 * VM_TerminateStack has to clean up mid-walk. Scanning the child's own pause
 * array keeps the deduplication free of any storage of this module's own,
 * avoiding an allocation just for deduplication. Replaying an endon still
 * allocates native variable entries and can exhaust them. */
static qboolean CT_ChildHasEndon(unsigned int childRoot, unsigned int object, unsigned int notifyName)
{
    unsigned int pauseObj;
    unsigned int entryId;
    unsigned int markerId;

    pauseObj = CT_PauseObject(childRoot);
    if (!pauseObj)
    {
        return qfalse;
    }
    for (entryId = FindFirstSibling(pauseObj); entryId; entryId = FindNextSibling(entryId))
    {
        markerId = GetVariableKeyObject(entryId);
        if (!CT_IsEndonMarker(childRoot, markerId))
        {
            continue;
        }
        if (Scr_GetThreadNotifyName(markerId) != notifyName)
        {
            continue;
        }
        if ((unsigned int)GetVariableValueAddress(entryId)->intValue == object)
        {
            return qtrue;
        }
    }
    return qfalse;
}

/* Replays one endon onto childRoot. Step for step OP_endon
 * (_scr_vm.asm:3018..3063), with the two references the opcode transfers off
 * the operand stack acquired explicitly instead:
 *   childRoot  is the endon-ing frame -> marker->self, released by
 *              Scr_KillEndonThread() (cscr_variable.cpp:2358);
 *   object     is the endon-ed object -> owned by the VAR_POINTER stored in
 *              pauseArrayId[childRoot][marker], released when that entry goes;
 *   notifyName -> the marker's notify name, released by
 *              Scr_RemoveThreadNotifyName() (cscr_variable.cpp:2714) reached
 *              from VM_CancelNotify(Internal) (_scr_vm.asm:212).
 * Allocation exhaustion raises Scr_TerminalError rather than returning 0.
 * During execution Scr_ErrorInternal jumps to the VM error handler, which calls
 * RuntimeError and then Com_Error(ERR_SCRIPT) for the terminal flag. The current
 * Com_Error path shuts down the server and calls Sys_Error; it does not resume
 * the caller with a partial child. This is fatal error handling, not rollback;
 * references and a partial registration can exist until shutdown. */
static void CT_InheritEndon(unsigned int childRoot, unsigned int object, unsigned int notifyName)
{
    VariableValue pointerValue;
    unsigned int marker;
    unsigned int byName;
    unsigned int pauseList;
    unsigned int entry;

    SL_AddRefToString(notifyName);

    AddRefToObject(childRoot);
    marker = AllocThread(childRoot);

    /* (a) object[OBJECT_ENDONLIST][notifyName][marker] */
    byName = GetArray(GetVariable(GetArray(GetVariable(object, OBJECT_ENDONLIST)), notifyName));
    GetObjectVariable(byName, marker);
    RemoveRefToObject(marker);

    /* (b) pauseArrayId[childRoot][marker] = VAR_POINTER(object) */
    pauseList = GetArray(GetObjectVariable(gScrVarPub.pauseArrayId, childRoot));
    entry = GetNewObjectVariable(pauseList, marker);
    AddRefToObject(object);
    pointerValue.type = VAR_POINTER;
    pointerValue.u.intValue = (int)object;
    SetNewVariableValue(entry, &pointerValue);

    Scr_SetThreadNotifyName(marker, notifyName);
}

/* Replays every endon frameId holds onto childRoot. The sibling walk captures
 * the next id before registering, and only ever holds hash ids (the same
 * discipline Scr_KillThread uses across RemoveObjectVariable,
 * cscr_variable.cpp:2395..2412), so the insertions this makes into
 * pauseArrayId[childRoot] and into object[OBJECT_ENDONLIST] -- neither of
 * which is the array being walked -- cannot invalidate the walk. */
static void CT_InheritFrameEndons(unsigned int childRoot, unsigned int frameId)
{
    unsigned int pauseObj;
    unsigned int entryId;
    unsigned int nextId;
    unsigned int markerId;
    unsigned int object;
    unsigned int notifyName;

    pauseObj = CT_PauseObject(frameId);
    if (!pauseObj)
    {
        return;
    }

    for (entryId = FindFirstSibling(pauseObj); entryId; entryId = nextId)
    {
        nextId = FindNextSibling(entryId);

        markerId = GetVariableKeyObject(entryId);
        if (!CT_IsEndonMarker(frameId, markerId))
        {
            continue;
        }
        object = (unsigned int)GetVariableValueAddress(entryId)->intValue;
        if (!object || CT_ObjectType(object) == VAR_UNDEFINED)
        {
            continue;
        }
        notifyName = Scr_GetThreadNotifyName(markerId);
        if (!notifyName)
        {
            continue;
        }
        if (CT_ChildHasEndon(childRoot, object, notifyName))
        {
            continue;
        }
        CT_InheritEndon(childRoot, object, notifyName);
    }
}

unsigned int __cdecl Scr_ChildThread_Start(unsigned int self, unsigned int parentLocalId)
{
    unsigned int childRoot;
    unsigned int frameId;

    /* Identical to the thread-call opcodes' AllocThread(self): the caller has
     * already taken the self reference (see the patched handlers), and the id
     * the VM installs in fs.localId is a complete, live root thread before any
     * inheritance work starts. */
    childRoot = AllocThread(self);

    /* Caller's frame chain, innermost first: fs.localId, then each
     * VAR_CHILD_THREAD parent, ending at the root VAR_THREAD, for which
     * GetSafeParentLocalId returns 0. A childthread started outside any frame
     * simply inherits nothing and is an ordinary thread; that is not an error
     * condition and raises none. */
    for (frameId = parentLocalId; frameId; frameId = GetSafeParentLocalId(frameId))
    {
        if (!CT_IsLiveFrame(frameId) || frameId == childRoot)
        {
            break;
        }
        CT_InheritFrameEndons(childRoot, frameId);
    }

    return childRoot;
}
