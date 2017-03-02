from nexup import archive
from base import NexupBaseTest
import tempfile
import os
from random import randint
import zipfile

class ArchiveZipest(NexupBaseTest):

	def test_small(self):
		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')

		self.write_zip(src_zip, paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_zip(src_zip, outdir)
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

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')
		
		self.write_zip(src_zip, maven_paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_zip(src_zip, outdir)
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

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')
		
		self.write_zip(src_zip, paths)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_zip(src_zip, outdir, max_count=2)
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

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')
		
		self.write_zip(src_zip, paths, content=src)

		outdir = tempfile.mkdtemp()
		zips = archive.create_partitioned_zips_from_zip(src_zip, outdir, max_size=2*len(src) + 1)
		self.assertEqual(len(zips), 2)
		print zips

		for z in zips:
			zf = zipfile.ZipFile(z)
			for info in zf.infolist():
				print "%s contains: %s" % (z, info.filename)
				self.assertEqual(info.filename in paths, True)
