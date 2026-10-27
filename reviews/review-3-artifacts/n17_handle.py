"""N17 residual: a non-root process can't get an fchmod-capable handle on a mode-000 directory."""
import os, tempfile, shutil
T = tempfile.mkdtemp(prefix='n17-', dir=os.path.dirname(os.path.abspath(__file__)))
try:
    s = os.open(T, os.O_RDONLY | os.O_DIRECTORY); os.mkdir(os.path.join(T, 'd')); os.chmod(os.path.join(T, 'd'), 0)
    for nm, fl in [('O_RDONLY|O_DIRECTORY|O_NOFOLLOW', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW),
                   ('O_PATH|O_DIRECTORY|O_NOFOLLOW', os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW)]:
        try:
            fd = os.open('d', fl, dir_fd=s)
            try: os.fchmod(fd, 0o700); print(nm, ': fchmod ok')
            except OSError as e: print(nm, ': open ok, fchmod fails:', e)
        except OSError as e: print(nm, ': open fails:', e)
    os.chmod('d', 0o700, dir_fd=s, follow_symlinks=False); print('fchmodat(parent, "d", AT_SYMLINK_NOFOLLOW): ok')
finally:
    os.chmod(os.path.join(T, 'd'), 0o700); shutil.rmtree(T)
