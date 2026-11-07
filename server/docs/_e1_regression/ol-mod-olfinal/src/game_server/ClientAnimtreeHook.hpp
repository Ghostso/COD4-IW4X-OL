#pragma once

// THE ANIMTREE RESOLVE HOOK (12.140).
//
// WHY A HOOK AND NOT A PROBE. 12.139 established that the name-to-asset lookup is
// only observable WHILE IT HAPPENS: `sub_40B210` resolves the six animtree names at
// map load, stores the returned pointers into the six-entry table at
// `ctx58 + 0x17E784`, and the bookkeeping is then released -- the interned string's
// refcount falls to zero and its registry chain is recycled. Every post-hoc probe
// from 12.135 onward was searching for state that no longer exists.
//
// WHAT IT ANSWERS. Our column 3 resolves to a 519-entry descriptor where retail's
// resolves to a 123-entry one (12.124), and that single difference accounts for the
// T-pose, the frozen animation and the apparent bad spawns (12.122, 12.133). The
// hook records, per resolve: the NAME asked for, the POINTER returned, and the entry
// count at that pointer. Run once against our match and once against a demo, the two
// logs sit side by side and the difference is attributed rather than inferred.
//
// THE SITE. `sub_40B210 + 0x7B` (file 0x0040B28B, RVA 0xB28B):
//
//     0040B288  8B 11           mov  edx, [ecx]       ; the name pointer
//     0040B28A  52              push edx
//     0040B28B  E8 60 FA 33 00  call sub_74ACF0       ; <- the five bytes replaced
//     0040B290  83 C4 04        add  esp, 4           ; CALLER cleanup, cdecl
//     0040B293  89 06           mov  [esi], eax       ; stored into the six-entry table
//
// One five-byte call redirect. The hook calls the original with the same argument and
// returns its result unchanged, so it is semantically transparent; the only effect is
// a log line. The original bytes are verified before anything is written, exactly as
// `installClientProcessPatches` does, and a mismatch refuses rather than patching.

#include <cstdint>

namespace CodolGameServer
{
    enum class AnimtreeHookResult
    {
        Installed,
        AlreadyInstalled,
        Disabled,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    [[nodiscard]] AnimtreeHookResult installClientAnimtreeHook();
    [[nodiscard]] const char *animtreeHookResultName(AnimtreeHookResult result);
}
