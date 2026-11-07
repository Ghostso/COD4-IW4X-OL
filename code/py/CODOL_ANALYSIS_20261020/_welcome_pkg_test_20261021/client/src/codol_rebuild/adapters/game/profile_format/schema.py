"""1649370 playerdata DDL 结构定义的只读导出；本模块不读写目标进程、不启动游戏。

宿主在 schema 构造点（0x7f69d0 内，asset+8 即定义对象）暂停后，把定义对象地址与
一个 read(address, size)->bytes 回调交给本模块，导出字段名/类型/数组/字节偏移为
JSON，供后续按结构读写档案（progression.seed 与 profile_store 的偏移换算依赖它）。

结构布局来源与置信度：
- 已交叉验证：新版 0x7f69d0 处 [asset+8]=定义对象、[定义对象+0x30]=size，与旧版
  2.6.9.7 导出器 header 索引 12（=+0x30）为 size 一致；size 上限 0x7ffc(=32764)
  也与新版缓冲区容量一致。
- 强推断（未经新版运行证实）：其余 header 索引（枚举/结构体/数组/根类型/偏移表）
  沿用同引擎 DDL 布局。为兜底，本模块在解析前先原样留存 header 字与相关内存页，
  即使布局不符也可离线重新推导，不会因断言失败丢失证据。

导出写入指定文件夹：
- playerdata-schema.json —— 解析后的结构定义（成功时）；
- schema-raw-header.json —— 原始 16 字头部与各表指针（总是先写）；
- asset-pages.json / asset-page-XXXXXXXX.bin —— 定义对象所在及邻接内存页。
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

# 新版档案 DDL 数据缓冲容量（0x7f69d0 要求 schema+0x30 的 size <= 0x7ffc）。
MAX_PROFILE_SIZE = 0x7FFC

# 定义对象头部布局（16 个 32 位字）。索引含义见模块 docstring；size 在索引 12。
_HEADER_WORDS = 16
_IDX_ENUM_COUNT, _IDX_ENUM_TABLE = 2, 3
_IDX_STRUCT_COUNT, _IDX_STRUCT_TABLE = 4, 5
_IDX_INDEXED_COUNT, _IDX_INDEXED_TABLE = 6, 7
_IDX_ENUMED_COUNT, _IDX_ENUMED_TABLE = 8, 9
_IDX_ROOT_TYPE = 10
_IDX_SIZE = 12
_IDX_OFFSET_COUNT, _IDX_OFFSET_TABLE = 13, 14


def _words(read, address: int, count: int) -> tuple:
    return struct.unpack('<' + 'I' * count, read(address, 4 * count))


def _name(read, address: int) -> str:
    """读一个 NUL 结尾的 UTF-8 名称；地址为 0 或不可读时给出可识别占位。"""
    if not address:
        return ''
    try:
        return read(address, 256).split(b'\x00')[0].decode('utf-8', errors='replace')
    except OSError:
        return f'@{address:08x}'


def _dump_raw_evidence(read, folder: Path, address: int, header: tuple) -> dict:
    """在解析前原样留存头部与相关内存页，作为布局不符时的重新推导依据。"""
    raw = {'address': hex(address), 'header': [hex(x) for x in header], 'tables': {}}
    for label, index in [('enums', _IDX_ENUM_TABLE), ('structs', _IDX_STRUCT_TABLE),
                         ('indexed_arrays', _IDX_INDEXED_TABLE), ('enumed_arrays', _IDX_ENUMED_TABLE),
                         ('offsets', _IDX_OFFSET_TABLE)]:
        if header[index] > 65536:
            try:
                raw['tables'][label] = {'address': hex(header[index]),
                                        'words': [hex(x) for x in _words(read, header[index], 64)]}
            except OSError as exc:
                raw['tables'][label] = {'error': str(exc)}
    (folder / 'schema-raw-header.json').write_text(json.dumps(raw, indent=2), encoding='utf-8')

    anchors = {address & ~65535}
    anchors.update(header[i] & ~65535 for i in
                   (_IDX_ENUM_TABLE, _IDX_STRUCT_TABLE, _IDX_INDEXED_TABLE, _IDX_ENUMED_TABLE, _IDX_OFFSET_TABLE)
                   if header[i] > 65536)
    regions = []
    for anchor in sorted(anchors):
        for base in range(max(0, anchor - 65536), anchor + 196608, 65536):
            if any(region['base'] == base for region in regions):
                continue
            try:
                block = read(base, 65536)
            except OSError:
                continue
            name = f'asset-page-{base:08x}.bin'
            (folder / name).write_bytes(block)
            regions.append({'base': base, 'file': name, 'size': len(block)})
    (folder / 'asset-pages.json').write_text(json.dumps(regions, indent=2), encoding='utf-8')
    return raw


def capture_schema(read, address: int, folder: Path, *,
                   profile_buffer: int | None = None) -> dict:
    """从定义对象地址导出结构定义，返回摘要；先落原始证据再做严格解析。

    read(address, size)->bytes 由宿主提供（只读目标进程内存）。folder 为会话证据目录。
    profile_buffer 若给定（新版记录 +0x90 的 DDL 缓冲地址），额外留存捕获时刻的档案原始
    内容供后续对比；不给定则跳过，绝不沿用旧版固定地址。
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    header = _words(read, address, _HEADER_WORDS)
    _dump_raw_evidence(read, folder, address, header)

    size = header[_IDX_SIZE]
    if not 0 < size <= MAX_PROFILE_SIZE:
        raise ValueError(f'定义对象 size={size} 超出新版档案缓冲上限 {MAX_PROFILE_SIZE}；'
                         '头部布局可能与旧版不同，请核对 schema-raw-header.json')
    for label, index in [('enums', _IDX_ENUM_COUNT), ('structs', _IDX_STRUCT_COUNT),
                         ('indexed_arrays', _IDX_INDEXED_COUNT), ('enumed_arrays', _IDX_ENUMED_COUNT)]:
        if header[index] >= 4096:
            raise ValueError(f'{label} 数量 {header[index]} 异常，头部布局可能与旧版不同')

    out = {'address': hex(address), 'header': [hex(x) for x in header],
           'root_type': list(header[_IDX_ROOT_TYPE:_IDX_ROOT_TYPE + 2]), 'size': size}

    enums = []
    for i in range(header[_IDX_ENUM_COUNT]):
        count, _value_table, name_table = _words(read, header[_IDX_ENUM_TABLE] + 12 * i, 3)
        if count >= 16384:
            raise ValueError(f'枚举 {i} 条目数 {count} 异常')
        entries = []
        for j in range(count):
            name_addr, index = _words(read, name_table + 8 * j, 2)
            entries.append({'name': _name(read, name_addr), 'index': index})
        enums.append({'header': [count, _value_table, name_table], 'entries': entries})

    structs = []
    for i in range(header[_IDX_STRUCT_COUNT]):
        prop_count, prop_table, extra1, extra2, header4 = _words(read, header[_IDX_STRUCT_TABLE] + 20 * i, 5)
        if prop_count >= 8192:
            raise ValueError(f'结构体 {i} 属性数 {prop_count} 异常')
        props = []
        for j in range(prop_count):
            name_addr, kind, index, offset, extra_a, extra_b = _words(read, prop_table + 24 * j, 6)
            props.append({'name': _name(read, name_addr), 'type': [kind, index],
                          'offset': offset, 'extra': [extra_a, extra_b]})
        structs.append({'header': [prop_count, prop_table, extra1, extra2, header4], 'properties': props})

    out.update(enums=enums, structs=structs,
               indexed_arrays=[list(_words(read, header[_IDX_INDEXED_TABLE] + 16 * i, 4))
                               for i in range(header[_IDX_INDEXED_COUNT])],
               enumed_arrays=[list(_words(read, header[_IDX_ENUMED_TABLE] + 16 * i, 4))
                              for i in range(header[_IDX_ENUMED_COUNT])])

    if 0 < header[_IDX_OFFSET_COUNT] < 65536 and header[_IDX_OFFSET_TABLE] > 65536:
        out['offsets'] = list(_words(read, header[_IDX_OFFSET_TABLE], header[_IDX_OFFSET_COUNT]))

    if profile_buffer is not None:
        try:
            (folder / 'profile-before.bin').write_bytes(read(profile_buffer, MAX_PROFILE_SIZE))
        except OSError:
            pass

    (folder / 'playerdata-schema.json').write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'schema': str(folder / 'playerdata-schema.json'), 'size': size,
            'root_type': out['root_type'],
            'counts': {'enums': header[_IDX_ENUM_COUNT], 'structs': header[_IDX_STRUCT_COUNT],
                       'indexed_arrays': header[_IDX_INDEXED_COUNT],
                       'enumed_arrays': header[_IDX_ENUMED_COUNT],
                       'offsets': header[_IDX_OFFSET_COUNT]}}
