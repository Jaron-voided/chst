"""M-bitflip-compressed.chst: one byte of the Compressed frame flipped (key not recomputed).
verify -> BLB-6 (exit 7). A streaming extractor sees the decode failure before the hash is complete."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr8
from compression import zstd as Z
H = os.path.dirname(os.path.abspath(__file__)); d = open(os.path.join(H, 'M-bitflip-compressed.chst'), 'rb').read()
print('verify:', rdr8.first(rdr8.check(d, ext=True)))
B = [b for b in rdr8.check(d, ext=True, mode='list').blobs if b['enc'] == 1][0]; st = d[B['off']:B['off']+B['st']]
dec = Z.ZstdDecompressor(options={Z.DecompressionParameter.window_log_max: 23})
try:
    for i in range(0, len(st), 64): dec.decompress(st[i:i+64])
except Z.ZstdError as e: print(f'streaming decode fails at input chunk ending {min(i+64, len(st))}/{len(st)}: {e} -> ZST-2 (exit 6) if reported then')
