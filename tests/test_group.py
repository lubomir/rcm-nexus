from base import (TEST_INPUT_DIR, NexupBaseTest)
import rcm_nexus
import responses
import os
import yaml
import traceback
import tempfile

PUBLIC_GROUP_TESTDATA=os.path.join(TEST_INPUT_DIR, 'public-group.xml')

class TestGroup(NexupBaseTest):

	@responses.activate
	def test_exists(self):
		conf = self.create_and_load_conf()
		key='public'
		path = rcm_nexus.group.NAMED_GROUP_PATH.format(key=key)

		responses.add(responses.HEAD, conf.url + path, status=200)

		sess = rcm_nexus.session.Session(conf)
		self.assertEqual(rcm_nexus.group.group_exists(sess, key), True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_save_new(self):
		conf = self.create_and_load_conf()
		key='foo'
		path = rcm_nexus.group.GROUPS_PATH

		def callbk(req):
			print "RECV body: '%s'" % req.body
			return (201,req.headers,req.body)

		responses.add_callback(responses.POST, conf.url + path, callback=callbk)

		sess = rcm_nexus.session.Session(conf)
		group = rcm_nexus.group.Group(key, 'Foo Repo')

		group.save(sess)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_load_change_save(self):
		conf = self.create_and_load_conf()
		key='public'
		path = rcm_nexus.group.NAMED_GROUP_PATH.format(key=key)

		def callbk(req):
			print "RECV body: '%s'" % req.body
			return (200,req.headers,req.body)

		responses.add_callback(responses.PUT, conf.url + path, callback=callbk)

		body = None
		with open(PUBLIC_GROUP_TESTDATA) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		group = rcm_nexus.group.load(sess, key)
		group.set_exposed(False)

		group.save(sess)
		self.assertEqual(len(responses.calls), 2)

	@responses.activate
	def test_load_public(self):
		conf = self.create_and_load_conf()
		key='public'
		path = rcm_nexus.group.NAMED_GROUP_PATH.format(key=key)
		body = None
		with open(PUBLIC_GROUP_TESTDATA) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		group = rcm_nexus.group.load(sess, key)

		self.assertEqual(group.id(), key)
		self.assertEqual(group.name(), 'Public Repositories')
		self.assertEqual(group.content_uri(), 'http://localhost:8081/nexus/content/groups/public')

		body_lines = body.split('\n')
		rendered_lines = group.render().split('\n')
		for i in range(0,len(body_lines)):
			self.assertEqual(rendered_lines[i], body_lines[i])

		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_set_properties(self):
		conf = self.create_and_load_conf()
		key='public'
		path = rcm_nexus.group.NAMED_GROUP_PATH.format(key=key)
		body = None
		with open(PUBLIC_GROUP_TESTDATA) as f:
			body=f.read()

		central_path=rcm_nexus.repo.NAMED_REPO_PATH.format(key='central')
		central_body=None
		with open(os.path.join(TEST_INPUT_DIR, 'central-repo.xml')) as f:
			central_body=f.read();

		responses.add(responses.GET, conf.url + path, body=body, status=200)
		responses.add(responses.GET, conf.url + central_path, body=central_body, status=200)

		sess = rcm_nexus.session.Session(conf)
		group = rcm_nexus.group.load(sess, key)

		self.assertEqual(group.id(), key)
		self.assertEqual(len(responses.calls), 1)

		group.set_name('Test')
		self.assertEqual(group.name(), 'Test')
		group.set_name('Public Repositories')

		self.assertEqual(group.data.exposed, True)
		group.set_exposed(False)
		self.assertEqual(group.data.exposed, False)
		group.set_exposed(True)

		self.assertEqual(len(group.members()), 4)
		group.remove_member(sess, 'central')
		self.assertEqual(len(group.members()), 3)
		group.append_member(sess, 'central')
		self.assertEqual(len(group.members()), 4)

		body_lines = body.split('\n')
		rendered_lines = group.render().split('\n')
		for i in range(0,len(body_lines)):
			print "Searching GROUP XML: %s" % rendered_lines[i]
			self.assertEqual(rendered_lines[i] in body_lines, True)


