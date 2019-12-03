from __future__ import print_function

import contextlib
import getpass
import subprocess
import os
import shutil
import sys
import tempfile
import textwrap

from six.moves import configparser

RCM_NEXUS_CONFIG = 'RCM_NEXUS_CONFIG'
SECTION = "general"

URL = 'url'
USERNAME = 'username'
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

GA_STAGING_PROFILE = 'ga'
EA_STAGING_PROFILE = 'ea'

IS_GA = True
IS_EA = not IS_GA

DEFAULTS = {
    SSL_VERIFY: "yes",
    PREEMPTIVE_AUTH: "no",
    USERNAME: getpass.getuser(),
    PASSWORD: "@oracle:ask_password",
    INTERACTIVE: "yes",
}


class NexusConfig(object):
    def __init__(self, name, data, profile_data):
        self.name = name
        self.url = data.get(name, URL)
        self.ssl_verify = data.getboolean(name, SSL_VERIFY)
        self.preemptive_auth = data.getboolean(name, PREEMPTIVE_AUTH)
        self.username = data.get(name, USERNAME)
        self.password = data.get(name, PASSWORD)
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

    def get_password(self):
        if self.password and self.password.startswith("@oracle:"):
            return eval_password(self.username, oracle=self.password, interactive=self.interactive)
        return self.password

    def get_profile_id(self, product, is_ga):
        profiles = self.profile_map.get(product.upper())
        if profiles is None:
            raise Exception( "No staging profiles found for: '%s' in environment: %s" % (product, self.name) )

        quality_level = GA_STAGING_PROFILE if is_ga is True else EA_STAGING_PROFILE
        profile_id = profiles.get(quality_level)
        if profile_id is None:
            raise Exception(
                "ProfileID not configured for quality level: %s in 'profile-maps' of configuration: %s for the product: '%s' (case-sensitive)" % 
                (quality_level, self.name, product))

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
    print(error_msg)
    sys.exit(1)


def load(environment, debug=False):
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


def _read_remote_repo(repo_url):
    """Clone a git repository and read rcm-nexus.conf from there."""
    tempdir = tempfile.mkdtemp(prefix="rcm-nexus-config-")
    clone_dir = os.path.join(tempdir, "clone")
    try:
        _clone_config_repo(clone_dir, repo_url)
        return _read_config(os.path.join(clone_dir, "rcm-nexus.conf"))
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


def add_product(clone_dir, key, ids):
    print("Adding new configuration entries...")
    parser = configparser.RawConfigParser()
    with open(os.path.join(clone_dir, "rcm-nexus.conf")) as f:
        parser.readfp(f)
    if not parser.has_section(key):
        parser.add_section(key)
    parser.set(key, "ga", ids[IS_GA])
    parser.set(key, "ea", ids[IS_EA])
    with open(os.path.join(clone_dir, "rcm-nexus.conf"), "w") as f:
        parser.write(f)
    print("Commiting the changes...")
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


def init_config():
    conf_path = get_config_path()[0]
    if os.path.exists(conf_path):
        die("%s already exists!" % conf_path)

    parser = configparser.RawConfigParser()
    conf_dir = os.path.dirname(conf_path)
    if not os.path.isdir(conf_dir):
        os.makedirs(conf_dir)
    parser.add_section(SECTION)
    parser.set(SECTION, "; username", "jdoe")
    parser.set(SECTION, "; password",  "@oracle:ask_password")
    parser.set(SECTION, "; config_repo", "git://example.com")
    with open(conf_path, "w") as f:
        parser.write(f)
        print("; For more information see: https://mojo.redhat.com/docs/DOC-1132234", file=f)
        print("; The config_repo options can be defined in system wide config file", file=f)

    return conf_path

#############################################################################
# Shamelessly ripped off and modified from bugwarrior:
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
    :return: Retrieved password (as string)
    """

    password = None
    if interactive and oracle == "@oracle:ask_password":
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
        die("Error retrieving password: `{command}` returned '{error}'".format(command=command, error=p.stderr.read().strip()))

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
