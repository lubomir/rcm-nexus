from __future__ import print_function

from base import (TEST_INPUT_DIR, NexupBaseTest)
import rcm_nexus
import responses
import os
import yaml
import traceback
import tempfile

class TestRepo(NexupBaseTest):

	@responses.activate
	def test_push_zip_with_delete(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.COMPRESSED_CONTENT_PATH.format(key=key, delete='?delete=true')
		# print("\n\n\n\nPOST: %s%s\n\n\n\n" % (conf.url, path))

		responses.add(responses.POST, conf.url + path, match_querystring=True, status=201)

		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')

		self.write_zip(src_zip, paths)

		sess = rcm_nexus.session.Session(conf)
		rcm_nexus.repo.push_zip(sess, key, src_zip, True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_push_zip_default_no_delete(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.COMPRESSED_CONTENT_PATH.format(key=key, delete='')
		# print("\n\n\n\nPOST: %s%s\n\n\n\n" % (conf.url, path))

		responses.add(responses.POST, conf.url + path, status=201)

		self.load_words()

		paths = ['path/one.txt', 'path/to/two.txt', 'path/to/stuff/three.txt']

		(_f,src_zip) = tempfile.mkstemp(suffix='.zip')

		self.write_zip(src_zip, paths)

		sess = rcm_nexus.session.Session(conf)
		rcm_nexus.repo.push_zip(sess, key, src_zip)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_exists(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.NAMED_REPO_PATH.format(key=key)

		responses.add(responses.HEAD, conf.url + path, status=200)

		sess = rcm_nexus.session.Session(conf)
		self.assertEqual(rcm_nexus.repo.repo_exists(sess, key), True)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_delete(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.NAMED_REPO_PATH.format(key=key)

		responses.add(responses.DELETE, conf.url + path, status=204)

		sess = rcm_nexus.session.Session(conf)
		rcm_nexus.repo.delete(sess, key)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_save_new(self):
		conf = self.create_and_load_conf()
		key='foo'
		path = rcm_nexus.repo.REPOS_PATH

		def callbk(req):
			print("RECV body: '%s'" % req.body)
			return (201,req.headers,req.body)

		responses.add_callback(responses.POST, conf.url + path, callback=callbk)

		sess = rcm_nexus.session.Session(conf)
		repo = rcm_nexus.repo.Repository(key, 'Foo Repo')

		repo.save(sess)
		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_load_change_save(self):
		conf = self.create_and_load_conf()
		key='central'
		central_path = rcm_nexus.repo.NAMED_REPO_PATH.format(key=key)

		def callbk(req):
			print("RECV body: '%s'" % req.body)
			return (200,req.headers,req.body)

		responses.add_callback(responses.PUT, conf.url + central_path, callback=callbk)

		body = None
		with open(os.path.join(TEST_INPUT_DIR, 'central-repo.xml')) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + central_path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		repo = rcm_nexus.repo.load(sess, key)
		repo.set_exposed(False)

		repo.save(sess)
		self.assertEqual(len(responses.calls), 2)

	@responses.activate
	def test_load_central(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.NAMED_REPO_PATH.format(key=key)
		body = None
		with open(os.path.join(TEST_INPUT_DIR, 'central-repo.xml')) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		repo = rcm_nexus.repo.load(sess, key)

		self.assertEqual(repo.id(), key)
		self.assertEqual(repo.name(), 'Central')
		self.assertEqual(repo.content_uri(), 'http://localhost:8081/nexus/content/repositories/central')

		body_lines = body.split('\n')
		rendered_lines = repo.render().split('\n')
		for i in range(0,len(body_lines)):
			self.assertEqual(rendered_lines[i], body_lines[i])

		self.assertEqual(len(responses.calls), 1)

	@responses.activate
	def test_set_properties(self):
		conf = self.create_and_load_conf()
		key='central'
		path = rcm_nexus.repo.NAMED_REPO_PATH.format(key=key)
		body = None
		with open(os.path.join(TEST_INPUT_DIR, 'central-repo.xml')) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		repo = rcm_nexus.repo.load(sess, key)

		self.assertEqual(repo.id(), key)
		self.assertEqual(len(responses.calls), 1)

		repo.set_nfc_ttl(12)
		self.assertEqual(repo.data.notFoundCacheTTL, '12')
		repo.set_nfc_ttl(1440)

		repo.set_checksum_policy(rcm_nexus.repo.CHECKSUM_POLICIES.fail)
		self.assertEqual(repo.data.checksumPolicy, 'FAIL')
		repo.set_checksum_policy(rcm_nexus.repo.CHECKSUM_POLICIES.warn)

		repo.set_repo_policy(rcm_nexus.repo.REPO_POLICIES.snapshot)
		self.assertEqual(repo.data.repoPolicy, 'SNAPSHOT')
		repo.set_repo_policy(rcm_nexus.repo.REPO_POLICIES.release)

		self.assertEqual(repo.data.downloadRemoteIndexes, False)
		repo.set_download_remote_indexes(True)
		self.assertEqual(repo.data.downloadRemoteIndexes, True)
		repo.set_download_remote_indexes(False)

		repo.set_hosted('/path/to/storage')
		self.assertEqual(repo.data.repoType, rcm_nexus.repo.REPO_TYPES.hosted)
		self.assertEqual(repo.data.overrideLocalStorageUrl, 'file:/path/to/storage')
		self.assertEqual(repo.data.get('remoteStorage'), None)

		repo.set_remote('https://repo1.maven.org/maven456/')
		self.assertEqual(repo.data.remoteStorage.remoteStorageUrl, 'https://repo1.maven.org/maven456/')
		self.assertEqual(repo.data.repoType, rcm_nexus.repo.REPO_TYPES.remote)
		self.assertEqual(repo.data.get('overrideLocalStorageUrl'), None)

		repo.set_remote('https://repo1.maven.org/maven789/')
		self.assertEqual(repo.data.remoteStorage.remoteStorageUrl, 'https://repo1.maven.org/maven789/')
		self.assertEqual(repo.data.repoType, rcm_nexus.repo.REPO_TYPES.remote)
		self.assertEqual(repo.data.get('overrideLocalStorageUrl'), None)

		repo.set_remote('https://repo1.maven.org/maven2/')

		self.assertEqual(repo.data.exposed, True)
		repo.set_exposed(False)
		self.assertEqual(repo.data.exposed, False)
		repo.set_exposed(True)

		self.assertEqual(repo.data.browseable, True)
		repo.set_browseable(False)
		self.assertEqual(repo.data.browseable, False)
		repo.set_browseable(True)

		self.assertEqual(repo.data.indexable, True)
		repo.set_indexable(False)
		self.assertEqual(repo.data.indexable, False)
		repo.set_indexable(True)

		repo.set_write_policy(rcm_nexus.repo.WRITE_POLICIES.write_once)
		self.assertEqual(repo.data.writePolicy, 'ALLOW_WRITE_ONCE')
		repo.set_write_policy(rcm_nexus.repo.WRITE_POLICIES.read_only)

		body_lines = body.split('\n')
		rendered_lines = repo.render().split('\n')
		for i in range(0,len(body_lines)):
			print("Searching: %s" % rendered_lines[i])
			self.assertEqual(rendered_lines[i] in body_lines, True)


	@responses.activate
	def test_load_all(self):
		conf = self.create_and_load_conf()
		path = rcm_nexus.repo.REPOS_PATH

		body = None
		with open(os.path.join(TEST_INPUT_DIR, 'all-repos.xml')) as f:
			body=f.read()

		responses.add(responses.GET, conf.url + path, body=body, status=200)

		sess = rcm_nexus.session.Session(conf)
		repos = rcm_nexus.repo.load_all(sess)

		print("Loaded all repositories: %s" % repos)
		self.assertEqual(len(repos), 6)
		self.assertEqual(len(responses.calls), 1)


