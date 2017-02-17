# coding: utf-8
from __future__ import unicode_literals

from base import ConfigTest
from unittest import TestCase
from nexup import config
import os

class TestConfigLoad(ConfigTest):

    def create(self, path, content):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        fpath = os.path.join(self.tempdir, path)
        if not os.path.exists(os.path.dirname(fpath)):
            os.makedirs(os.path.dirname(fpath))

        with open(fpath, 'w') as f:
            f.write(content)

        return fpath

    def test_minimal_from_default(self):
        yaml="""
            test:
                url: http://nowhere.com/nexus
            """
        rc = self.create('.config/nexup/config.yaml', yaml)
        nxconfig = config.load('test')
        print nxconfig.url

class TestOracleEval(TestCase):

    def test_echo(self):
        self.assertEqual(config.oracle_eval("echo fööbår"), "fööbår")
