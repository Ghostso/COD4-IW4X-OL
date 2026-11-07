"""Read-only, guarded C1 scene DObj skeleton capture. No engine calls/writes."""
import argparse
import ctypes
import json
import hashlib
import math
from pathlib import Path
import struct
import time


def inspect(pid, draw_only=False):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k.OpenProcess.restype = ctypes.c_void_p
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
    k.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    h = k.OpenProcess(0x1010, False, pid)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    def read(a, n):
        b = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if not k.ReadProcessMemory(h, a, b, n, ctypes.byref(got)) or got.value != n:
            raise OSError(f'Unreadable {a:#x}+{n:#x}')
        return b.raw
    def u(a):
        return struct.unpack('<I', read(a, 4))[0]
    def name(a):
        return read(a, 128).split(b'\0', 1)[0].decode('ascii', 'replace')
    try:
        path = ctypes.create_unicode_buffer(32768)
        n = ctypes.c_uint32(len(path))
        if not k.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(n)):
            raise ctypes.WinError(ctypes.get_last_error())
        expected = Path('D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/C1.exe')
        if Path(path.value).resolve() != expected.resolve():
            raise ValueError('Unexpected client executable')
        for a, hexbytes in {
            0x637940: '558bec8b45088b8098000000',
            0x637c40: '558bec8b45080fb6400a5dc3',
            0xaa6980: '558bec83e4f081ecd4040000',
            0xabcfb0: '538b5c240856578db380060000bf1000',
            0xabd420: '8b158043cf008b8a401904008b442408',
            0xa7e6c8: '69c080ba1200050044cf00',
            0xab0353: '8b4d1483c518556a3653898b881300',
            0xa8265f: '8dbb80010000b90a000000be94a9fa00',
            0xa83c84: '8b0c8500062d0189742428890da8a9fa00',
            0xabcb99: '8b5c243083c41433ff83c3708d4c2420',
            0xad9e4e: '8b0d7040cf008b151843cf0089442428',
            0xab9857: 'd9442428d95668d94710',
            0x429070: 'a1acd2c3068b0c85583b6d0181f10c400b49',
        }.items():
            b = bytes.fromhex(hexbytes)
            if read(a, len(b)) != b:
                raise ValueError(f'Wrong C1 image at {a:#x}')
        index = u(0x6c3d2ac)
        if index > 1024:
            raise ValueError('Invalid CG table index')
        cg = u(0x16d3b58 + index * 4) ^ 0x490b400c
        out = dict(pid=pid, path=path.value, commandTime=u(cg))
        if not out['commandTime']:
            return dict(out, status='inactive; no scene read')
        world = u(0xcf39a0)
        out['world'] = name(u(world))
        if out['world'] != 'maps/mp/mp_killhouse_sh.d3dbsp':
            return dict(out, status='not Killhouse; no scene read')
        frontend = u(0xcf4380)
        for _ in range(200):
            if frontend >= 0x10000:
                break
            time.sleep(0.001)
            frontend = u(0xcf4380)
        out['frontendPointer'] = hex(frontend)
        if frontend < 0x10000:
            return dict(out, status='active gameplay; frontend unavailable; scene skipped')
        if frontend not in (0xcf4400, 0xcf4400 + 0x12ba80):
            raise ValueError('Frontend is not one of the two C1 static allocations')
        # Probe both allocation ends with RPM before interpreting internal fields.
        read(frontend, 4)
        read(frontend + 0x12ba80 - 4, 4)
        out['renderOriginAddedToBones'] = struct.unpack('<3f', read(0xfaa99c, 12))
        out['preparedDrawKeyCount'] = u(frontend + 0x41940)
        out['preparedDrawKeyCapacity'] = 0x4000
        out['sunTechnique'] = u(0xcf3f40)
        # ACECA4 -> ACE960 -> AB0370 copies exactly the first64 bytes of
        # sun output to the command source's shadow lookup matrix.
        lookup_bytes = read(frontend + 0x41c50, 64)
        lookup = struct.unpack('<16f', lookup_bytes)
        out['sunReceiverLookupMatrix'] = lookup
        out['sunReceiverLookupFinite'] = all(map(math.isfinite, lookup))
        # A83AEF/A83AF5: view records have stride FD0, pointer frontend+419C8.
        # Capture record zero explicitly, without assuming it is the active view.
        first_view = u(frontend + 0x419c8)
        out['firstViewPointer'] = hex(first_view)
        out['firstViewSunDestinations'] = []
        if first_view >= 0x10000:
            # A8265F copies scene FAA994 to view+180. The world callback's
            # real local source receives view+194 at source+1388, followed
            # by view+198's four floats as constant54 (AB0353..AB0363).
            # A83C84 selected the image from renderTarget[index].image;
            # A83C7E retains that index in view+FAC. Never infer GPU contents
            # from pointer agreement or use the unrelated global 2D source.
            image_input = read(first_view + 0x194, 20)
            image_pointer = struct.unpack_from('<I', image_input)[0]
            parameters = struct.unpack_from('<4f', image_input, 4)
            target_index = u(first_view + 0xfac)
            width = u(first_view + 0xfa8)
            tiles = u(first_view + 0xfb0)
            receiver_texture = dict(imagePointer=hex(image_pointer),
                parameters=parameters, parametersFinite=all(map(math.isfinite, parameters)),
                renderTargetIndex=target_index,
                targetWidth=width, targetTiles=tiles,
                note='Prepared view0 input to real local world source; does not inspect GPU depth contents or prove the active receiver draw.')
            # A83C78..A83CE8: constant54 uses full target dimensions, not
            # CF3EFC's scaled viewport extent. Only interpret bounded sizes.
            if 128 <= width <= 2048 and tiles in (1, 2, 4):
                expected_parameters = (.25 / width, .5 / (width * tiles),
                                       .5 / width, -.25 / (width * tiles))
                receiver_texture.update(expectedParameters=expected_parameters,
                    maxParameterError=max(abs(a-b) for a,b in zip(parameters, expected_parameters)),
                    dimensionsStable=(u(first_view + 0xfa8) == width and u(first_view + 0xfb0) == tiles))
            else:
                receiver_texture['parameterComparisonSkipped'] = 'Unrecognized target dimensions'
            if target_index in (10, 11):
                target = read(0x12d0600 + target_index * 20, 20)
                target_image = struct.unpack_from('<I', target)[0]
                receiver_texture.update(renderTargetName='SHADOWMAP_LARGE' if target_index == 10 else 'SHADOWMAP_SMALL',
                    expectedImagePointer=hex(target_image), imageMatchesTarget=image_pointer == target_image,
                    renderTargetWords=struct.unpack('<5I', target),
                    targetBytesStable=read(0x12d0600 + target_index * 20, 20) == target)
            else:
                receiver_texture['targetSkipped'] = 'Unexpected target index; no inferred image table read'
            receiver_texture['viewInputStable'] = read(first_view + 0x194, 20) == image_input
            out['firstViewReceiverTexture'] = receiver_texture
            # A84033 -> ABCEB0 -> ABCB99 uses frontend+41C50+70 for
            # projection records. AD9E uses frontend+41CB0 as a containing
            # record: its +78 is projection+68, not projection+78.
            view_frontend = u(first_view + 0xf94)
            bias_capture = dict(viewFrontend=hex(view_frontend), partitions=[])
            if view_frontend == frontend:
                scale_ptr, bias_ptr = u(0xcf4070), u(0xcf4318)
                if name(u(scale_ptr)) != '1611' or name(u(bias_ptr)) != '1612':
                    raise ValueError('Unexpected sun bias dvar identity')
                scale = struct.unpack('<f', read(scale_ptr + 12, 4))[0]
                bias = struct.unpack('<f', read(bias_ptr + 12, 4))[0]
                for partition in range(2):
                    projection = frontend + 0x41cc0 + partition * 0x160
                    raw = read(projection + 0x40, 64)
                    matrix = struct.unpack('<16f', raw)
                    depth_scale = matrix[10]
                    bias_capture['partitions'].append(dict(partition=partition,
                        projectionPointer=hex(projection), depthScale=depth_scale,
                        projectionMatrix=matrix, finite=all(map(math.isfinite, matrix)),
                        derivedConstant22=(bias * .03 * depth_scale, scale * .65, 0., 0.),
                        bytesStable=read(projection + 0x40, 64) == raw))
                bias_capture['viewOwnerStable'] = u(first_view + 0xf94) == view_frontend
                bias_capture['note'] = 'Derived from verified CPU inputs; does not capture GPU constant upload or shadow texels.'
            else:
                bias_capture['skipped'] = 'View owner differs from current frontend'
            out['sunDepthBiasInputs'] = bias_capture
            sun_light = u(world + 0x20)
            shadow_dvar = u(0xcf4138)
            shadow_name = name(u(shadow_dvar))
            if shadow_name != '1544':
                raise ValueError('Unexpected receiver shadow dvar identity')
            view_shadow_enabled = read(first_view + 0xfa4, 1)[0]
            shadowable_light_count = u(first_view + 0x1b0)
            # Same bit selection as AB1F4F..AB1F64; reject out-of-mask indices.
            receiver_bits = read(frontend + 0x41920, 32)
            receiver_eligible = bool(struct.unpack_from('<I', receiver_bits, (sun_light >> 5) * 4)[0] & (1 << (sun_light & 31))) if sun_light < 256 else None
            out['firstViewReceiverGate'] = dict(viewShadowByte=view_shadow_enabled,
                world20SelectedLightIndex=sun_light, shadowableLightBit=receiver_eligible,
                viewShadowableLightCount=shadowable_light_count,
                additionalLightBranchEntered=sun_light < shadowable_light_count,
                numeric1544=read(shadow_dvar + 12, 1)[0], numeric1544Reset=read(shadow_dvar + 44, 1)[0],
                note='AB1EA0 iterates additional lights beginning at world primaryLightCount(+20), ending before view+1B0. AB1F2D is the type2 branch, not sun eligibility. Technique IDs37/39 are normal/shadowed type2 choices.')
            for partition in range(2):
                desc = first_view + 0x5fc + partition * 0x94
                destination = read(desc + 0x40, 8)
                pointer, key_count = struct.unpack('<II', destination)
                item = dict(partition=partition, pointer=hex(pointer), count=key_count)
                arena = frontend + 0xd3b00
                in_arena = arena <= pointer <= arena + 0x4000 * 8 and pointer + key_count * 8 <= arena + 0x4000 * 8
                item['withinFrontendKeyArena'] = in_arena
                if pointer and key_count <= 0x4000 and in_arena:
                    data = read(pointer, key_count * 8)
                    item['sha256'] = hashlib.sha256(data).hexdigest()
                    item['keys'] = [hex(x[0]) for x in struct.iter_unpack('<Q', data)]
                    type_counts = {}
                    for packed_key, in struct.iter_unpack('<Q', data):
                        # C1 AADC08: high word >>22, mask15, dispatch BF4620.
                        surface_type = (packed_key >> 54) & 15
                        type_counts[surface_type] = type_counts.get(surface_type, 0) + 1
                    item['surfaceTypeCounts'] = type_counts
                    item['scope'] = 'Generic key stream; separate BSP/static streams also exist.'
                    item['bytesStable'] = read(pointer, len(data)) == data
                item['metadataStable'] = read(desc + 0x40, 8) == destination
                out['firstViewSunDestinations'].append(item)
        elif first_view:
            out['firstViewDestinationSkipped'] = 'Pointer is below readable user allocation range; frontend lifecycle/layout unresolved'
        out['sunDrawLists'] = []
        # ABCFB0 supplies these two source lists to ABD490 -> ABD420.
        # Actual transfer shares a 16384-key frontend allocation with other lists.
        for partition in range(2):
            count_address = 0xfaa938 + partition * 4
            pointer_address = 0xfaa960 + partition * 4
            draw_count, draw_pointer = u(count_address), u(pointer_address)
            entry = dict(partition=partition, count=draw_count, pointer=hex(draw_pointer))
            if draw_count <= 0x4000 and (draw_pointer or not draw_count):
                keys = read(draw_pointer, draw_count * 8) if draw_count else b''
                entry['sha256'] = hashlib.sha256(keys).hexdigest()
                entry['firstKeys'] = [hex(x[0]) for x in struct.iter_unpack('<Q', keys[:512])]
                entry['bytesStable'] = read(draw_pointer, len(keys)) == keys if keys else True
            else:
                entry['skipped'] = 'source count/pointer outside bounded capture'
            entry['metadataStable'] = u(count_address) == draw_count and u(pointer_address) == draw_pointer
            out['sunDrawLists'].append(entry)
        if draw_only:
            # Verified global command source used by AAA3EA and AAC4AD.
            # It is reused for 2D; mode/backend ownership must qualify evidence.
            source_address = 0x12a6b30
            source_bytes = read(source_address, 0x1774)
            source_word = lambda offset: struct.unpack_from('<I', source_bytes, offset)[0]
            source_floats = lambda offset, count: struct.unpack_from('<' + 'f' * count, source_bytes, offset)
            backend_owner = source_word(0x1404)
            raw_matrix = source_floats(0x1570, 16)
            shader_matrix = source_floats(0x300, 16)
            vector = source_floats(0x1560, 4)
            expected_last_row = [sum(vector[i] * raw_matrix[4*i+j] for i in range(4)) for j in range(4)]
            version = struct.unpack_from('<H', source_bytes, 0x16c8)[0]
            applied_version = struct.unpack_from('<H', source_bytes, 0x1666)[0]
            out['globalCommandSource'] = dict(address=hex(source_address), backendOwner=hex(backend_owner),
                ownerMatchesFrontend=backend_owner == frontend, mode=source_word(0x171c),
                viewParameters=hex(source_word(0x16f0)), selectedLight=source_word(0x16e0),
                currentLight=source_word(0x176c), sourceVersion=version, appliedVersion=applied_version,
                translationVector=vector, originalMatrix=raw_matrix, shaderMatrix=shader_matrix,
                expectedLastRow=expected_last_row,
                maxLastRowError=max(abs(a-b) for a,b in zip(expected_last_row, shader_matrix[12:])),
                bytesStable=read(source_address, len(source_bytes)) == source_bytes,
                limitation='Global source also serves 2D and is not proof of the command source used by a particular sun receiver draw.')
            out['sunReceiverLookupBytesStable'] = read(frontend + 0x41c50, 64) == lookup_bytes
            out['frontendStable'] = u(0xcf4380) == frontend
            out['viewPointerStable'] = u(frontend + 0x419c8) == first_view
            out['commandTimeAfter'] = u(cg)
            return out
        count = u(0xfb5618)
        if count > 768:
            raise ValueError('Invalid world DObj count')
        out['records'] = []
        for slot in range(count):
            a = 0xfb5624 + slot * 0x78
            raw = read(a, 0x78)
            vis = [read(x + slot, 1)[0] for x in (0xfcc4e4, 0xfcc7e4)]
            packed, obj = struct.unpack_from('<II', raw, 0x68)
            row = dict(slot=slot, entity=(packed >> 7) & 4095,
                       packedKey=hex(packed), visibility=vis,
                       preparedSurfaces=hex(struct.unpack_from('<I', raw, 0x44)[0]),
                       object=hex(obj))
            # Only actual sun partition candidates. Unused bones are not assumed valid.
            if obj and 1 in vis:
                header = read(obj, 0xc8)
                models, bones = header[9], header[10]
                matrices = struct.unpack_from('<I', header, 0x98)[0]
                row.update(modelCount=models, boneCount=bones, matrices=hex(matrices))
                if models > 32:
                    row['skipped'] = 'invalid model count'
                else:
                    pointers = struct.unpack('<' + 'I' * models, read(struct.unpack_from('<I', header, 0xc0)[0], models * 4)) if models else []
                    row['models'] = [name(u(p)) for p in pointers]
                    selected = set()
                    offset = 0
                    selection_valid = True
                    row['modelSelections'] = []
                    for model_index, model in enumerate(pointers):
                        local_count = read(model + 4, 1)[0]
                        lod = struct.unpack_from('<b', raw, 0x48 + model_index)[0]
                        item = dict(boneOffset=offset, boneCount=local_count, lod=lod)
                        # Four embedded 0x38-byte LOD records precede +0x128.
                        # Negative LOD means no selected surface in C1 637997.
                        if lod >= 4:
                            selection_valid = False
                            item['skipped'] = 'LOD outside bounded embedded records'
                        elif lod >= 0:
                            lod_data = read(model + 0x48 + lod * 0x38, 0x38)
                            bits = struct.unpack_from('<8I', lod_data, 0x10)
                            item['surfaceCount'] = struct.unpack_from('<H', lod_data, 4)[0]
                            item['partBits'] = list(bits)
                            # C1 637A81..637BAC shifts each model mask by the
                            # cumulative bone count, using MSB-first bit order.
                            for bit in range(256):
                                if bits[bit >> 5] & (0x80000000 >> (bit & 31)):
                                    if offset + bit < bones:
                                        selected.add(offset + bit)
                            item['lodBytesStable'] = read(model + 0x48 + lod * 0x38, 0x38) == lod_data
                        row['modelSelections'].append(item)
                        offset += local_count
                    row['selectedBones'] = sorted(selected) if selection_valid else None
                    row['modelBoneCountMatches'] = offset == bones
                    if matrices and bones:
                        data = read(matrices, bones * 32)
                        rows = list(struct.iter_unpack('<8f', data))
                        row['nonfiniteBones'] = [i for i, bone in enumerate(rows) if not all(map(math.isfinite, bone))]
                        row['selectedNonfiniteBones'] = [i for i in selected if not all(map(math.isfinite, rows[i]))] if selection_valid else None
                        finite = [bone for bone in rows if all(map(math.isfinite, bone))]
                        row['translationBounds'] = [[min(b[j] for b in finite), max(b[j] for b in finite)] for j in (4, 5, 6)] if finite else []
                        row['bones'] = rows
                        row['matrixBytesStable'] = read(matrices, len(data)) == data
                        row['matrixPointerStable'] = u(obj + 0x98) == matrices
            row['sceneRecordStable'] = read(a, len(raw)) == raw
            out['records'].append(row)
        out.update(frontendStable=u(0xcf4380) == frontend,
                   countStable=u(0xfb5618) == count, commandTimeAfter=u(cg),
                   limitations=['Nonatomic read; per-record stability only.',
                                'LOD masks reconstruct bounds-consumer selection; per-surface skin/hide filtering can exclude more bones.',
                                'Finite transforms do not establish GPU shadow correctness or visibility of an artifact.'])
        return out
    finally:
        k.CloseHandle(h)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pid', type=int)
    p.add_argument('output', type=Path)
    p.add_argument('--draw-only', action='store_true')
    args = p.parse_args()
    result = inspect(args.pid, args.draw_only)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))
