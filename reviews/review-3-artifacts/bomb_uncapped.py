"""A WRONG reader: streams the bomb through libzstd with a small output buffer, never applying
the raw_length cap, and only compares the total at the end. Measures time and peak RSS."""
import sys, time, resource
sys.path.insert(0, '.')
import rdr8
from compression import zstd as Z
d = open('/home/jaron/projects/container-format-rs/fixtures/extended/invalid/ZST-2-bomb.chst', 'rb').read()
r = rdr8.check(d, ext=True, mode='list', all_=True); B = r.blobs[2]; st = d[B['off']:B['off']+B['st']]
t = time.time(); dec = Z.ZstdDecompressor(options={Z.DecompressionParameter.window_log_max: 23}); total = 0
out = dec.decompress(st, max_length=131072); total += len(out)
while not dec.eof:
    out = dec.decompress(b'', max_length=131072); total += len(out)
print(f'uncapped streaming decode: {total} bytes in {time.time()-t:.2f}s, peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss} KiB; '
      f'then length {total} != raw {B["raw"]} -> ZST-2 anyway')
