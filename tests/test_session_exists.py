from __future__ import print_function

from base import NexupBaseTest
import rcm_nexus
import responses
import os
import yaml
import traceback

class TestSessionExists(NexupBaseTest):

	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=200)

		sess = rcm_nexus.session.Session(conf)
		self.assertEqual(sess.exists(path), True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_missing(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = rcm_nexus.session.Session(conf)
		self.assertEqual(sess.exists(path), False)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_error(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=500, body="Test error")

		sess = rcm_nexus.session.Session(conf)
		try:
			self.assertEqual(sess.exists(path), False)
			self.fail('should have failed with exception on 500 response')
		except:
			print("Caught expected Exception.")
		finally:
			self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_error_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=500, body="Test error")

		sess = rcm_nexus.session.Session(conf)
		try:
			self.assertEqual(sess.exists(path, fail=False), False)
		except:
			print(traceback.format_exc())
			self.fail('should NOT have raised exception on 500 response')
		finally:
			self.assertEqual(len(responses.calls), 1)

