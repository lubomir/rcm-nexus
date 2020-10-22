from __future__ import print_function

import contextlib
import getpass
import subprocess
import os
import shutil
import sys
import tempfile
import textwrap
from ConfigParser import NoOptionError, NoSectionError

from enum import Enum


from six.moves import configparser

RCM_NEXUS_CONFIG = 'RCM_NEXUS_CONFIG'
SECTION = "general"

URL = 'url'
WEB_URL = 'web_url'
USERNAME = 'username'
# noinspection HardcodedPassword
PASSWORD = 'password'
SSL_VERIFY = 'ssl-verify'
PREEMPTIVE_AUTH = 'preemptive-auth'
INTERACTIVE = 'interactive'
CONFIG_REPO = "config_repo"
WRITE_CONFIG_REPO = "write_config_repo"
GA_PROMOTE_PROFILES = "ga-promote-profiles"
EA_PROMOTE_PROFILES = "ea-promote-profiles"

TARGET_GROUPS_GA = "target_groups_ga"
TARGET_GROUPS_EA = "target_groups_ea"
PROMOTE_RULESET_GA = "promote_ruleset_ga"
PROMOTE_RULESET_EA = "promote_ruleset_ea"
PROMOTE_TARGET_GA = "promote_target_ga"
PROMOTE_TARGET_EA = "promote_target_ea"
DEPLOYER_ROLE = "deployer_role"

ENVIRONMENT_PRODUCTION = "prod"
ENVIRONMENT_STAGE = "stage"

GA_STAGING_PROFILE = 'ga'
EA_STAGING_PROFILE = 'ea'

IS_GA = True
IS_EA = not IS_GA

DEFAULTS = {
    SSL_VERIFY: "yes",
    PREEMPTIVE_AUTH: "no",
    INTERACTIVE: "yes"
}

CONFIG_FILE_NAME = "rcm-nexus.conf"
PRODUCT_NAME = "prod_name"
NPM_REPOSITORY = "npm_repository"
DEFAULT_PASSWORD = "@oracle:ask_password"


class ProfileType(Enum):
    """Possible profile types"""
    UNKNOWN = 0
    JAVA = 1
    NPM = 2


class NexusConfig(object):
    def __init__(self, name, data, profile_data):
        self.name = name
        try:
            self.url = data.get(name, URL)
        except NoOptionError:
            die('Deployment URL was not found in the environment {}!'.format(name))
        except NoSectionError:
            die('Environment "{}" was not found in the configuration file!'.format(name))

        try:
            self.web_url = data.get(name, WEB_URL)
        except configparser.NoOptionError:
            self.web_url = None
        self.ssl_verify = data.getboolean(name, SSL_VERIFY)
        self.preemptive_auth = data.getboolean(name, PREEMPTIVE_AUTH)

        self.username = self.get_from_name_and_section(data, name, USERNAME, default=getpass.getuser())
        self.password = self.get_from_name_and_section(data, name, PASSWORD, default=DEFAULT_PASSWORD)

        self.interactive = data.getboolean(name, INTERACTIVE)
        self.target_groups = {
            IS_GA: data.get(SECTION, TARGET_GROUPS_GA),
            IS_EA: data.get(SECTION, TARGET_GROUPS_EA),
        }
        self.promote_ruleset = {
            IS_GA: data.get(SECTION, PROMOTE_RULESET_GA),
            IS_EA: data.get(SECTION, PROMOTE_RULESET_EA),
        }
        self.promote_target = {
            IS_GA: data.get(SECTION, PROMOTE_TARGET_GA),
            IS_EA: data.get(SECTION, PROMOTE_TARGET_EA),
        }
        self.deployer_role = data.get(SECTION, DEPLOYER_ROLE)
        self.write_remote_repo = data.get(SECTION, WRITE_CONFIG_REPO)
        self.profile_map = profile_data

    @staticmethod
    def get_from_name_and_section(data, environment, key, default=None):
        """ Gets a string value from the specified section of the data and if the entry is not found there
        it fallbacks to the [global] .

        :param data: the configparser object to search in
        :type data: configparser.RawConfigParser
        :param environment: the environment to search for prod/stage
        :type environment: str
        :param key: key to search for
        :type key: str
        :param default: default value if the key is not to be found anywhere
        :type default: string
        :return: string value
        """
        try:
            return data.get(environment, key)
        except NoOptionError:
            try:
                return data.get(SECTION, key)
            except NoOptionError:
                pass
        except NoSectionError:
            die("Environment "+environment+" does not exist!")
        return default

    @staticmethod
    def get_from_name_and_section_boolean(data, environment, key, default=False):
        """ Gets a boolean value from the specified section of the data and if the entry is not found there
        it fallbacks to the [global] .

        :param data: the configparser object to search in
        :type data: configparser.RawConfigParser
        :param environment: the environment to search for prod/stage
        :type environment: str
        :param key: key to search for
        :type key: str
        :param default: default value if the key is not to be found anywhere
        :type default: bool
        :return: boolean value
        """
        try:
            return data.getboolean(environment, key)
        except NoOptionError:
            try:
                return data.getboolean(SECTION, key)
            except NoOptionError:
                pass
        except NoSectionError:
            die("Environment "+environment+" does not exist!")
        return default

    def get_password(self):
        if self.password and self.password.startswith("@oracle:"):
            return eval_password(self.username, oracle=self.password, interactive=self.interactive)
        return self.password

    def _get_profiles(self, product):
        """ Tries to find a profiles for the specific product

        :param product: the product key
        :return: the profile
        """
        profiles = self.profile_map.get(product.upper())
        if profiles is None:
            die("No product profiles found for: '%s' in environment: %s" % (product, self.name))
        return profiles

    def get_npm_repository(self, product):
        """ Returns npm repository name if present in the specific product

        :type: str
        :return: None or repository name
        """
        profiles = self._get_profiles(product)
        return profiles.get(NPM_REPOSITORY)

    def get_profile_data(self, product):
        """ Prepares data about the given product. Fills irrelevant fields with empty string

        :param product: product key
        :return: yields  product type, product name, ga profile ID, ea profile ID, npm repository name
        """

        profiles = self._get_profiles(product)
        if profiles:
            product_name = profiles.get(PRODUCT_NAME, "")
            ga_id = profiles.get(GA_STAGING_PROFILE, "")
            ea_id = profiles.get(EA_STAGING_PROFILE, "")
            if not ea_id:
                ea_id = ""
            npm_repository = profiles.get(NPM_REPOSITORY, "")
            return (
                self._determine_type(profiles),
                product_name,
                ga_id,
                ea_id,
                npm_repository)
        else:
            die("Can not find profile of product " + product)

    @staticmethod
    def _determine_type(profiles):
        """ Extracts staging profile/product type from the given profile

        :param profiles:
        :return: product type
        """
        if not profiles:
            return ProfileType.UNKNOWN
        elif NPM_REPOSITORY in profiles:
            return ProfileType.NPM
        elif GA_STAGING_PROFILE in profiles or EA_STAGING_PROFILE in profiles:
            return ProfileType.JAVA
        else:
            return ProfileType.UNKNOWN

    def get_profile_type(self, product):
        """Detects a profile type
        :param product: product to be searched for
        :type product: str
        :return ProfileType: profile type
        """
        profiles = self._get_profiles(product)
        return self._determine_type(profiles)

    def get_profile_id(self, product, is_ga):
        profiles = self._get_profiles(product.upper())
        quality_level = GA_STAGING_PROFILE if is_ga is True else EA_STAGING_PROFILE
        profile_id = profiles.get(quality_level)
        if profile_id is None:
            die(
                ("ProfileID not configured for quality level: %s in 'profile-maps' of configuration: %s " +
                 "for the product: '%s' (case-sensitive)") % (quality_level, self.name, product))

        return profile_id

    def get_promote_profile_ids(self, product, is_ga):
        return self.profile_map[product.upper()][
            GA_PROMOTE_PROFILES if is_ga else EA_PROMOTE_PROFILES
        ].split()

    def __str__(self):
        return """RCMNexusConfig [
    URL: %(url)s
    SSL verification: %(ssl_verify)s
    use-preemptive-auth: %(preemptive_auth)s
    username: %(username)s
    interactive: %(interactive)s
]""" % self.__dict__

    def __repr__(self):
        return self.__str__()


def die(error_msg):
    """Die with honor!
    :param error_msg: error message to be displayed
    :type error_msg: str
    """
    sys.stderr.write(error_msg)
    sys.exit(1)


def load(environment):
    """ Loads

    :param environment: environment in the configuration file to load (usually prod/stage)
    :type environment: str
    :return: NexusConfig object
    """
    config_paths = list(reversed(get_config_path()))
    parser = configparser.RawConfigParser(DEFAULTS)
    if not parser.read(config_paths):
        die("Failed to load config file from any path:\n%s" % "\n".join(config_paths))

    profile_data = read_config(parser.get(SECTION, CONFIG_REPO))

    return NexusConfig(environment, parser, profile_data)


def read_config(repo_url):
    """Read configuration from given location.
    If needed, a Git repo will be cloned and the file read from there.
    """
    if "://" in repo_url:
        return _read_remote_repo(repo_url)
    return _read_config(repo_url)


def _clone_config_repo(destination, repo_url, limit_depth=True):
    """Clone a git repository into a given location."""
    cmd = ["git", "clone"]
    if limit_depth:
        cmd.append("--depth=1")
    subprocess.check_call(
        cmd + [repo_url, destination], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def _normalize_dir_name(dir_name):
    """Normalizes a repository name by cutting off the ending slash (if present)

    :param dir_name: name of the directory (taken from the configuration)
    :type dir_name: basestring
    :return: directory name without
    """

    if dir_name and dir_name[-1] in ('/', '\\'):
        return dir_name[:-1]
    return dir_name


def _read_remote_repo(repo_url):
    """Clone a git repository and read rcm-nexus.conf from there."""
    tempdir = tempfile.mkdtemp(prefix="rcm-nexus-config-")
    clone_dir = os.path.join(tempdir, "clone")
    try:
        _clone_config_repo(clone_dir, repo_url)
        return _read_config(os.path.join(clone_dir, CONFIG_FILE_NAME))
    finally:
        shutil.rmtree(tempdir)


def _read_config(path):
    result = {}
    parser = configparser.RawConfigParser()
    with open(path) as f:
        parser.readfp(f)
    for product in parser.sections():
        result[product.upper()] = dict(parser.items(product))
    return result


@contextlib.contextmanager
def cloned_repo(config):
    tempdir = tempfile.mkdtemp(prefix="rcm-nexus-config-")
    clone_dir = os.path.join(tempdir, "clone")
    remote_url = config.write_remote_repo.format(user=config.username.split("@")[0])
    try:
        print("Cloning remote git configuration repository...")
        _clone_config_repo(clone_dir, remote_url, limit_depth=False)
        yield clone_dir
    except Exception:
        xdg_config_home = (
                os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        )
        error = textwrap.dedent(
            """
            Failed to clone configuration repository from writable URL:
              {0}

            Modify {1}/rcm-nexus.conf and add following snippet with correct
            URL to which it is possible to push a new commit.

            [{2}]
            write_config_repo = FILL_ME
            """.format(remote_url, xdg_config_home, SECTION)
        )
        raise RuntimeError(error)
    finally:
        shutil.rmtree(tempdir)


def _save_changes(clone_dir, parser, key):
    with open(os.path.join(clone_dir, CONFIG_FILE_NAME), "w") as f:
        parser.write(f)
    print("Committing the changes...")
    subprocess.check_call(
        ["git", "commit", "-a", "-m", "%s added" % key],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=clone_dir,
    )
    print("Pushing changes to remote repo...")
    subprocess.check_call(
        ["git", "push", "origin", "master"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=clone_dir,
    )


def add_npm_product(clone_dir, key, prod_name, repo_name):
    """ Adds a new npm repository

    :param clone_dir: directory with cloned GIT configuration file
    :type clone_dir: str
    :param key: section name
    :type key: str
    :param prod_name: Name of the product
    :type prod_name: str
    :param repo_name: Nexus repository name
    :type repo_name: str
    """
    print("Adding new NPM configuration entries...")
    parser = configparser.RawConfigParser()
    with open(os.path.join(clone_dir, CONFIG_FILE_NAME)) as f:
        parser.readfp(f)
    if not parser.has_section(key):
        parser.add_section(key)
    parser.set(key, PRODUCT_NAME, prod_name)
    parser.set(key, NPM_REPOSITORY, repo_name)
    _save_changes(clone_dir, parser, key)


def add_product(clone_dir, key, prod_name, ids):
    print("Adding new configuration entries...")
    parser = configparser.RawConfigParser()
    with open(os.path.join(clone_dir, CONFIG_FILE_NAME)) as f:
        parser.readfp(f)
    if not parser.has_section(key):
        parser.add_section(key)
    parser.set(key, PRODUCT_NAME, prod_name)
    parser.set(key, GA_STAGING_PROFILE, ids[IS_GA])
    parser.set(key, EA_STAGING_PROFILE, ids[IS_EA])
    _save_changes(clone_dir, parser, key)


def init_config():
    conf_path = get_config_path()[0]
    if os.path.exists(conf_path):
        die("%s already exists!" % conf_path)

    parser = configparser.RawConfigParser()
    conf_dir = os.path.dirname(conf_path)
    if not os.path.isdir(conf_dir):
        os.makedirs(conf_dir)
    parser.add_section(SECTION)
    parser.set(SECTION, "username", getpass.getuser())
    parser.set(SECTION, "; password", DEFAULT_PASSWORD)
    parser.set(SECTION, "config_repo", "https://code.engineering.redhat.com/gerrit/rcm/rcm-nexus-config")
    parser.set(SECTION, "; write_config_repo", "ssh://{user}@code.engineering.redhat.com/rcm/rcm-nexus-config")
    parser.set(SECTION, "target_groups_ga", "product-all")
    parser.set(SECTION, "target_groups_ea", "product-all")
    parser.set(SECTION, "promote_ruleset_ga", "57aa9ee54e2f6")
    parser.set(SECTION, "promote_ruleset_ea", "13091dda10832d")
    parser.set(SECTION, "promote_target_ga", "product-old-releases")
    parser.set(SECTION, "promote_target_ea", "product-old-releases-ea")
    parser.set(SECTION, "deployer_role", "product_deployer")
    parser.set(SECTION, "; " + SSL_VERIFY, DEFAULTS.get(SSL_VERIFY))
    parser.set(SECTION, "; " + PREEMPTIVE_AUTH, DEFAULTS.get(PREEMPTIVE_AUTH))
    parser.set(SECTION, "; " + INTERACTIVE, DEFAULTS.get(INTERACTIVE))

    parser.add_section(ENVIRONMENT_PRODUCTION)
    parser.set(ENVIRONMENT_PRODUCTION, URL, "https://repository.jboss.org/nexus")
    parser.set(ENVIRONMENT_PRODUCTION, "; username", "{production specific user name}")
    parser.set(ENVIRONMENT_PRODUCTION, "; password", "{production specific password}")

    parser.add_section(ENVIRONMENT_STAGE)
    parser.set(ENVIRONMENT_STAGE, URL, "https://repository.stage.jboss.org/nexus")
    parser.set(ENVIRONMENT_STAGE, "; username", "{staging specific user name}")
    parser.set(ENVIRONMENT_STAGE, "; password", "{staging specific password}")

    with open(conf_path, "w") as f:
        parser.write(f)
        print("; For more information see: https://mojo.redhat.com/docs/DOC-1132234", file=f)
        print("; The config_repo options can be defined in system wide config file", file=f)

    return conf_path


#############################################################################
# Shamelessly ripped off and modified from Bugwarrior:
#     https://github.com/ralphbean/bugwarrior
#
# Modified to remove keyring support (for now).
#
# Thanks, Bugwarrior team!
#
def eval_password(username, oracle=None, interactive=False):
    """
    Retrieve the sensitive password by:

      * asking the password from the user (@oracle:ask_password, interactive)
      * executing a command and use the output as password
        (@oracle:eval:<command>)

    :param username:    Username for the service (as string).
    :param oracle:      Hint which password oracle strategy to use.
    :param interactive: If true, ask for password
    :return: Retrieved password (as string)
    """
    password = None
    if interactive and oracle == DEFAULT_PASSWORD:
        prompt = "Enter %s's password: " % username
        password = getpass.getpass(prompt)
    elif oracle.startswith('@oracle:eval:'):
        command = oracle[13:]
        return oracle_eval(command)

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s" % (oracle, interactive))
    return password


def oracle_eval(command):
    """ Retrieve password from the given command """
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        return p.stdout.readline().strip().decode('utf-8')
    else:
        die("Error retrieving password: `{command}` returned '{error}'".format(command=command,
                                                                               error=p.stderr.read().strip()))


def get_config_path():
    """
    Determine the path to the config file. This will return, in this order of
    precedence:
    - the value of $RCM_NEXUS_CONFIG if set
    - $XDG_CONFIG_HOME/rcm-nexus/config.conf if exists
    - ~/.rcm-nexus/config.conf if exists
    - <dir>/rcm-nexus/config.conf if exists, for dir in $XDG_CONFIG_DIRS
    - $XDG_CONFIG_HOME/rcm-nexus/config.conf otherwise
    """
    if RCM_NEXUS_CONFIG in os.environ:
        return [os.environ[RCM_NEXUS_CONFIG]]
    xdg_config_home = (
            os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
    xdg_config_dirs = (
        (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':'))
    paths = [
        os.path.join(xdg_config_home, 'rcm-nexus.conf'),
        os.path.expanduser("~/.rcm-nexus.conf")]
    paths += [
        os.path.join(d, 'rcm-nexus.conf') for d in xdg_config_dirs]
    return paths
#
# END Bugwarrior code.
###############################################################################
