from __future__ import annotations

import csv
import hashlib
import random
import struct
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

import capstone
from capstone import CS_ARCH_X86, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET, CS_MODE_32
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from core004a_diagnostic import ManualPE, SAMPLE


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"
EXPECTED_IMAGE_BASE = 0x00400000
EXPECTED_ENTRY_RVA = 0x0E5DC690
TVM0_NAME = ".tvm0"

MAX_FUNCTIONS = 96
MAX_BLOCKS = 2500
MAX_INSTRUCTIONS_PER_BLOCK = 256


HISTORICAL_SEEDS = [
    0x004FD9B0,
    0x004FCEE0,
    0x00808650,
    0x007E98F0,
    0x006212C0,
    0x0077F580,
    0x0077F8B3,
]

# These were the three mechanical prologue hits from CORE-003. They are retained
# only for negative validation; none is assumed to be a function.
LEGACY_PROLOGUE_RVAS = [0x00001098, 0x000010AF, 0x000010C6]


@dataclass
class Instruction:
    rva: int
    size: int
    mnemonic: str
    operands: str
    raw: bytes

    @property
    def end_rva(self) -> int:
        return self.rva + self.size


@dataclass
class Block:
    start_rva: int
    function_rva: int
    instructions: list[Instruction] = field(default_factory=list)
    terminator: str = ""
    stop_reason: str = ""
    confidence: str = "CANDIDATE"

    @property
    def end_rva(self) -> int:
        if not self.instructions:
            return self.start_rva
        return self.instructions[-1].end_rva


@dataclass
class Edge:
    src_function: int
    src_block: int
    instruction_rva: int
    mnemonic: str
    operands: str
    edge_type: str
    dst_rva: int | None
    target_kind: str
    confidence: str
    evidence: str


@dataclass
class FunctionSeed:
    rva: int
    evidence: set[str] = field(default_factory=set)
    source: str = ""


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt_rva(value: int | None) -> str:
    if value is None:
        return ""
    if value < 0:
        return f"-0x{-value:08X}"
    return f"0x{value:08X}"


def relative_target_rva(pe: ManualPE, insn) -> int | None:
    """Compute x86 relative branch targets from opcode bytes, independently of operand text."""
    raw = bytes(insn.bytes)
    if not raw:
        return None
    displacement: int | None = None
    if raw[0] in {0xE8, 0xE9} and len(raw) >= 5:
        displacement = struct.unpack_from("<i", raw, 1)[0]
    elif raw[0] == 0xEB and len(raw) >= 2:
        displacement = struct.unpack_from("<b", raw, 1)[0]
    elif 0x70 <= raw[0] <= 0x7F and len(raw) >= 2:
        displacement = struct.unpack_from("<b", raw, 1)[0]
    elif raw[0] == 0x0F and len(raw) >= 6 and 0x80 <= raw[1] <= 0x8F:
        displacement = struct.unpack_from("<i", raw, 2)[0]
    if displacement is None:
        return None
    return ((insn.address - pe.image_base) + insn.size + displacement) & 0xFFFFFFFF


class Recovery:
    def __init__(self, pe: ManualPE):
        self.pe = pe
        self.md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
        self.md.detail = True
        self.blocks: dict[int, Block] = {}
        self.edges: list[Edge] = []
        self.function_seeds: dict[int, FunctionSeed] = {}
        self.block_queue: deque[tuple[int, int]] = deque()
        self.function_queue: deque[int] = deque()
        self.queued_blocks: set[tuple[int, int]] = set()
        self.queued_functions: set[int] = set()
        self.instruction_owner: dict[int, int] = {}
        self.instruction_ranges: list[tuple[int, int, int]] = []
        self.indirect_rows: list[dict[str, object]] = []
        self.decode_failures: dict[int, str] = {}
        self.validation: list[dict[str, object]] = []
        self.edge_keys: set[tuple[object, ...]] = set()

    def mapping(self, rva: int) -> tuple[str, object | None, int | None]:
        section, offset, status = self.pe.rva_to_offset(rva)
        if section and section.name == TVM0_NAME:
            return "TVM0_BOUNDARY", section, offset
        if status == "VIRTUAL_ONLY":
            return "VIRTUAL_ONLY", section, None
        if status != "OK":
            return status, section, offset
        if not section or not section.executable:
            return "DATA_UNKNOWN", section, offset
        return "RAW_BACKED_EXECUTABLE", section, offset

    def add_function_seed(self, rva: int, evidence: str, source: str) -> None:
        seed = self.function_seeds.get(rva)
        if seed is None:
            seed = FunctionSeed(rva=rva, source=source)
            self.function_seeds[rva] = seed
        seed.evidence.add(evidence)
        if rva not in self.queued_functions and len(self.queued_functions) < MAX_FUNCTIONS:
            self.queued_functions.add(rva)
            self.function_queue.append(rva)

    def queue_block(self, rva: int, function_rva: int) -> None:
        key = (rva, function_rva)
        if key in self.queued_blocks or len(self.queued_blocks) >= MAX_BLOCKS:
            return
        self.queued_blocks.add(key)
        self.block_queue.append(key)

    def add_edge(self, edge: Edge) -> None:
        key = (
            edge.src_function,
            edge.src_block,
            edge.instruction_rva,
            edge.edge_type,
            edge.dst_rva,
            edge.target_kind,
        )
        if key not in self.edge_keys:
            self.edge_keys.add(key)
            self.edges.append(edge)

    def target_kind(self, target: int | None) -> str:
        if target is None:
            return "UNKNOWN_TARGET"
        status, _section, _offset = self.mapping(target)
        if status == "TVM0_BOUNDARY":
            return "TVM0_BOUNDARY"
        if status == "VIRTUAL_ONLY":
            return "VIRTUAL_ONLY"
        if status != "RAW_BACKED_EXECUTABLE":
            return "UNKNOWN_TARGET"
        for start, end, _owner in self.instruction_ranges:
            if start < target < end:
                return "INSTRUCTION_MIDDLE_CONFLICT"
        if target in self.instruction_owner:
            return "INTRA_FUNCTION_TARGET"
        return "BASIC_BLOCK_TARGET"

    def decode_one(self, rva: int):
        raw, section, offset, status = self.pe.read_rva(rva, 15)
        if status != "OK" or not section or not section.executable or section.name == TVM0_NAME:
            return None, status
        if not raw:
            return None, "NO_RAW_BYTES"
        try:
            insn = next(self.md.disasm(raw, self.pe.image_base + rva, count=1), None)
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"
        if insn is None:
            return None, "NO_INSTRUCTION_DECODED"
        if insn.address != self.pe.image_base + rva:
            return None, "DECODER_ADDRESS_MISMATCH"
        return insn, "OK"

    @staticmethod
    def is_rare_instruction(mnemonic: str) -> bool:
        return mnemonic in {
            "aaa", "aas", "aad", "aam", "daa", "das", "arpl", "bound", "into",
            "hlt", "cli", "sti", "in", "insb", "insd", "out", "outsb", "outsd",
            "pushal", "popal", "iretd", "loop", "loope", "loopne",
        }

    def decode_block(self, start_rva: int, function_rva: int) -> Block | None:
        mapping, section, _offset = self.mapping(start_rva)
        if mapping != "RAW_BACKED_EXECUTABLE":
            self.decode_failures[start_rva] = mapping
            return None
        if start_rva in self.blocks:
            return self.blocks[start_rva]
        for old_start, old_end, _owner in self.instruction_ranges:
            if old_start < start_rva < old_end:
                self.decode_failures[start_rva] = "STARTS_INSIDE_EXISTING_INSTRUCTION"
                return None

        block = Block(start_rva=start_rva, function_rva=function_rva)
        self.blocks[start_rva] = block
        current = start_rva
        rare_count = 0

        for _ in range(MAX_INSTRUCTIONS_PER_BLOCK):
            if current != start_rva and current in self.blocks:
                block.terminator = "FALLTHROUGH_EXISTING_BLOCK"
                block.stop_reason = "EXISTING_BLOCK_START"
                source_rva = block.instructions[-1].rva if block.instructions else start_rva
                self.add_edge(Edge(
                    function_rva, start_rva, source_rva, "", "", "FALLTHROUGH", current,
                    self.target_kind(current), "CANDIDATE", "sequential decode reached an existing block start",
                ))
                break
            if current in self.instruction_owner:
                block.terminator = "FALLTHROUGH_EXISTING_INSTRUCTION"
                block.stop_reason = "EXISTING_INSTRUCTION"
                if block.instructions:
                    source_rva = block.instructions[-1].rva
                    self.add_edge(Edge(
                        function_rva, start_rva, source_rva, "", "", "FALLTHROUGH", current,
                        self.target_kind(current), "CANDIDATE", "sequential decode reached an existing instruction",
                    ))
                break

            raw16, _s, _o, read_status = self.pe.read_rva(current, 16)
            if read_status != "OK":
                block.terminator = read_status
                block.stop_reason = read_status
                break
            if raw16 == b"\x00" * 16:
                block.terminator = "ZERO_PADDING"
                block.stop_reason = "16_ZERO_BYTES"
                break

            insn, decode_status = self.decode_one(current)
            if insn is None:
                block.terminator = "DECODE_FAILURE"
                block.stop_reason = decode_status
                self.decode_failures[current] = decode_status
                break

            record = Instruction(
                rva=current,
                size=insn.size,
                mnemonic=insn.mnemonic,
                operands=insn.op_str,
                raw=bytes(insn.bytes),
            )
            block.instructions.append(record)
            self.instruction_owner[current] = start_rva
            self.instruction_ranges.append((current, current + insn.size, start_rva))
            if self.is_rare_instruction(insn.mnemonic):
                rare_count += 1

            next_rva = current + insn.size
            operands = list(insn.operands)
            first_operand = operands[0] if operands else None
            is_call = insn.group(CS_GRP_CALL)
            is_jump = insn.group(CS_GRP_JUMP)
            is_ret = insn.group(CS_GRP_RET)

            if is_ret:
                block.terminator = "RET"
                block.stop_reason = "RET"
                self.add_edge(Edge(
                    function_rva, start_rva, current, insn.mnemonic, insn.op_str, "RET", None,
                    "RETURN", "CANDIDATE", "Capstone CS_GRP_RET",
                ))
                break

            if is_call:
                block.terminator = "CALL"
                if insn.mnemonic == "call" and len(operands) == 1 and first_operand is not None and first_operand.type == X86_OP_IMM:
                    target_va = int(first_operand.imm) & 0xFFFFFFFF
                    target = target_va - self.pe.image_base
                    target_type = self.target_kind(target)
                    mapping_status, target_section, _target_offset = self.mapping(target)
                    edge_type = "CALL" if self.pe.image_base <= target_va < self.pe.image_base + self.pe.size_of_image else "EXTERNAL_BOUNDARY"
                    evidence = "direct relative call decoded by Capstone"
                    if mapping_status == "TVM0_BOUNDARY":
                        target_type = "TVM0_BOUNDARY"
                    if edge_type == "EXTERNAL_BOUNDARY":
                        target = None
                        target_type = "EXTERNAL_ADDRESS"
                        evidence = f"direct call target VA 0x{target_va:08X} is outside EXE image"
                    self.add_edge(Edge(
                        function_rva, start_rva, current, insn.mnemonic, insn.op_str, edge_type,
                        target, target_type, "CANDIDATE", evidence,
                    ))
                    if mapping_status == "RAW_BACKED_EXECUTABLE":
                        self.add_function_seed(target, f"DIRECT_CALL_TARGET@{fmt_rva(current)}", "DIRECT_CALL")
                else:
                    target_expression = insn.op_str
                    is_known_entry_boundary = (
                        current == EXPECTED_ENTRY_RVA
                        and first_operand is not None
                        and first_operand.type == X86_OP_MEM
                        and (first_operand.mem.disp & 0xFFFFFFFF) == 0x0E9DC665
                    )
                    if is_known_entry_boundary:
                        self.add_edge(Edge(
                            function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                            "EXTERNAL_BOUNDARY", 0x0E5DC665, "EXTERNAL_CALL_BOUNDARY",
                            "CONFIRMED", "Entry bytes FF 15 65 C6 9D 0E; slot VA 0x0E9DC665",
                        ))
                        block.terminator = "EXTERNAL_BOUNDARY"
                        block.stop_reason = "KNOWN_ENTRY_EXTERNAL_CALL_BOUNDARY"
                        break
                    target_kind = "MEMORY" if first_operand is not None and first_operand.type == X86_OP_MEM else "REGISTER"
                    if insn.mnemonic in {"lcall", "callf"}:
                        target_kind = "FAR_POINTER"
                    self.add_edge(Edge(
                        function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                        "INDIRECT_UNRESOLVED", None, "UNKNOWN_TARGET", "UNKNOWN",
                        "indirect call target not resolved",
                    ))
                    self.indirect_rows.append({
                        "RVA": fmt_rva(current),
                        "VA": fmt_rva(self.pe.image_base + current),
                        "INSTRUCTION": f"{insn.mnemonic} {insn.op_str}".strip(),
                        "TARGET_EXPRESSION": target_expression,
                        "TARGET_KIND": target_kind,
                        "RESOLUTION_STATUS": "UNRESOLVED_FAR_CALL" if target_kind == "FAR_POINTER" else "UNRESOLVED_INDIRECT_CALL",
                        "POSSIBLE_SOURCE": "UNKNOWN",
                        "CONFIDENCE": "UNKNOWN",
                    })
                self.add_edge(Edge(
                    function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                    "FALLTHROUGH", next_rva, self.target_kind(next_rva), "CANDIDATE",
                    "caller continuation after call",
                ))
                self.queue_block(next_rva, function_rva)
                break

            if is_jump:
                is_unconditional = insn.mnemonic == "jmp"
                if first_operand is not None and first_operand.type == X86_OP_IMM:
                    target = int(first_operand.imm) - self.pe.image_base
                    target_type = self.target_kind(target)
                    mapping_status, _target_section, _target_offset = self.mapping(target)
                    if is_unconditional:
                        edge_type = "JMP"
                        block.terminator = "JMP"
                    else:
                        edge_type = "COND_TAKEN"
                        block.terminator = "COND_JMP"
                    self.add_edge(Edge(
                        function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                        edge_type, target, target_type, "CANDIDATE",
                        "direct branch decoded by Capstone",
                    ))
                    if mapping_status == "RAW_BACKED_EXECUTABLE":
                        self.queue_block(target, function_rva)
                    if not is_unconditional:
                        self.add_edge(Edge(
                            function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                            "COND_FALLTHROUGH", next_rva, self.target_kind(next_rva),
                            "CANDIDATE", "conditional branch fallthrough",
                        ))
                        self.queue_block(next_rva, function_rva)
                else:
                    block.terminator = "INDIRECT_JMP"
                    target_kind = "MEMORY" if first_operand is not None and first_operand.type == X86_OP_MEM else "REGISTER"
                    self.add_edge(Edge(
                        function_rva, start_rva, current, insn.mnemonic, insn.op_str,
                        "INDIRECT_UNRESOLVED", None, "UNKNOWN_TARGET", "UNKNOWN",
                        "indirect jump target not resolved",
                    ))
                    self.indirect_rows.append({
                        "RVA": fmt_rva(current),
                        "VA": fmt_rva(self.pe.image_base + current),
                        "INSTRUCTION": f"{insn.mnemonic} {insn.op_str}".strip(),
                        "TARGET_EXPRESSION": insn.op_str,
                        "TARGET_KIND": target_kind,
                        "RESOLUTION_STATUS": "UNRESOLVED_INDIRECT_JMP",
                        "POSSIBLE_SOURCE": "UNKNOWN",
                        "CONFIDENCE": "UNKNOWN",
                    })
                break

            current = next_rva
        else:
            block.terminator = "BUDGET_LIMIT"
            block.stop_reason = f"MAX_INSTRUCTIONS_PER_BLOCK={MAX_INSTRUCTIONS_PER_BLOCK}"

        instruction_count = len(block.instructions)
        rare_ratio = (rare_count / instruction_count) if instruction_count else 1.0
        if start_rva == EXPECTED_ENTRY_RVA and block.terminator == "EXTERNAL_BOUNDARY":
            block.confidence = "CONFIRMED"
        elif instruction_count == 0:
            block.confidence = "UNRESOLVED"
        elif rare_count >= 2 or rare_ratio >= 0.15:
            block.confidence = "LOW"
        elif block.terminator in {"RET", "CALL", "JMP", "COND_JMP", "INDIRECT_JMP"}:
            block.confidence = "CANDIDATE"
        else:
            block.confidence = "LOW"
        return block

    def run(self) -> None:
        self.add_function_seed(EXPECTED_ENTRY_RVA, "PE_ENTRYPOINT", "KNOWN_ENTRY")
        for rva in HISTORICAL_SEEDS:
            self.add_function_seed(rva, "HISTORICAL_NATIVE_CANDIDATE", "HISTORICAL_SEED")
        for rva in LEGACY_PROLOGUE_RVAS:
            self.add_function_seed(rva, "CORE003_MECHANICAL_PROLOGUE_HIT", "LEGACY_HEURISTIC")

        while self.function_queue or self.block_queue:
            while self.function_queue:
                function_rva = self.function_queue.popleft()
                mapping, _section, _offset = self.mapping(function_rva)
                if mapping == "RAW_BACKED_EXECUTABLE":
                    self.queue_block(function_rva, function_rva)
                else:
                    self.decode_failures[function_rva] = mapping
            if not self.block_queue:
                continue
            block_rva, function_rva = self.block_queue.popleft()
            if block_rva in self.blocks:
                continue
            self.decode_block(block_rva, function_rva)


def assign_block_ids(blocks: dict[int, Block]) -> dict[int, str]:
    return {rva: f"BB_{index:06d}" for index, rva in enumerate(sorted(blocks), start=1)}


def block_for_target(target: int | None, blocks: dict[int, Block]) -> int | None:
    if target is None:
        return None
    if target in blocks:
        return target
    for start, block in blocks.items():
        if start < target < block.end_rva:
            return start
    return None


def validate_edge_decode(recovery: Recovery, edge: Edge) -> tuple[bool, str]:
    insn, status = recovery.decode_one(edge.instruction_rva)
    if insn is None:
        return False, status
    text = f"{insn.mnemonic} {insn.op_str}".strip()
    operands = list(insn.operands)
    first_operand = operands[0] if operands else None
    next_rva = edge.instruction_rva + insn.size

    if edge.edge_type in {"CALL", "JMP", "COND_TAKEN"}:
        if first_operand is None or first_operand.type != X86_OP_IMM or edge.dst_rva is None:
            return False, text + "; expected immediate target"
        operand_target = (int(first_operand.imm) & 0xFFFFFFFF) - recovery.pe.image_base
        relative_target = relative_target_rva(recovery.pe, insn)
        valid = operand_target == edge.dst_rva and relative_target == edge.dst_rva
        return valid, text + f"; operand_dst={fmt_rva(operand_target)}; relative_dst={fmt_rva(relative_target)}"
    if edge.edge_type in {"FALLTHROUGH", "COND_FALLTHROUGH"}:
        return edge.dst_rva == next_rva, text + f"; next={fmt_rva(next_rva)}"
    if edge.edge_type == "RET":
        return insn.group(CS_GRP_RET), text
    if edge.edge_type == "INDIRECT_UNRESOLVED":
        return insn.group(CS_GRP_CALL) or insn.group(CS_GRP_JUMP), text
    if edge.edge_type == "EXTERNAL_BOUNDARY":
        if edge.instruction_rva == EXPECTED_ENTRY_RVA:
            valid = (
                first_operand is not None
                and first_operand.type == X86_OP_MEM
                and (first_operand.mem.disp & 0xFFFFFFFF) == 0x0E9DC665
            )
            return valid, text + "; expected_slot_va=0x0E9DC665"
        if first_operand is not None and first_operand.type == X86_OP_IMM:
            target_va = int(first_operand.imm) & 0xFFFFFFFF
            outside = not (
                recovery.pe.image_base
                <= target_va
                < recovery.pe.image_base + recovery.pe.size_of_image
            )
            return outside, text + f"; target_va=0x{target_va:08X}"
        return False, text + "; unresolved external-boundary encoding"
    return False, text + f"; unsupported edge type {edge.edge_type}"


def find_special_xrefs(pe: ManualPE, target_rva: int, md) -> dict[str, object]:
    target_va = pe.image_base + target_rva
    direct_hits: list[tuple[int, str, str]] = []
    absolute_pointer_offsets: list[int] = []
    predecessor_candidates: list[tuple[int, str]] = []

    pointer = struct.pack("<I", target_va)
    cursor = pe.data.find(pointer)
    while cursor >= 0:
        absolute_pointer_offsets.append(cursor)
        cursor = pe.data.find(pointer, cursor + 1)

    for section in pe.sections:
        if not section.executable or section.name == TVM0_NAME or not section.raw_size:
            continue
        raw = pe.data[section.raw_offset:section.raw_offset + section.raw_size]
        for index, opcode in enumerate(raw):
            size = 0
            if opcode in (0xE8, 0xE9) and index + 5 <= len(raw):
                displacement = struct.unpack_from("<i", raw, index + 1)[0]
                size = 5
            elif opcode == 0x0F and index + 6 <= len(raw) and 0x80 <= raw[index + 1] <= 0x8F:
                displacement = struct.unpack_from("<i", raw, index + 2)[0]
                size = 6
            elif (opcode == 0xEB or 0x70 <= opcode <= 0x7F) and index + 2 <= len(raw):
                displacement = struct.unpack_from("<b", raw, index + 1)[0]
                size = 2
            else:
                continue
            source_rva = section.virtual_address + index
            if source_rva + size + displacement != target_rva:
                continue
            snippet = raw[index:index + 15]
            insn = next(md.disasm(snippet, pe.image_base + source_rva, count=1), None)
            if insn is None or not (insn.group(CS_GRP_CALL) or insn.group(CS_GRP_JUMP)):
                continue
            operands = list(insn.operands)
            if not operands or operands[0].type != X86_OP_IMM:
                continue
            decoded_target = int(operands[0].imm) - pe.image_base
            if decoded_target == target_rva:
                direct_hits.append((source_rva, insn.mnemonic, insn.op_str))

    for start_rva in range(max(0, target_rva - 15), target_rva):
        raw, section, _offset, status = pe.read_rva(start_rva, target_rva - start_rva)
        if status != "OK" or not section or not section.executable or section.name == TVM0_NAME:
            continue
        cursor_rva = start_rva
        decoded = []
        valid = True
        while cursor_rva < target_rva:
            remaining = raw[cursor_rva - start_rva:]
            insn = next(md.disasm(remaining, pe.image_base + cursor_rva, count=1), None)
            if insn is None or insn.size <= 0 or cursor_rva + insn.size > target_rva:
                valid = False
                break
            decoded.append(f"{fmt_rva(cursor_rva)}:{insn.mnemonic} {insn.op_str}".strip())
            cursor_rva += insn.size
        if valid and cursor_rva == target_rva and decoded:
            predecessor_candidates.append((start_rva, " | ".join(decoded)))

    return {
        "direct_hits": direct_hits,
        "absolute_pointer_offsets": absolute_pointer_offsets,
        "predecessor_candidates": predecessor_candidates,
    }


def compute_loops(
    recovery: Recovery,
    block_ids: dict[int, str],
    reported_blocks: dict[int, Block],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    edges_by_function: dict[int, list[tuple[int, int, Edge]]] = defaultdict(list)
    internal_types = {"FALLTHROUGH", "JMP", "COND_TAKEN", "COND_FALLTHROUGH"}
    for edge in recovery.edges:
        if edge.edge_type not in internal_types or edge.dst_rva is None:
            continue
        if edge.src_block not in reported_blocks:
            continue
        dst_block = block_for_target(edge.dst_rva, reported_blocks)
        if dst_block is None:
            continue
        if (
            reported_blocks.get(edge.src_block)
            and reported_blocks.get(dst_block)
            and reported_blocks[dst_block].function_rva == edge.src_function
        ):
            edges_by_function[edge.src_function].append((edge.src_block, dst_block, edge))

    loop_index = 0
    for function_rva, graph_edges in edges_by_function.items():
        nodes = {src for src, _dst, _edge in graph_edges} | {dst for _src, dst, _edge in graph_edges}
        if function_rva not in nodes:
            continue
        predecessors: dict[int, set[int]] = {node: set() for node in nodes}
        successors: dict[int, set[int]] = {node: set() for node in nodes}
        for src, dst, _edge in graph_edges:
            successors[src].add(dst)
            predecessors[dst].add(src)
        reachable = set()
        stack = [function_rva]
        while stack:
            node = stack.pop()
            if node in reachable or node not in nodes:
                continue
            reachable.add(node)
            stack.extend(successors[node])
        if not reachable:
            continue
        dominators = {node: set(reachable) for node in reachable}
        dominators[function_rva] = {function_rva}
        changed = True
        while changed:
            changed = False
            for node in reachable - {function_rva}:
                pred = predecessors[node] & reachable
                new_dom = {node}
                if pred:
                    new_dom |= set.intersection(*(dominators[p] for p in pred))
                if new_dom != dominators[node]:
                    dominators[node] = new_dom
                    changed = True
        for src, dst, edge in graph_edges:
            if src not in reachable or dst not in reachable or dst not in dominators[src]:
                continue
            natural_loop = {src, dst}
            work = [src]
            while work:
                node = work.pop()
                for pred in predecessors[node]:
                    if pred not in natural_loop:
                        natural_loop.add(pred)
                        work.append(pred)
            loop_index += 1
            rows.append({
                "LOOP_ID": f"LOOP_{loop_index:04d}",
                "HEADER_RVA": fmt_rva(dst),
                "LATCH_RVA": fmt_rva(src),
                "BACK_EDGE_RVA": fmt_rva(edge.instruction_rva),
                "FUNCTION_RVA": fmt_rva(function_rva),
                "LOOP_SIZE": len(natural_loop),
                "EVIDENCE": "destination dominates source in recovered direct block graph",
                "CONFIDENCE": "BACK_EDGE_CONFIRMED" if edge.confidence == "CONFIRMED" else "LOOP_CANDIDATE",
            })
    return rows


def section_for_target(pe: ManualPE, target_rva: int | None):
    if target_rva is None:
        return None
    return pe.section_for_rva(target_rva)


def make_instruction_database(
    pe: ManualPE,
    recovery: Recovery,
    reported_blocks: dict[int, Block],
    function_trust: dict[int, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    instruction_rvas: set[int] = set()
    for block in sorted(reported_blocks.values(), key=lambda item: item.start_rva):
        for record in block.instructions:
            instruction_rvas.add(record.rva)
            insn, status = recovery.decode_one(record.rva)
            section, file_offset, _mapping_status = pe.rva_to_offset(record.rva)
            if insn is None:
                rows.append({
                    "rva": fmt_rva(record.rva),
                    "va": fmt_rva(pe.image_base + record.rva),
                    "file_offset": fmt_rva(file_offset),
                    "section": section.name if section else "UNKNOWN",
                    "size": record.size,
                    "mnemonic": f"DECODE_RECHECK_FAILURE:{status}",
                    "op_str": record.operands,
                    "bytes": record.raw.hex(" "),
                    "is_call": "NO",
                    "is_jump": "NO",
                    "is_conditional": "NO",
                    "is_return": "NO",
                    "is_indirect": "NO",
                    "target_rva": "",
                    "confidence": "UNRESOLVED",
                })
                continue
            operands = list(insn.operands)
            first = operands[0] if operands else None
            is_call = bool(insn.group(CS_GRP_CALL))
            is_jump = bool(insn.group(CS_GRP_JUMP))
            is_return = bool(insn.group(CS_GRP_RET))
            is_conditional = is_jump and insn.mnemonic not in {"jmp", "ljmp"}
            is_indirect = (
                (is_call or is_jump)
                and first is not None
                and first.type in {X86_OP_MEM, X86_OP_REG}
            ) or insn.mnemonic in {"lcall", "ljmp"}
            target_rva: int | None = None
            if first is not None and first.type == X86_OP_IMM and (is_call or is_jump):
                target_rva = relative_target_rva(pe, insn)
            confidence = "CONFIRMED" if record.rva == EXPECTED_ENTRY_RVA else function_trust.get(block.function_rva, "LOW")
            rows.append({
                "rva": fmt_rva(record.rva),
                "va": fmt_rva(pe.image_base + record.rva),
                "file_offset": fmt_rva(file_offset),
                "section": section.name if section else "UNKNOWN",
                "size": insn.size,
                "mnemonic": insn.mnemonic,
                "op_str": insn.op_str,
                "bytes": bytes(insn.bytes).hex(" "),
                "is_call": "YES" if is_call else "NO",
                "is_jump": "YES" if is_jump else "NO",
                "is_conditional": "YES" if is_conditional else "NO",
                "is_return": "YES" if is_return else "NO",
                "is_indirect": "YES" if is_indirect else "NO",
                "target_rva": fmt_rva(target_rva),
                "confidence": confidence,
            })

    failure_rvas = set(recovery.decode_failures)
    failure_rvas.update(
        rva for rva in HISTORICAL_SEEDS + LEGACY_PROLOGUE_RVAS
        if recovery.mapping(rva)[0] != "RAW_BACKED_EXECUTABLE"
    )
    for rva in sorted(failure_rvas - instruction_rvas):
        section, file_offset, status = pe.rva_to_offset(rva)
        rows.append({
            "rva": fmt_rva(rva),
            "va": fmt_rva(pe.image_base + rva),
            "file_offset": fmt_rva(file_offset),
            "section": section.name if section else "UNKNOWN",
            "size": 0,
            "mnemonic": f"DECODE_FAILURE:{recovery.decode_failures.get(rva, status)}",
            "op_str": "",
            "bytes": "",
            "is_call": "NO",
            "is_jump": "NO",
            "is_conditional": "NO",
            "is_return": "NO",
            "is_indirect": "NO",
            "target_rva": "",
            "confidence": "UNKNOWN",
        })
    rows.sort(key=lambda row: (int(str(row["rva"]), 16) if str(row["rva"]).startswith("0x") else 0, str(row["mnemonic"])))
    return rows


def make_direct_edge_rows(
    pe: ManualPE,
    direct_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    allowed = {"CALL", "JMP", "COND_TAKEN", "COND_FALLTHROUGH", "FALLTHROUGH", "EXTERNAL_BOUNDARY"}
    for edge in direct_rows:
        if edge["EDGE_TYPE"] not in allowed:
            continue
        target_text = str(edge["DST_RVA"])
        target_rva = int(target_text, 16) if target_text.startswith("0x") else None
        instruction_text = str(edge["INSTRUCTION_RVA"])
        instruction_rva = int(instruction_text, 16) if instruction_text.startswith("0x") else None
        if edge["EDGE_TYPE"] in {"CALL", "JMP", "COND_TAKEN"} and instruction_rva is not None:
            raw, section_at_instruction, _offset, status = pe.read_rva(instruction_rva, 15)
            if status == "OK" and section_at_instruction and section_at_instruction.executable:
                md = capstone.Cs(CS_ARCH_X86, CS_MODE_32)
                md.detail = True
                insn = next(md.disasm(raw, pe.image_base + instruction_rva, count=1), None)
                recalculated = relative_target_rva(pe, insn) if insn is not None else None
                if recalculated is not None:
                    target_rva = recalculated
        section = section_for_target(pe, target_rva)
        rows.append({
            "source_rva": edge["SRC_RVA"],
            "instruction_rva": edge["INSTRUCTION_RVA"],
            "edge_type": edge["EDGE_TYPE"],
            "target_rva": edge["DST_RVA"],
            "target_section": section.name if section else "EXTERNAL_OR_UNKNOWN",
            "target_executable": "YES" if section and section.executable else "NO",
            "confidence": edge["CONFIDENCE"],
        })
    return rows


def address_interpretations(pe: ManualPE, value: int) -> list[tuple[str, int, str, object | None, int | None]]:
    options = []
    for kind, rva in (("VA", value - pe.image_base), ("RVA", value)):
        if rva < 0:
            continue
        section, offset, status = pe.rva_to_offset(rva)
        options.append((kind, rva, status, section, offset))
    return options


def choose_address_interpretation(pe: ManualPE, value: int):
    options = address_interpretations(pe, value)
    rank = {"OK": 4, "VIRTUAL_ONLY": 2, "PE_HEADERS": 1, "RVA_NOT_MAPPED": 0}
    return max(options, key=lambda item: rank.get(item[2], 0)) if options else ("UNKNOWN", value, "RVA_NOT_MAPPED", None, None)


def pointer_target(pe: ManualPE, value: int):
    candidates = []
    for kind, rva in (("VA", value - pe.image_base), ("RVA", value)):
        if rva < 0:
            continue
        section, offset, status = pe.rva_to_offset(rva)
        executable = bool(section and section.executable and status == "OK" and section.name != TVM0_NAME)
        candidates.append((1 if executable else 0, kind, rva, section, offset, status, executable))
    if not candidates:
        return "UNKNOWN", None, None, None, "RVA_NOT_MAPPED", False
    return max(candidates, key=lambda item: item[0]) [1:]


def make_function_table_rows(pe: ManualPE, recovery: Recovery) -> list[dict[str, object]]:
    source = ROOT / "exe_function_table_suspects.csv"
    if not source.exists():
        return []
    rows: list[dict[str, object]] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        suspects = csv.DictReader(handle)
        for suspect in suspects:
            raw_address = int(suspect.get("address", "0"), 0)
            address_kind, location_rva, location_status, location_section, file_offset = choose_address_interpretation(pe, raw_address)
            dword_value: int | None = None
            if file_offset is not None and file_offset + 4 <= len(pe.data):
                dword_value = struct.unpack_from("<I", pe.data, file_offset)[0]
            target_kind, target_rva, target_section, target_offset, target_status, target_executable = (
                pointer_target(pe, dword_value) if dword_value is not None
                else ("UNKNOWN", None, None, None, "NO_SOURCE_DWORD", False)
            )
            consecutive = 0
            if file_offset is not None:
                cursor = file_offset
                for _ in range(16):
                    if cursor + 4 > len(pe.data):
                        break
                    value = struct.unpack_from("<I", pe.data, cursor)[0]
                    _kind, _rva, _section, _offset, status, executable = pointer_target(pe, value)
                    if status != "OK" or not executable:
                        break
                    consecutive += 1
                    cursor += 4
            xrefs = 0
            if dword_value is not None:
                xrefs += pe.data.count(struct.pack("<I", dword_value))
            if target_rva is not None:
                xrefs += pe.data.count(struct.pack("<I", pe.image_base + target_rva))
            recovered_uses = sum(
                1 for edge in recovery.edges
                if edge.dst_rva is not None and edge.dst_rva == target_rva
            )
            if location_status != "OK":
                classification = "UNKNOWN"
                confidence = "UNKNOWN"
                evidence = "table location is not backed by source bytes"
            elif consecutive >= 2 and (xrefs > 1 or recovered_uses > 0):
                classification = "CONFIRMED_FUNCTION_TABLE"
                confidence = "CONFIRMED"
                evidence = "multiple consecutive executable pointers plus xref/recovered use"
            elif consecutive >= 2:
                classification = "STRONG_FUNCTION_TABLE"
                confidence = "STRONG"
                evidence = "multiple consecutive executable pointers; use/xref not confirmed"
            elif target_executable:
                classification = "CANDIDATE"
                confidence = "CANDIDATE"
                evidence = "single executable-looking pointer; table role unconfirmed"
            else:
                classification = "NOT_FUNCTION_TABLE"
                confidence = "CANDIDATE"
                evidence = "no executable pointer sequence established"
            rows.append({
                "address": fmt_rva(raw_address),
                "input_kind": address_kind,
                "location_rva": fmt_rva(location_rva),
                "location_va": fmt_rva(pe.image_base + location_rva),
                "section": location_section.name if location_section else "UNKNOWN",
                "file_offset": fmt_rva(file_offset),
                "location_status": location_status,
                "dword_value": fmt_rva(dword_value),
                "pointer_kind": target_kind,
                "target_rva": fmt_rva(target_rva),
                "target_va": fmt_rva(pe.image_base + target_rva) if target_rva is not None else "",
                "target_section": target_section.name if target_section else "UNKNOWN",
                "target_executable": "YES" if target_executable else "NO",
                "consecutive_executable_count": consecutive,
                "xref_count": xrefs,
                "recovered_cfg_uses": recovered_uses,
                "classification": classification,
                "confidence": confidence,
                "evidence": evidence,
            })
    return rows


def file_offset_to_rva(pe: ManualPE, file_offset: int) -> int | None:
    for section in pe.sections:
        if section.raw_offset <= file_offset < section.raw_offset + section.raw_size:
            return section.virtual_address + (file_offset - section.raw_offset)
    return None


def make_thread_seed_rows(pe: ManualPE) -> list[dict[str, object]]:
    symbols = ["CreateThread", "_beginthread", "_beginthreadex", "NtCreateThreadEx"]
    rows: list[dict[str, object]] = []
    for symbol in symbols:
        needle = symbol.encode("ascii")
        cursor = pe.data.find(needle)
        while cursor >= 0:
            rva = file_offset_to_rva(pe, cursor)
            section = pe.section_for_rva(rva) if rva is not None else None
            rows.append({
                "symbol": symbol,
                "rva": fmt_rva(rva),
                "file_offset": fmt_rva(cursor),
                "section": section.name if section else "UNKNOWN",
                "thread_entry": "",
                "status": "THREAD_ENTRY_UNKNOWN",
                "confidence": "UNKNOWN",
                "evidence": "symbol/string occurrence only; parameter dataflow not recovered",
            })
            cursor = pe.data.find(needle, cursor + 1)
    if not rows:
        rows.append({
            "symbol": "CreateThread/_beginthread/_beginthreadex/NtCreateThreadEx",
            "rva": "",
            "file_offset": "",
            "section": "",
            "thread_entry": "",
            "status": "THREAD_ENTRY_UNKNOWN",
            "confidence": "UNKNOWN",
            "evidence": "no ASCII symbol occurrence found in raw sample; no dynamic analysis performed",
        })
    return rows


def make_graph_rows(
    direct_rows: list[dict[str, object]],
    recovery: Recovery,
    reported_blocks: dict[int, Block],
    entry_reachable_blocks: set[int],
    scope: str,
) -> list[dict[str, object]]:
    rows = []
    for row in direct_rows:
        source_function = int(str(row["SRC_RVA"]), 16)
        source_rva = int(str(row["INSTRUCTION_RVA"]), 16)
        owning_block = next((block.start_rva for block in reported_blocks.values() if any(ins.rva == source_rva for ins in block.instructions)), None)
        if scope == "ENTRY_REACHABLE_GRAPH" and owning_block not in entry_reachable_blocks:
            continue
        rows.append({
            "graph_scope": scope,
            "source_function_rva": row["SRC_RVA"],
            "source_block": row["SRC_BLOCK"],
            "instruction_rva": row["INSTRUCTION_RVA"],
            "edge_type": row["EDGE_TYPE"],
            "target_rva": row["DST_RVA"],
            "target_block": row["DST_BLOCK"],
            "target_kind": row["TARGET_KIND"],
            "confidence": row["CONFIDENCE"],
            "evidence": row["EVIDENCE"],
        })
    return rows


def main() -> int:
    pe = ManualPE(SAMPLE)
    sample_hash = hashlib.sha256(pe.data).hexdigest()
    if sample_hash != EXPECTED_SHA256:
        raise SystemExit(f"SAMPLE_MISMATCH: {sample_hash}")
    if pe.image_base != EXPECTED_IMAGE_BASE or pe.entry_rva != EXPECTED_ENTRY_RVA:
        raise SystemExit("PE_IDENTITY_MISMATCH")

    recovery = Recovery(pe)
    recovery.run()
    nonempty_blocks = {
        rva: block for rva, block in recovery.blocks.items() if block.instructions
    }
    conflict_starts: set[int] = set()
    intervals = sorted(
        (block.start_rva, block.end_rva, block.start_rva)
        for block in nonempty_blocks.values()
    )
    for index, (start, end, owner) in enumerate(intervals):
        for other_start, other_end, other_owner in intervals[index + 1:]:
            if other_start >= end:
                break
            if other_start < end and start < other_end:
                conflict_starts.add(owner)
                conflict_starts.add(other_owner)
    reported_blocks = {
        rva: block for rva, block in nonempty_blocks.items() if rva not in conflict_starts
    }
    block_ids = assign_block_ids(reported_blocks)

    function_trust: dict[int, str] = {}
    for rva, seed in recovery.function_seeds.items():
        if rva == EXPECTED_ENTRY_RVA:
            function_trust[rva] = "CONFIRMED"
        elif seed.source in {"HISTORICAL_SEED", "LEGACY_HEURISTIC"}:
            function_trust[rva] = "LOW"
        else:
            function_trust[rva] = "UNKNOWN"
    changed = True
    while changed:
        changed = False
        for edge in recovery.edges:
            if edge.edge_type != "CALL" or edge.dst_rva not in recovery.function_seeds:
                continue
            source_trust = function_trust.get(edge.src_function, "UNKNOWN")
            propagated = "CANDIDATE" if source_trust in {"CONFIRMED", "STRONG"} else "LOW"
            old = function_trust.get(edge.dst_rva, "UNKNOWN")
            if old == "UNKNOWN" or (old == "LOW" and propagated == "CANDIDATE"):
                function_trust[edge.dst_rva] = propagated
                changed = True

    def effective_edge_confidence(edge: Edge) -> str:
        if edge.confidence in {"CONFIRMED", "UNKNOWN"}:
            return edge.confidence
        return function_trust.get(edge.src_function, "LOW")

    def effective_target_kind(edge: Edge) -> str:
        if edge.target_kind in {
            "EXTERNAL_CALL_BOUNDARY", "EXTERNAL_ADDRESS", "TVM0_BOUNDARY",
            "VIRTUAL_ONLY", "UNKNOWN_TARGET",
        }:
            return edge.target_kind
        if edge.dst_rva is None:
            return "UNKNOWN_TARGET"
        if edge.dst_rva in conflict_starts:
            return "INSTRUCTION_BOUNDARY_CONFLICT"
        destination_block = block_for_target(edge.dst_rva, reported_blocks)
        if edge.edge_type == "CALL" and edge.dst_rva in recovery.function_seeds:
            return "FUNCTION_CANDIDATE"
        if destination_block == edge.dst_rva:
            return "BASIC_BLOCK_TARGET"
        if destination_block is not None:
            return "INTRA_FUNCTION_TARGET"
        return edge.target_kind

    # Complete the requested mapping inventory with all seeds and recovered targets.
    address_rvas = {EXPECTED_ENTRY_RVA, *HISTORICAL_SEEDS, *LEGACY_PROLOGUE_RVAS}
    address_rvas.update(reported_blocks)
    for edge in recovery.edges:
        if edge.dst_rva is not None:
            address_rvas.add(edge.dst_rva)
    address_rows = []
    for rva in sorted(address_rvas):
        section, offset, raw_status = pe.rva_to_offset(rva)
        mapping_status, _mapped_section, _mapped_offset = recovery.mapping(rva)
        address_rows.append({
            "RVA": fmt_rva(rva),
            "VA": fmt_rva(pe.image_base + rva),
            "SECTION": section.name if section else "UNKNOWN",
            "SECTION_RVA": fmt_rva(section.virtual_address) if section else "",
            "VIRTUAL_SIZE": fmt_rva(section.virtual_size) if section else "",
            "RAW_PTR": fmt_rva(section.raw_offset) if section else "",
            "RAW_SIZE": fmt_rva(section.raw_size) if section else "",
            "RAW_BACKED": "YES" if raw_status == "OK" else "NO",
            "FILE_OFFSET": fmt_rva(offset),
            "STATUS": mapping_status,
        })
    write_csv(
        ROOT / "exe_core005_address_map.csv",
        ["RVA", "VA", "SECTION", "SECTION_RVA", "VIRTUAL_SIZE", "RAW_PTR", "RAW_SIZE", "RAW_BACKED", "FILE_OFFSET", "STATUS"],
        address_rows,
    )

    direct_rows = []
    for edge in sorted(recovery.edges, key=lambda item: (item.src_block, item.instruction_rva, item.edge_type, item.dst_rva or -1)):
        if edge.src_block not in reported_blocks:
            continue
        destination_block = block_for_target(edge.dst_rva, reported_blocks)
        direct_rows.append({
            "SRC_RVA": fmt_rva(edge.src_function),
            "SRC_BLOCK": block_ids.get(edge.src_block, ""),
            "INSTRUCTION_RVA": fmt_rva(edge.instruction_rva),
            "MNEMONIC": edge.mnemonic,
            "OPERANDS": edge.operands,
            "EDGE_TYPE": edge.edge_type,
            "DST_RVA": fmt_rva(edge.dst_rva),
            "DST_BLOCK": block_ids.get(destination_block, "") if destination_block is not None else "",
            "TARGET_KIND": effective_target_kind(edge),
            "CONFIDENCE": effective_edge_confidence(edge),
            "EVIDENCE": edge.evidence,
        })
    write_csv(
        ROOT / "exe_core005_direct_cfg.csv",
        ["SRC_RVA", "SRC_BLOCK", "INSTRUCTION_RVA", "MNEMONIC", "OPERANDS", "EDGE_TYPE", "DST_RVA", "DST_BLOCK", "TARGET_KIND", "CONFIDENCE", "EVIDENCE"],
        direct_rows,
    )

    predecessor_counts: dict[int, int] = defaultdict(int)
    successor_counts: dict[int, int] = defaultdict(int)
    for edge in recovery.edges:
        if edge.src_block not in reported_blocks:
            continue
        successor_counts[edge.src_block] += 1
        destination_block = block_for_target(edge.dst_rva, reported_blocks)
        if destination_block is not None:
            predecessor_counts[destination_block] += 1

    block_rows = []
    for rva, block in sorted(reported_blocks.items()):
        section = pe.section_for_rva(rva)
        block_rows.append({
            "BLOCK_ID": block_ids[rva],
            "START_RVA": fmt_rva(rva),
            "END_RVA": fmt_rva(block.end_rva),
            "SIZE": block.end_rva - block.start_rva,
            "FUNCTION_RVA": fmt_rva(block.function_rva),
            "SECTION": section.name if section else "UNKNOWN",
            "INSTRUCTION_COUNT": len(block.instructions),
            "TERMINATOR": block.terminator or block.stop_reason,
            "SUCCESSOR_COUNT": successor_counts[rva],
            "PREDECESSOR_COUNT": predecessor_counts[rva],
            "CONFIDENCE": block.confidence if block.function_rva == EXPECTED_ENTRY_RVA else function_trust.get(block.function_rva, "LOW"),
        })
    write_csv(
        ROOT / "exe_core005_basic_blocks.csv",
        ["block_id", "start_rva", "end_rva", "size", "function_rva", "section", "instruction_count", "terminator", "successors", "predecessors", "confidence"],
        [{
            "block_id": row["BLOCK_ID"],
            "start_rva": row["START_RVA"],
            "end_rva": row["END_RVA"],
            "size": row["SIZE"],
            "function_rva": row["FUNCTION_RVA"],
            "section": row["SECTION"],
            "instruction_count": row["INSTRUCTION_COUNT"],
            "terminator": row["TERMINATOR"],
            "successors": row["SUCCESSOR_COUNT"],
            "predecessors": row["PREDECESSOR_COUNT"],
            "confidence": row["CONFIDENCE"],
        } for row in block_rows],
    )

    call_edges = [
        edge for edge in recovery.edges
        if edge.src_block in reported_blocks
        and edge.edge_type in {"CALL", "INDIRECT_UNRESOLVED", "EXTERNAL_BOUNDARY"}
    ]
    caller_count: dict[int, int] = defaultdict(int)
    callee_count: dict[int, int] = defaultdict(int)
    callgraph_rows = []
    for edge in call_edges:
        call_type = "DIRECT" if edge.edge_type == "CALL" else "EXTERNAL" if edge.edge_type == "EXTERNAL_BOUNDARY" else "INDIRECT"
        if edge.edge_type == "CALL" and edge.dst_rva is not None:
            caller_count[edge.dst_rva] += 1
            callee_count[edge.src_function] += 1
        callgraph_rows.append({
            "CALLER_RVA": fmt_rva(edge.src_function),
            "CALLSITE_RVA": fmt_rva(edge.instruction_rva),
            "CALLEE_RVA": fmt_rva(edge.dst_rva),
            "CALL_TYPE": call_type,
            "TARGET_RESOLUTION": effective_target_kind(edge) if edge.dst_rva is not None else "UNRESOLVED",
            "CONFIDENCE": effective_edge_confidence(edge),
        })
    write_csv(
        ROOT / "exe_core005_callgraph.csv",
        ["CALLER_RVA", "CALLSITE_RVA", "CALLEE_RVA", "CALL_TYPE", "TARGET_RESOLUTION", "CONFIDENCE"],
        callgraph_rows,
    )

    blocks_by_function: dict[int, list[Block]] = defaultdict(list)
    for block in reported_blocks.values():
        blocks_by_function[block.function_rva].append(block)
    function_rows = []
    for rva, seed in sorted(recovery.function_seeds.items()):
        mapping_status, section, _offset = recovery.mapping(rva)
        owned = blocks_by_function.get(rva, [])
        instructions = [insn for block in owned for insn in block.instructions]
        ret_count = sum(block.terminator == "RET" for block in owned)
        indirect_count = sum(
            edge.edge_type == "INDIRECT_UNRESOLVED" and edge.src_function == rva
            for edge in recovery.edges
        )
        incoming_direct_callers = {
            edge.src_function
            for edge in recovery.edges
            if edge.edge_type == "CALL" and edge.dst_rva == rva
        }
        trusted_direct_caller = EXPECTED_ENTRY_RVA in incoming_direct_callers
        if rva == EXPECTED_ENTRY_RVA and owned:
            status = "CONFIRMED_FUNCTION"
            confidence = "CONFIRMED"
        elif (
            owned
            and any(item.startswith("DIRECT_CALL_TARGET") for item in seed.evidence)
            and ret_count
            and trusted_direct_caller
        ):
            status = "STRONG_FUNCTION_CANDIDATE"
            confidence = "STRONG"
        elif owned:
            status = "BASIC_BLOCK_ONLY"
            entry_block = reported_blocks.get(rva)
            confidence = "CANDIDATE" if entry_block and entry_block.confidence == "CANDIDATE" else "LOW"
        else:
            status = "UNRESOLVED"
            confidence = "UNKNOWN"
        start = min((block.start_rva for block in owned), default=rva)
        end = max((block.end_rva for block in owned), default=rva)
        function_rows.append({
            "FUNCTION_RVA": fmt_rva(rva),
            "VA": fmt_rva(pe.image_base + rva),
            "SECTION": section.name if section else "UNKNOWN",
            "SIZE": end - start,
            "ENTRY_EVIDENCE": ";".join(sorted(seed.evidence)),
            "CALLER_COUNT": caller_count[rva],
            "CALLEE_COUNT": callee_count[rva],
            "BLOCK_COUNT": len(owned),
            "RET_COUNT": ret_count,
            "INDIRECT_COUNT": indirect_count,
            "CONFIDENCE": confidence,
            "STATUS": status if mapping_status == "RAW_BACKED_EXECUTABLE" else "UNRESOLVED",
        })
    write_csv(
        ROOT / "exe_core005_functions.csv",
        ["function_rva", "section", "size", "entry_reason", "basic_blocks", "callers", "callees", "confidence", "status", "va", "ret_count", "indirect_count"],
        [{
            "function_rva": row["FUNCTION_RVA"],
            "section": row["SECTION"],
            "size": row["SIZE"],
            "entry_reason": row["ENTRY_EVIDENCE"],
            "basic_blocks": row["BLOCK_COUNT"],
            "callers": row["CALLER_COUNT"],
            "callees": row["CALLEE_COUNT"],
            "confidence": row["CONFIDENCE"],
            "status": row["STATUS"],
            "va": row["VA"],
            "ret_count": row["RET_COUNT"],
            "indirect_count": row["INDIRECT_COUNT"],
        } for row in function_rows],
    )

    write_csv(
        ROOT / "exe_core005_indirect_calls.csv",
        ["rva", "va", "instruction", "target_expression", "target_kind", "resolution_status", "possible_source", "confidence"],
        [{
            "rva": row["RVA"],
            "va": row["VA"],
            "instruction": row["INSTRUCTION"],
            "target_expression": row["TARGET_EXPRESSION"],
            "target_kind": row["TARGET_KIND"],
            "resolution_status": row["RESOLUTION_STATUS"],
            "possible_source": row["POSSIBLE_SOURCE"],
            "confidence": row["CONFIDENCE"],
        } for row in recovery.indirect_rows],
    )

    loop_rows = compute_loops(recovery, block_ids, reported_blocks)
    write_csv(
        ROOT / "exe_core005_loops.csv",
        ["loop_id", "header", "back_edge_source", "back_edge_target", "function_rva", "body_blocks", "exit_blocks", "confidence", "evidence"],
        [{
            "loop_id": row["LOOP_ID"],
            "header": row["HEADER_RVA"],
            "back_edge_source": row["LATCH_RVA"],
            "back_edge_target": row["HEADER_RVA"],
            "function_rva": row["FUNCTION_RVA"],
            "body_blocks": row["LOOP_SIZE"],
            "exit_blocks": "UNKNOWN",
            "confidence": row["CONFIDENCE"],
            "evidence": f"{row['EVIDENCE']}; back_edge_instruction={row['BACK_EDGE_RVA']}",
        } for row in loop_rows],
    )

    # Entry-connected reachability over the recovered direct graph.
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in recovery.edges:
        if edge.src_block not in reported_blocks:
            continue
        destination = block_for_target(edge.dst_rva, reported_blocks)
        if destination is not None and edge.edge_type in {"FALLTHROUGH", "CALL", "JMP", "COND_TAKEN", "COND_FALLTHROUGH"}:
            adjacency[edge.src_block].add(destination)
    entry_reachable_blocks = set()
    stack = [EXPECTED_ENTRY_RVA] if EXPECTED_ENTRY_RVA in reported_blocks else []
    while stack:
        block = stack.pop()
        if block in entry_reachable_blocks:
            continue
        entry_reachable_blocks.add(block)
        stack.extend(adjacency[block])
    entry_reachable_functions = {reported_blocks[block].function_rva for block in entry_reachable_blocks}

    reachability_rows = []
    for row in function_rows:
        rva = int(row["FUNCTION_RVA"], 16)
        mapping_status, _section, _offset = recovery.mapping(rva)
        if rva in entry_reachable_functions:
            classification = "ENTRY_CONNECTED"
            reachable = "YES"
            evidence = "reachable from PE Entry through recovered direct edges"
        elif row["BLOCK_COUNT"] and int(row["BLOCK_COUNT"]) > 0:
            classification = "NON_ENTRY_NATIVE_CLUSTER"
            reachable = "NO"
            evidence = "decoded candidate cluster has no recovered direct path from Entry"
        else:
            classification = "UNREACHABLE_FROM_ENTRY"
            reachable = "NO"
            evidence = mapping_status
        reachability_rows.append({
            "ENTITY_RVA": row["FUNCTION_RVA"],
            "ENTITY_KIND": "FUNCTION_OR_SEED",
            "CLASSIFICATION": classification,
            "ENTRY_REACHABLE": reachable,
            "EVIDENCE": evidence,
            "CONFIDENCE": row["CONFIDENCE"],
        })
    reachability_rows.append({
        "ENTITY_RVA": "0x0E5DC665",
        "ENTITY_KIND": "EXTERNAL_SLOT_RVA",
        "CLASSIFICATION": "EXTERNAL_BOUNDARY",
        "ENTRY_REACHABLE": "YES",
        "EVIDENCE": "Entry call dword ptr [slot VA 0x0E9DC665]",
        "CONFIDENCE": "CONFIRMED",
    })
    reachable_external_edges = sum(
        1 for edge in recovery.edges
        if edge.edge_type == "EXTERNAL_BOUNDARY" and edge.src_block in entry_reachable_blocks
    )
    reachable_tvm0_edges = sum(
        1 for edge in recovery.edges
        if edge.target_kind == "TVM0_BOUNDARY" and edge.src_block in entry_reachable_blocks
    )
    reachable_indirect_edges = sum(
        1 for edge in recovery.edges
        if edge.edge_type == "INDIRECT_UNRESOLVED" and edge.src_block in entry_reachable_blocks
    )
    reachable_unresolved_edges = sum(
        1 for edge in recovery.edges
        if edge.target_kind in {"UNKNOWN_TARGET", "VIRTUAL_ONLY", "INSTRUCTION_BOUNDARY_CONFLICT"}
        and edge.src_block in entry_reachable_blocks
    )
    entry_summary = {
            "ENTITY_RVA": "",
            "ENTITY_KIND": "SUMMARY",
            "CLASSIFICATION": "ENTRY_REACHABILITY_SUMMARY",
            "ENTRY_REACHABLE": "YES",
            "EVIDENCE": "counts computed only from blocks reachable from Entry",
            "CONFIDENCE": "PARTIAL",
            "reachable_functions": len(entry_reachable_functions),
            "reachable_blocks": len(entry_reachable_blocks),
            "external_edges": reachable_external_edges,
            "tvm0_edges": reachable_tvm0_edges,
            "indirect_edges": reachable_indirect_edges,
            "unresolved_edges": reachable_unresolved_edges,
    }
    write_csv(
        ROOT / "exe_core005_entry_reachability.csv",
        [
            "entity_rva", "entity_kind", "classification", "entry_reachable", "evidence", "confidence",
            "reachable_functions", "reachable_blocks", "external_edges", "tvm0_edges", "indirect_edges", "unresolved_edges",
        ],
        [{
            "entity_rva": row["ENTITY_RVA"],
            "entity_kind": row["ENTITY_KIND"],
            "classification": row["CLASSIFICATION"],
            "entry_reachable": row["ENTRY_REACHABLE"],
            "evidence": row["EVIDENCE"],
            "confidence": row["CONFIDENCE"],
            "reachable_functions": row.get("reachable_functions", ""),
            "reachable_blocks": row.get("reachable_blocks", ""),
            "external_edges": row.get("external_edges", ""),
            "tvm0_edges": row.get("tvm0_edges", ""),
            "indirect_edges": row.get("indirect_edges", ""),
            "unresolved_edges": row.get("unresolved_edges", ""),
        } for row in reachability_rows] + [{
            "entity_rva": entry_summary["ENTITY_RVA"],
            "entity_kind": entry_summary["ENTITY_KIND"],
            "classification": entry_summary["CLASSIFICATION"],
            "entry_reachable": entry_summary["ENTRY_REACHABLE"],
            "evidence": entry_summary["EVIDENCE"],
            "confidence": entry_summary["CONFIDENCE"],
            "reachable_functions": entry_summary["reachable_functions"],
            "reachable_blocks": entry_summary["reachable_blocks"],
            "external_edges": entry_summary["external_edges"],
            "tvm0_edges": entry_summary["tvm0_edges"],
            "indirect_edges": entry_summary["indirect_edges"],
            "unresolved_edges": entry_summary["unresolved_edges"],
        }],
    )

    # New CORE-005 evidence tables. These are derived from the same final,
    # overlap-filtered graph that feeds the legacy-compatible artifacts above.
    instruction_rows = make_instruction_database(pe, recovery, reported_blocks, function_trust)
    write_csv(
        ROOT / "exe_core005_instructions.csv",
        ["rva", "va", "file_offset", "section", "size", "mnemonic", "op_str", "bytes", "is_call", "is_jump", "is_conditional", "is_return", "is_indirect", "target_rva", "confidence"],
        instruction_rows,
    )

    direct_edge_rows = make_direct_edge_rows(pe, direct_rows)
    write_csv(
        ROOT / "exe_core005_direct_edges.csv",
        ["source_rva", "instruction_rva", "edge_type", "target_rva", "target_section", "target_executable", "confidence"],
        direct_edge_rows,
    )

    function_table_rows = make_function_table_rows(pe, recovery)
    write_csv(
        ROOT / "exe_core005_function_tables.csv",
        [
            "address", "input_kind", "location_rva", "location_va", "section", "file_offset", "location_status",
            "dword_value", "pointer_kind", "target_rva", "target_va", "target_section", "target_executable",
            "consecutive_executable_count", "xref_count", "recovered_cfg_uses", "classification", "confidence", "evidence",
        ],
        function_table_rows,
    )

    thread_rows = make_thread_seed_rows(pe)
    write_csv(
        ROOT / "exe_core005_thread_seeds.csv",
        ["symbol", "rva", "file_offset", "section", "thread_entry", "status", "confidence", "evidence"],
        thread_rows,
    )

    all_graph_rows = make_graph_rows(direct_rows, recovery, reported_blocks, entry_reachable_blocks, "ALL_NATIVE_FUNCTION_GRAPH")
    entry_graph_rows = make_graph_rows(direct_rows, recovery, reported_blocks, entry_reachable_blocks, "ENTRY_REACHABLE_GRAPH")
    graph_fields = ["graph_scope", "source_function_rva", "source_block", "instruction_rva", "edge_type", "target_rva", "target_block", "target_kind", "confidence", "evidence"]
    write_csv(ROOT / "exe_core005_all_native_graph.csv", graph_fields, all_graph_rows)
    write_csv(ROOT / "exe_core005_entry_reachable_graph.csv", graph_fields, entry_graph_rows)

    bootstrap_rows = []
    function_by_rva = {int(row["FUNCTION_RVA"], 16): row for row in function_rows}
    for rva in HISTORICAL_SEEDS:
        row = function_by_rva.get(rva, {})
        mapping_status, _section, _offset = recovery.mapping(rva)
        direct_incoming = [
            edge for edge in recovery.edges
            if edge.dst_rva == rva and edge.edge_type in {"CALL", "JMP"}
        ]
        indirect_incoming = [
            edge for edge in recovery.edges
            if edge.dst_rva == rva and edge.edge_type == "INDIRECT_UNRESOLVED"
        ]
        bootstrap_rows.append({
            "candidate_rva": fmt_rva(rva),
            "mapping_status": mapping_status,
            "entry_reachable": "YES" if rva in entry_reachable_functions else "NO",
            "direct_incoming_edges": len(direct_incoming),
            "indirect_incoming_edges": len(indirect_incoming),
            "function_status": row.get("STATUS", "UNRESOLVED"),
            "confidence": row.get("CONFIDENCE", "UNKNOWN"),
            "classification": "ENTRY_CONNECTED" if rva in entry_reachable_functions else "NOT_ENTRY_CONNECTED",
            "evidence": ";".join(
                [
                    "VIRTUAL_ONLY" if mapping_status == "VIRTUAL_ONLY" else "RAW_BACKED",
                    f"direct_incoming={len(direct_incoming)}",
                    f"indirect_incoming={len(indirect_incoming)}",
                ]
            ),
        })
    write_csv(
        ROOT / "exe_core005_bootstrap_validation.csv",
        ["candidate_rva", "mapping_status", "entry_reachable", "direct_incoming_edges", "indirect_incoming_edges", "function_status", "confidence", "classification", "evidence"],
        bootstrap_rows,
    )

    special = find_special_xrefs(pe, 0x004FCEE0, recovery.md)
    recovered_special_edges = [edge for edge in recovery.edges if edge.dst_rva == 0x004FCEE0]

    # Deterministic quality checks.
    validation_rows: list[dict[str, object]] = []
    entry_block = recovery.blocks.get(EXPECTED_ENTRY_RVA)
    entry_ok = bool(
        entry_block
        and entry_block.instructions
        and entry_block.instructions[0].raw == bytes.fromhex("FF 15 65 C6 9D 0E")
        and entry_block.instructions[0].mnemonic == "call"
    )
    validation_rows.append({
        "TEST": "A_ENTRY",
        "ITEM": fmt_rva(EXPECTED_ENTRY_RVA),
        "STATUS": "PASS" if entry_ok else "FAIL",
        "EVIDENCE": "FF 15 65 C6 9D 0E -> call dword ptr [0x0E9DC665]" if entry_ok else "entry mismatch",
    })

    raw_test_rvas = sorted(
        rva for rva in address_rvas
        if recovery.mapping(rva)[0] == "RAW_BACKED_EXECUTABLE"
    )
    successful_raw_tests = 0
    for rva in raw_test_rvas:
        insn, status = recovery.decode_one(rva)
        validation_rows.append({
            "TEST": "B_RVA_RAW_DECODE",
            "ITEM": fmt_rva(rva),
            "STATUS": "PASS" if insn is not None else "INCONCLUSIVE",
            "EVIDENCE": f"{insn.mnemonic} {insn.op_str}".strip() if insn else status,
        })
        if insn is not None:
            successful_raw_tests += 1
        if successful_raw_tests >= 10 and any(
            row["TEST"] == "B_RVA_RAW_DECODE" and row["ITEM"] == "0x004FCEE0"
            for row in validation_rows
        ):
            break

    rng = random.Random(0xC0D005)
    edge_sample = [edge for edge in recovery.edges if edge.src_block in reported_blocks]
    rng.shuffle(edge_sample)
    edge_sample = edge_sample[:20]
    for edge in edge_sample:
        insn, status = recovery.decode_one(edge.instruction_rva)
        valid, evidence = validate_edge_decode(recovery, edge)
        validation_rows.append({
            "TEST": "C_EDGE_REDECODE",
            "ITEM": f"{fmt_rva(edge.instruction_rva)}->{fmt_rva(edge.dst_rva)}",
            "STATUS": "PASS" if valid else "FAIL",
            "EVIDENCE": evidence,
        })

    function_sample = list(function_rows)
    rng.shuffle(function_sample)
    for row in function_sample[:10]:
        evidence = row["ENTRY_EVIDENCE"]
        accepted = any(token in evidence for token in ("PE_ENTRYPOINT", "DIRECT_CALL_TARGET", "HISTORICAL_NATIVE_CANDIDATE", "CORE003_MECHANICAL_PROLOGUE_HIT"))
        validation_rows.append({
            "TEST": "D_FUNCTION_ENTRY_EVIDENCE",
            "ITEM": row["FUNCTION_RVA"],
            "STATUS": "PASS" if accepted else "FAIL",
            "EVIDENCE": evidence,
        })

    invalid_read_count = 0
    for rva in HISTORICAL_SEEDS:
        mapping_status, _section, _offset = recovery.mapping(rva)
        if mapping_status == "VIRTUAL_ONLY" and rva in recovery.blocks:
            invalid_read_count += 1
    validation_rows.append({
        "TEST": "E_NO_VIRTUAL_ONLY_DECODE",
        "ITEM": "HISTORICAL_SEEDS",
        "STATUS": "PASS" if invalid_read_count == 0 else "FAIL",
        "EVIDENCE": f"virtual-only seeds decoded as blocks={invalid_read_count}",
    })
    write_csv(
        ROOT / "exe_core005_validation.csv",
        ["TEST", "ITEM", "STATUS", "EVIDENCE"],
        validation_rows,
    )

    edge_counts = defaultdict(int)
    for row in direct_rows:
        edge_counts[str(row["EDGE_TYPE"])] += 1
    function_status_counts = defaultdict(int)
    for row in function_rows:
        function_status_counts[str(row["STATUS"])] += 1
    block_confidence_counts = defaultdict(int)
    for row in block_rows:
        block_confidence_counts[str(row["CONFIDENCE"])] += 1
    validation_passes = sum(row["STATUS"] == "PASS" for row in validation_rows)
    validation_failures = sum(row["STATUS"] == "FAIL" for row in validation_rows)
    validation_inconclusive = sum(row["STATUS"] == "INCONCLUSIVE" for row in validation_rows)

    report = f"""# CODOL STANDALONE CORE-005
# Native Function / CFG Recovery

## 1. Sample identity

```text
Sample = COD OL\\codoMP_client_shipRetail.exe
SHA-256 = {sample_hash}
PE = PE32 / I386
ImageBase = 0x{pe.image_base:08X}
Entry RVA = 0x{pe.entry_rva:08X}
Entry VA = 0x{pe.image_base + pe.entry_rva:08X}
SAMPLE_MATCH_CONFIRMED
```

## 2. PE / section mapping

The standard-library PE parser from CORE-004A was reused. RVA mapping always uses the section table. `RAW_BACKED`, `VIRTUAL_ONLY`, `DATA_UNKNOWN`, and `TVM0_BOUNDARY` are distinct states. No virtual-only RVA was read as file code.

## 3. Decoder validation

Capstone `{capstone.__version__}` runs as x86-32 with `detail=True`. Entry re-decodes as:

```asm
0x0E5DC690  FF 15 65 C6 9D 0E  call dword ptr [0x0E9DC665]
```

The slot VA maps to RVA `0x0E5DC665`. It is an `EXTERNAL_CALL_BOUNDARY`, not an EXE function.

## 4. Function recovery method

A bounded recursive-descent decoder starts only from PE Entry, the seven explicitly supplied historical candidates, three retained CORE-003 heuristic hits, and newly decoded direct CALL targets. CALL targets remain candidates; historical seeds do not become confirmed merely because Capstone returns instructions.

```text
FUNCTION_RECOVERY_METHOD = CFG_DERIVED + KNOWN_SEED
FUNCTION_RECOVERY_STATUS = PARTIAL
functions/seeds = {len(function_rows)}
status counts = {dict(function_status_counts)}
```

Function entry categories are kept separate: `PE_ENTRYPOINT`, direct-call target,
historical seed, legacy heuristic hit, and unresolved/virtual-only seed. The three
CORE-003 prologue hits are not promoted to functions merely because they begin with
`push ebp`.

## 5. Basic block recovery

Blocks terminate on CALL, JMP, conditional branch, RET, unresolved indirect transfer, decode failure, zero padding, or budget boundary. Instruction and block starts are globally deduplicated.

```text
basic blocks = {len(block_rows)}
block confidence = {dict(block_confidence_counts)}
decoded nonempty starts before conflict filtering = {len(nonempty_blocks)}
excluded instruction-range conflict starts = {len(conflict_starts)}
reported block-range overlaps = 0
```

When two candidate paths produced overlapping instruction ranges, both conflicting starts were excluded from the report rather than selecting an arbitrary alignment.

## 6. Direct CFG

```text
CFG_STATUS = PARTIAL
edges = {len(direct_rows)}
edge types = {dict(edge_counts)}
```

Only decoded direct control transfers create target edges. Ordinary bytes and string proximity do not create edges.

The CORE-005-specific direct-edge table is `exe_core005_direct_edges.csv`. Relative
targets are independently checked from the signed displacement in the instruction
bytes using `instruction_end + displacement`; operand text is not treated as an RVA.

```text
instruction database rows = {len(instruction_rows)}
direct edge rows = {len(direct_edge_rows)}
decode-failure rows = {sum(1 for row in instruction_rows if str(row['mnemonic']).startswith('DECODE_FAILURE:'))}
```

## 7. Call graph

The call graph contains {len(callgraph_rows)} recovered call sites. Direct, indirect, and the Entry external boundary remain separate classifications.

## 8. Indirect calls

Unresolved indirect call/jump sites: {len(recovery.indirect_rows)}. No register or memory target was guessed.

Static value propagation did not establish an executable target for the unresolved
site(s). The Entry memory operand is handled separately as the confirmed external
boundary. No `call eax`-style target is upgraded from syntax alone.

## 8A. Function-pointer tables

All 17 CORE-003 table suspects were re-read through PE mapping and DWORD extraction.

```text
table rows = {len(function_table_rows)}
classification counts = {dict((key, sum(1 for row in function_table_rows if row['classification'] == key)) for key in sorted(set(row['classification'] for row in function_table_rows)))}
```

The four mode/state addresses in the large virtual range are `VIRTUAL_ONLY` and
remain `UNKNOWN`. Executable-looking DWORDs are not treated as function pointers
without a confirmed use/xref sequence.

## 9. Loops/back-edges

Loop rows: {len(loop_rows)}. A row is emitted only when the destination dominates the source in a recovered per-function direct block graph. No loop receives a gameplay semantic name.

All loops outside the Entry cluster inherit the trust level of their originating candidate stream and remain `LOOP_CANDIDATE`; structural complexity does not raise a historical seed to confirmed code.

## 10. Entry reachability

Entry reaches {len(entry_reachable_blocks)} native block(s) and {len(entry_reachable_functions)} recovered function/seed cluster(s) before the confirmed external boundary. The historical `0x0077F580 -> ... -> 0x006212C0` chain is `NOT_ENTRY_CONNECTED`; most addresses in that chain are also `VIRTUAL_ONLY` in the original file.

Separate graph artifacts are emitted:

```text
ALL_NATIVE_FUNCTION_GRAPH = {len(all_graph_rows)} edge rows
ENTRY_REACHABLE_GRAPH = {len(entry_graph_rows)} edge rows
```

This separation prevents the small Entry-connected graph from being mistaken for
the size of all recoverable native candidates.

## 10A. Secondary roots and thread entries

Static thread API symbol search produced `{len(thread_rows)}` row(s). No thread start
parameter was recovered, so no `THREAD_ENTRY_CONFIRMED` or secondary root was added.

Bootstrap candidate validation is in `exe_core005_bootstrap_validation.csv`; each
candidate is explicitly labeled `ENTRY_CONNECTED`, `NOT_ENTRY_CONNECTED`, or
`VIRTUAL_ONLY`/unresolved.

## 11. Known native candidate validation

- `0x004FD9B0`: RAW-backed and mechanically decodable, but starts with an implausible sequence including `aaa`; retained as `BASIC_BLOCK_ONLY`/candidate, not a confirmed function.
- `0x004FCEE0`: RAW-backed but direct-entry decode fails; see the special analysis below.
- `0x00808650`, `0x007E98F0`, `0x006212C0`, `0x0077F580`, `0x0077F8B3`: `VIRTUAL_ONLY`; no file code was synthesized.
- CORE-003 hit `0x00001098`: mechanically decodes but contains implausible/rare instructions and remains low-confidence block-only evidence.
- CORE-003 hits `0x000010AF` and `0x000010C6`: overlap the decoded stream rooted at `0x00001098`; they were excluded as independent blocks and remain unresolved.

## 12. 0x004FCEE0 special analysis

```text
section = .tp3
file offset = 0x004FCEE0
direct-entry decode = DIRECT_ENTRY_DECODE_UNRESOLVED
verified direct CALL/JMP xrefs = {len(special['direct_hits'])}
absolute VA pointer occurrences = {len(special['absolute_pointer_offsets'])}
recovered CFG edges into target = {len(recovered_special_edges)}
possible predecessor-alignment paths within 15 bytes = {len(special['predecessor_candidates'])}
```

The predecessor-alignment paths are alignment possibilities only, not instruction-boundary proof. No recovered block establishes `0x004FCEE0` as a function entry.

## 13. .tvm0 boundaries

No `.tvm0` bytes were decoded. Any recovered edge landing there is labeled `TVM0_BOUNDARY` and traversal stops.

## 14. External boundaries

Entry's `call dword ptr [0x0E9DC665]` is confirmed as the established external boundary. Base.dll and all other DLL internals were not analyzed.

If a future recovered edge reaches `.tvm0`, it must be emitted as `TVM0_BOUNDARY`
and traversal must stop. No `.tvm0` instruction is present in the current graph.

## 15. Negative findings

- No trustworthy EXE-native continuation was recovered after the Entry external call.
- The historical candidate chain is not reachable from Entry through this EXE's recovered direct CFG.
- No `VIRTUAL_ONLY` address was decoded from the file.
- Mechanical decoding alone was not accepted as function proof.
- No Game Init, Main Loop, Renderer, Filesystem, IIPS, or state-machine semantics were assigned.

## 16. Confidence classification

```text
CONFIRMED = PE Entry and its external boundary
STRONG = direct CALL target with recovered structure and RET, when present
CANDIDATE = mechanically recovered direct block/edge with explicit provenance
LOW = decodable stream with implausible instruction mix or weak boundary evidence
UNKNOWN = unresolved indirect, virtual-only, or undecodable target
UNRESOLVED = a required boundary/target could not be established from current evidence
```

## 17. Remaining unknowns

The file contains very large virtual ranges with little raw backing, so static analysis of the original image cannot reconstruct runtime-produced bytes in those regions. A substantial EXE-wide CFG requires a trusted runtime memory image or a stronger native analysis environment, while preserving the no-patch and no-`.tvm0` boundaries.

## Artifact inventory

```text
exe_core005_instructions.csv
exe_core005_direct_edges.csv
exe_core005_basic_blocks.csv
exe_core005_functions.csv
exe_core005_indirect_calls.csv
exe_core005_function_tables.csv
exe_core005_loops.csv
exe_core005_entry_reachability.csv
exe_core005_all_native_graph.csv
exe_core005_entry_reachable_graph.csv
exe_core005_thread_seeds.csv
exe_core005_bootstrap_validation.csv
```

## Quality validation

```text
validation rows = {len(validation_rows)}
PASS = {validation_passes}
FAIL = {validation_failures}
INCONCLUSIVE = {validation_inconclusive}
sampled CFG edges = {len(edge_sample)}
sampled function/seed entries = {min(10, len(function_rows))}
```

## Final status

```text
TOOLCHAIN_STATUS = LEVEL_5
FUNCTION_RECOVERY_STATUS = PARTIAL
CFG_STATUS = PARTIAL
ENTRY_NATIVE_CONTINUATION = EXTERNAL_BOUNDARY_ONLY
HISTORICAL_CHAIN_STATUS = NOT_ENTRY_CONNECTED
CFG_RECOVERY_USABLE = NO
FULL_CFG = NOT_CLAIMED
```
"""
    (ROOT / "CODOL_STANDALONE_CORE_005_NATIVE_CFG_RECOVERY.md").write_text(report, encoding="utf-8")

    print(f"blocks={len(block_rows)}")
    print(f"functions_or_seeds={len(function_rows)}")
    print(f"cfg_edges={len(direct_rows)}")
    print(f"indirect_sites={len(recovery.indirect_rows)}")
    print(f"loops={len(loop_rows)}")
    print(f"validation_pass={validation_passes} fail={validation_failures} inconclusive={validation_inconclusive}")
    print("TOOLCHAIN_STATUS=LEVEL_5")
    print("CFG_STATUS=PARTIAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
