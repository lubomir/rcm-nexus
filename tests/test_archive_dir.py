from base import NexupBaseTest
import archive
import tempfile
import os
from random import randint
import zipfile

class ArchiveTest(NexupBaseTest):

	def write_dir(self, srcdir, paths, content=None):
		for fname in paths:
			path = os.path.join(srcdir, fname)
			os.makedirs(os.path.dirname(path))
			with open(path, 'w') as f:
				if content is None:
					for i in range(randint(1,10)):
						f.write(self.words[randint(1,len(self.words))])
						f.write(' ')
				else:
					f.write(content)

	def test_small(self):
		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']

		srcdir = tempfile.mkdtemp()
		self.write_dir(srcdir, paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_dir(srcdir, outdir)
		self.assertEqual(len(zips), 1)

		print zips

		z = zips[0]
		zf = zipfile.ZipFile(z)
		for info in zf.infolist():
			print "%s contains: %s" % (z, info.filename)
			self.assertEqual(info.filename in paths, True)


	def test_trim_maven_dir(self):
		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']
		maven_paths = ["maven-repository/%s" % path for path in paths]

		srcdir = tempfile.mkdtemp()
		self.write_dir(srcdir, maven_paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_dir(srcdir, outdir)
		self.assertEqual(len(zips), 1)

		print zips

		z = zips[0]
		zf = zipfile.ZipFile(z)
		for info in zf.infolist():
			print "%s contains: %s" % (z, info.filename)
			self.assertEqual(info.filename in paths, True)


	def test_count_rollover(self):
		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']

		srcdir = tempfile.mkdtemp()
		self.write_dir(srcdir, paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_dir(srcdir, outdir, max_count=2)
		self.assertEqual(len(zips), 2)
		print zips

		for z in zips:
			zf = zipfile.ZipFile(z)
			for info in zf.infolist():
				print "%s contains: %s" % (z, info.filename)
				self.assertEqual(info.filename in paths, True)

	def test_size_rollover(self):
		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']
		src = "This is a test of the system"

		srcdir = tempfile.mkdtemp()
		self.write_dir(srcdir, paths, content=src)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_dir(srcdir, outdir, max_size=2*len(src) + 1)
		self.assertEqual(len(zips), 2)
		print zips

		for z in zips:
			zf = zipfile.ZipFile(z)
			for info in zf.infolist():
				print "%s contains: %s" % (z, info.filename)
				self.assertEqual(info.filename in paths, True)
