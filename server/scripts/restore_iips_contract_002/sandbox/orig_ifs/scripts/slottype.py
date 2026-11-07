"""判定某个绝对地址（全局槽/变量）的引用形态：读 / 写 / 读改写。

背景：img.xrefs_to_imm32() 是纯字节模式匹配，返回的 va 是 imm32 的首字节，
不是指令首字节。本脚本往回反汇编，找出真正包含这个 imm32 的那条指令，
再按助记符判定是「读槽」还是「写槽」。

用法：
    python scripts/slottype.py <hexva> [<hexva> ...]
"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image, IMAGE_BASE
import x86callers as X

# mnemonic + operand 形态 -> 类别
WRITE_MNEM = {'mov', 'movzx', 'movsx', 'xchg', 'lea'}   # 目标操作数写
READ_MNEM = {'call', 'jmp', 'push', 'cmp', 'test', 'or', 'and', 'add', 'sub',
             'inc', 'dec', 'not', 'neg', 'mov'}


def classify(img, target_va):
    hits = img.xrefs_to_imm32(target_va)
    out = []
    for fo, imm_va, b in hits:
        # 从 imm_va-15 反汇编，找包含 imm_va 的那条指令
        ins_list = list(X.dis(img, imm_va - 15, 30))
        found = None
        for ins in ins_list:
            if ins.address <= imm_va < ins.address + ins.size:
                found = ins
                break
        out.append((imm_va, found, b))
    return out


def shape(ins, target_va):
    if ins is None:
        return 'RAW', '无法解码为指令（真字节巧合或数据区）'
    ops = ins.op_str
    tgt = '0x%08x' % target_va
    mn = ins.mnemonic
    # 目标操作数是内存且正好是 target -> 写
    if mn in ('mov', 'movzx', 'movsx', 'xchg', 'lea') and ops.startswith(
            'dword ptr [%s]' % tgt) or (mn in ('mov',) and ops.startswith('[%s]' % tgt)):
        return 'WRITE', '%s %s' % (mn, ops)
    if mn == 'call' and ops == 'dword ptr [%s]' % tgt:
        return 'CALL', 'call [slot]  ← 间接调用'
    if mn == 'jmp' and ops == 'dword ptr [%s]' % tgt:
        return 'JMP', 'jmp [slot]  ← 间接跳转/尾调用'
    if mn == 'push' and ops == tgt:
        return 'PUSH-ADDR', 'push slot地址（取址，通常给函数当参数）'
    if '[' in ops and tgt in ops:
        # 读或 RMW
        if mn in ('cmp', 'test', 'push'):
            return 'READ', '%s %s' % (mn, ops)
        return 'RMW', '%s %s' % (mn, ops)
    return 'OTHER', '%s %s' % (mn, ops)


def main():
    img = Image()
    for a in sys.argv[1:]:
        t = int(a, 16)
        print('=' * 62)
        print('SLOT 0x%08x' % t)
        res = classify(img, t)
        cnt = collections.Counter()
        for imm_va, ins, b in res:
            k, d = shape(ins, t)
            cnt[k] += 1
            pre = ''
            if ins is not None:
                pre = X.render(ins)
            else:
                pre = '%08x  %-24s (no insn)' % (imm_va, b.hex())
            print('  [%-10s] %s' % (k, pre))
        print('  --- 统计:', dict(cnt))


if __name__ == '__main__':
    main()
