from __future__ import print_function

import time
from rcm_nexus.session import Session
import rcm_nexus.config as config
import rcm_nexus.repo as repos
import rcm_nexus.archive as archive
import rcm_nexus.staging as staging
import os.path
import sys
import click
import shutil
import tempfile


@click.command()
def init():
    """Create a starter configuration for rcm-nexus.

    More Information: https://mojo.redhat.com/docs/DOC-1132234
    """
    conf_path = config.init_config()
    print("""Wrote starter config to:

    %s

    Next steps:

    - Modify configuration to include each Nexus environment you intend to manage.
    - Fine tune each environment's configuration (username, ssl-verify, etc.).
    - Setup passwords (`pass` is a nice tool for this) to match the configured password keys.
    - Add Nexus staging profiles for each product you intend to manage via Nexus.
    
    For more information on using rcm-nexus (nexus-push, nexus-rollback), see:

    https://mojo.redhat.com/docs/DOC-1132234
    """ % conf_path)

@click.command()
@click.argument('repo', type=click.Path(exists=True))
@click.option('--environment', '-e', help='The target Nexus environment (from ~/.config/rcm-nexus/config.yaml)')
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration')
@click.option('--version', '-v', help='The product version, used in repository definition metadata')
@click.option('--ga', '-g', is_flag=True, default=False, help='Push content to the GA group (as opposed to earlyaccess)')
@click.option('--debug', '-D', is_flag=True, default=False)
def push(repo, environment, product, version, ga=False, debug=False):
    """Push Apache Maven repository content to a Nexus staging repository, 
    then add the staging repository to appropriate content groups.

    More Information: https://mojo.redhat.com/docs/DOC-1132234
    """

    nexus_config = config.load(environment, debug=debug)

    session = Session(nexus_config, debug=debug)
    
    try:
        print("Pushing: %s content to: %s" % (repo, environment))
        
        # produce a set of clean repository zips for PUT upload.
        zips_dir = tempfile.mkdtemp()
        print("Creating ZIP archives in: %s" % zips_dir)
        if os.path.isdir(repo):
            print("Processing repository directory: %s" % repo)

            # Walk the directory tree, and create a zip.
            zip_paths = archive.create_partitioned_zips_from_dir(repo, zips_dir)
        else:
            print("Processing repository zip archive: %s" % repo)

            # Open the zip, walk the entries and normalize the structure to clean zip (if necessary)
            zip_paths = archive.create_partitioned_zips_from_zip(repo, zips_dir)

        # Open new staging repository with description
        staging_repo_id = staging.start_staging_repo(session, nexus_config, product, version, ga)

        # HTTP PUT clean repository zips to Nexus.
        delete_first = True
        for idx, zipfile in enumerate(zip_paths, start=1):
            print("Uploading zip %s out of %s" % (idx, len(zip_paths)))
            repos.push_zip(session, staging_repo_id, zipfile, delete_first)
            delete_first = False

        # Close staging repository
        staging.finish_staging_repo(session, nexus_config, staging_repo_id, product, version, ga)

        if staging.verify_action(session, staging_repo_id, "close"):
            sys.exit(1)

        print("Promoting repo")
        promote_profile = nexus_config.get_promote_profile_id(ga)
        staging.promote(session, promote_profile, staging_repo_id, product, version, ga)

        if staging.verify_action(session, staging_repo_id, "promote"):
            sys.exit(1)
    finally:
        if session is not None:
            session.close()

        shutil.rmtree(zips_dir)


@click.command()
@click.argument('staging_repo_name')
@click.option('--environment', '-e', help='The target Nexus environment (from ~/.config/rcm-nexus/config.yaml)')
@click.option('--debug', '-D', is_flag=True, default=False)
def rollback(staging_repo_name, environment, debug=False):
    """Drop given staging repository.

    More Information: https://mojo.redhat.com/docs/DOC-1132234
    """
    nexus_config = config.load(environment, debug=debug)

    session = Session(nexus_config, debug=debug)

    try:
        print("Dropping repository %s" % staging_repo_name)
        if not staging.drop_staging_repo(session, staging_repo_name):
            sys.exit(1)
    finally:
        if session is not None:
            session.close()
