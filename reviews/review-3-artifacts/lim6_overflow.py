"""LIM-6 with --max-ratio 2^64-1 (newly legal per Appendix C, N23) on a valid fixture: exact arithmetic
(rdr8, the generator) -> valid; u64 checked_mul per '(an overflow is a violation)' -> LIM-6, exit 8."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append('/home/jaron/projects/container-format-rs/fixtures/gen')
import rdr8, check as g
d = open('/home/jaron/projects/container-format-rs/fixtures/extended/valid/zstd-compressed/container.chst', 'rb').read()
L = 2**64 - 1
print('exact arithmetic: rdr8', rdr8.first(rdr8.check(d, ext=True, limits={'ratio': L})), '| generator', g.check(d, limits={'ratio': L}))
for B in rdr8.check(d, ext=True, mode='list').blobs:
    if B['enc'] == 1:
        print(f"checked u64: {L} x {B['st']} overflows = {L*B['st'] >= 2**64} -> violation -> limit-exceeded/limit.ratio, exit 8")
