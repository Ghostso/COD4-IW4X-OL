/*
 * codol_script_childthread.h -- native GSC "childthread" support.
 *
 * CoD4's VM has no childthread construct. Opcodes 0x50..0x53 (ordinary calls)
 * use AllocChildThread() to build a VAR_CHILD_THREAD *call frame* parented to
 * the caller's frame; opcodes 0x54..0x57 (thread calls) use AllocThread() to
 * build a root thread. The IW-line "childthread" keyword is a third thing: a
 * root thread, scheduled like "thread", with inherited endon subscriptions.
 * Its exact lifetime rules remain under investigation, as described below.
 *
 *   1. source recognition   Scr_ChildThread_LowerSource() rewrites the keyword
 *                           in place, byte-length preserving, and records the
 *                           source span of every childthread call: receiverless
 *                           or receiver-qualified, local, far (ns\file::func)
 *                           or function pointer.
 *   2. compiler tagging     Scr_ChildThread_MapOpcode() is called from the four
 *                           thread-call emit sites in EmitPostFunctionCall with
 *                           the AST node's own source positions, and returns the
 *                           childthread opcode when they identify a recorded
 *                           call. Positions are byte offsets into the source
 *                           buffer (same basis as Scr_GetLineNumInternal).
 *   3. runtime lifetime   Scr_ChildThread_Start() allocates an ordinary root
 *                           thread and then replays onto it, one by one, the
 *                           endon subscriptions currently held by the calling
 *                           frame and by every ancestor frame up to the root
 *                           thread. Each replay is exactly the pair of
 *                           registrations OP_endon performs, with the child as
 *                           the endon-ing frame, so both death orders are
 *                           handled by the engine's own code and the module
 *                           needs neither bookkeeping nor a hook in
 *                           Scr_KillThread. The script evidence for that rule,
 *                           with file:line, is at the head of layer 3 in the
 *                           .cpp.
 *
 * Feature state: the source-level construct is evidenced in the IW4/IW5 script
 * corpora and the inheritance rule above is derived from specific sites in them
 * (af_chase_knife_fight_code.gsc create_dof_targetent/dof_target_manager and
 * af_chase_waterfall.gsc rapids_scene/rumbly_rocks_bumps for inheritance at all,
 * _utility.gsc create_blend -> _utility_code.gsc process_blend for ancestor
 * scope, hamburg_tank_ai.gsc:46 vs :73 for the start-time snapshot). The two
 * sub-rules that previously held this module back -- snapshot versus live link,
 * and whether the child additionally ends with the caller's root thread -- are
 * answered at the head of layer 3 in the .cpp from those sites. No engine-side
 * definition was read out of a reference binary and nothing here has been
 * observed running, so the derivation is a script-level argument, not a
 * measurement.
 */

#ifndef __CODOL_SCRIPT_CHILDTHREAD_H__
#define __CODOL_SCRIPT_CHILDTHREAD_H__

#include "q_shared.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Kill switch: 0 explicitly rejects childthread during source preparation and
 * keeps the opcode mapper at identity. Keyword detection still runs so the
 * retained parser cannot miscompile the disabled construct as an identifier.
 * Parser/compiler/VM integration is installed in source; it has not yet been
 * built or exercised. Inheritance semantics are derived from script evidence. */
#define CODOL_CHILDTHREAD_ENABLED 1

/* Bytecode extension. Stock CoD4 uses 0x00..0x86; the VM dispatch bound is
 * raised to 0x8A. Operand layout of each opcode is identical to the thread-call
 * opcode it mirrors, so the operand-size tables reuse the same handlers. */
#define OP_ScriptChildThreadCall              0x87 /* mirrors 0x54 */
#define OP_ScriptChildThreadCallPointer       0x88 /* mirrors 0x55 */
#define OP_ScriptMethodChildThreadCall        0x89 /* mirrors 0x56 */
#define OP_ScriptMethodChildThreadCallPointer 0x8A /* mirrors 0x57 */

#define CHILDTHREAD_OPCODE_DELTA (OP_ScriptChildThreadCall - 0x54)

/* ---------------------------------------------------------------- layer 1 */

/* qtrue when the buffer contains a childthread keyword; lets the caller take a
 * writable copy before lowering a buffer it does not own. */
qboolean Scr_ChildThread_SourceHasKeyword(const char *buf, int len);

/* Rewrites every childthread keyword in buf to "thread" plus padding and
 * records the call spans for filename. The rewrite preserves every byte offset,
 * line and column, so recorded spans and compiler source positions share one
 * coordinate system. Must run on the buffer that is handed to the parser, i.e.
 * after any other source lowering.
 *
 * qtrue on success. On a malformed construct or an allocation failure it
 * returns qfalse with *errMsg set and *errPos at the offending byte; spans
 * recorded for the file are dropped and the buffer keeps whatever was already
 * rewritten, so the caller must fail the script rather than compile it. */
qboolean Scr_ChildThread_LowerSource(const char *filename, char *buf, int len,
                                     const char **errMsg, int *errPos);

void Scr_ChildThread_ClearFile(const char *filename);
void Scr_ChildThread_ClearAll(void);

/* ---------------------------------------------------------------- layer 2 */

/* Selects whose spans MapOpcode consults. LowerSource sets it for the file it
 * lowered, but that selection does not survive to compile time: ScriptCompile
 * (_scr_compiler.asm:10913) calls Scr_LoadScriptInternal for #include'd files,
 * so a nested file is prepared -- and selects itself -- in the middle of the
 * including file's own compilation. The integration therefore has to re-select
 * around the compile, next to the save/restore of gScrParserPub.scriptfilename
 * that Scr_LoadScriptInternal (scr_vm_main.c:1230..1240) already performs, and
 * with the same name: the extFilename ("<script>.gsc"/".gsx") that
 * Scr_PrepareSource records spans under. filename == NULL selects nothing. */
void Scr_ChildThread_BeginFile(const char *filename);

/* callPos and funcPos are the call node's sourcePos fields (sval+0x8, sval+0xc)
 * as passed by EmitPostFunctionCall. Returns opcode unchanged unless it is
 * 0x54..0x57 and a position identifies a recorded childthread call. */
int Scr_ChildThread_MapOpcode(int opcode, int callPos, int funcPos);

qboolean Scr_ChildThread_IsChildOpcode(int opcode);

/* ---------------------------------------------------------------- layer 3 */

/* Allocates the root thread of a childthread call and gives it the endon
 * subscriptions of the calling frame chain. Returns the new thread's local id
 * for fs.localId, exactly as AllocThread() does for a thread call.
 *
 * Allocators raise Scr_TerminalError instead of returning 0. This prevents a
 * normal partial-child return. The VM error handler routes terminal allocation
 * failures through RuntimeError to fatal Com_Error(ERR_SCRIPT) shutdown; it
 * does not roll back registrations or resume the caller. */
unsigned int __cdecl Scr_ChildThread_Start(unsigned int self, unsigned int parentLocalId);

#ifdef __cplusplus
}
#endif

#endif /* __CODOL_SCRIPT_CHILDTHREAD_H__ */
