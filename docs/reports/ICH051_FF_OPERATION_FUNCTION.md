# ICH-051 — FF_OPERATION (0x009C19C0) Complete Function Analysis

## Function Signature
- Calling convention: __thiscall, ret 8 (2 stack args)
- ECX = FF/Zone object
- arg1 ([ebp+0x08]) = handle+1 (from process_item)
- arg2 ([ebp+0x0C]) = size/offset (from process_item)
- Function size: 0x76 bytes (0x009C19C0..0x009C1A36)

## Semantic Role: ARRAY RESIZE / TRUNCATE

**NOT a FF/Zone loader.**

This function manages a dynamic element array within the FF/Zone object:

1. Reads current capacity from [this+0x04]
2. If requested size < capacity:
   - Iterates from last element backwards
   - Refcount decrements each element
   - Frees elements with refcount==0 (via 0x00887660)
3. If requested size >= capacity:
   - Calls RESIZE (0x0097F580) to reallocate array
   - Grows by 25% or to exact size

## FF/Zone Object Layout (from this function)

```
FF/Zone Object (ecx)
 ├── +0x00   → array base pointer (element array)
 ├── +0x04   → current capacity (DWORD)
 ├── +0x08   → allocation size / growth hint
 └── ...     → element array (each element is 4-byte pointer)
               elements have +0x0C refcount field
```

## Direct Callees

| Address | Module | Purpose | FF relevance |
|---|---|---|---|
| 0x0097F580 | Base.dll | array RESIZE/reallocate | Infrastructure |
| 0x00887660 | Base.dll | free/cleanup element | Infrastructure |

## Verdict

**PROCESS_ITEM_TO_FF must be DOWNGRADED.**

0x009C19C0 is NOT the FF/Zone loader. It is a dynamic array management
primitive (resize/truncate). The handle+size parameters passed from
process_item are used for array management, not file operations.

The actual FF/Zone loading logic must be elsewhere.
