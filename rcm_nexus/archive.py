from __future__ import print_function

import zipfile
import os


MAX_COUNT = 1000
MAX_SIZE = 10 ** 9  # 1GB
OUT_ZIP_FORMAT = "part-%03d.zip"


def create_partitioned_zips_from_dir(
    src, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE
):
    """
    Given directory, create a set of zips that contain all files in there. No
    filtering is done here.
    """
    zips = Zipper(out_dir, max_count, max_size)

    for (dirpath, dirnames, filenames) in os.walk(src):
        dir_skip = len(src)
        dirname = dirpath[dir_skip:]
        if dirname.startswith("/"):
            dirname = dirname[1:]

        for filename in filenames:
            path = os.path.join(dirpath, filename)
            entry_name = os.path.join(dirname, filename)
            with open(path, "rb") as f:
                zips.append(entry_name, os.path.getsize(path), lambda: f.read())

    return zips.list()


def create_partitioned_zips_from_zip(
    src, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE
):
    """
    Given a zip archive, split it into smaller chunks and possibly filter out
    only some parts.

    The general structure is like this (given foo-1.0.0-maven-repository.zip):

    foo-1.0-maven-repository/
    foo-1.0-maven-repository/examples/
    foo-1.0-maven-repository/maven-repository/...
    foo-1.0-maven-repository/licenses/
    foo-1.0-maven-repository/example-config.xml

    This function will look for a maven-subdirectory inside the top-level
    directory and only repackage its contents. If there is no such
    subdirectory, all content will be taken without any changes.
    The top-level directory name does not matter at all.
    """
    zips = Zipper(out_dir, max_count, max_size)
    zf = zipfile.ZipFile(src)
    repodir = None

    zip_objects = zf.infolist()

    # Find if there is a maven-repository subdir under top-level directory.
    for info in zip_objects:
        parts = info.filename.split("/")
        if len(parts) < 3:
            # Not a subdirectory of top-level dir or a file in there.
            continue
        if parts[1] == "maven-repository":
            repodir = os.path.join(*parts[:2]) + "/"
            break

    # Iterate over all objects in the directory.
    for info in zip_objects:
        if info.filename.endswith("/") and info.file_size == 0:
            # Skip directories for this iteration.
            continue

        filename = info.filename
        # We found maven-repository subdirectory previously, only content from
        # there should be taken.
        if repodir:
            if filename.startswith(repodir):
                # It's in correct location, move to top-level.
                filename = filename[len(repodir):]
            else:
                # Not correct location, ignore it.
                continue

        zips.append(filename, info.file_size, lambda: zf.read(info.filename))

    return zips.list()


class Zipper(object):
    def __init__(self, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE):
        self.out_dir = out_dir
        self.max_count = max_count
        self.max_size = max_size
        self.file_count = 0
        self.file_size = 0
        self.counter = 0
        self.zip = None

    def should_rollover(self, size):
        return (
            self.zip is None  # No zip created yet
            or self.file_count >= self.max_count  # Maximum file count reached
            or self.file_size + size >= self.max_size  # Maximum size reached
        )

    def rollover(self):
        if self.zip is not None:
            self.zip.close()
            self.counter += 1
            self.file_count = 0
            self.file_size = 0

        self.zip = zipfile.ZipFile(
            os.path.join(self.out_dir, OUT_ZIP_FORMAT % self.counter), mode="w"
        )

    def append(self, filename, size, stream_func):
        if self.should_rollover(size):
            self.rollover()

        self.zip.writestr(filename, stream_func())
        self.file_count += 1
        self.file_size += size

    def close(self):
        if self.zip is not None:
            self.zip.close()

    def list(self):
        return sorted(
            os.path.join(self.out_dir, fname) for fname in os.listdir(self.out_dir)
        )
