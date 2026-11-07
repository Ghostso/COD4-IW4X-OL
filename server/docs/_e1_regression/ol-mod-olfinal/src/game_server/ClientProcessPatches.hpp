#pragma once

#include <cstdint>
#include <span>

namespace CodolGameServer
{
    // Native battery HUD units, with a safe default before replicated dvars arrive.
    int clientBatteryDisplayDivisor(double multiplier);
    bool patchClientBatteryDisplayBuffer(std::span<std::uint8_t> image,
        std::uintptr_t imageBase, std::uintptr_t replacement);
    enum class ClientProcessPatchResult
    {
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        UnexpectedTarget,
        ProtectionFailed,
    };

    enum class ClientRawInputPatchResult
    {
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    ClientProcessPatchResult installClientBatteryDisplayPatch();

    enum class PlaintextConfigPatchResult
    {
        NotRequested,
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    const char *plaintextConfigPatchResultName(PlaintextConfigPatchResult result);

    // WRITE AND READ players/config_mp.cfg AS PLAIN TEXT.
    //
    // The game ALREADY writes it as text and then re-encrypts it in a second pass.
    // Com_WriteConfigToFile 0x004FDAF0 prints the header, unbindall, the binds and the
    // dvars into the file, closes it, and only then does
    //
    //     if (!strcmp(name, "config_mp.cfg")) { read back; sub_7BC570(name, len, size);
    //                                           write back; }
    //
    // and the read path 0x004F30C0 is the mirror -- the SAME sub_7BC570, so the cipher is
    // symmetric, and it is keyed on the FILE NAME, which is why settings_c.zip.iw4 needs
    // its own key. Both gates are the identical inlined strcmp ending in one conditional
    // jump, so turning "jump when the name is NOT config_mp.cfg" into an unconditional
    // jump skips the second pass on write and the decrypt on read:
    //
    //     0x004FDBCC   75 6E  jnz  ->  EB 6E     never re-encrypt what was just written
    //     0x004F3119   75 34  jnz  ->  EB 34     never decrypt what is about to be run
    //
    // MIGRATION IS GRACEFUL AND NEEDS NO FILE DELETED. An existing ENCRYPTED config, read
    // without decryption, fails the "starts with //" validation at 0x004F3144 and is
    // ignored; the game then writes a fresh plaintext one on exit.
    //
    // Off unless OLMOD_PLAINTEXT_CONFIG=1, and it refuses any build whose bytes differ.
    PlaintextConfigPatchResult installPlaintextConfigPatch();

    enum class MaxFpsCeilingPatchResult
    {
        NotRequested,
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    const char *maxFpsCeilingPatchResultName(MaxFpsCeilingPatchResult result);

    // RAISE THE CEILING com_maxfps IS REGISTERED WITH.
    //
    // Com_InitDvars registers it at 0x004FC400 as
    //     Dvar_RegisterInt("com_maxfps", value=200, min=0, MAX=200, flags=ARCHIVE, desc)
    // so 200 is not a default a player can raise -- it is the dvar's own upper bound, and
    // any higher value clamps back down on set AND on config load. That is why the graphics
    // menu's "uncapped" writes 200 and why ~186-190 is where everyone lands: the limiter is
    // 1000/maxfps in INTEGER milliseconds, so 200 asks for 5 ms and Sleep(1) rounding makes
    // it about 5.3.
    //
    // This rewrites the imm32 of the `push 0C8h` that supplies MAX (0x004FC408), leaving the
    // DEFAULT push at 0x004FC40F alone -- so nothing changes for anyone who never sets the
    // dvar, and a value that is set now survives a config round-trip instead of clamping.
    //
    // ORDERING IS THE RISK AND IT FAILS SAFE. The push only matters while Com_InitDvars is
    // still to run; patching after registration writes a byte nothing will execute again and
    // changes nothing. It cannot corrupt an already-registered dvar.
    //
    // AND THE CEILING IS NOT FREE ABOVE ~320. The client makes one usercmd per rendered
    // frame, so fps/10 of them arrive per 100 ms server frame against a queue of
    // PendingUserCmdCapacity: measured 2026-09-06, com_maxfps 0 gave 490 fps, pending sat at
    // 32 and cmdAge reached 268 ms, and the player called it unbelievably laggy.
    //
    // OLMOD_MAXFPS_CEILING=<n>, 1..10000.
    MaxFpsCeilingPatchResult installMaxFpsCeilingPatch();

    enum class TclsMappingResult
    {
        NotRequested,      // OLMOD_TCLS_BLOB is unset -- Windows keeps SampleLauncher's path
        AlreadyVisible,    // another process had it; we now HOLD a handle so it cannot vanish
        Published,         // we created it in THIS process and filled it from the blob file
        BlobUnreadable,    // OLMOD_TCLS_BLOB names a file we cannot read
        CreateFailed,      // CreateFileMapping refused
        MapFailed,         // MapViewOfFile refused
    };

    const char *tclsMappingResultName(TclsMappingResult result);

    // PUBLISH TCLS_SHAREDMEMEMORY<pid> FROM INSIDE THE CLIENT.
    //
    // TenProxy opens that name during this process's own startup and dies at [100] if it
    // cannot. SampleLauncher creates it from ANOTHER process, which works on Windows and was
    // measured NOT to work under Wine on 2026-09-05: the mapping existed twice over --
    // pre-published across a window of pids AND published again on discovery, pid 352 inside
    // the window 276..2320 -- and TenProxy still got `OpenFileMapping ... fail! Error code = 2`.
    // A name that exists and cannot be opened from the target process is a namespace boundary,
    // and no amount of publishing from outside crosses one.
    //
    // Doing it HERE cannot hit that: same process, so the same session, the same architecture
    // and the same namespace as the caller that will look for it. The timing is settled too --
    // this runs where "client process patch patched" is logged, measured ~30 s before TenProxy
    // asked on the failing machine.
    //
    // The BLOB comes from a file rather than being rebuilt here, because SampleLauncher already
    // knows how to compose it and a file crosses any namespace a mapping cannot.
    //
    // IT ALSO ANSWERS THE QUESTION: it tries OpenFileMapping FIRST and reports whether another
    // process's mapping was visible, from the exact place TenProxy asks.
    TclsMappingResult publishTclsMapping();

    // Exposed for deterministic tests. Runtime installation additionally
    // validates the CODOL PE identity and imported function target.
    bool patchClientExecutionStateBuffer(std::span<std::uint8_t> image);
    bool patchClientRawMouseCallBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);

    using ClientAlphaWeaponPrepareCallback = void (*)();

    // CL_ParseGamestate clears and rebuilds the client's native weapon
    // registry in one call. Alpha WeaponDefs linked while the player is in the
    // frontend therefore disappear after the last ordinary-weapon pass but
    // before the modular pass resolves strings that refer to them. Redirect
    // only that second pass's call so the callback can restore the ordinary
    // alpha definitions at their server-assigned indices first.
    bool patchClientAlphaWeaponGamestateCallBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientAlphaWeaponGamestatePatch(
        ClientAlphaWeaponPrepareCallback callback);

    // A missing looping-effect asset must not take down the client. The
    // retail effect runner dereferences its FxEffectDef without a null check;
    // this redirects the shared worker entry through a guard and otherwise
    // keeps the original call ABI and implementation.
    bool patchClientLoopFxWorkerEntryBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientLoopFxNullGuardPatch();

    // CG_EntityEvent reads a WeaponDef flag before its later null check. Guard
    // that one read so a malformed or weaponless presentation event follows
    // the native function's existing null-WeaponDef path instead of crashing.
    bool patchClientEntityEventWeaponGuardBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientEntityEventWeaponGuardPatch();

    // Reject entity-event ids outside the native dispatcher's 0..184 table.
    // The stock default arm raises ERR_DROP and indexes the name table with the
    // invalid value; a stale network event should have no client-side effect.
    bool patchClientEntityEventRangeGuardBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientEntityEventRangeGuardPatch();

    // BG ammo lookup receives weapon 0 during some death/respawn transitions.
    // Return zero ammo instead of dereferencing a missing WeaponDef.
    bool patchClientAmmoLookupWeaponGuardBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientAmmoLookupWeaponGuardPatch();

    // Inventory aggregation must skip a nonzero weapon index whose WeaponDef
    // is unavailable after a death/respawn registry transition.
    bool patchClientWeaponInventoryGuardBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientWeaponInventoryGuardPatch();

    // UI expression operators use a 20 x 3 x 3 function-pointer table. Reject
    // invalid operator/type indices through the resolver's native null result.
    bool patchClientUiOperatorResolverGuardBuffer(
        std::span<std::uint8_t> image,
        std::uintptr_t imageBase,
        std::uintptr_t replacement);
    ClientProcessPatchResult installClientUiOperatorResolverGuardPatch();

    enum class UnsignedFastfilePatchResult
    {
        NotRequested,
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    // Permit locally repacked OLFinal fastfiles while retaining the native
    // header, version, SHA-256 block checks, zone-name binding and inflate path.
    // Only the RSA signature verdict is accepted. Off unless
    // OLMOD_ALLOW_UNSIGNED_FASTFILES=1 and pinned to the verified 1649370 bytes.
    bool patchUnsignedFastfileVerificationBuffer(
        std::span<std::uint8_t> image);
    UnsignedFastfilePatchResult installUnsignedFastfilePatch();
    const char *unsignedFastfilePatchResultName(
        UnsignedFastfilePatchResult result);

    ClientProcessPatchResult installClientProcessPatches();
    ClientRawInputPatchResult installClientRawInputPatch();

    enum class UnlockAllPatchResult
    {
        NotRequested,
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    // OWN EVERY ITEM, without sending a single extra inventory byte.
    //
    // The inventory reply is capped at 8,460 records by a 512 KB buffer the client passes
    // per task, the catalogue is 21,753 ids, and the client does NOT page -- told 19,900
    // existed while receiving 8,460 it never asked for the rest (measured 2026-09-03). So
    // no amount of work on the wire can deliver the catalogue.
    //
    // It does not have to. The store list is not built FROM the inventory array: the
    // client walks its own item table and asks an ownership resolver per entry
    // (sub_5E3760, 94 call sites). That resolver already has an "owned without being in
    // the inventory" branch, and the branch is guarded by a predicate with exactly ONE
    // caller -- itself. Forcing that predicate true fills the out-record as owned with
    // quantity -1, for every item the inventory did not carry.
    //
    // ONE CALLER is why this is the safe place to cut. The hash lookup underneath it has
    // six callers and returns a RECORD POINTER, so forcing that would hand callers a wild
    // pointer; the list-walk beside it has twenty-three callers and gates things this has
    // no business changing. This predicate is a bool used in one branch of one function.
    UnlockAllPatchResult installUnlockAllPatch();

    const char *unlockAllPatchResultName(UnlockAllPatchResult result);
    bool maintainClientRawInputWindow();
    const char *clientProcessPatchResultName(ClientProcessPatchResult result);
    const char *clientRawInputPatchResultName(ClientRawInputPatchResult result);
}
