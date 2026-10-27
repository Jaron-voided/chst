"""P2: EXT-4 'Holding it' requires fstat to show 'permission bits exactly 0700'.
mkdirat(0700) does not give st_mode & 0o7777 == 0o700 in a setgid parent (Linux inherits S_ISGID on
directories), nor under a umask that masks owner bits. Two readings of 'permission bits'
(& 0o777, POSIX's definition, vs & 0o7777, all of S_IMODE) then disagree: success vs refused/extract.unsafe-object."""
import os, stat, tempfile
here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(dir=here, prefix='p2-')
def staging_mode(parent, umask):
    old = os.umask(umask)
    try:
        pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        os.mkdir('.out.chst-' + '0'*32, 0o700, dir_fd=pfd)
        fd = os.open('.out.chst-' + '0'*32, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=pfd)
        m = os.fstat(fd).st_mode; os.close(fd); os.rmdir('.out.chst-' + '0'*32, dir_fd=pfd); os.close(pfd)
        return m
    finally: os.umask(old)
plain = os.path.join(root, 'plain'); os.mkdir(plain)
sgid = os.path.join(root, 'sgid'); os.mkdir(sgid); os.chmod(sgid, 0o2775)
for label, parent, um in [('ordinary parent, umask 022', plain, 0o022), ('setgid parent (g+s), umask 022', sgid, 0o022),
                          ('ordinary parent, umask 0277', plain, 0o277)]:
    m = staging_mode(parent, um)
    print(f'{label:34s}: st_mode&0o7777={oct(stat.S_IMODE(m)):7s} '
          f'check(&0o777==0o700)={"pass" if m & 0o777 == 0o700 else "FAIL -> refused"}  '
          f'check(&0o7777==0o700)={"pass" if stat.S_IMODE(m) == 0o700 else "FAIL -> refused"}')
os.system(f'rm -rf "{root}"')
