from __future__ import print_function

import rcm_nexus
import os
import tempfile
import shutil
import unittest
from rcm_nexus import config
import zipfile
import random

from six.moves import configparser


WORDS = ['/usr/share/dict/words', '/usr/dict/words']

TEST_BASEURL='http://localhost:8080/nexus'
TEST_INPUT_DIR='test-input'

TEST_CONFIG = {
    'test': {
        rcm_nexus.config.URL: TEST_BASEURL,
        rcm_nexus.config.USERNAME: "jdoe",
        rcm_nexus.config.PASSWORD: "password",
    }
}


class NexupBaseTest(unittest.TestCase):
    """
    Creates config files, configures the environment, and cleans up afterwards.
    """
    def setUp(self):
        self.old_environ = os.environ.copy()
        self.tempdir = tempfile.mkdtemp(prefix='rcm-nexus')

        # Configure environment.
        os.environ['HOME'] = self.tempdir
        os.environ.pop(config.RCM_NEXUS_CONFIG, None)
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ['XDG_CONFIG_DIRS'] = os.path.join(self.tempdir, "xdg")

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
                content = " ".join(random.sample(self.words, 10))
            zf.writestr(path, content)
        zf.close()

    def write_dir(self, srcdir, paths, content=None):
        for fname in paths:
            path = os.path.join(srcdir, fname)
            os.makedirs(os.path.dirname(path))
            with open(path, 'w') as f:
                if content is None:
                    f.write(" ".join(random.sample(self.words, 10)))
                else:
                    f.write(content)

    def write_config(self, conf, profile_data={}):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        path = ".config/rcm-nexus.conf"
        fpath = os.path.join(self.tempdir, path)
        fdir = os.path.dirname(fpath)
        profile_mappings = os.path.join(fdir, "environments.conf")
        if not os.path.exists(os.path.dirname(fpath)):
            os.makedirs(os.path.dirname(fpath))

        parser = configparser.RawConfigParser()
        parser.add_section(config.SECTION)
        parser.set(config.SECTION, config.CONFIG_REPO, profile_mappings)
        parser.set(config.SECTION, config.WRITE_CONFIG_REPO, profile_mappings)
        parser.set(config.SECTION, config.TARGET_GROUPS_GA, "tgt-grp-ga")
        parser.set(config.SECTION, config.TARGET_GROUPS_EA, "tgt-grp-ea")
        parser.set(config.SECTION, config.PROMOTE_RULESET_GA, "promote-rules-ga")
        parser.set(config.SECTION, config.PROMOTE_RULESET_EA, "promote-rules-ea")
        parser.set(config.SECTION, config.PROMOTE_TARGET_GA, "promote-tgt-ga")
        parser.set(config.SECTION, config.PROMOTE_TARGET_EA, "promote-tgt-ea")
        parser.set(config.SECTION, config.DEPLOYER_ROLE, "deployer-role")
        for env in conf:
            parser.add_section(env)
            for key, value in conf[env].items():
                parser.set(env, key, value)

        with open(fpath, 'w') as f:
            parser.write(f)

        parser = configparser.RawConfigParser()
        for e in profile_data:
            parser.add_section(e)
            for key, value in profile_data[e].items():
                parser.set(e, key, value)
        with open(profile_mappings, "w") as f:
            parser.write(f)

        return fpath

    def create_and_load_conf(self, conf=TEST_CONFIG, profile_data={}):
        fpath = self.write_config(conf, profile_data)
        return rcm_nexus.config.load('test')
