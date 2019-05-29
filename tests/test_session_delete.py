from __future__ import print_function

from base import NexupBaseTest
import rcm_nexus
import responses
import os
import yaml
import traceback

class TestSessionDelete(NexupBaseTest):
	
	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=204)

		sess = rcm_nexus.session.Session(conf)
		resp,_content=sess.delete(path)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 204)

	@responses.activate
	def test_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = rcm_nexus.session.Session(conf)
		resp,_content=sess.delete(path, expect_status=203)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 203)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')

	@responses.activate
	def test_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=404)

		sess = rcm_nexus.session.Session(conf)
		resp,_content=sess.delete(path, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=404)

		sess = rcm_nexus.session.Session(conf)

		try:
			resp,_content=sess.delete(path, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print("Caught expected Exception")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=404)

		sess = rcm_nexus.session.Session(conf)

		try:
			sess.delete(path, ignore_404=False, fail=False)
		except:
			print(traceback.format_exc())
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			print(req.url)
			return (203,req.headers,'')

		responses.add_callback(responses.DELETE, conf.url + path, callback=callbk)

		sess = rcm_nexus.session.Session(conf)

		resp,_content=sess.delete(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

