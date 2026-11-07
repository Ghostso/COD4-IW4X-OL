# EX-039 IIPS Static Candidate Reconstruction and Minimal Dynamic Validation

## Final Classification

```text
IIPS_STATIC_CANDIDATES_RECONSTRUCTED
IIPS_LOADER_CALLER_UNCONFIRMED
IIPS_INIT_CALLER_UNCONFIRMED
IIPS_ERROR_CALLER_UNCONFIRMED
NO_NEW_EXECUTION_NODE
```

The static string/reference scan produced candidates for the IIPS loader
and IFS2 internals, but no plain `.text` caller for `WIN_IIPS_INIT_ERROR`
or `8189FEC`. Runtime validation was not expanded beyond the existing
`-q` run in EX-038/EX-037 because the candidates did not reach
`IIPS_STATIC_LOADER_CANDIDATE_L2` confidence.

## String Locations

### `codoMP_client_shipRetail.exe`

```text
WIN_IIPS_INIT_ERROR
  file 0x6B53A8
  RVA 0x9C93A8
  VA 0xDC93A8

WIN_IIPS_INIT_FAILED
  file 0x6B53D8
  RVA 0x9C93D8
  VA 0xDC93D8

WIN_IIPS_DLL_ERROR
  file 0x6B5408
  RVA 0x9C9408
  VA 0xDC9408

IIPS\iips.dll
  file 0x6B53F0
  RVA 0x9C93F0
  VA 0xDC93F0

Environment List Box
  file 0x6B5440
  RVA 0x9C9440
  VA 0xDC9440

iipsinit
  file 0x75B90C
  RVA 0xA6F90C
  VA 0xE6F90C
```

The EXE string xrefs found were weak packed-data references:

```text
WIN_IIPS_DLL_ERROR    ref at file 0x18F35E
WIN_IIPS_INIT_FAILED  ref at file 0x18F3CD
Environment List Box  ref at file 0x18F229
```

All are in `.tp3` packed regions, not plain `.text`.

### `iips.dll`

```text
CreateIFSLibDll
  file 0x34964, VA 0x10034964
  one plain .text reference at file 0x9777

IIPSHostApp.exe
  multiple hits in .rdata string cluster
IIPSERR_CACHE_INIT
IIPSERR_ERROR_INIT
LaunchIIPSHostApp failed
```

`GetResourceManagerII` and `ReleaseResourceManagerII` are exported by
`iips.dll` but no plaintext `GetProcAddress("GetResourceManagerII")`
sequence was found.

## Loader Candidates

### Candidate A: L1

```text
EXE packed string IIPS\iips.dll
file 0x6B53F0
```

This shows the EXE is aware of the IIPS DLL path, but the string sits in
packed data. No plain `.text` `LoadLibraryW` argument construction was
resolved.

### Candidate B: L0/L1

```text
Environment List Box / iipsinit
EXE packed string cluster
```

Indicates the EXE creates or hosts the iipsinit UI. No plain caller was
found.

### Candidate C: L2 inside iips.dll

```text
CreateIFSLibDll
file 0x34964
plain .text ref at file 0x9777
```

This is the only strong static dataflow candidate in plain `.text`, but
it is inside `iips.dll` and represents an IFS2 dependency inside IIPS, not
the CODOL-side loader of `iips.dll`.

## `GetResourceManagerII` Resolution

No static resolver evidence was found:

```text
GetProcAddress("GetResourceManagerII"): MISSING
function pointer storage to GetResourceManagerII: MISSING
indirect call target using export RVA: MISSING
```

The export exists at:

```text
iips.dll RVA 0x1C80 -> VA 0x10001C80
```

but there is no usable plaintext reference chain.

## `WIN_IIPS_INIT_ERROR` Caller

Best candidate:

```text
EXE packed region around file 0x18F35E
```

It is L1/L0 only. No plain `.text` caller was found.

## Init Success/Failure Branch

No plain `.text` CODOL branch of the form:

```text
call iips init
test/cmp eax
jnz WIN_IIPS_INIT_ERROR
```

was recovered.

## Runtime

No new runtime validation was performed beyond EX-037/EX-038 observations:

```text
iips.dll loaded
iipsinit window
WIN_IIPS_INIT_ERROR / 8189FEC
```

Because no static loader/init candidate met the confidence threshold,
no limited three-candidate validation pass was started.

## `8189FEC`

Still classified:

```text
8189FEC_PACKED_OR_VM_GENERATED
```

No plaintext constant found in EXE, Base.dll, or iips.dll.

## Answers

1. IIPS loader candidates: EXE packed `IIPS\iips.dll` string; no confirmed caller.
2. Plain `.text` candidates: only `CreateIFSLibDll` ref inside `iips.dll`.
3. L0/L1 candidates: `WIN_IIPS_*`, `IIPS\iips.dll`, `iipsinit`, `Environment List Box` in packed EXE.
4. L2 dataflow candidates: `CreateIFSLibDll` reference inside `iips.dll`.
5. `GetResourceManagerII` resolver evidence: none.
6. Best `WIN_IIPS_INIT_ERROR` .text caller: none; incoming caller is packed/VM-side.
7. Init success/failure branch: not found.
8. Runtime validation of top three candidates: none performed due to low confidence.
9. New L3/L4: none.
10. `8189FEC`: still packed/VM-generated classification.

## Final

```text
IIPS_STATIC_CANDIDATES_RECONSTRUCTED
IIPS_LOADER_CALLER_UNCONFIRMED
IIPS_INIT_CALLER_UNCONFIRMED
IIPS_ERROR_CALLER_UNCONFIRMED
NO_NEW_EXECUTION_NODE
```
