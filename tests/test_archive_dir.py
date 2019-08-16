from __future__ import print_function

from rcm_nexus import archive
from .base import NexupBaseTest
import tempfile
import zipfile


class ArchiveZipest(NexupBaseTest):
    def test_small(self):
        self.load_words()

        paths = ["path/one.txt", "path/to/two.txt", "path/to/stuff/three.txt"]

        srcdir = tempfile.mkdtemp()
        self.write_dir(srcdir, paths)

        outdir = tempfile.mkdtemp()
        zips = archive.create_partitioned_zips_from_dir(srcdir, outdir)
        self.assertEqual(len(zips), 1)

        self.assertEqual(
            sorted(info.filename for info in zipfile.ZipFile(zips[0]).infolist()),
            sorted(paths),
        )

    def test_count_rollover(self):
        self.load_words()

        paths = ["path/one.txt", "path/to/two.txt", "path/to/stuff/three.txt"]

        srcdir = tempfile.mkdtemp()
        self.write_dir(srcdir, paths)

        outdir = tempfile.mkdtemp()
        zips = archive.create_partitioned_zips_from_dir(srcdir, outdir, max_count=2)
        self.assertEqual(len(zips), 2)

        self.assertEqual(
            sorted(info.filename for info in zipfile.ZipFile(zips[0]).infolist()),
            paths[:2],
        )
        self.assertEqual(
            sorted(info.filename for info in zipfile.ZipFile(zips[1]).infolist()),
            paths[2:],
        )

    def test_size_rollover(self):
        self.load_words()

        paths = ["path/one.txt", "path/to/two.txt", "path/to/stuff/three.txt"]
        src = "This is a test of the system"

        srcdir = tempfile.mkdtemp()
        self.write_dir(srcdir, paths, content=src)

        outdir = tempfile.mkdtemp()
        zips = archive.create_partitioned_zips_from_dir(
            srcdir, outdir, max_size=2 * len(src) + 1
        )
        self.assertEqual(len(zips), 2)

        self.assertEqual(
            sorted(info.filename for info in zipfile.ZipFile(zips[0]).infolist()),
            paths[:2],
        )
        self.assertEqual(
            sorted(info.filename for info in zipfile.ZipFile(zips[1]).infolist()),
            paths[2:],
        )
