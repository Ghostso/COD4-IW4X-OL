# Native SortByDistance

`CODOL_Scr_SortByDistance` is registered as a native function. It reads up to
2,048 object entries from the retained VM array, evaluates their canonical
`origin` field, and returns the same objects in a new numerically indexed array
ordered by squared float distance to argument 1. It accepts script structs and
entities, preserves the input array and keys, and releases temporary field
values. Equal distances preserve traversal order; native tie order is not
otherwise promised. Nonfinite origins are rejected.

Evidence: IW4 function 0x5f63a0 checks the array type and 2,048-entry cap,
extracts object values through 0x4fb0f0, retrieves each vector-valued origin
through 0x445980, sorts with the squared-distance comparator 0x5f4e90, and
builds a new array. Missing/nonvector origins produce an error. The Python
reference in `gsc/gscbuiltins.py` sorts nearest-first too, but its permissive
fallback for invalid entries was not copied.

The live retained-VM fixture is
`tests/fixtures/codol_sort_vm/maps/mp/gametypes/_callbacksetup.gsc`. It checks
mixed numeric/string keys, nearest-first order, unchanged input, a changed
reference origin, empty arrays, and mixed entity/struct origins. The initial
run exposed ordinary-string versus canonical-field-ID lookup; using the native
canonical field resolver corrected it. This is an actual native map startup
fixture, not a Python gameplay proxy.

Windows build passed (`/tmp/sh1x-sort-distance-win32.log`). The vendor-script
retry moved past SortByDistance and now fails at `GetPointInBounds` in
`maps/mp/_stinger.gsc:119`; log `obj/sort-vendor-probe.log`. Inventory coverage
is 480 matching names and 827 missing names, not a semantic completion score.
Full vendor startup and real C1 match entry remain unverified.
