# Native reference CSV tables

When the native script asset lookup cannot find a string table in mounted
fastfiles, it now searches CSV files beneath `codol_scriptPath`. It uses the
same validated relative paths and `root/mp` then `root` precedence as reference
script loading. Only `.csv` names qualify. Script overlays do not replace
tables, and a present but invalid mounted table does not fall back.

This supplies the CSV resources shipped with alpha0022's IW4 script export.
The Python reference loads them in `gsc/gscbuiltins.py` `_table`; native gameplay
does not import or execute that Python implementation.

The parser owns its strings, preserves header rows, pads short rows with empty
cells, and supports CRLF/LF, quoted commas/newlines and doubled quotes. It
rejects embedded NUL, malformed quoting, inputs above 16 MiB and tables above
1,048,576 cells. Empty input is rejected. Parsing failure preserves output.
It does not claim parity with every permissive Python CSV dialect behavior.

Cache keys include source root and asset name. Returned engine tables remain
valid until `CODOL_UnmountArchives`; changing a file does not invalidate live
VM pointers. Unmount releases cache strings, cells, names and pointer arrays.
Developer logs identify reference lookups with `CoDOL reference stringtable`.

Validation on 2026-09-08:

- Parser tests passed 32-bit Linux ASan/UBSan, covering ownership, quoted
  delimiters/newlines, ragged rows, trailing empty fields and malformed input.
- Windows build passed (`/tmp/sh1x-csv-final-win32.log`). The asset-registry
  suite passed, including new cache-lifetime, malformed-reload, output
  preservation and path-traversal rejection assertions.
- An isolated native Bog server on UDP 17771 loaded a copy of the actual
  reference `mp/unlocktable.csv` under its configured test source root. Native
  `tableLookup` calls returned arctic/desert/urban ghillie requirements and
  printed `SH1X_REFERENCE_TABLE_VM_PASS`. Developer logs confirmed the CSV
  fallback was used. The fixture is `tests/fixtures/codol_csv_vm`.

The probe was stopped afterward; C1 and the Python lobby remained responsive.
The separate `isItemUnlocked` profile adapter and real C1 match entry remain
incomplete.
