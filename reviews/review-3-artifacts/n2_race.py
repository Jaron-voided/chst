"""Spec-literal EXT-4 extractor skeleton (Linux) with a parent-writer race between
'create staging' and 'open staging with no-follow'. Everything runs in a fresh temp dir."""
import os, stat, secrets, tempfile, shutil, sys
ND = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
def cleanup_via_handle(dfd):
    """EXT-4 cleanup: handle-relative, never follows links, restores owner rwx with fchmod first (N17)."""
    os.fchmod(dfd, 0o700)
    for name in os.listdir(dfd):
        st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
        if stat.S_ISDIR(st.st_mode):
            c = os.open(name, ND, dir_fd=dfd); cleanup_via_handle(c); os.close(c)
            os.rmdir(name, dir_fd=dfd)
        else:
            os.unlink(name, dir_fd=dfd)
def extract(entries, dest, hook=lambda *a: None):
    parent, name = os.path.split(dest)
    pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.stat(name, dir_fd=pfd, follow_symlinks=False); return 'refused/extract.dest-exists'
    except FileNotFoundError: pass
    sname = f'.{name}.chst-{secrets.token_hex(16)}'
    os.mkdir(sname, 0o700, dir_fd=pfd)                       # "create-new semantics", mode 0700
    hook('after-create', parent, sname)                       # <-- the race window
    sfd = os.open(sname, ND, dir_fd=pfd)                      # "right after creating it, opens it no-follow"
    st = os.fstat(sfd); ident = (st.st_dev, st.st_ino)        # "records its identity"
    try:
        for p, content in entries:                            # EXT-2 create-new, EXT-8 handle-relative
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=sfd)
            os.write(fd, content); os.close(fd)
    except FileExistsError:
        cleanup_via_handle(sfd)                               # cleanup through the handle
        return 'refused/extract.collision (cleanup ran through the staging handle)'
    os.fchmod(sfd, 0o755 & ~0o022)                            # final permissions via handle
    s2 = os.stat(sname, dir_fd=pfd, follow_symlinks=False)    # identity check before the rename
    if (s2.st_dev, s2.st_ino) != ident: return 'refused/extract.unsafe-object'
    os.rename(sname, name, src_dir_fd=pfd, dst_dir_fd=pfd)    # (stands in for renameat2 NOREPLACE)
    s3 = os.stat(name, dir_fd=pfd, follow_symlinks=False)
    if (s3.st_dev, s3.st_ino) != ident: return 'refused/extract.unsafe-object'
    return 'ok'
T = tempfile.mkdtemp(prefix='n2race-', dir=os.path.dirname(os.path.abspath(__file__)))
try:
    par = os.path.join(T, 'shared-parent'); os.mkdir(par)
    # A "victim" tree that sits outside staging, in a place the parent-writer can rename from.
    os.makedirs(os.path.join(par, 'victim', 'sub')); open(os.path.join(par, 'victim', 'sub', 'precious.txt'), 'w').write('data')
    def attacker(ev, parent, sname):
        os.rename(os.path.join(parent, sname), os.path.join(parent, 'real-staging-moved-away'))
        os.mkdir(os.path.join(parent, sname), 0o777)                       # attacker's own directory
        os.rename(os.path.join(parent, 'victim'), os.path.join(parent, sname, 'victim'))
        open(os.path.join(parent, sname, 'f0'), 'w').close()               # forces EXT-2 -> cleanup
    print('case 1 (forced error -> cleanup):', extract([('f0', b'x')], os.path.join(par, 'out'), attacker))
    print('   victim/sub/precious.txt still exists?', any('precious.txt' in fs for _, _, fs in os.walk(par)))
    print('   left in parent:', sorted(os.listdir(par)))
    shutil.rmtree(par); os.mkdir(par)
    def attacker2(ev, parent, sname):
        os.rename(os.path.join(parent, sname), os.path.join(parent, 'real-staging-moved-away'))
        os.mkdir(os.path.join(parent, sname), 0o777)
    print('case 2 (no error):', extract([('f1', b'x')], os.path.join(par, 'out'), attacker2))
    print('   destination mode', oct(os.stat(os.path.join(par, 'out')).st_mode & 0o777), '- it is the attacker\'s directory; identity checks passed')
finally:
    shutil.rmtree(T)
