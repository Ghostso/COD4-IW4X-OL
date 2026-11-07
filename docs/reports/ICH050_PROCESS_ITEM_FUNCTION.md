# ICH-050 — process_item (0x009C2940) Complete Function Analysis

## Function Signature
- Calling convention: __thiscall, ret 4 (1 stack arg)
- ECX = event object (created by Slot 41's log/report call)
- arg1 ([ebp+0x08]) = state value pointer (DWORD ptr)
- Function size: 0x5D bytes (0x009C2940..0x009C299D)

## Access Chain
```
event object (ecx)
 ├── +0x0C   → FF/Zone object (for FF_OPERATION call)
 ├── +0x10   → handle (zone/FF index)
 ├── +0x18   → size/offset
 └── +0x20   → filename string (null-terminated, read by 0x00A4EC10)
```

## Complete Disassembly

### Phase 1: Refcount increment (0x009C2940..0x009C294E)
```
mov edi, [ebp+0x08]      ; edi = arg1 (state value)
test edi, edi
je skip
inc dword [edi+0x0C]     ; increment refcount
```

### Phase 2: Read filename string (0x009C294E..0x009C2960)
```
lea esi, [ecx+0x20]      ; esi = event data area (contains filename)
lea eax, [ebp+0x0B]      ; local buffer on stack
push eax
mov ecx, esi
call 0x00A4EC10          ; read_string(ecx=event_data, out=local)
cmp byte [eax], 0        ; check if string is empty
je skip_FF_path          ; if empty → skip FF path
```

### Phase 3: FF/Zone Operation (0x009C2962..0x009C297D) ★ KEY
```
mov ecx, [esi+0x10]      ; handle = [event_data+0x10]
mov edx, [esi+0x18]      ; size = [event_data+0x18]
inc ecx                  ; handle++
push ecx                 ; push handle+1
push edx                 ; push size
lea ecx, [esi+0x0C]      ; ecx = FF/Zone object
call 0x009C19C0          ; ★ FF_OPERATION(ecx=zone_obj, size, handle+1)
                         ; ★ This is in Engine gap
                         ; ★ This is the FF/Zone entry

mov eax, [esi+0x10]      ; re-read handle
mov ecx, [esi+0x0C]      ; FF/Zone object
lea eax, [ecx+eax*4-4]   ; array indexing: obj + (handle-1)*4
test eax, eax
je skip
inc dword [edi+0x0C]     ; increment refcount
mov [eax], edi           ; store state value into array
```

### Phase 4: Cleanup (0x009C298A..0x009C299D)
```
pop esi
test edi, edi
je done
dec dword [edi+0x0C]     ; decrement refcount
jnz done
mov ecx, edi
call 0x00887600          ; cleanup/free
done:
pop edi
pop ebp
ret 4
```

## Semantic Analysis

process_item is a **Resource Event Processor** that:

1. Receives an event object (created by Slot 41's log/report)
2. Reads a **filename string** from the event data
3. If filename is non-empty:
   - Gets a handle and size from event data
   - Calls **FF_OPERATION (0x009C19C0)** with (zone_obj, size, handle+1)
   - Stores the result in an array indexed by handle
4. Manages refcounting of the state value

## Direct Callees

| Address | Module | Purpose | FF relevance |
|---|---|---|---|
| **0x00A4EC10** | Engine gap | read_string | Reads filename from event |
| **0x009C19C0** | **Engine gap** | **FF_OPERATION** | **YES — this is the FF/Zone entry** |
| 0x00887600 | Base.dll | cleanup/free | No |

## Conclusion

**process_item (0x009C2940) IS the Resource → FF/Zone bridge.**

It reads a filename from the event data and calls 0x009C19C0 (FF_OPERATION) to perform the actual file/zone operation. The FF_OPERATION callee at 0x009C19C0 is the function that receives (zone_obj, size, handle) parameters consistent with a FastFile/Zone load operation.
