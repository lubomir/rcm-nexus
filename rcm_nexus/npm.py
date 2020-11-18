# npm stuff
from __future__ import print_function

import os
import sys
import zipfile
import tarfile
import tempfile
import rcm_nexus.config as config
import base64
import shutil
import subprocess
from .config import DEFAULT_PASSWORD

from enum import Enum

try:
    from hmac import compare_digest
except ImportError:
    from operator import eq as compare_digest


class NpmArchiveType(Enum):
    """Possible types of detected archive"""
    NOT_NPM = 0
    DIRECTORY = 1
    ZIP_FILE = 2
    TAR_FILE = 3


def detect_npm_archive(repo):
    """Detects, if the archive needs to have npm workflow.
    :parameter repo repository directory
    :return NpmArchiveType value
    """

    expanded_repo = os.path.expanduser(repo)
    if not os.path.exists(expanded_repo):
        print("Repository {} does not exist!".format(expanded_repo), file=sys.stderr)
        sys.exit(1)

    if os.path.isdir(expanded_repo):
        # we have archive repository
        repo_path = "".join((expanded_repo, "/package.json"))
        if os.path.isfile(repo_path):
            return NpmArchiveType.DIRECTORY
    elif zipfile.is_zipfile(expanded_repo):
        # we have a ZIP file to expand
        with zipfile.ZipFile(expanded_repo) as zz:
            try:
                if zz.getinfo('package.json'):
                    return NpmArchiveType.ZIP_FILE
            except KeyError:
                pass
    elif tarfile.is_tarfile(expanded_repo):
        with tarfile.open(expanded_repo) as tt:
            try:
                if tt.getmember('package/package.json').isfile():
                    return NpmArchiveType.TAR_FILE  # it is a tar file and has package.json in the right place
            except KeyError:
                pass

    return NpmArchiveType.NOT_NPM


def _create_npmrc_file(nexus_config, directory, product):
    """Creates the .npmrc file with authentication where needed.

    :type nexus_config: config.NexusConfig
    :param nexus_config: loaded configuration file
    :type directory: str
    :param directory: repository directory
    :type product: str
    :param product: product
    """
    with open(os.path.join(directory, ".npmrc"), "wt") as f:
        f.write("_auth=" + base64.standard_b64encode((
            (":".join((nexus_config.username, nexus_config.password))))))
        f.write("\n")
        if nexus_config.preemptive_auth:
            f.write("always-auth=true")
        f.write("registry = " + _npm_repository(nexus_config, product))


def _npm_repository(nexus_config, product):
    """ Calculates URL to be used to deploy stuff.

    :type nexus_config: config.NexusConfig
    :param nexus_config: nexus configuration object
    :type: str
    :return: URL to npm repository
    """
    repository = nexus_config.get_npm_repository(product)
    if repository:
        return nexus_config.url + "/content/repositories/" + repository


def _publish_directory(nexus_config, tempdir, product, debug):
    """ Publishes npm product from its expanded version in a temporary directory

    :type nexus_config: config.NexusConfig
    :param nexus_config: nexus config object
    :type tempdir: str
    :param tempdir: temporary directory, where it is expanded
    :return: None
    """
    # create np
    _create_npmrc_file(nexus_config, tempdir, product)

    command = ["npm", "publish"]
    if debug:
        command.extend(["--verbose"])

    try:
        result = subprocess.check_output(command, cwd=tempdir)
        if debug:
            print(result)
    except subprocess.CalledProcessError:
        die("npm deployment failed!")
    print("npm deployment was successfully pushed to the server.")


def die(message):
    """Reports an error and stops with error code 1
    :param message: message to be reported
    :type message: str
    """
    sys.stderr.write(message)
    exit(1)


def push(nexus_config, repo, repo_type, product, debug=False):
    """Publishes given repository
    :param nexus_config: loaded configuration file
    :type nexus_config: config.NexusConfig
    :param repo: repository directory
    :type repo: str
    :param repo_type: type of the npm repository
    :type repo_type: NpmArchiveType
    :param product: product
    :type product: str
    :param debug: optional extended output
    :type debug: bool
    """

    if not nexus_config.username or not nexus_config.password:
        die('Missing user credentials! Please, supply user name and password!')

    if not _npm_repository(nexus_config, product):
        die(product + ' is not an npm product!')

    if not nexus_config.get_npm_repository(product):
        die('Deployment data for product {} were not found in the common configuration file!'.format(product))

    expanded_repo = os.path.expanduser(repo)

    tempdir = tempfile.mkdtemp()
    try:
        if repo_type == NpmArchiveType.DIRECTORY:
            if expanded_repo[-1] != '/':
                expanded_repo += '/'

            if debug:
                print("Temporary directory: "+tempdir)
                print("Repository: "+expanded_repo)

            copy_command = ('cp', '-rf', expanded_repo, tempdir)
            subprocess.check_output(copy_command)

            _publish_directory(nexus_config, tempdir, product, debug)

        elif repo_type == NpmArchiveType.ZIP_FILE:
            if debug:
                print("Temporary directory: "+tempdir)
                print("Repository: "+expanded_repo)

            with zipfile.ZipFile(expanded_repo) as zz:
                zz.extractall(tempdir)
                _publish_directory(nexus_config, tempdir, product, debug)
        elif repo_type == NpmArchiveType.TAR_FILE:
            # create np
            _create_npmrc_file(nexus_config, tempdir, product)

            try:
                shutil.copy2(expanded_repo, tempdir)
            except IOError:
                shutil.rmtree(tempdir)
                die("Unable to copy {} to {}!".format(expanded_repo, tempdir))

            package = os.path.join(tempdir, os.path.split(expanded_repo)[-1])

            if debug:
                print("Temporary directory: "+tempdir)
                print("Repository: "+expanded_repo)
                print("Target repository: "+package)

            # publish the tarball using npm
            command = ["npm", "publish", package]
            if debug:
                command.extend(["--verbose"])
                print("Username: " + nexus_config.username)
                if compare_digest(nexus_config.password, DEFAULT_PASSWORD):
                    print("Password: not default password provided")
                else:
                    print("Password: default password used.")
                print("Temporary directory: " + tempdir)

            try:
                result = subprocess.check_output(command, cwd=tempdir)
                if debug:
                    print(result)
            except subprocess.CalledProcessError:
                die("npm deployment failed:")
            print("npm deployment was successfully pushed to the server.")
        else:
            die("Unsupported repository type!")
    finally:
        shutil.rmtree(tempdir)
