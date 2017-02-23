
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

	@responses.activate
	def test_session_exists(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=200)

		sess = nexup.session.Session(conf)
		self.assertEqual(sess.exists(path), True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_session_exists_missing(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		self.assertEqual(sess.exists(path), False)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_session_exists_error(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=500, body="Test error")

		sess = nexup.session.Session(conf)
		try:
			self.assertEqual(sess.exists(path), False)
			self.fail('should have failed with exception on 500 response')
		except:
			print "Caught expected Exception."
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_session_head(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=200, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
		resp,_content=sess.head(path)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')

	@responses.activate
	def test_session_head_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
		resp,_content=sess.head(path, expect_status=203)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 203)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')

	@responses.activate
	def test_session_head_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		resp,_content=sess.head(path, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_session_head_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			resp,_content=sess.head(path, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print "Caught expected Exception"
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_session_head_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			sess.head(path, ignore_404=False, fail=False)
		except:
			print traceback.format_exc()
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_session_head_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			return (203,req.headers,'')

		responses.add_callback(responses.HEAD, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,_content=sess.head(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

