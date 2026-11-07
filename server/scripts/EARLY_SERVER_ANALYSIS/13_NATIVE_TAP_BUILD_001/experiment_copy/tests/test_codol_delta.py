"""Native snapshot value codecs against alpha0022's independent wire model."""
import argparse
import ast
import ctypes as C
import importlib.util
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

ROOT = Path(__file__).resolve().parents[1]
LIB = REF = None
ANIM = None


class Msg(C.Structure):
    _fields_ = [('data', C.c_void_p), ('size', C.c_size_t), ('capacity', C.c_size_t),
                ('cursor', C.c_size_t), ('bit', C.c_size_t), ('failed', C.c_int)]


class Context(C.Structure):
    _fields_ = [('server_time', C.c_uint32), ('position_base', C.c_int32 * 3),
                ('clamp_positions', C.c_int), ('clamped', C.c_uint)]

class PlayerFields(C.Structure):
    _fields_ = [('field', C.c_uint32 * 244)]

class PlayerField(C.Structure):
    _fields_ = [('offset', C.c_uint16), ('bits', C.c_int16), ('hint', C.c_uint8)]

class Entity(C.Structure):
    _fields_ = [('number', C.c_uint16), ('type', C.c_uint16), ('field', C.c_uint32*66)]

def read_entity_with_hint_pass(data, before=None):
    """C1 0x5A0C00 read sequence, including 0x5A0DD9's [0,lc) pass.

    alpha0022's decoder omits this pass. Use its independent value decoders,
    but transcribe the entity ordering from the shipped client.
    """
    r = REF.MsgReader(data)
    number = REF._read_index(r, -1)
    assert r.read_bit() == 0 and r.read_bit() == 1
    no_delta_pos = r.read_bit()
    lc = r.read_bits(7)
    assert REF._read_gap(r) == 1
    etype = REF.decode_value(r, -77, 20000, kind='i')
    table = REF.entity_table(etype)
    out = list(before.field) if before else [0]*66
    out[0] = etype
    def field(index):
        _, bits, _ = table[index]
        base = before.field[index] if before and before.type == etype and not (
            no_delta_pos and -83 <= bits <= -78) else 0
        if REF.kind_of(bits) == 'f':
            base = struct.unpack('<f', struct.pack('<I', base))[0]
        value = REF.decode_value(r, bits, 20000, frm=base)
        out[index] = word(bits, value)
    last = 0
    while last != lc:
        last += REF._read_gap(r)
        assert last <= lc
        field(last)
    for index in range(lc):
        if table[index][2] == 2:
            field(index)
    assert REF._read_index(r, number) == 2047
    return out

class Client(C.Structure):
    _fields_ = [('number', C.c_uint), ('field', C.c_uint32*77)]

class Actor(C.Structure):
    _fields_ = [('number', C.c_uint), ('data', C.c_uint8*92)]

class Anim(C.Structure):
    _fields_ = [('time', C.c_uint32), ('entity', C.c_uint16), ('ref', C.c_uint16),
                ('sub', C.c_uint16), ('type', C.c_uint8), ('arg2', C.c_uint8),
                ('rate', C.c_float), ('weight', C.c_float), ('blend', C.c_float), ('fraction', C.c_float)]

class Snapshot(C.Structure):
    _fields_ = [('sequence', C.c_uint32), ('player', C.POINTER(PlayerFields)), ('hud', C.c_void_p),
                ('entities', C.POINTER(Entity)), ('entity_count', C.c_size_t),
                ('clients', C.POINTER(Client)), ('client_count', C.c_size_t),
                ('actors', C.POINTER(Actor)), ('actor_count', C.c_size_t)]

class HudElement(C.Structure):
    _fields_ = [('field', C.c_uint32*42)]

class Hud(C.Structure):
    _fields_ = [('count', C.c_uint*2), ('elements', (HudElement*31)*2)]


def word(bits, value):
    if REF.kind_of(bits) == 'f':
        return struct.unpack('<I', struct.pack('<f', value))[0]
    return value & 0xffffffff


def normalized(bits, value):
    return REF.i2f(word(bits, value)) if REF.kind_of(bits) == 'f' else value


def vectors():
    samples = {
        0: [(0., -0.), (12., 0.), (-1., 4095.), (2., -4096.), (0., 1.25), (8., 5000.)],
        -99: [(0., -0.), (1., 0.), (2., 2047.), (2., 2048.), (0., 1.25)],
        -89: [(2., 3.), (2., -4096.), (0., -0.), (0., 1.25)],
        -96: [(0, n) for n in (0, 1, 7, 8, 2046, 2047)],
        -98: [(0, n) for n in (0, 1, 0x3fffffff)],
        -75: [(100, n) for n in (100, 101, 132, 133, 2047, 0)],
        -76: [(0, n) for n in (-128, -17, -16, 0, 15, 16, 127)],
        -85: [(0, 0), (0, 0xf8abcdef)],
        -86: [(0., n) for n in (0., 0.1, 1.25, 6.3)],
        -65: [(0, n) for n in (0, 100, 102300)],
    }
    for b in (-92, -91, -90, -83, -82, -81):
        samples[b] = [(0., -32768.), (9.5, -10.5), (-123.25, 32767.), (0., 0.)]
    for b in (-100, -79, -87):
        samples[b] = [(0., n) for n in (-360., -90., 0., 0.5, 90., 359.9, 720.)]
    for b in (-97, -74, -72, -70, -69):
        samples[b] = [(0, n) for n in (20000, 19999, 19745, 19744, 19950, 19650, 7200, 20001)]
    for b, maximum in ((-77, 255), (-93, 2047), (-94, 255), (-84, 127)):
        samples[b] = [(0, n) for n in (0, 1, maximum)]
    for b in (-80, -78, -88):
        samples[b] = [(123.25, -456.75), (0., -0.)]
    for b in (-73, -71):
        samples[b] = [(123, 0xffffffff)]
    for b in range(1, 33):
        samples[b] = [(0, 0), (3, (1 << b)-1)]
        samples[-b] = [(0, -(1 << (b-1))), (0, (1 << (b-1))-1)]
    for bits, pairs in samples.items():
        for old, new in pairs:
            yield bits, normalized(bits, old), normalized(bits, new)


def encode(bits, old, new, pool=0, capacity=128, context=None):
    backing = C.create_string_buffer(capacity)
    msg = Msg()
    ctx = context or Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
    LIB.CODOL_MsgWriteInit(C.byref(msg), backing, capacity)
    if pool:
        LIB.CODOL_WriteBits(C.byref(msg), (1 << pool)-1, pool)
        LIB.CODOL_WriteByte(C.byref(msg), 0xa5)
    result = LIB.CODOL_WriteDeltaValue(C.byref(msg), bits, word(bits, old), word(bits, new), C.byref(ctx))
    return result, backing.raw[:msg.size], msg, ctx


class Delta(unittest.TestCase):
    def test_pending_history_transport_acceptance(self):
        h = LIB.CODOL_CreateHistory()
        ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
        player = PlayerFields(); player.field[0] = 1234
        state = Snapshot(); state.sequence = 1; state.player = C.pointer(player)
        try:
            self.assertTrue(LIB.CODOL_PrepareHistory(h, C.byref(state), 0, 1, C.byref(ctx)))
            self.assertFalse(LIB.CODOL_FindHistoryBase(h, 1, 2))
            self.assertFalse(LIB.CODOL_PrepareHistory(h, C.byref(state), 0, 1, C.byref(ctx)))
            self.assertFalse(LIB.CODOL_FinishHistory(h, 2, 1))
            self.assertTrue(LIB.CODOL_FinishHistory(h, 1, 0))
            self.assertFalse(LIB.CODOL_FindHistoryBase(h, 1, 2))
            self.assertTrue(LIB.CODOL_PrepareHistory(h, C.byref(state), 0, 1, C.byref(ctx)))
            player.field[0] = 9999
            self.assertTrue(LIB.CODOL_FinishHistory(h, 1, 1))
            self.assertEqual(LIB.CODOL_FindHistoryBase(h, 1, 2).contents.player.contents.field[0], 1234)
            self.assertFalse(LIB.CODOL_FinishHistory(h, 1, 1))
            state.sequence = 2
            self.assertTrue(LIB.CODOL_PrepareHistory(h, C.byref(state), 1, 1, C.byref(ctx)))
            self.assertTrue(LIB.CODOL_FindHistoryBase(h, 1, 2))
            LIB.CODOL_ClearHistory(h)
            self.assertFalse(LIB.CODOL_FinishHistory(h, 2, 1))
            self.assertFalse(LIB.CODOL_FindHistoryBase(h, 1, 2))
        finally:
            LIB.CODOL_DestroyHistory(h)

    def test_reached_snapshot_history(self):
        history = LIB.CODOL_CreateHistory()
        ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
        try:
            player, entity, client, hud = PlayerFields(), Entity(), Client(), Hud()
            entity.number = 7; entity.type = 1; client.number = 3
            position = next(i for i in range(1, 66) if LIB.CODOL_EntityField(1, i).contents.bits == -82)
            entity.field[position] = word(-82, 12.7)
            angle = next(i for i in range(244) if LIB.CODOL_PlayerField(i).contents.bits == -100)
            player.field[angle] = word(-100, 270.)
            cf = next(i for i in range(77) if LIB.CODOL_ClientField(i).contents.bits == 0)
            client.field[cf] = word(0, 1.25)
            hud.count[0] = 1; hud.elements[0][0].field[3] = 1
            hud.elements[0][0].field[16] = word(-86, 1.25)
            state = Snapshot(1, C.pointer(player), C.addressof(hud), C.pointer(entity), 1,
                             C.pointer(client), 1, None, 0)
            self.assertTrue(LIB.CODOL_CommitReachedHistory(history, C.byref(state), 0, 1, C.byref(ctx)))
            held = LIB.CODOL_FindHistoryBase(history, 1, 2).contents
            self.assertEqual(held.player.contents.field[angle], word(-100, -90.))
            self.assertEqual(held.entities[0].field[position], word(-82, 13.))
            self.assertEqual(held.clients[0].field[cf], word(0, 1.25))
            self.assertEqual(C.cast(held.hud, C.POINTER(Hud)).contents.elements[0][0].field[16], word(-86, 1.2))
            state.sequence = 2
            self.assertFalse(LIB.CODOL_CommitReachedHistory(history, C.byref(state), 99, 1, C.byref(ctx)))
            hud.count[0] = 32
            self.assertFalse(LIB.CODOL_CommitReachedHistory(history, C.byref(state), 1, 1, C.byref(ctx)))
            self.assertTrue(LIB.CODOL_FindHistoryBase(history, 1, 2))
            hud.count[0] = 0
            self.assertTrue(LIB.CODOL_CommitReachedHistory(history, C.byref(state), 1, 1, C.byref(ctx)))
            held = LIB.CODOL_FindHistoryBase(history, 2, 3).contents
            self.assertEqual(held.entities[0].field[position], word(-82, 13.))
            self.assertEqual(C.cast(held.hud, C.POINTER(Hud)).contents.count[0], 0)
        finally:
            LIB.CODOL_DestroyHistory(history)

    def test_owned_snapshot_history(self):
        history = LIB.CODOL_CreateHistory()
        self.assertTrue(history)
        try:
            player = PlayerFields(); player.field[0] = 100
            entity = Entity(); entity.number = 7; entity.type = 1; entity.field[1] = 123
            state = Snapshot(); state.sequence = 1; state.player = C.pointer(player)
            state.entities = C.pointer(entity); state.entity_count = 1
            self.assertTrue(LIB.CODOL_CommitHistory(history, C.byref(state)))
            player.field[0] = 999; entity.field[1] = 999
            held = LIB.CODOL_FindHistoryBase(history, 1, 2)
            self.assertTrue(held)
            self.assertEqual(held.contents.player.contents.field[0], 100)
            self.assertEqual(held.contents.entities[0].field[1], 123)
            self.assertFalse(LIB.CODOL_CommitHistory(history, C.byref(state)))
            self.assertFalse(LIB.CODOL_FindHistoryBase(history, 2, 3))
            self.assertFalse(LIB.CODOL_FindHistoryBase(history, 1, 33))
            self.assertTrue(LIB.CODOL_FindHistoryBase(history, 1, 32))
            state.sequence = 33
            self.assertTrue(LIB.CODOL_CommitHistory(history, C.byref(state)))
            self.assertFalse(LIB.CODOL_FindHistoryBase(history, 1, 34))
            self.assertTrue(LIB.CODOL_FindHistoryBase(history, 33, 34))
            state.sequence = 34; state.entity_count = 2048
            self.assertFalse(LIB.CODOL_CommitHistory(history, C.byref(state)))
            self.assertEqual(LIB.CODOL_FindHistoryBase(history, 33, 34).contents.sequence, 33)
            LIB.CODOL_ClearHistory(history)
            self.assertFalse(LIB.CODOL_FindHistoryBase(history, 33, 34))
            state.sequence = 1; state.entity_count = 1
            self.assertTrue(LIB.CODOL_CommitHistory(history, C.byref(state)))
        finally:
            LIB.CODOL_DestroyHistory(history)

    def test_client_held_values(self):
        cases = list(vectors()) + [(b, 100000., 3.) for b in (0, -89, -99)]
        cases += [(b, 0., 3.) for b in (-100, -79, -87)]
        for bits, old, new in cases:
            ok, data, _, ctx = encode(bits, old, new)
            self.assertTrue(ok)
            decoded = REF.decode_value(REF.MsgReader(data), bits, server_time=20000, frm=old)
            if bits == -87:
                # entity_codec double-sign-extends its already signed read_short;
                # the dedicated player-state reader implements this arm correctly.
                decoded = REF.pf.decode_field(REF.MsgReader(data), bits, old, 20000, 'f')
            if bits == -85:
                decoded = sum(c << (8*i) for i, c in enumerate(decoded))
            held = C.c_uint32(0xdeadbeef)
            self.assertTrue(LIB.CODOL_ReachDeltaValue(bits, word(bits, old), word(bits, new), C.byref(ctx), C.byref(held)))
            self.assertEqual(held.value, word(bits, decoded))
        # Explicit proof of the trimmed-base regression: large -> small is exact.
        for bits in (0, -89, -99):
            _, data, _, _ = encode(bits, 100000., 3.)
            self.assertEqual(REF.decode_value(REF.MsgReader(data), bits, frm=100000.), 3.)

    def test_held_player_prediction(self):
        base, desired, held = PlayerFields(), PlayerFields(), PlayerFields()
        ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
        for i, (offset, bits, hint) in enumerate(REF.pf.NETFIELDS):
            if hint == 3 or offset in (0x14c, 0x150, 0x154):
                base.field[i] = word(bits, 1)
        self.assertTrue(LIB.CODOL_ReachPlayerFields(C.byref(held), C.byref(base), C.byref(desired), 0, C.byref(ctx)))
        self.assertEqual(list(held.field), list(base.field))
        self.assertTrue(LIB.CODOL_ReachPlayerFields(C.byref(held), C.byref(base), C.byref(desired), 1, C.byref(ctx)))
        self.assertEqual(list(held.field), list(desired.field))

    def test_snapshot_assembly(self):
        player = PlayerFields(); player.field[0] = 20000
        state = Snapshot(); state.sequence = 10; state.player = C.pointer(player)
        base = Snapshot(); base.sequence = 9; base.player = C.pointer(player)
        for delta in (False, True):
            buffer = C.create_string_buffer(4096); msg = Msg()
            ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
            flags = 0 if delta else 8
            self.assertTrue(LIB.CODOL_WriteSnapshot(C.byref(msg), C.byref(state), C.byref(base) if delta else None,
                None, None, 0, flags, 1, C.byref(ctx)))
            w = REF.MsgWriter()
            w.write_byte(0); w.write_long(20000); w.write_byte(int(delta)); w.write_byte(flags)
            w.write_bit(int(delta)); w.write_bit(1); w.write_bits(0 if delta else 1, 8)
            if not delta:
                REF.pf.write_gap(w, 1); REF.encode_value(w, -97, 20000, server_time=20000)
            w.write_bits(0, 7) # empty player array sections
            w.write_bits(0, 5) # animation terminator
            w.write_bit(0) # actors
            REF.encode_entities(w, [], 20000)
            w.write_bit(0); w.write_bit(0); w.write_byte(5)
            self.assertEqual(buffer.raw[:msg.size], w.bytes())
            for capacity in range(msg.size):
                test = Msg(); LIB.CODOL_MsgWriteInit(C.byref(test), buffer, capacity)
                self.assertFalse(LIB.CODOL_WriteSnapshot(C.byref(test), C.byref(state), C.byref(base) if delta else None,
                    None, None, 0, flags, 1, C.byref(ctx)))
        state.sequence = 41 # base gap exceeds retained client ring
        LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
        self.assertFalse(LIB.CODOL_WriteSnapshot(C.byref(msg), C.byref(state), C.byref(base),
            None, None, 0, 0, 1, C.byref(ctx)))

    def test_animation_commands(self):
        commands = (Anim*48)()
        refs = []
        values = (-1., 0., .1, .2, .5, 1., 2., 8.)
        for i, c in enumerate(commands):
            c.time = 20000 - (0 if i < 8 else 255 if i < 16 else 1000)
            c.entity = (i//3) * 100; c.ref = 2047-i; c.type = 1+i%6; c.arg2 = i%4
            c.sub = (0, 3, 2047)[i%3]
            c.rate = values[i%8]; c.weight = values[(i+1)%8]
            c.blend = values[(i+2)%8]; c.fraction = values[(i+3)%8]
            refs.append(ANIM['AnimCmd'](c.type, c.entity, c.ref, c.time, sub=c.sub,
                rate=c.rate, weight=c.weight, blend=c.blend, frac=c.fraction, arg2=c.arg2))
        for count in (0, 1, len(commands)):
            for pool in range(8):
                buffer = C.create_string_buffer(4096); msg = Msg()
                LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
                LIB.CODOL_WriteBits(C.byref(msg), 5, pool)
                self.assertTrue(LIB.CODOL_WriteAnimCommands(C.byref(msg), commands, count, 20000))
                writer = REF.MsgWriter(); writer.write_bits(5, pool)
                ANIM['encode_animcmds'](writer, refs[:count], 20000)
                self.assertEqual(buffer.raw[:msg.size], writer.bytes())
        size = msg.size
        for capacity in range(size):
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, capacity)
            LIB.CODOL_WriteBits(C.byref(msg), 5, 7)
            self.assertFalse(LIB.CODOL_WriteAnimCommands(C.byref(msg), commands, len(commands), 20000))
        commands[0].entity = 2048
        LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
        self.assertFalse(LIB.CODOL_WriteAnimCommands(C.byref(msg), commands, 1, 20000))

    def test_actor_records_and_overlap(self):
        import actor_codec as ac
        def mapped(actor):
            data = bytes(actor.data)
            return {off: struct.unpack_from('<I', data, off)[0] for off, _, _ in ac.ACTOR_FIELDS}
        changes = [(off, struct.pack('<I', 1)) for off, _, _ in ac.ACTOR_FIELDS]
        changes += [(0x44, bytes.fromhex('123456789abcdef0'))]
        for offset, change in changes:
            old, new = Actor(), Actor(); old.number = new.number = 31
            for i, value in enumerate(change): new.data[offset+i] = value
            for before, after in ((old, new), (new, old), (new, new)):
                buffer = C.create_string_buffer(4096); msg = Msg()
                ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
                LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
                self.assertTrue(LIB.CODOL_WriteActors(C.byref(msg), C.byref(before), 1, C.byref(after), 1, C.byref(ctx)))
                writer = REF.MsgWriter()
                ac.encode_actors(writer, {31: mapped(after)}, {31: mapped(before)}, 20000, allow_overlap=True)
                self.assertEqual(buffer.raw[:msg.size], writer.bytes())
                # Reconstruct actual overlapping bytes, not separate logical slots.
                decoded = ac.decode_actors(REF.MsgReader(buffer.raw[:msg.size]), {31: mapped(before)}, 20000)
                rebuilt = bytearray(before.data)
                for off, _, _ in ac.ACTOR_FIELDS:
                    struct.pack_into('<I', rebuilt, off, decoded[31][off] & 0xffffffff)
                self.assertEqual(rebuilt[4:], bytes(after.data)[4:])

    def test_client_records(self):
        import snapshot_sections as sections
        for i, (offset, bits, hint) in enumerate(sections.CLIENT_STATE_FIELDS):
            actual = LIB.CODOL_ClientField(i).contents
            self.assertEqual((actual.offset, actual.bits, actual.hint), (offset, bits, hint))
            client = Client(); client.number = 31
            value = 90.0 if bits == 0 else 1
            client.field[i] = word(bits, value)
            buffer = C.create_string_buffer(4096); msg = Msg()
            ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
            self.assertTrue(LIB.CODOL_WriteClients(C.byref(msg), None, 0, C.byref(client), 1, C.byref(ctx)))
            writer = REF.MsgWriter()
            sections.encode_clients(writer, [{'clientNum': 31, 'fields': {offset: value}}], 20000)
            self.assertEqual(buffer.raw[:msg.size], writer.bytes())
        for remove in (False, True):
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
            self.assertTrue(LIB.CODOL_WriteClients(C.byref(msg), C.byref(client), 1,
                None if remove else C.byref(client), 0 if remove else 1, C.byref(ctx)))
            writer = REF.MsgWriter()
            sections.encode_clients(writer, [{'clientNum': 31, 'removed': True}] if remove else [], 20000)
            self.assertEqual(buffer.raw[:msg.size], writer.bytes())
        # A previously nonzero field becoming zero is an update, not omission.
        cleared = Client(); cleared.number = 31
        LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
        self.assertTrue(LIB.CODOL_WriteClients(C.byref(msg), C.byref(client), 1, C.byref(cleared), 1, C.byref(ctx)))
        writer = REF.MsgWriter()
        sections.encode_clients(writer, [{'clientNum': 31, 'fields': {offset: 0}}], 20000)
        self.assertEqual(buffer.raw[:msg.size], writer.bytes())
        cleared.number = 32
        self.assertFalse(LIB.CODOL_WriteClients(C.byref(msg), None, 0, C.byref(cleared), 1, C.byref(ctx)))

    def test_entity_tables_and_baselines(self):
        for etype in range(22):
            table = REF.entity_table(etype)
            for i, entry in enumerate(table):
                native_field = LIB.CODOL_EntityField(etype, i).contents
                self.assertEqual((native_field.offset, native_field.bits, native_field.hint), entry)
            for i in range(1, 66):
                entity = Entity(); entity.type = etype; entity.number = 1024
                offset, bits, _ = table[i]
                value = 90.0 if REF.kind_of(bits) == 'f' else 1
                entity.field[i] = word(bits, value)
                buffer = C.create_string_buffer(1024); msg = Msg()
                ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
                LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
                ok = LIB.CODOL_WriteEntities(C.byref(msg), None, 0, C.byref(entity), 1, C.byref(ctx))
                if any(h == 2 for _, _, h in table[:i+1]):
                    self.assertTrue(ok)
                    expected = list(entity.field); expected[0] = etype
                    self.assertEqual(read_entity_with_hint_pass(buffer.raw[:msg.size]), expected)
                    continue
                self.assertTrue(ok)
                writer = REF.MsgWriter()
                REF.encode_entities(writer, [{'number': 1024, 'eType': etype, 'fields': {offset: value}}], 20000)
                self.assertEqual(buffer.raw[:msg.size], writer.bytes())

    def test_entity_hint_pass_deltas(self):
        table = REF.entity_table(13)
        for source_type in (1, 13):
            for index in range(1, 66):
                old, new = Entity(), Entity()
                old.type = source_type; new.type = 13
                old.number = new.number = 7
                if source_type == 13:
                    for j, (_, bits, hint) in enumerate(table):
                        if hint == 2:
                            old.field[j] = new.field[j] = word(bits, 1)
                new.field[index] = word(table[index][1], 2)
                buffer = C.create_string_buffer(4096); msg = Msg()
                ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
                LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
                self.assertTrue(LIB.CODOL_WriteEntities(C.byref(msg), C.byref(old), 1,
                    C.byref(new), 1, C.byref(ctx)))
                # Compare with client-held quantized values, including protected
                # fields and type changes, rather than assuming float identity.
                held = Entity()
                self.assertTrue(LIB.CODOL_ReachEntity(C.byref(held), C.byref(old), C.byref(new), C.byref(ctx)))
                self.assertEqual(read_entity_with_hint_pass(buffer.raw[:msg.size], old), list(held.field))
        for capacity in range(msg.size):
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, capacity)
            self.assertFalse(LIB.CODOL_WriteEntities(C.byref(msg), C.byref(old), 1,
                C.byref(new), 1, C.byref(ctx)))

    def test_entity_removal_and_unchanged(self):
        states = (Entity*4)()
        for i, number in enumerate((0, 510, 1024, 2046)):
            states[i].number = number; states[i].type = 1
        for before, nf, after, nt in ((states, 4, states, 4), (states, 4, None, 0)):
            buffer = C.create_string_buffer(1024); msg = Msg()
            ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
            self.assertTrue(LIB.CODOL_WriteEntities(C.byref(msg), before, nf, after, nt, C.byref(ctx)))
            writer = REF.MsgWriter()
            REF.encode_entities(writer, [] if nt else [{'number': e.number, 'removed': True} for e in states], 20000)
            self.assertEqual(buffer.raw[:msg.size], writer.bytes())
        states[1].number = 0
        self.assertFalse(LIB.CODOL_WriteEntities(C.byref(msg), None, 0, states, 4, C.byref(ctx)))

    def test_entity_type_change_and_clear(self):
        for changed_type in (False, True):
            old, new = Entity(), Entity()
            old.type = 1; new.type = 2 if changed_type else 1
            old.number = new.number = 7
            old.field[1] = word(REF.entity_table(1)[1][1], 1)
            buffer = C.create_string_buffer(4096); msg = Msg()
            ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
            LIB.CODOL_MsgWriteInit(C.byref(msg), buffer, len(buffer))
            self.assertTrue(LIB.CODOL_WriteEntities(C.byref(msg), C.byref(old), 1, C.byref(new), 1, C.byref(ctx)))
            writer = REF.MsgWriter(); REF._write_index(writer, 7, -1)
            fields = {0: new.type}
            if changed_type:
                fields.update({i: 0.0 if REF.kind_of(b) == 'f' else 0
                               for i, (_, b, _) in enumerate(REF.entity_table(new.type)) if i})
            else:
                fields[1] = 0
            REF.encode_entity_payload(writer, new.type, fields, 20000,
                                      no_delta_pos=not changed_type,
                                      frm_by_index={1: 1} if not changed_type and
                                          REF.entity_table(new.type)[1][1] not in range(-83, -77) else None)
            REF._write_index(writer, 2047, 7)
            self.assertEqual(buffer.raw[:msg.size], writer.bytes())

    def test_player_table(self):
        for i, entry in enumerate(REF.pf.NETFIELDS):
            actual = LIB.CODOL_PlayerField(i).contents
            self.assertEqual((actual.offset, actual.bits, actual.hint), entry)
        self.assertFalse(LIB.CODOL_PlayerField(244))

    def test_player_field_assembly(self):
        rng = random.Random(187)
        # Includes hint-2-only frames, the final field, clears, and sparse gaps.
        cases = [[], *[[i] for i in range(244)], list(range(244))]
        cases += [rng.sample(range(244), rng.randrange(1, 100)) for _ in range(100)]
        for indices in cases:
            for rov in (0, 1):
                old, new = PlayerFields(), PlayerFields()
                for i, (_, bits, _) in enumerate(REF.pf.NETFIELDS):
                    if REF.kind_of(bits) == 'f':
                        value = 2.0
                    else:
                        value = 0 if i % 2 else 1
                    old.field[i] = new.field[i] = word(bits, value)
                for i in indices:
                    _, bits, _ = REF.pf.NETFIELDS[i]
                    # Alternating clears and changes; width-one fields stay representable.
                    value = (90.0 if i % 2 else 0.0) if REF.kind_of(bits) == 'f' else (1 if i % 2 else 0)
                    new.field[i] = word(bits, value)
                backing = C.create_string_buffer(8192); msg = Msg()
                ctx = Context(20000, (C.c_int32*3)(0, 0, 0), 0, 0)
                LIB.CODOL_MsgWriteInit(C.byref(msg), backing, len(backing))
                # Shared pool with the usingDeltaPlayerstate bit in the actual snapshot.
                LIB.CODOL_WriteBits(C.byref(msg), 1, 1)
                self.assertTrue(LIB.CODOL_WritePlayerFields(C.byref(msg), C.byref(old), C.byref(new), rov, C.byref(ctx)))
                reader = REF.MsgReader(backing.raw[:msg.size])
                self.assertEqual(reader.read_bit(), 1)
                self.assertEqual(reader.read_bit(), rov)
                lc = reader.read_bits(8)
                self.assertEqual(lc, max(indices) + 1 if indices else 0)
                result = list(old.field)
                index = -1
                while index < lc - 1:
                    index += REF.pf.read_gap(reader)
                    _, bits, hint = REF.pf.NETFIELDS[index]
                    base = 0 if rov and hint == 3 else old.field[index]
                    base = REF.i2f(base) if REF.kind_of(bits) == 'f' else base
                    value = REF.decode_value(reader, bits, server_time=20000, frm=base)
                    result[index] = word(bits, value)
                for i in range(lc-1):
                    _, bits, hint = REF.pf.NETFIELDS[i]
                    if hint == 2:
                        value = REF.decode_value(reader, bits, server_time=20000, frm=old.field[i])
                        result[i] = word(bits, value)
                self.assertEqual(result, list(new.field))
                self.assertEqual(reader.readcount, msg.size)

    def test_all_codecs_and_bit_pools(self):
        for bits, old, new in vectors():
            for pool in range(8):
                with self.subTest(bits=bits, old=old, new=new, pool=pool):
                    writer = REF.MsgWriter()
                    if pool:
                        writer.write_bits((1 << pool)-1, pool)
                        writer.write_byte(0xa5)
                    REF.encode_value(writer, bits, new, server_time=20000, frm=old)
                    ok, data, msg, _ = encode(bits, old, new, pool)
                    self.assertTrue(ok)
                    self.assertFalse(msg.failed)
                    self.assertEqual(data, writer.bytes())

    def test_capacity(self):
        for bits, old, new in vectors():
            _, data, _, _ = encode(bits, old, new, 3)
            for size in range(len(data)):
                self.assertFalse(encode(bits, old, new, 3, size)[0])

    def test_positions_and_invalid_values(self):
        for bits, value in ((-96, 2048), (-98, 0x40000000), (-65, 101), (-77, 256),
                            (-94, 256), (-85, 0x01000000), (4, 16), (-8, 128),
                            (-92, 50000.), (-100, float('nan'))):
            self.assertFalse(encode(bits, 0, value)[0])
        ctx = Context(20000, (C.c_int32*3)(100, 200, 300), 1, 0)
        ok, data, _, ctx = encode(-92, -50000., 50000., context=ctx)
        self.assertTrue(ok)
        self.assertEqual(ctx.clamped, 2)
        writer = REF.MsgWriter()
        writer.write_bit(1); writer.write_bits(65535, 16)
        self.assertEqual(data, writer.bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--reference', type=Path, required=True)
    args, rest = parser.parse_known_args()
    sys.path.insert(0, str(args.reference))
    import entity_codec as REF
    # Isolate the pure animcmd codec from bot AI and its gameplay dependencies.
    tree = ast.parse((args.reference/'bot_ai.py').read_text(encoding='utf-8-sig'))
    names = {'AnimCmd', 'enc_blend', 'enc_rate', 'enc_weight', 'enc_frac', 'enc_sub',
             'encode_animcmd', 'encode_animcmds'}
    ANIM = {'math': math, 'ANIM_REF_BITS': 11, 'ANIM_REF_MAX': 2048,
            'ANIM_REFENT_INIT': 0xffffffff, 'ANIM_REFTIME_INIT': -100003,
            'ANIM_TERMINAL_TYPES': (1, 2, 3, 4, 5, 6)}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                                 and n.name in names], type_ignores=[]), '<reference animcmd>', 'exec'), ANIM)
    with tempfile.TemporaryDirectory(prefix='codol-delta-') as folder:
        target = Path(folder) / ('delta.dll' if os.name == 'nt' else 'delta.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', '-O2', str(ROOT/'src/codol/net/codol_msg.c'),
                        str(ROOT/'src/codol/snapshot/codol_delta.c'), str(ROOT/'src/codol/snapshot/codol_playerstate.c'),
                        str(ROOT/'src/codol/snapshot/codol_player_arrays.c'),
                        str(ROOT/'src/codol/snapshot/codol_entities.c'),
                        str(ROOT/'src/codol/snapshot/codol_clients.c'),
                        str(ROOT/'src/codol/snapshot/codol_actors.c'),
                        str(ROOT/'src/codol/snapshot/codol_animcmd.c'),
                        str(ROOT/'src/codol/snapshot/codol_snapshot.c'),
                        str(ROOT/'src/codol/snapshot/codol_history.c'),
                        '-lm', '-o', str(target)], check=True)
        LIB = C.CDLL(str(target))
        LIB.CODOL_MsgWriteInit.argtypes = [C.POINTER(Msg), C.c_void_p, C.c_size_t]
        LIB.CODOL_WriteBits.argtypes = [C.POINTER(Msg), C.c_uint32, C.c_uint]
        LIB.CODOL_WriteAnimCommands.argtypes = [C.POINTER(Msg), C.POINTER(Anim), C.c_size_t, C.c_uint32]
        LIB.CODOL_WriteSnapshot.argtypes = [C.POINTER(Msg), C.POINTER(Snapshot), C.POINTER(Snapshot),
            C.c_void_p, C.POINTER(Anim), C.c_size_t, C.c_uint, C.c_int, C.POINTER(Context)]
        LIB.CODOL_CreateHistory.restype = C.c_void_p
        LIB.CODOL_DestroyHistory.argtypes = [C.c_void_p]
        LIB.CODOL_ClearHistory.argtypes = [C.c_void_p]
        LIB.CODOL_CommitHistory.argtypes = [C.c_void_p, C.POINTER(Snapshot)]
        LIB.CODOL_PrepareHistory.argtypes = [C.c_void_p, C.POINTER(Snapshot), C.c_uint32,
                                            C.c_int, C.POINTER(Context)]
        LIB.CODOL_FinishHistory.argtypes = [C.c_void_p, C.c_uint32, C.c_int]
        LIB.CODOL_CommitReachedHistory.argtypes = [C.c_void_p, C.POINTER(Snapshot), C.c_uint32,
                                                  C.c_int, C.POINTER(Context)]
        LIB.CODOL_FindHistoryBase.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32]
        LIB.CODOL_FindHistoryBase.restype = C.POINTER(Snapshot)
        LIB.CODOL_WriteByte.argtypes = [C.POINTER(Msg), C.c_uint32]
        LIB.CODOL_WriteDeltaValue.argtypes = [C.POINTER(Msg), C.c_int, C.c_uint32, C.c_uint32, C.POINTER(Context)]
        LIB.CODOL_ReachDeltaValue.argtypes = [C.c_int, C.c_uint32, C.c_uint32, C.POINTER(Context), C.POINTER(C.c_uint32)]
        LIB.CODOL_ReachPlayerFields.argtypes = [C.POINTER(PlayerFields), C.POINTER(PlayerFields),
                                              C.POINTER(PlayerFields), C.c_int, C.POINTER(Context)]
        LIB.CODOL_PlayerField.argtypes = [C.c_uint]
        LIB.CODOL_PlayerField.restype = C.POINTER(PlayerField)
        LIB.CODOL_EntityField.argtypes = [C.c_uint, C.c_uint]
        LIB.CODOL_EntityField.restype = C.POINTER(PlayerField)
        LIB.CODOL_ClientField.argtypes = [C.c_uint]
        LIB.CODOL_ClientField.restype = C.POINTER(PlayerField)
        LIB.CODOL_WriteActors.argtypes = [C.POINTER(Msg), C.POINTER(Actor), C.c_size_t,
                                        C.POINTER(Actor), C.c_size_t, C.POINTER(Context)]
        LIB.CODOL_WriteClients.argtypes = [C.POINTER(Msg), C.POINTER(Client), C.c_size_t,
                                         C.POINTER(Client), C.c_size_t, C.POINTER(Context)]
        LIB.CODOL_WriteEntities.argtypes = [C.POINTER(Msg), C.POINTER(Entity), C.c_size_t,
                                          C.POINTER(Entity), C.c_size_t, C.POINTER(Context)]
        LIB.CODOL_WritePlayerFields.argtypes = [C.POINTER(Msg), C.POINTER(PlayerFields),
                                               C.POINTER(PlayerFields), C.c_int, C.POINTER(Context)]
        run = unittest.main(argv=[__file__] + rest, exit=False)
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(LIB._handle)
    sys.exit(0 if run.result.wasSuccessful() else 1)

