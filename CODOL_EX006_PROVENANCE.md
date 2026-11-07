# EX-006 .tvm0 -> Base+0x2ED2 Boundary ABI Provenance

Experiment: EX-006 (provenance only, no binary patch)

Boundary state at `Base+0x2ED8` (crashing invocation):
```text
ecx = 0x141CE020
esi = 0x141CE020
[esp+4] = 0x7AA7AC6D  (.tvm0 boundary return, Base+0x267AC6D)
```

First observable formation of `ESI=3`:
```text
Base+0x2EEB  mov edi, [eax]       ; eax = esi+4
             edi = [0x141CE020+4] = 3

Base+0x2EFF  push edi              ; free(3)
Base+0x2F00  call Base+0x27D28B
             -> Base+0x27E3B0 mov esi,[ebp+8] ; esi = 3

Base+0x2F0B  mov ecx, esi          ; ecx = 3
Base+0x306A  cmp [ecx+18h], 10h    ; AV at 0x1B
```

Answers:
1. `ESI=3` is produced in Base `.text`, not returned from `.tvm0`.
2. The value `3` comes from memory field `[0x141CE020+4]`, loaded at `Base+0x2EEB`.
3. `.tvm0` is only the caller boundary into `Base+0x2ED2`; it does not directly produce the `3`.
4. The `3` is then passed as the free argument, and the free wrapper copies it into `ESI`.

Evidence level:
L3 runtime registers + L2 static instruction mapping (SUCCESS C).
