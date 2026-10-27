"""Round-8 reviewer reader, adapted from the round-7 rdr.py to FORMAT_SPEC at 51c6a39.
Spec-only Chst reader (written from FORMAT_SPEC.md before reading fixtures/gen/).

check(data, ext=True/False, mode='verify'|'list', limits={}) -> list of (rule, detail) in
section 13 order. first element = reported violation. With all_=True it keeps going where
it safely can (best effort, for also_violates comparison).
"""
import hashlib, struct, unicodedata, json, sys

MAGIC = bytes.fromhex("434853540D0A1A00")
TMAGIC = bytes.fromhex("001A0A0D54534843")
BLOB, ENTRY, PATH, KV = 0x80000001, 0x80000002, 0x80000003, 0x00000010
DET = {
 'HDR-1':'hdr.too-short','HDR-2':'hdr.magic','HDR-3':'hdr.major-version','HDR-4':'hdr.hash-alg',
 'HDR-5':'hdr.reserved','HDR-6':'hdr.required-flag','TRL-1':'trl.magic','TRL-2':'trl.index-range',
 'TRL-3':'trl.hash','SEC-1':'sec.bounds','SEC-2':'sec.unknown-critical','SEC-3':'sec.layout',
 'SEC-4':'sec.record-size-min','SEC-5':'sec.record-size','BLB-1':'blob.reserved','BLB-2':'blob.encoding',
 'BLB-3':'blob.raw-length','BLB-4':'blob.layout','BLB-5':'blob.duplicate-key','BLB-6':'blob.hash',
 'BLB-7':'blob.unreferenced','ENT-1':'entry.type','ENT-2':'entry.reserved','ENT-3':'entry.dir-key',
 'ENT-4':'entry.dangling-key','ENT-5':'entry.path-range','ENT-6':'entry.parent','PATH-1':'path.utf8',
 'PATH-2':'path.nfc','PATH-3':'path.length','PATH-4':'path.slash','PATH-5':'path.dot-segment',
 'PATH-6':'path.control-char','PATH-7':'path.forbidden-char','PATH-8':'path.trailing-dot-space',
 'PATH-9':'path.reserved-name','PATH-10':'path.depth','PATH-11':'path.case-collision',
 'CAN-1':'canon.entry-order','CAN-2':'canon.blob-order','CAN-3':'canon.path-pool','FLG-1':'flag.mismatch',
 'LIM-2':'lim.index-size','LIM-3':'limit.entries','LIM-4':'limit.index-size','LIM-5':'limit.total-size',
 'LIM-6':'limit.ratio','ZST-1':'zstd.raw-length','ZST-2':'zstd.frame','ZST-3':'zstd.not-smaller',
 'ATT-1':'attrs.range','KV-1':'kv.format'}
CAT = {}
for r in DET:
    p = r.split('-')[0]
    CAT[r] = 'malformed'
for r in ('HDR-1','HDR-2'): CAT[r]='not-a-container'
for r in ('HDR-3','HDR-4','HDR-6','SEC-2'): CAT[r]='unsupported'
for r in ('TRL-3','BLB-6','ZST-1'): CAT[r]='integrity'
for r in ('LIM-3','LIM-4','LIM-5','LIM-6'): CAT[r]='limit-exceeded'
EXIT = {'not-a-container':4,'unsupported':5,'malformed':6,'integrity':7,'limit-exceeded':8}
DEFAULTS = {'entries':1048576,'index':268435456,'total':68719476736,'ratio':1000}

u8 = lambda b,o: b[o]
u16 = lambda b,o: struct.unpack_from('<H',b,o)[0]
u32 = lambda b,o: struct.unpack_from('<I',b,o)[0]
u64 = lambda b,o: struct.unpack_from('<Q',b,o)[0]
i64 = lambda b,o: struct.unpack_from('<q',b,o)[0]

class Stop(Exception): pass

# ---------------- XXH64 (for zstd content checksum) ----------------
P1=11400714785074694791; P2=14029467366897019727; P3=1609587929392839161
P4=9650029242287828579; P5=2870177450012600261; M=(1<<64)-1
def _rotl(x,r): return ((x<<r)|(x>>(64-r)))&M
def _round(acc,inp): acc=(acc+inp*P2)&M; acc=_rotl(acc,31); return (acc*P1)&M
def _merge(acc,v): acc^=_round(0,v); return (acc*P1+P4)&M
def xxh64(data, seed=0):
    n=len(data); i=0
    if n>=32:
        v1=(seed+P1+P2)&M; v2=(seed+P2)&M; v3=seed; v4=(seed-P1)&M
        while i+32<=n:
            v1=_round(v1,u64(data,i)); v2=_round(v2,u64(data,i+8)); v3=_round(v3,u64(data,i+16)); v4=_round(v4,u64(data,i+24)); i+=32
        h=(_rotl(v1,1)+_rotl(v2,7)+_rotl(v3,12)+_rotl(v4,18))&M
        for v in (v1,v2,v3,v4): h=_merge(h,v)
    else:
        h=(seed+P5)&M
    h=(h+n)&M
    while i+8<=n:
        h^=_round(0,u64(data,i)); h=(_rotl(h,27)*P1+P4)&M; i+=8
    if i+4<=n:
        h^=(u32(data,i)*P1)&M; h=(_rotl(h,23)*P2+P3)&M; i+=4
    while i<n:
        h^=(data[i]*P5)&M; h=(_rotl(h,11)*P1)&M; i+=1
    h^=h>>33; h=(h*P2)&M; h^=h>>29; h=(h*P3)&M; h^=h>>32
    return h

# ---------------- zstd frame: FORMAT_SPEC 12.5 / 13 step 11 as of round 8 ----------
def zstd_header(b):
    """Parse frame header. Return ('ZST-2', why) or (None, hdr dict)."""
    if len(b) < 4 or u32(b,0) != 0xFD2FB528:
        return 'ZST-2', 'magic'
    if len(b) < 5: return 'ZST-2','header longer than blob'
    fhd = b[4]; fcs_flag = fhd>>6; ss = (fhd>>5)&1; reserved=(fhd>>3)&1; cks=(fhd>>2)&1; did_flag=fhd&3
    if reserved: return 'ZST-2','reserved bit'
    p=5; window=None
    if not ss:
        if p>=len(b): return 'ZST-2','header longer than blob'
        wd=b[p]; p+=1; e=wd>>3; m=wd&7; base=1<<(10+e); window=base+(base//8)*m
    dsz=[0,1,2,4][did_flag]
    if p+dsz>len(b): return 'ZST-2','header longer than blob'
    did=int.from_bytes(b[p:p+dsz],'little'); p+=dsz
    fsz=[1 if ss else 0,2,4,8][fcs_flag]
    if p+fsz>len(b): return 'ZST-2','header longer than blob'
    fcs=None
    if fsz:
        fcs=int.from_bytes(b[p:p+fsz],'little'); p+=fsz
        if fsz==2: fcs+=256
    if ss: window=fcs
    if window > 8388608: return 'ZST-2', f'window {window}'
    if did != 0: return 'ZST-2', f'dictid {did}'
    return None, dict(window=window, fcs=fcs, ss=ss, cks=cks, hdr_end=p, fhd=fhd)

def zstd_decode_pass(b, raw_length, h):
    """One pass, output capped at raw_length. Any failure -> ('ZST-2', why)."""
    p = h['hdr_end']; window = h['window']; bmax = min(window, 131072)
    out = bytearray(); comp = []   # we decode Raw/RLE ourselves
    any_comp = False
    while True:
        if p+3 > len(b): return 'ZST-2','truncated block header'
        bh = int.from_bytes(b[p:p+3],'little'); p += 3
        last = bh&1; bt = (bh>>1)&3; bs = bh>>3
        if bt == 3: return 'ZST-2','reserved block type'
        if bs > bmax: return 'ZST-2', f'block size {bs} > {bmax}'
        if bt == 0:
            if p+bs > len(b): return 'ZST-2','truncated raw'
            if not any_comp and len(out)+bs > raw_length: return 'ZST-2','output over cap'
            out += b[p:p+bs]; p += bs
        elif bt == 1:
            if p+1 > len(b): return 'ZST-2','truncated rle'
            if not any_comp and len(out)+bs > raw_length: return 'ZST-2','output over cap'
            out += bytes([b[p]])*bs; p += 1
        else:
            if p+bs > len(b): return 'ZST-2','truncated compressed'
            any_comp = True; p += bs
        if last: break
    if h['cks']:
        if p+4 > len(b): return 'ZST-2','truncated checksum'
        ck = u32(b,p); p += 4
    if p != len(b): return 'ZST-2', f'trailing bytes {len(b)-p}'
    if any_comp:
        import compression.zstd as z
        try:
            d = z.ZstdDecompressor(options={z.DecompressionParameter.window_log_max:23})
            content = d.decompress(bytes(b), max_length=raw_length+1)
            if len(content) > raw_length: return 'ZST-2','output over cap (libzstd)'
            if not d.eof: return 'ZST-2','incomplete (libzstd)'
        except Exception as ex:
            return 'ZST-2', f'libzstd: {ex}'
    else:
        content = bytes(out)
    if len(content) != raw_length: return 'ZST-2', f'short output {len(content)}'
    if h['cks'] and (xxh64(content)&0xFFFFFFFF) != ck: return 'ZST-2','checksum'
    return None, content

def zstd_frame(stored, raw_length):
    """Step 11 for an encoded blob after BLB-6: header ZST-2; FCS != raw ZST-1; decode ZST-2."""
    rule, h = zstd_header(stored)
    if rule: return rule, h
    if h['fcs'] is not None and h['fcs'] != raw_length: return 'ZST-1', f"fcs {h['fcs']}"
    rule, info = zstd_decode_pass(stored, raw_length, h)
    if rule: return rule, info
    return None, (info, h)

# ---------------- path rules ----------------
DEV = {'con','prn','aux','nul','conin$','conout$'} | {f'com{i}' for i in range(10)} | {f'lpt{i}' for i in range(10)} \
      | {'com¹','com²','com³','lpt¹','lpt²','lpt³'}
def asciilower(s): return ''.join(chr(ord(c)+32) if 'A'<=c<='Z' else c for c in s)
def path_rules(pb):
    """yield rules violated by path bytes pb in the section 13 (g) order."""
    try:
        s = pb.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        yield 'PATH-1'; return
    if any(0xD800<=ord(c)<=0xDFFF for c in s): yield 'PATH-1'; return
    if unicodedata.normalize('NFC', s) != s: yield 'PATH-2'
    if s.startswith('/') or s.endswith('/') or '//' in s: yield 'PATH-4'
    segs = s.split('/')
    if not (1 <= len(pb) <= 4096) or any(not (1 <= len(g.encode()) <= 255) for g in segs): yield 'PATH-3'
    if any(g in ('.','..') for g in segs): yield 'PATH-5'
    if any(ord(c)<=0x1F or 0x7F<=ord(c)<=0x9F or 0x202A<=ord(c)<=0x202E or 0x2066<=ord(c)<=0x2069 or ord(c) in (0x061C,0x200E,0x200F) for c in s): yield 'PATH-6'
    if any(c in '\\<>:"|?*' for c in s): yield 'PATH-7'
    if any(g not in ('.','..') and g and g[-1] in '. ' for g in segs): yield 'PATH-8'
    for g in segs:
        stem = g.split('.',1)[0].rstrip(' ')
        if asciilower(stem) in DEV: yield 'PATH-9'; break
    if len(segs) > 256: yield 'PATH-10'

# ---------------- reader ----------------
class R:
    pass

def check(data, ext=True, mode='verify', limits=None, all_=False, selected=None, flg1='closure'):
    L = dict(DEFAULTS); L.update(limits or {})
    v = []; r = R(); r.data = data
    def viol(rule, stop=False):
        v.append(rule)
        if not all_ or stop: raise Stop
    try:
        n = len(data)
        if n < 88: viol('HDR-1', True)
        if data[:8] != MAGIC: viol('HDR-2', True)
        if u16(data,8) != 1: viol('HDR-3', True)
        if data[12] != 1: viol('HDR-4', True)
        tr = n-56
        if data[tr+48:tr+56] != TMAGIC: viol('TRL-1', True)
        io, il = u64(data,tr), u64(data,tr+8)
        r.io, r.il = io, il
        s = io+il+56
        if io < 32 or s >= 2**64 or s != n: viol('TRL-2', True)
        if il > 2**32: viol('LIM-2', True)
        if il > L['index']: viol('LIM-4', True)
        h = hashlib.sha256(data[:32] + data[io:io+il] + data[tr:tr+16]).digest()
        if h != data[tr+16:tr+48]: viol('TRL-3', True)
        req, opt = u64(data,16), u64(data,24)
        r.req, r.opt = req, opt
        kreq = 1 if ext else 0; kopt = 3 if ext else 0
        if req & ~kreq: viol('HDR-6', True)
        if data[13:16] != b'\0\0\0': viol('HDR-5')
        allknown = not (req & ~kreq) and not (opt & ~kopt)
        # step 9
        secs = []; p = io; end = io+il
        while p < end:
            if p+16 > end: viol('SEC-1', True)
            t, rs, rc = u32(data,p), u32(data,p+4), u64(data,p+8)
            plen = rs*rc
            if plen >= 2**64 or p+16+plen > end: viol('SEC-1', True)
            secs.append((t, rs, rc, p)); p += 16+plen
        r.secs = secs
        impl = {BLOB, ENTRY, PATH} | ({KV} if ext else set())
        for (t,rs,rc,p) in secs:
            if t not in impl and t & 0x80000000: viol('SEC-2', True)
        types = [s_[0] for s_ in secs]
        ok3 = types[:3] == [BLOB, ENTRY, PATH]
        rest = types[3:]
        if not ok3 or any(a >= b for a,b in zip(rest, rest[1:])) or any(t in (BLOB,ENTRY,PATH) for t in rest):
            viol('SEC-3', True)
        base = {BLOB:64, ENTRY:48, PATH:1, KV:1}
        sec4bad = False
        for (t,rs,rc,p) in secs:
            if t in impl:
                if (t in (PATH,KV) and rs != 1) or rs < base[t]: viol('SEC-4'); sec4bad = True
        if sec4bad: raise Stop
        if allknown:
            want = {BLOB:64, ENTRY: 64 if (ext and opt & 1) else 48, PATH:1, KV:1}
            for (t,rs,rc,p) in secs:
                if t in impl and rs != want[t]: viol('SEC-5')
        (_, brs, bc, bp), (_, ers, ec, ep), (_, _, pc, pp) = secs[0], secs[1], secs[2]
        if ec > L['entries']: viol('LIM-3', True)
        pool = data[pp+16:pp+16+pc]
        kvsec = [s_ for s_ in secs if s_[0] == KV and ext]
        # step 10
        zflag = ext and (req & 1)
        blobs = []
        for i in range(bc):
            o = bp+16+i*brs
            B = dict(key=data[o:o+32], off=u64(data,o+32), st=u64(data,o+40), raw=u64(data,o+48), enc=data[o+56], res=data[o+57:o+64], extra=data[o+64:o+brs], rec=o)
            blobs.append(B)
            if B['res'] != bytes(7): viol('BLB-1')
            if not (B['enc'] == 0 or (B['enc'] == 1 and zflag)): viol('BLB-2')
            if B['enc'] == 0 and B['st'] != B['raw']: viol('BLB-3')
            if B['enc'] == 1:
                if B['st'] < 4: viol('ZST-2')
                if not B['st'] < B['raw']: viol('ZST-3')
                if B['raw'] > L['ratio']*B['st']: viol('LIM-6')
        r.blobs = blobs
        pos = 32; bad = False
        for B in blobs:
            if B['off'] != pos: bad = True; break
            pos += B['st']
        if not bad and pos != io: bad = True
        if bad: viol('BLB-4')
        keys = [B['key'] for B in blobs]
        if len(set(keys)) != len(keys): viol('BLB-5')
        keyset = set(keys)
        ents = []
        for i in range(ec):
            o = ep+16+i*ers
            E = dict(po=u64(data,o), pl=u32(data,o+8), type=data[o+12], res=data[o+13:o+16], key=data[o+16:o+48], rec=o, rs=ers)
            ents.append(E)
            if E['type'] not in (1,2): viol('ENT-1')
            if E['res'] != b'\0\0\0': viol('ENT-2')
            if E['type'] == 1 and E['key'] != bytes(32): viol('ENT-3')
            if E['type'] == 2 and E['key'] not in keyset: viol('ENT-4')
        r.ents = ents
        e5 = False
        for E in ents:
            if E['po']+E['pl'] > pc: viol('ENT-5'); e5 = True
        if e5: raise Stop
        acc = 0; c3 = False
        for E in ents:
            if E['po'] != acc: c3 = True
            acc += E['pl']
        if acc != pc: c3 = True
        if c3: viol('CAN-3')
        paths = [bytes(pool[E['po']:E['po']+E['pl']]) for E in ents]
        r.paths = paths
        for pb in paths:
            for rule in path_rules(pb):
                viol(rule)
        if any(a >= b for a,b in zip(paths, paths[1:])): viol('CAN-1')
        dirs = {pb for pb,E in zip(paths,ents) if E['type']==1}
        for pb in paths:
            if b'/' in pb and pb.rsplit(b'/',1)[0] not in dirs: viol('ENT-6')
        folds = [bytes(c+32 if 65<=c<=90 else c for c in pb) for pb in paths]
        if len(set(folds)) != len(folds): viol('PATH-11')
        refd = []
        for E in ents:
            if E['type']==2 and E['key'] not in refd: refd.append(E['key'])
        if any(k not in refd for k in keys): viol('BLB-7')
        if keys[:len(refd)] != refd: viol('CAN-2')
        if ext:
            if bool(req & 1) != any(B['enc']==1 for B in blobs): viol('FLG-1')
            elif bool(opt & 1) and ers < 64: viol('FLG-1')   # FLG-1 one-way (M4)
            elif bool(opt & 2) != bool(kvsec): viol('FLG-1')
        attrs = ext and (opt & 1) and ers >= 64
        if attrs:
            for E in ents:
                o = E['rec']
                if u32(data,o+56) >= 10**9 or u16(data,o+60) > 0o777 or data[o+62:o+64] != b'\0\0': viol('ATT-1')
        if kvsec:
            (_, _, kc, kp) = kvsec[0]
            kvp = data[kp+16:kp+16+kc]
            if not kv_ok(kvp): viol('KV-1')
        bykey = {B['key']: B for B in blobs}
        total = sum(bykey[E['key']]['raw'] for i,E in enumerate(ents) if E['type']==2 and (selected is None or i in selected))
        if mode in ('verify','extract') and total > L['total']: viol('LIM-5')
        if mode in ('verify','extract'):
            selkeys = None if selected is None else {E['key'] for i,E in enumerate(ents) if E['type']==2 and i in selected}
            for B in blobs:
                if selkeys is not None and B['key'] not in selkeys: continue
                st = data[B['off']:B['off']+B['st']]
                if hashlib.sha256(st).digest() != B['key']: viol('BLB-6'); continue
                if B['enc'] == 1:
                    rule, info = zstd_frame(st, B['raw'])
                    if rule: viol(rule)
    except Stop:
        pass
    except Exception as ex:
        if not all_: raise
        v.append('(stopped:'+type(ex).__name__+')') if False else None
    r.v = v
    return r

def kv_ok(p):
    if len(p) == 0: return False
    i = 0; prev = None
    while i < len(p):
        if i+2 > len(p): return False
        kl = u16(p,i); i += 2
        if not (1 <= kl <= 255) or i+kl > len(p): return False
        k = p[i:i+kl]; i += kl
        if i+4 > len(p): return False
        vl = u32(p,i); i += 4
        if vl > 65536 or i+vl > len(p): return False
        val = p[i:i+vl]; i += vl
        try: k.decode('utf-8'); val.decode('utf-8')
        except UnicodeDecodeError: return False
        if prev is not None and not prev < k: return False
        prev = k
    return True

# ---------------- reports ----------------
def J(x): return x if -(2**53-1) <= x <= 2**53-1 else str(x)

def flagnames(bits, kind, ext):
    names = []
    for i in range(64):
        if bits >> i & 1:
            if ext and kind == 'req' and i == 0: names.append('ZSTD')
            elif ext and kind == 'opt' and i == 0: names.append('ENTRY_ATTRS')
            elif ext and kind == 'opt' and i == 1: names.append('KV_METADATA')
            else: names.append(f'bit{i}')
    return names

def base_report(cmd): return {"schema":"chst-report/1","command":cmd,"ok":True,"error":None,"warnings":[]}

def list_report(r, ext):
    rep = base_report('list'); out = []
    bykey = {B['key']:B for B in r.blobs}
    attrs = ext and (r.opt & 1) and r.ents and r.ents[0]['rs'] >= 64
    for pb,E in zip(r.paths, r.ents):
        e = {"path": pb.decode(), "type": "dir" if E['type']==1 else "file"}
        if E['type']==2:
            B = bykey[E['key']]
            e.update(size=J(B['raw']), stored_size=J(B['st']), encoding="stored" if B['enc']==0 else "zstd", blob=B['key'].hex())
        if attrs:
            o = E['rec']; e.update(mtime_seconds=J(i64(r.data,o+48)), mtime_nanos=u32(r.data,o+56), mode=u16(r.data,o+60))
        out.append(e)
    rep['entries'] = out; return rep

def summary(r, ext):
    files = [E for E in r.ents if E['type']==2]
    bykey = {B['key']:B for B in r.blobs}
    return {"entries": len(r.ents), "files": len(files), "directories": len(r.ents)-len(files), "blobs": len(r.blobs),
            "stored_bytes": J(sum(B['st'] for B in r.blobs)), "raw_bytes": J(sum(B['raw'] for B in r.blobs)),
            "extracted_bytes": J(sum(bykey[E['key']]['raw'] for E in files)),
            "required_flags": flagnames(r.req,'req',ext), "optional_flags": flagnames(r.opt,'opt',ext)}

def verify_report(r, ext):
    rep = base_report('verify'); rep['summary'] = summary(r, ext); return rep

def F(name, off, ln, kind, data):
    f = {"name": name, "offset": off, "length": ln}
    b = data[off:off+ln]
    if kind == 'int': f['value'] = J(int.from_bytes(b,'little'))
    elif kind == 'sint': f['value'] = J(int.from_bytes(b,'little',signed=True))
    elif kind == 'hex': f['value'] = b.hex()
    elif kind == 'text': f['value'] = b.decode()
    return f

def inspect_report(r, ext):
    d = r.data; rep = base_report('inspect'); n = len(d)
    rep['file_length'] = n
    rep['header'] = {"offset":0,"length":32,"fields":[F('magic',0,8,'hex',d),F('major_version',8,2,'int',d),F('minor_version',10,2,'int',d),
        F('hash_alg',12,1,'int',d),F('reserved',13,3,'hex',d),F('required_flags',16,8,'int',d),F('optional_flags',24,8,'int',d)]}
    rep['data'] = {"offset":32,"length":J(r.io-32),"fields":[{"name":f"blob[{i}].data","offset":J(B['off']),"length":J(B['st'])} for i,B in enumerate(r.blobs)]}
    impl = {BLOB:'BLOB_TABLE', ENTRY:'ENTRY_TABLE', PATH:'PATH_POOL'}
    if ext: impl[KV] = 'KV_METADATA'
    secs = []
    attrs = ext and (r.opt & 1)
    for (t,rs,rc,p) in r.secs:
        name = impl.get(t, 'unknown')
        S = {"type": f"0x{t:08x}", "name": name, "offset": p, "length": J(16+rs*rc), "record_size": rs, "record_count": J(rc),
             "fields": [F('type',p,4,'int',d),F('record_size',p+4,4,'int',d),F('record_count',p+8,8,'int',d)], "records": []}
        if name == 'BLOB_TABLE':
            for i in range(rc):
                o = p+16+i*rs
                fl = [F('key',o,32,'hex',d),F('offset',o+32,8,'int',d),F('stored_length',o+40,8,'int',d),F('raw_length',o+48,8,'int',d),F('encoding',o+56,1,'int',d),F('reserved',o+57,7,'hex',d)]
                if rs > 64: fl.append(F('extra',o+64,rs-64,'hex',d))
                S['records'].append({"index":i,"offset":o,"length":rs,"fields":fl})
        elif name == 'ENTRY_TABLE':
            for i in range(rc):
                o = p+16+i*rs
                fl = [F('path_offset',o,8,'int',d),F('path_length',o+8,4,'int',d),F('type',o+12,1,'int',d),F('reserved',o+13,3,'hex',d),F('blob_key',o+16,32,'hex',d)]
                if attrs and rs >= 64:
                    fl += [F('mtime_seconds',o+48,8,'sint',d),F('mtime_nanos',o+56,4,'int',d),F('mode',o+60,2,'int',d),F('attrs_reserved',o+62,2,'hex',d)]
                    if rs > 64: fl.append(F('extra',o+64,rs-64,'hex',d))
                elif rs > 48: fl.append(F('extra',o+48,rs-48,'hex',d))
                S['records'].append({"index":i,"offset":o,"length":rs,"fields":fl})
        else:
            if rs*rc:
                S['fields'].append(F('payload',p+16,rs*rc,'text' if name=='PATH_POOL' else 'hex',d))
        secs.append(S)
    rep['sections'] = secs
    tr = n-56
    rep['trailer'] = {"offset":tr,"length":56,"fields":[F('index_offset',tr,8,'int',d),F('index_length',tr+8,8,'int',d),F('structure_hash',tr+16,32,'hex',d),F('trailer_magic',tr+48,8,'hex',d)]}
    return rep

def first(r):
    if not r.v: return None
    x = r.v[0]; return (x, CAT[x], DET[x], EXIT[CAT[x]])
