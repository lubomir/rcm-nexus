
from base import NexupBaseTest
from unittest import TestCase
import nexup
import responses
import os
import yaml
import traceback

TEST_BASEURL='http://localhost:8080/nexus'

class TestSession(NexupBaseTest):

	def create_and_load_conf(self, conf={'test':{nexup.config.URL: TEST_BASEURL}}):
		fpath = self.write_config(conf)
		return nexup.config.load('test')

