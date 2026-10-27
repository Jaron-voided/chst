import sys, os, struct, random, collections
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
sys.path.append('/home/jaron/projects/container-format-rs/fixtures/gen')
import rdr8, mk, check as gchk
from mk import fhd, frame, raw, rle
FX = '/home/jaron/projects/container-format-rs/fixtures'
d = open(f'{FX}/extended/valid/zstd-compressed/container.chst', 'rb').read()
r = rdr8.check(d, ext=True, mode='list')
comp = [(d[B['off']:B['off']+B['st']], B['raw']) for B in r.blobs if B['enc'] == 1]
x64 = lambda b: (rdr8.xxh64(b) & 0xFFFFFFFF).to_bytes(4, 'little')
bases = comp + [
  (frame(fhd(cks=1), wd=0x40, blocks=rle(65, 4096) + raw(b'xyz' * 30) + rle(66, 4006, 1), cksum=x64(b'A'*4096 + b'xyz'*30 + b'B'*4006)), 8192),
  (frame(fhd(fcs_flag=1, ss=1), fcsb=struct.pack('<H', 8192-256), blocks=rle(65, 8192, 1)), 8192),
  (frame(fhd(fcs_flag=2), wd=0x00, fcsb=struct.pack('<I', 3000), blocks=rle(65, 1000) * 2 + rle(65, 1000, 1)), 3000)]
for st, rl in bases:
    assert rdr8.first(rdr8.check(mk.build([(st, rl, 1)]), ext=True)) is None
rng = random.Random(8); N = int(sys.argv[1]); diff = 0; hist = collections.Counter()
for i in range(N):
    st, rl = rng.choice(bases); b = bytearray(st)
    for _ in range(rng.choice([1, 1, 2, 3])):
        if not b: break
        k = rng.random()
        if k < 0.6: b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
        elif k < 0.75: b[rng.randrange(len(b))] = rng.randrange(256)
        elif k < 0.85: del b[rng.randrange(len(b)):]
        else: b += bytes(rng.randrange(256) for _ in range(rng.randrange(1, 6)))
    if len(b) < 4: continue
    rl2 = rl + rng.choice([0, 0, 0, 1, -1])
    data = mk.build([(bytes(b), rl2, 1)])
    a = rdr8.first(rdr8.check(data, ext=True)); a = a and a[0]
    g = gchk.check(data); g = g[0] if g else None
    hist[a] += 1
    if a != g:
        diff += 1
        if diff <= 5: print('DIFF', a, g, bytes(b[:16]).hex(), rl2); open(f'{H}/adv/fuzzdiff{diff}.chst', 'wb').write(data)
print('cases', sum(hist.values()), 'differences', diff, dict(hist))
