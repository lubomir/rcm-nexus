from .base import (TEST_INPUT_DIR, NexupBaseTest)
from rcm_nexus import (staging, config, session)
import responses
import os
import yaml
import traceback
import tempfile

class TestGroup(NexupBaseTest):

    @responses.activate
    def test_start_staging_repo_success(self):
        ga_profile = '0123456789'

        profile_map = {
            'test':{
                'eap': {
                    config.GA_PROFILE: str(ga_profile),
                    config.EA_PROFILE: '9876543210'
                }
            }
        }

        expected_repo_id = 'xyz-1001'
        response_xml ="""
        <promoteResponse>
          <data>
            <stagedRepositoryId>%s</stagedRepositoryId>
            <description>Unused Description</description>
          </data>
        </promoteResponse>
        """ % expected_repo_id

        conf = self.create_and_load_conf(profile_data=profile_map)

        profile_id = conf.get_profile_id( 'eap', is_ga=True )
        path = staging.STAGE_START_FORMAT.format(profile_id=profile_id)

        responses.add(responses.POST, conf.url + path, body=response_xml, status=201)
        
        sess = session.Session(conf)
        repo_id = staging.start_staging_repo(sess, conf, 'eap', '1.1.1', is_ga=True)

        self.assertEqual(repo_id, expected_repo_id)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_finish_staging_repo_success(self):
        ga_profile = '0123456789'

        profile_map = {
            'test':{
                'eap': {
                    config.GA_PROFILE: str(ga_profile),
                    config.EA_PROFILE: '9876543210'
                }
            }
        }

        repo_id = 'xyz-1001'

        conf = self.create_and_load_conf(profile_data=profile_map)

        profile_id = conf.get_profile_id( 'eap', is_ga=True )
        path = staging.STAGE_FINISH_FORMAT.format(profile_id=profile_id)

        responses.add(responses.POST, conf.url + path, body='Unspecified...', status=201)
        
        sess = session.Session(conf)
        staging.finish_staging_repo(sess, conf, repo_id, 'eap', '1.1.1', is_ga=True)

        self.assertEqual(len(responses.calls), 1)
