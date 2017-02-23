# coding: utf-8
from __future__ import unicode_literals

from base import ConfigTest
from unittest import TestCase
from nexup import config
import os
import yaml

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
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.url, url)

    def test_preemptive_auth(self):
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url,
                config.PREEMPTIVE_AUTH: True,
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.url, url)
        self.assertEqual(nxconfig.preemptive_auth, True)

    def test_interactive(self):
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url,
                config.INTERACTIVE: True,
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.url, url)
        self.assertEqual(nxconfig.interactive, True)

    def test_ssl_verify(self):
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url,
                config.SSL_VERIFY: True,
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.url, url)
        self.assertEqual(nxconfig.ssl_verify, True)

    def test_with_username_and_password(self):
        username='myuser'
        password='mypassword'
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url,
                config.USERNAME: username,
                config.PASSWORD: password
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.username, username)
        self.assertEqual(nxconfig.password, password)

    def test_with_username_and_oracle_password(self):
        username='myuser'
        password='mypassword'
        url='http://nowhere.com/nexus'
        data={
            'test': {
                config.URL: url,
                config.USERNAME: username,
                config.PASSWORD: "@oracle:eval:echo %s" % password
            }
        }
        rc = self.create('.config/nexup/config.yaml', yaml.safe_dump(data, allow_unicode=False))
        nxconfig = config.load('test')
        self.assertEqual(nxconfig.username, username)
        self.assertEqual(nxconfig.get_password(), password)


class TestOracleEval(TestCase):

    def test_echo(self):
        self.assertEqual(config.oracle_eval("echo fööbår"), "fööbår")
