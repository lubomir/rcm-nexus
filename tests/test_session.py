
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

class TestSessionExists(TestSession):

	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=200)

		sess = nexup.session.Session(conf)
		self.assertEqual(sess.exists(path), True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_missing(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		self.assertEqual(sess.exists(path), False)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_error(self):
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
	def test_error_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=500, body="Test error")

		sess = nexup.session.Session(conf)
		try:
			self.assertEqual(sess.exists(path, fail=False), False)
		except:
			print traceback.format_exc()
			self.fail('should NOT have raised exception on 500 response')
		finally:
			self.assertEqual(len(responses.calls), 1)

class TestSessionHead(TestSession):

	@responses.activate
	def test_default(self):
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
	def test_expect_203(self):
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
	def test_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.HEAD, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		resp,_content=sess.head(path, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
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
	def test_dont_ignore_404_no_fail(self):
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
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			return (203,req.headers,'')

		responses.add_callback(responses.HEAD, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,_content=sess.head(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

	@responses.activate
	def test_custom_headers_no_body(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			return (203,req.headers,None)

		responses.add_callback(responses.HEAD, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,_content=sess.head(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

class TestSessionDelete(TestSession):
	
	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=204)

		sess = nexup.session.Session(conf)
		resp,_content=sess.delete(path)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 204)

	@responses.activate
	def test_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
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

		sess = nexup.session.Session(conf)
		resp,_content=sess.delete(path, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			resp,_content=sess.delete(path, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print "Caught expected Exception"
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.DELETE, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			sess.delete(path, ignore_404=False, fail=False)
		except:
			print traceback.format_exc()
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			print req.url
			return (203,req.headers,'')

		responses.add_callback(responses.DELETE, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,_content=sess.delete(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

class TestSessionGet(TestSession):
	
	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'
		src="This is a test"

		responses.add(responses.GET, conf.url + path, body=src, status=200)

		sess = nexup.session.Session(conf)
		resp,content=sess.get(path)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(content, src)

	@responses.activate
	def test_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.GET, conf.url + path, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
		resp,_content=sess.get(path, expect_status=203)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 203)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')

	@responses.activate
	def test_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.GET, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		resp,_content=sess.get(path, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.GET, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			resp,_content=sess.get(path, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print "Caught expected Exception"
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		responses.add(responses.GET, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			sess.get(path, ignore_404=False, fail=False)
		except:
			print traceback.format_exc()
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		def callbk(req):
			print req.url
			return (203,req.headers,'')

		responses.add_callback(responses.GET, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,_content=sess.get(path, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')

class TestSessionPost(TestSession):
	
	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'
		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.POST, conf.url + path, body=response_src, status=201)

		sess = nexup.session.Session(conf, debug=True)
		resp,content=sess.post(path, request_src)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(content, response_src)

	@responses.activate
	def test_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.POST, conf.url + path, body=response_src, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
		resp,content=sess.post(path, request_src, expect_status=203)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 203)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')
		self.assertEqual(content, response_src)

	@responses.activate
	def test_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.POST, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		resp,content=sess.post(path, request_src, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		responses.add(responses.POST, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			resp,content=sess.post(path, request_src, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print "Caught expected Exception"
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		responses.add(responses.POST, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			sess.post(path, request_src, ignore_404=False, fail=False)
		except:
			print traceback.format_exc()
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		def callbk(req):
			print req.url
			return (203,req.headers,response_src)

		responses.add_callback(responses.POST, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,content=sess.post(path, request_src, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')
		self.assertEqual(content, response_src)

class TestSessionPut(TestSession):
	
	@responses.activate
	def test_default(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'
		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.PUT, conf.url + path, body=response_src, status=200)

		sess = nexup.session.Session(conf, debug=True)
		resp,content=sess.put(path, request_src)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(content, response_src)

	@responses.activate
	def test_expect_203(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.PUT, conf.url + path, body=response_src, status=203, adding_headers={'content-length': '12'}, content_type='application/json')

		sess = nexup.session.Session(conf)
		resp,content=sess.put(path, request_src, expect_status=203)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 203)
		self.assertEqual(int(resp.headers['content-length']), 12)
		self.assertEqual(resp.headers['content-type'], 'application/json')
		self.assertEqual(content, response_src)

	@responses.activate
	def test_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"

		responses.add(responses.PUT, conf.url + path, status=404)

		sess = nexup.session.Session(conf)
		resp,content=sess.put(path, request_src, ignore_404=True)

		self.assertEqual(len(responses.calls), 1)
		self.assertEqual(resp.status_code, 404)

	@responses.activate
	def test_dont_ignore_404(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		responses.add(responses.PUT, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			resp,content=sess.put(path, request_src, ignore_404=False)
			self.fail("Should have thrown Exception on 404")
		except:
			print "Caught expected Exception"
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_dont_ignore_404_no_fail(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		responses.add(responses.PUT, conf.url + path, status=404)

		sess = nexup.session.Session(conf)

		try:
			sess.put(path, request_src, ignore_404=False, fail=False)
		except:
			print traceback.format_exc()
			self.fail("Should have suppressed Exception on 404.")
		finally:
			self.assertEqual(len(responses.calls), 1)


	@responses.activate
	def test_custom_headers(self):
		conf = self.create_and_load_conf()
		path = '/foo/bar'

		request_src="Test request"
		response_src="Request successful"
		
		def callbk(req):
			print req.url
			return (203,req.headers,response_src)

		responses.add_callback(responses.PUT, conf.url + path, callback=callbk)

		sess = nexup.session.Session(conf)

		resp,content=sess.put(path, request_src, expect_status=203, headers={'my-header': 'foo'})

		self.assertEqual(resp.status_code, 203)
		self.assertEqual(resp.headers.get('my-header'), 'foo')
		self.assertEqual(content, response_src)

