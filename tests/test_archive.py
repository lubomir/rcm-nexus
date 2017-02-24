from base import NexupBaseTest
import zipfile
import os
from random import randint

class ArchiveBaseTest(NexupBaseTest):

	def write_zip(self, src_zip, paths, content=None):
		zf = zipfile.ZipFile(src_zip, mode='w')
		for path in paths:
			if content is None:
				content = ''
				for i in range(randint(1,10)):
					content += self.words[randint(1,len(self.words))]
					content += ' '
			zf.writestr(path, content)
		zf.close()

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

