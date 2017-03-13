import zipfile
import os


MAX_COUNT = 1000
MAX_SIZE = 1000000000 #1GB
OUT_ZIP_FORMAT = "part-%03d.zip"

def create_partitioned_zips(src, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE):
    if os.path.isdir(src) is True:
        return create_partitioned_zips_from_dir(src, out_dir, max_count, max_size)
    elif src.endswith('.zip') and os.path.exists(src):
        return create_partitioned_zips_from_zip(src, out_dir, max_count, max_size)
    else:
        raise Exception("Invalid input: %s" % src)

def create_partitioned_zips_from_dir(src, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE):
    zips = Zipper(out_dir, max_count, max_size)

    for (dirpath, dirnames, filenames) in os.walk(src):
        dir_skip = len(src)
        dirname = dirpath[dir_skip:]
        if dirname.startswith('/'):
            dirname = dirname[1:]

        for filename in filenames:
            path = os.path.join(dirpath, filename)
            entry_name = os.path.join(dirname, filename)
            # print "Path: %s (uncompressed size: %s)" % (os.path.join(dirname, filename), os.path.getsize(path))
            with open(path, 'rb') as f:
                zips.append(entry_name, os.path.getsize(path), lambda: f.read())

    return zips.list()

def create_partitioned_zips_from_zip(src, out_dir, max_count=MAX_COUNT, max_size=MAX_SIZE):
    zips = Zipper(out_dir, max_count, max_size)
    zf = zipfile.ZipFile(src)
    for info in zf.infolist():

        # print "Path: %s (uncompressed size: %s)" % (info.filename, info.file_size)
        zips.append(info.filename, info.file_size, lambda: zf.read(info.filename) )

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

    def append(self, filename, size, stream_func):
        if self.zip is None or self.file_count >= self.max_count or self.file_size + size >= self.max_size:
            if self.zip is not None:
                self.zip.close()
                self.counter+=1

            self.zip = zipfile.ZipFile(os.path.join(self.out_dir, OUT_ZIP_FORMAT % self.counter), mode='w')

        if '/' in filename:
            filename_parts = filename.split('/')

            if 'maven' in filename_parts[0]:
                if len(filename_parts) > 1:
                    filename = '/'.join(filename_parts[1:])
                else:
                    filename = ''

        self.zip.writestr(filename, stream_func())
        self.file_count+=1
        self.file_size+=size

    def close(self):
        if self.zip is not None:
            self.zip.close()

    def list(self):
        return sorted([os.path.join(self.out_dir, fname) for fname in os.listdir(self.out_dir)])



