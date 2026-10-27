"""A wrong-but-plausible reader (own header check + libzstd one-shot decode) passes every ZST fixture,
yet accepts adv/T.chst (trailing skippable frame) and adv/U.chst (two frames). Run from review-work/."""
import sys, glob, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr8
from compression import zstd as Z
FX = '/home/jaron/projects/container-format-rs/fixtures'
def lax(st, raw):
    rule, h = rdr8.zstd_header(st)
    if rule: return rule
    if h['fcs'] is not None and h['fcs'] != raw: return 'ZST-1'
    try: out = Z.decompress(st)
    except Exception: return 'ZST-2'
    return None if len(out) == raw else 'ZST-2'
def first_zst(d):
    r = rdr8.check(d, ext=True, mode='list', all_=True); res = None
    for B in r.blobs:
        if B['enc'] == 1 and B['st'] >= 4: res = res or lax(d[B['off']:B['off']+B['st']], B['raw'])
    return res
miss = [os.path.basename(f) for f in sorted(glob.glob(f'{FX}/extended/invalid/ZST-*.chst'))
        if not f.endswith('ZST-2-short.chst') and json.load(open(f[:-5] + '.expect.json'))['rule'] in ('ZST-1', 'ZST-2')
        and first_zst(open(f, 'rb').read()) != json.load(open(f[:-5] + '.expect.json'))['rule']]
print('ZST fixtures the lax reader gets wrong:', miss or 'none')
for n in ('T', 'U'):
    d = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adv', n + '.chst'), 'rb').read()
    print(f'adv/{n}.chst: spec reader {rdr8.first(rdr8.check(d, ext=True))[0]}, lax reader {first_zst(d)}')
