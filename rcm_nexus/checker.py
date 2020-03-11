from __future__ import print_function

import hashlib
import sys
import zipfile

from . import archive
from .session import FileNotFoundError


def _print(msg):
    """Print value to stdout if it is attached to a TTY."""
    if sys.stdout.isatty():
        sys.stdout.write(msg)
        sys.stdout.flush()


def _print_progress(iterable, total_size):
    """This is a wrapper for iterating over dict of file records. It prints
    progress both in terms of files processed as well as total file size
    processed.
    """
    width = 60
    processed = 0
    num_files = len(iterable)
    num_len = len(str(num_files))
    num = 0
    for x in iterable:
        num += 1
        processed += iterable[x]["size"]

        perc = int(width * processed / total_size)
        hashes = "#" * perc
        gap = " " * (width - perc)

        consumed_perc = 100 * processed / total_size
        _print(
            "\r  {3:{5}d} / {4} {0:3.0f} % [{1}{2}]\r".format(
                consumed_perc, hashes, gap, num, num_files, num_len
            )
        )
        yield x
    # Make sure the progress bar doesn't overflow into next prompt.
    _print("\n")


def check_zip_file(session, base_url, zip_file):
    """Check each file in the zip file.
    1. The corresponding file in published repo must have the same checksum (or
    not exist yet)
    2. The MD5 and SHA1 checksums in the zip file must both be correct (or both
    missing).
    """
    all_ok = True
    zf = zipfile.ZipFile(zip_file)
    files = {}
    total_size = 0
    for target, size, source in archive.iterate_zip_content(zf):
        files[source] = {"target": target, "size": size}
        total_size += size

    for file_ in _print_progress(files, total_size):
        if file_.endswith(".md5") or file_.endswith(".sha1"):
            continue

        content = zf.read(file_)
        md5 = hashlib.md5()
        md5.update(content)
        sha1 = hashlib.sha1()
        sha1.update(content)

        try:
            remote_md5 = hashlib.md5()
            remote_sha1 = hashlib.sha1()
            url = base_url + files[file_]["target"]
            for chunk in session.stream_remote(url):
                remote_md5.update(chunk)
                remote_sha1.update(chunk)

            md5_correct = md5.digest() == remote_md5.digest()
            sha1_correct = sha1.digest() == remote_sha1.digest()
            if not (md5_correct and sha1_correct):
                print(
                    "File %s already uploaded with different checksum" % file_,
                    file=sys.stderr,
                )
                all_ok = False
        except FileNotFoundError:
            pass

        md5_file = file_ + ".md5"
        sha1_file = file_ + ".sha1"
        if (md5_file in files) != (sha1_file in files):
            print("\rIncomplete checksums for %s" % file_, file=sys.stderr)
            all_ok = False
        if md5_file in files and zf.read(md5_file) != md5.hexdigest().encode():
            print("\rMD5 mismatch: %s" % file_, file=sys.stderr)
            all_ok = False
        if sha1_file in files and zf.read(sha1_file) != sha1.hexdigest().encode():
            print("\rSHA1 mismatch: %s" % file_, file=sys.stderr)
            all_ok = False

    return all_ok
