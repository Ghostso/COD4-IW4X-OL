"""Passive C1 1.1.1.13 world lightmap/brush/camera capture; never writes process memory.



Fixed image base is intentional: exact code guards reject another build/base.

No debugger, hooks, input, or renderer changes. Inactive gameplay is not sampled.

"""

import argparse

import ctypes

import json

import math

import struct

import time





def inspect(pid):

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]

    kernel.OpenProcess.restype = ctypes.c_void_p

    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,

        ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

    kernel.ReadProcessMemory.restype = ctypes.c_int

    kernel.CloseHandle.argtypes = [ctypes.c_void_p]

    handle = kernel.OpenProcess(0x10, False, pid)

    if not handle:

        raise ctypes.WinError(ctypes.get_last_error())



    def read(address, size):

        buffer = ctypes.create_string_buffer(size)

        got = ctypes.c_size_t()

        if not kernel.ReadProcessMemory(handle, address, buffer, size,

                                       ctypes.byref(got)) or got.value != size:

            raise OSError(f"Unreadable C1 memory {address:#x}")

        return buffer.raw



    def word(address):

        return struct.unpack("<I", read(address, 4))[0]



    def decoded_origin(data):

        x, y, z = struct.unpack_from("<3I", data, 0x18)

        return struct.unpack("<3f", struct.pack("<3I",

            x ^ 0x073ff35a, y ^ x ^ 0xedb436a0, z ^ y ^ 0x893fead3))



    try:

        guards = {

            0xa82e20: "a19441cf00",

            0x429070: "a1acd2c3068b0c85583b6d0181f10c400b49d9815c010000",

            0xa80510: "568b74240866837e3400746b6a0168fc",

            0xa804f0: "8b4424048b15a039cf008bc8c1e1042bc8",

        }

        for address, code in guards.items():

            expected = bytes.fromhex(code)

            if read(address, len(expected)) != expected:

                raise ValueError(f"Wrong C1 build/base at {address:#x}")

        cg_index = word(0x6c3d2ac)

        entity_index = word(0x6c3d2b4)

        if max(cg_index, entity_index) > 1024:

            raise ValueError("Invalid encoded pointer table index")

        cg = word(0x16d3b58 + cg_index * 4) ^ 0x490b400c

        entities = word(0x16d3b58 + entity_index * 4) ^ 0x189bfead

        command_time = word(cg)

        result = {"pid": pid, "commandTime": command_time,

            "hasPredictedGameplayState": command_time > 0,

            "viewOrigin": struct.unpack("<3f", read(cg + 0xb0384, 12)),

            "limitations": ["Reads are not an atomic engine frame.",

                "commandTime identifies predicted state, not a received snapshot pointer.",

                "Quaternion is captured, not independently recomputed.",

                "Submission does not establish shadow casting or artifact causation."]}

        result["shadowSamplingDvars"]=[]
        for pointer,kind,role in [(0xcf4070,"float","shadow polygon offset scale"),(0xcf4318,"float","shadow polygon offset bias"),(0xcf430c,"float","shadow sampling scale"),(0xcf41f8,"float","sampling coefficient input"),(0xcf40b8,"bool","sampling scale forced-one switch"),(0xcf41f4,"int","primary shadow target dimension"),(0xcf4258,"int","primary shadow target count"),(0xcf40e8,"int","alternate shadow target dimension"),(0xcf41d0,"int","alternate shadow target count")]:
            d=word(pointer)
            name=read(word(d),16).split(b"\0",1)[0].decode("ascii")
            fmt="<f" if kind=="float" else "<I"
            current=struct.unpack(fmt,read(d+12,4))[0];reset=struct.unpack(fmt,read(d+44,4))[0]
            if kind=="bool":current&=255;reset&=255
            result["shadowSamplingDvars"].append(dict(name=name,kind=kind,role=role,current=current,reset=reset))
        decal_dvar=word(0xcf428c)
        result["decalSurfaceFilter1529"]={"current":read(decal_dvar+12,1)[0],"reset":read(decal_dvar+44,1)[0],
            "identityEvidence":"C1 brush consumers match named IW3 r_drawDecals consumers; not a symbol name recovered from C1."}
        if not command_time:

            result["status"] = "inactive; scene capture skipped"

            return result

        axes=struct.unpack("<9f",read(cg+0xb0390,36))

        result["cameraAxes"]=axes

        result["cameraAxisNorms"]=[math.sqrt(sum(v*v for v in axes[j:j+3])) for j in (0,3,6)]

        dvar=word(0xcf4194)

        result["lightmapOverrideEnum1475"]={"current":word(dvar+12),"reset":word(dvar+44)}

        front=word(0xcf4380)

        # Frontend globals are cleared outside frame submission. A valid

        # gameplay snapshot alone does not make this transient pointer valid.

        for _ in range(200):

            if front>=0x10000:break

            time.sleep(0.001)

            front=word(0xcf4380)

        if front<0x10000:

            result.update(status="active gameplay; frontend pointer unavailable",frontendPointer=hex(front))

            return result

        result["frontendPointer"]=hex(front)

        # Nonzero predicted command time can survive in a viewer/lobby world.
        # Record the actual render-world identity before treating it as MP.
        world_pointer=word(0xcf39a0)
        world_name_pointer=word(world_pointer)
        world_name=bytearray()
        for offset in range(256):
            char=read(world_name_pointer+offset,1)
            if char==b'\0':break
            world_name.extend(char)
        else:raise ValueError("Unterminated renderer world name")
        result["renderWorldName"]=world_name.decode("ascii","replace")
        if result["renderWorldName"].replace("\\","/").lower()!="maps/mp/mp_killhouse_sh.d3dbsp":
            result["status"]="different render world; Killhouse scene capture skipped"
            return result

        # These are renderer-owned derived values, not dvar reset values.
        # ABC789..ABC7AB consumes their ratio for its +4c/+50 footprint.
        # Capture only after both gameplay and frontend guards above.
        scalar=struct.unpack("<f",read(0xcf3ef8,4))[0]
        footprint=struct.unpack("<f",read(0xcf3f04,4))[0]
        result["derivedShadowSampling"]={
            "scalarCF3EF8":scalar,
            "quantizedCountCF3EFC":word(0xcf3efc),
            "footprintCF3F04":footprint,
            "consumerRatio":footprint/scalar if scalar else None,
            "targetConstantsFAA9A8Hex":read(0xfaa9a8,20).hex(),
            "limitation":"Renderer globals sampled passively; not GPU depth or shadow texels."}

        bank=word(0xcecb20)

        if bank<0x10000:raise ValueError("No world input bank")

        result["sunDirectionOverride"]=word(front+0x4190c)

        # C1 AB5890 reads world+150..158 for the camera/sun dot, then
        # AB58D1/AB5970 gates/multiplies darkening by world+130.
        world=word(0xcf39a0)
        result["worldSunFlare"]={
            "valid":read(world+0xfc,1)[0],
            "blindMaxDarken":struct.unpack("<f",read(world+0x130,4))[0],
            "glareMaxLighten":struct.unpack("<f",read(world+0x144,4))[0],
            "sunFxDirection":struct.unpack("<3f",read(world+0x150,12)),
            "rawFCto15C":read(world+0xfc,96).hex(),
            "limitation":"Authored flare/blind inputs, distinct from sun-shadow depth partitions."}

        direction=struct.unpack("<3f",read(front+0x419d0,12))

        result["projectionInputs"]={"lightDirection":direction,

            "lightDirectionLength":math.sqrt(sum(v*v for v in direction)),

            "worldCenterAndHalfSize":struct.unpack("<6f",read(word(0xcf39a0)+0xd8,24)),

            "sunOutput41c50Hex":read(front+0x41c50,0x330).hex(),

            "viewCopiedCoefficients":struct.unpack("<8f",read(front+0x41c90,32)),

            "limitation":"Raw sun output captured; internal matrix field meanings not yet verified."}

        result["sunOverrideBytes"]=list(read(0xcf3e36,3))

        count_lm=word(bank+0x10)

        if count_lm>65536:raise ValueError("Invalid lightmap bank count")

        src=word(bank+0x14); first=word(bank+0x18);second=word(bank+0x1c)

        overrides=[word(bank+0x20),word(bank+0x24)]

        rows=[]

        for i in range(count_lm):

            a,b=word(src+8*i),word(src+8*i+4)

            original=[word(a) if a else None,word(b) if b else None]

            published=[word(first+4*i),word(second+4*i)]

            expected=[word(overrides[j]) if overrides[j] else original[j] for j in range(2)]

            rows.append(dict(index=i,original=original,published=published,expected=expected,matches=published==expected))

        result["frontendPointerStillCurrent"]=word(0xcf4380)==front

        result["lightmapBank"]={"count":count_lm,"overrides":overrides,"entries":rows}

        dynamic_count=word(0xfb5618); view_count=word(0xfb561c)

        if dynamic_count>768 or view_count>8:raise ValueError("Invalid scene DObj count")

        dynamic=[]

        for slot in list(range(dynamic_count))+list(range(768,768+view_count)):

            row=read(0xfb5624+slot*0x78,0x78)

            key,dobj=struct.unpack_from("<2I",row,0x68)

            if dobj<0x10000:continue

            bounds=struct.unpack_from("<3f",row,0x38)

            models=[];model_count=read(dobj+9,1)[0]

            if model_count>32:raise ValueError("Invalid scene DObj model count")

            model_array=word(dobj+0xc0)

            for j in range(model_count):

                model=word(model_array+j*4);name_ptr=word(model)

                name=read(name_ptr,128).split(b"\0",1)[0].decode("latin1")

                models.append(name)

            dynamic.append(dict(slot=slot,entity=(key>>7)&0xfff,renderFlags=hex(key>>19),

                boundsFields38=bounds,models=models,raw=row.hex(),

                sunPartitionVisibility=[read(0xfcc4e4+slot,1)[0],read(0xfcc7e4+slot,1)[0]] if slot<768 else None,

                populatedSurfaceRecord=hex(word(0xfb5624+slot*0x78+0x44))))

        result["submittedDObjs"]={"worldCount":dynamic_count,"viewCount":view_count,"records":dynamic}

        # C1 A835A5..A83666 single-XModel scene branch, separate from
        # sceneDObj. A8B0CA..A8B124 submits its visible shadow surfaces.
        model_count=word(0xfcd6f0)
        if model_count>1024:raise ValueError("Invalid single-model scene count")
        single_models=[]
        for slot in range(model_count):
            row=read(0xfcd6fc+slot*0x48,0x48)
            model=struct.unpack_from("<I",row,4)[0]
            if model<0x10000:raise ValueError("Invalid submitted single model")
            key=struct.unpack_from("<I",row,0x2c)[0]
            single_models.append(dict(slot=slot,entity=(key>>7)&0xfff,
                renderFlags=hex(key>>19),model=read(word(model),128).split(b"\0",1)[0].decode("latin1"),
                quaternion=struct.unpack_from("<4f",row,0xc),
                origin=struct.unpack_from("<3f",row,0x1c),
                scale=struct.unpack_from("<f",row,0x28)[0],
                radius=struct.unpack_from("<f",row,0x30)[0],
                lightingOrigin=struct.unpack_from("<3f",row,0x38),
                cameraVisibility=read(0xfdf6fc+slot,1)[0],
                sunPartitionVisibility=[read(0xfdfafc+slot,1)[0],read(0xfdfefc+slot,1)[0]],
                unchangedAcrossRead=row==read(0xfcd6fc+slot*0x48,0x48)))
        result["submittedSingleModels"]={"count":model_count,
            "countUnchangedAcrossReads":model_count==word(0xfcd6f0),"records":single_models}

        count = word(0xfe12fc)

        if count > 512:

            raise ValueError("Invalid C1 scene brush count")

        scene = read(0xfe1304, count * 0x28) if count else b""

        world = word(0xcf39a0)

        if world < 0x10000:

            raise ValueError("No C1 render world")

        model_base = word(world + 0xd4)

        records = []

        for i in range(count):

            row = scene[i * 0x28:(i + 1) * 0x28]

            entity = struct.unpack_from("<H", row, 2)[0]

            model = struct.unpack_from("<I", row, 4)[0]

            quaternion = struct.unpack_from("<4f", row, 8)

            origin = struct.unpack_from("<3f", row, 0x18)

            record = {"slot": i, "entity": entity,

                "modelPointer": hex(model), "origin": origin,

                "quaternion": quaternion,

                "quaternionNorm": math.sqrt(sum(v*v for v in quaternion))}

            delta = model - model_base

            record["inlineModelIndex"] = delta // 60 if delta >= 0 and delta % 60 == 0 else None

            record["sunPartitionVisibility"]=[read(0xfe6504+i,1)[0],read(0xfe6704+i,1)[0]]

            record["sunMaterials"]=[]

            if 1 in record["sunPartitionVisibility"] and word(0xcf4380)==front:

                technique=word(0xcf3f40)

                if technique>255:raise ValueError("Invalid shadow technique index")

                selector=read(word(0xcf428c)+12,1)[0]

                surface_count=struct.unpack("<H",read(model+(0x34 if selector else 0x38),2))[0]

                if surface_count>4096:raise ValueError("Invalid brush surface count")

                first_surface=struct.unpack_from("<H",row,0)[0]

                for j in range(surface_count):

                    surf=word(front+0x42704+first_surface*4+j*8)

                    material=word(surf+0x10)

                    techset=word(word(material+0x50)+8)

                    cast=word(techset+12+technique*4)!=0

                    name=read(word(material),128).split(b"\0",1)[0].decode("latin1")

                    record["sunMaterials"].append(dict(name=name,techniqueIndex=technique,hasTechnique=cast))

            if entity < 2048:

                cent = read(entities + entity * 0x228, 0x228)

                number, kind, flags = struct.unpack_from("<3I", cent, 0xe4)

                current_origin = decoded_origin(cent)

                record["centity"] = {"nextEntityNumber": number, "type": kind,

                    "flags": hex(flags), "inlineModelIndex": struct.unpack_from("<I", cent, 0x17c)[0],

                    "solid": hex(struct.unpack_from("<I", cent, 0x18c)[0]),

                    "angles": struct.unpack_from("<3f", cent, 0x24),

                    "origin": current_origin,

                    "scale": struct.unpack_from("<f", cent, 0x30)[0]}

                record["maxOriginDifference"] = max(abs(a-b) for a,b in zip(origin, current_origin))

                record["modelIndexMatches"] = record["inlineModelIndex"] == record["centity"]["inlineModelIndex"]

            records.append(record)

        count_after = word(0xfe12fc)

        unchanged = count_after == count and (not count or read(0xfe1304, count*0x28) == scene)

        result.update(status="captured", count=count,

            sceneUnchangedAcrossReads=unchanged, commandTimeAfter=word(cg), records=records)

        return result

    finally:

        kernel.CloseHandle(handle)





if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--pid", type=int, required=True)

    print(json.dumps(inspect(parser.parse_args().pid), indent=2, allow_nan=False))



