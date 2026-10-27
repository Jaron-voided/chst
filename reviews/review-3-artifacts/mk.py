"""Minimal independent container builder: one file 'f' per blob, Extended ZSTD flag."""
import hashlib, struct
MAGIC = bytes.fromhex("434853540D0A1A00"); TMAGIC = bytes.fromhex("001A0A0D54534843")
def build(blobs, req=None, opt=0, ers=48, names=None):
    """blobs: list of (stored, raw_length, encoding)."""
    names = names or [f'f{i}' for i in range(len(blobs))]
    if req is None: req = 1 if any(e == 1 for _, _, e in blobs) else 0
    hdr = MAGIC + struct.pack('<HHB3sQQ', 1, 0, 1, b'\0'*3, req, opt)
    data = b''.join(s for s, _, _ in blobs); off = 32; bt = b''
    for s, raw, enc in blobs:
        bt += hashlib.sha256(s).digest() + struct.pack('<QQQB7s', off, len(s), raw, enc, b'\0'*7); off += len(s)
    et = b''; po = 0
    for i, (s, _, _) in enumerate(blobs):
        p = names[i].encode()
        et += struct.pack('<QIB3s', po, len(p), 2, b'\0'*3) + hashlib.sha256(s).digest() + b'\0'*(ers-48); po += len(p)
    pool = b''.join(n.encode() for n in names)
    idx = struct.pack('<IIQ', 0x80000001, 64, len(blobs)) + bt + struct.pack('<IIQ', 0x80000002, ers, len(blobs)) + et \
        + struct.pack('<IIQ', 0x80000003, 1, len(pool)) + pool
    io = 32 + len(data); t16 = struct.pack('<QQ', io, len(idx))
    return hdr + data + idx + t16 + hashlib.sha256(hdr + idx + t16).digest() + TMAGIC
def fhd(fcs_flag=0, ss=0, unused=0, reserved=0, cks=0, did=0):
    return (fcs_flag << 6) | (ss << 5) | (unused << 4) | (reserved << 3) | (cks << 2) | did
def frame(fh, wd=None, didb=b'', fcsb=b'', blocks=b'', cksum=b''):
    return b'\x28\xb5\x2f\xfd' + bytes([fh]) + (bytes([wd]) if wd is not None else b'') + didb + fcsb + blocks + cksum
def blk(bt, size, body, last=0):
    return (last | (bt << 1) | (size << 3)).to_bytes(3, 'little') + body
def raw(b, last=0): return blk(0, len(b), b, last)
def rle(byte, n, last=0): return blk(1, n, bytes([byte]), last)
