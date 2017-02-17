import time
from session import Session
import config
import repo as repos
import group as groups
import os.path
import sys
import re
import click

RELEASE_GROUP_NAME = 'product-ga'
TECHPREVIEW_GROUP_NAME = 'product-techpreview'
PRERELEASE_GROUP_NAME = 'product-earlyaccess'

@click.command()
@click.argument('repo', type=click.Path(exists=True))
@click.option('--environment', '-e', help='The target Nexus environment (from ~/.config/nexup/nexup.yaml)')
@click.option('--ga', '-g', is_flag=True, default=False, help='Push content to the GA group (as opposed to earlyaccess)')
@click.option('--debug', '-D', is_flag=True, default=False)
def push(repo, environment, ga=False, debug=False):
    "Push maven repository content to a Nexus staging repository."

    nexus_config = config.load(environment)

    if release:
        groups = [RELEASE_GROUP_NAME, TECHPREVIEW_GROUP_NAME]
    else:
        groups = [PRERELEASE_GROUP_NAME]

    session = Session(nexus_config, debug=debug)
    
    try:
        print "Pushing: %s content to: %s" % (repo, environment)
        
        # produce a set of clean repository zips for PUT upload.
        if os.path.isdir(repo):
            print "Processing repository directory: %s" % repo

            # TODO: Walk the directory tree, and create a zip.
        else:
            print "Processing repository zip archive: %s" % repo
            # TODO: Open the zip, walk the entries and normalize the structure to clean zip (if necessary)

        
        # TODO: Open new staging repository with description

        # TODO: HTTP PUT clean repository zips to Nexus.

        # TODO: Close staging repository
        staging_repo_name = "FIXME"

        for group_name in groups:
            group = groups.load(session, group_name, ignore_missing=True)
            if group is not None:
                print "Adding %s to group: %s" % (staging_repo_name, group_name)

                # TODO: How do you reference a staging repository for group membership??
                group.append_member(session, staging_repo_name).save(session)
            else:
                print "No such group: %s" % group_name
                raise Exception("No such group: %s" % group_name)
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
