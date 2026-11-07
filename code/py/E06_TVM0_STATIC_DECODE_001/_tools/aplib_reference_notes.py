"""aPLib depacker (reference implementation, x86 32-bit flavour).

aPLib by Jorgen Ibsen. This is a clean-room implementation of the public
aP_depack algorithm as documented in the aPLib technical description.
Only used to test the hypothesis that section payloads are aPLib-packed.
"""
import struct

class APError(Exception): pass

def depack(src, out_limit=64*1024*1024, verbose=False):
    """Return (output_bytes, consumed_input_len)."""
    out = bytearray()
    i = 0
    n = len(src)
    def getb():
        nonlocal i
        if i >= n: raise APError("input exhausted")
        b = src[i]; i += 1
        return b
    # first token = literal
    out.append(getb())
    while True:
        if i >= n: break
        tag = getb()
        for bit in range(7, -1, -1):
            if i >= n: 
                return bytes(out), i
            if tag & (1 << bit):
                # literal
                out.append(getb())
            else:
                # match: read gamma-coded offset
                a = 0
                while True:
                    b = getb()
                    a += b
                    if b != 255: break
                a += 2  # minimum offset
                if len(out) < a:
                    raise APError("offset beyond output: need %d have %d" % (a, len(out)))
                # gamma-coded length
                b = getb()
                length = b + 3
                if b == 0:
                    length = 3
                    b = getb()
                    while b == 255:
                        length += 255
                        b = getb()
                    length += b
                else:
                    length = b + 3
                # copy (possibly overlapping)
                for k in range(length):
                    out.append(out[len(out) - a])
                    if len(out) > out_limit: raise APError("output limit")
            if len(out) > out_limit: raise APError("output limit")
    return bytes(out), i