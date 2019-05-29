from __future__ import print_function

import rcm_nexus
import traceback
import os
import tempfile
import shutil
import unittest
import yaml
from rcm_nexus import config
import zipfile
from random import randint


WORDS = ['/usr/share/dict/words', '/usr/dict/words']

TEST_BASEURL='http://localhost:8080/nexus'
TEST_INPUT_DIR='test-input'

class NexupBaseTest(unittest.TestCase):
    """
    Creates config files, configures the environment, and cleans up afterwards.
    """
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='rcm-nexus')

        # Create temporary config files.
        self.taskrc = os.path.join(self.tempdir, '.taskrc')
        self.lists_path = os.path.join(self.tempdir, 'lists')
        os.mkdir(self.lists_path)
        with open(self.taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % self.lists_path)

        # Configure environment.
        os.environ['HOME'] = self.tempdir
        os.environ.pop(config.RCM_NEXUS_YAML, None)
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ.pop('XDG_CONFIG_DIRS', None)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.environ = self.old_environ

    def load_words(self):
        self.words = []
        for w in WORDS:
            if os.path.exists(w):
                with open(w) as f:
                    self.words.extend([line.rstrip() for line in f.readlines()])

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

    def write_config(self, conf, profile_data={}):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        path = '.config/rcm-nexus/config.yaml'
        fpath = os.path.join(self.tempdir, path)
        if not os.path.exists(os.path.dirname(fpath)):
            os.makedirs(os.path.dirname(fpath))

        with open(fpath, 'w') as f:
            yml = yaml.safe_dump(conf)
            #print("""Writing config to: %s)
            #
            #%s
            #""" % (fpath, yml)

            f.write(yml)

        fdir = os.path.dirname(fpath)
        for e in profile_data.keys():
            profile_mappings = os.path.join(fdir, "%s.yaml" % e)
            print("Writing profile-mapping YAML: %s" % profile_mappings)
            with open(profile_mappings, 'w') as f:
                yml = yaml.safe_dump(profile_data[e])
                f.write(yml)

        return fpath

    def create_and_load_conf(self, conf={'test':{rcm_nexus.config.URL: TEST_BASEURL}}, profile_data={}):
        fpath = self.write_config(conf, profile_data)
        return rcm_nexus.config.load('test')


