# PLAN_A — ORDINAL-1 LIFECYCLE CLOSURE (working notes)

## Inherited (frozen, not re-derived)
- EXE Entry RVA 0x0E5DC690, bytes FF 15 65 C6 9D 0E = call dword ptr [0x0E9DC665]
- IAT slot 0x0E9DC665 -> Base.dll ordinal 1
- Base ordinal-1 RVA 0x1D6582C  (CONFIRMED statically: export dir .rdata 0x952D60, OrdinalBase 9776532, nfunc 3, ordinal1 func RVA = 0x1D6582C)
- Base ImageBase(file) 0x10000000; runtime base observed 0x78FE0000
- ordinal-1 entry register set: EAX=Base+0x1D6582C, EDX=Base+0x110, ESI=Base+0, EDI=0x20, EFLAGS=0x202
- 12/12 ordinal-1 entry, 0/12 return to EXE return site (0x0E5DC696)
- CORE-011: 7 historical post-boundary RVAs -> 0 hits; CORE-013R: no unique static target

## NEW STATIC FACT (this round, capstone)
ordinal-1 0x1D6582C is inside .tvm0 (not .text):
    1D6582C  push 0x592A35B8
    1D65831  push ecx
    1D65832  push edx
    1D65833  push ebx
    1D65834  push eax
    1D65835  jmp  0x1F27FDC          <- single static direct transfer
  0x1F27FDC (also .tvm0):
    push esi / pushfd / push ebp / push edi / jmp 0x1F9DFFD
  => ordinal-1 is a VM entry stub with NO RET; there is a nonzero, statically
     resolved first hop. This is evidence for Case E (runtime generation),
     NOT for Case A (normal RET).

## Method (this round)
- Dynamic: minimal life-cycle observer (x86 debugger, NO file modification).
  - breakpoints: EXE Entry, ordinal-1 entry, EXE return site, ORDINAL1_HOP (jmp dest),
    first instruction of any newly-MAPPED executable region after ordinal-1.
  - record: entry regs, hop, module map, executable region map (VirtualQueryEx),
    exceptions, thread create/exit, process exit, exit code.
  - 3 runs, same environment, per run keep first-hop evidence.
- Static: ordinal-1 direct exits only -> base_ordinal1_lifecycle.csv

## Prohibitions honoured
no EXE/DLL modification, no patch, no hook, no Tencent/TCLS/WeGame analysis,
no Procmon/Sandboxie, no EXE full scan, no bootstrap RVA re-search, no .tvm0 decode,
no IW4X analysis.
