import time
from session import Session
import config
import repo as repos
import group as groups
import archive
import staging
import os.path
import sys
import re
import click
import tempfile

RELEASE_GROUP_NAME = 'product-ga'
TECHPREVIEW_GROUP_NAME = 'product-techpreview'
PRERELEASE_GROUP_NAME = 'product-earlyaccess'

@click.command()
@click.argument('repo', type=click.Path(exists=True))
@click.option('--environment', '-e', help='The target Nexus environment (from ~/.config/nexup/nexup.yaml)')
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration')
@click.option('--version', '-v', help='The product version, used in repository definition metadata')
@click.option('--ga', '-g', is_flag=True, default=False, help='Push content to the GA group (as opposed to earlyaccess)')
@click.option('--debug', '-D', is_flag=True, default=False)
def push(repo, environment, product, version, ga=False, debug=False):
    "Push maven repository content to a Nexus staging repository, and add the staging repository to the appropriate content groups."

    nexus_config = config.load(environment)

    if release:
        groups = [RELEASE_GROUP_NAME, TECHPREVIEW_GROUP_NAME]
    else:
        groups = [PRERELEASE_GROUP_NAME]

    session = Session(nexus_config, debug=debug)
    
    try:
        print "Pushing: %s content to: %s" % (repo, environment)
        
        # produce a set of clean repository zips for PUT upload.
        zips_dir = tempfile.mkdtemp()
        print "Creating ZIP archives in: %s" % zips_dir
        if os.path.isdir(repo):
            print "Processing repository directory: %s" % repo

            # Walk the directory tree, and create a zip.
            zip_paths = archive.create_partitioned_zips_from_dir(repo, zips_dir)
        else:
            print "Processing repository zip archive: %s" % repo

            # Open the zip, walk the entries and normalize the structure to clean zip (if necessary)
            zip_paths = archive.create_partitioned_zips_from_zip(repo, zips_dir)

        
        # Open new staging repository with description
        staging_repo_id = staging.start_staging_repo(session, nexus_config, product, version, ga)

        # HTTP PUT clean repository zips to Nexus.
        delete_first = True
        for zipfile in zip_paths:
            repo.push_zip(session, staging_repo_id, zipfile, delete_first)
            delete_first = False

        # Close staging repository
        staging.finish_staging_repo(session, nexus_config, staging_repo_id, product, version, ga)

        for group_id in groups:
            group = groups.load(session, group_id, ignore_missing=True)
            if group is not None:
                print "Adding %s to group: %s" % (staging_repo_id, group_id)

                group.append_member(session, staging_repo_id).save(session)
            else:
                print "No such group: %s" % group_id
                raise Exception("No such group: %s" % group_id)
    finally:
        if session is not None:
            session.close()
    
@click.command()
@click.argument('staging_repo_name')
@click.option('--environment', '-e', help='The target Nexus environment (from ~/.config/nexup/nexup.yaml)')
@click.option('--debug', '-D', is_flag=True, default=False)
def rollback(args, config, session, delete_log=None, debug=False):
    "Remove the given staging repository from all release groups"

    nexus_config = config.load(environment)

    groups = [RELEASE_GROUP_NAME, TECHPREVIEW_GROUP_NAME, PRERELEASE_GROUP_NAME]

    session = Session(config.base_url, user, debug=debug, disable_ssl_validation=config.permissive_ssl, preemptive_auth=config.preemptive_auth)
    
    try:
        print "Removing content of: %s" % staging_repo_name
        
        for group_name in groups:
            group = groups.load(session, group_name, True)
            if group is not None:
                print "Removing %s from group %s" % (staging_repo_name, group_name)
                group.remove_member(session, staging_repo_name).save(session)
    finally:
        if session is not None:
            session.close()
