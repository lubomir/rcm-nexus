import yaml
import getpass
import subprocess
import os
import sys

RCM_NEXUS_YAML = 'RCM_NEXUS_YAML'

URL = 'url'
USERNAME = 'username'
PASSWORD = 'password'
SSL_VERIFY = 'ssl-verify'
PREEMPTIVE_AUTH = 'preemptive-auth'
INTERACTIVE = 'interactive'
GA_PROMOTE_PROFILE = "ga-promote-profile"
EA_PROMOTE_PROFILE = "ea-promote-profile"

GA_PROFILE = 'ga'
EA_PROFILE = 'ea'

class NexusConfig(object):
    def __init__(self, name, data, profile_data):
        self.name = name
        self.url = data[URL]
        self.ssl_verify = data.get(SSL_VERIFY, True)
        self.preemptive_auth = data.get(PREEMPTIVE_AUTH, False)
        self.username = data.get(USERNAME, None)
        self.password = data.get(PASSWORD, None)
        self.interactive = data.get(INTERACTIVE, True)
        self.profile_map = profile_data
        self.ga_promote_profile = data.get(GA_PROMOTE_PROFILE)
        self.ea_promote_profile = data.get(EA_PROMOTE_PROFILE)

    def get_password(self):
        if self.password and self.password.startswith("@oracle:"):
            return eval_password(self.username, oracle=self.password, interactive=self.interactive)
        return self.password

    def get_profile_id(self, product, is_ga):
        profiles = self.profile_map.get(product)
        if profiles is None:
            raise Exception( "No staging profiles found for: '%s' in environment: %s" % (product, self.name) )

        quality_level = GA_PROFILE if is_ga is True else EA_PROFILE
        profile_id = profiles.get(quality_level)
        if profile_id is None:
            raise Exception( 
                "ProfileID not configured for quality level: %s in 'profile-maps' of configuration: %s for the product: '%s' (case-sensitive)" % 
                (quality_level, config.name, product) )

        return profile_id

    def get_promote_profile_id(self, is_ga):
        return self.ga_promote_profile if is_ga else self.ea_promote_profile

    def __str__(self):
        return """RCMNexusConfig [
    URL: %(url)s
    SSL verification: %(ssl_verify)s
    use-preemptive-auth: %(preemptive_auth)s
    username: %(username)s
    interactive: %(interactive)s
]""" % self
    
    def __repr__(self):
        return self.__str__()


def die(error_msg):
    print error_msg
    sys.exit(1)

def load(environment, cli_overrides=None, debug=False):
    config_path = get_config_path()
    data = None

    if debug is True:
        print "Loading main config: %s" % config_path
    with open(config_path) as f:
        dataMap = yaml.safe_load(f)
        data=dataMap.get(environment)

    if data is None:
        die("Missing configuration for environment: %s (config file: %s)" % (environment, config_path))

    if cli_overrides is not None:
        data.update(cli_overrides)

    profiles = os.path.join(os.path.dirname(config_path), "%s.yaml" % environment)
    
    if debug is True:
        print "Loading staging profiles: %s" % profiles
    profile_data = {}
    if os.path.exists(profiles):
        with open(profiles) as f:
            profile_data = yaml.safe_load(f)
        if debug is True:
            print "Loaded %d product profiles for: %s" % (len(profile_data.keys()), environment)
    elif debug is True:
        print "WARNING: No profile mappings found in: %s" % profiles

    return NexusConfig(environment, data, profile_data)


def init_config():
    conf_path = get_config_path()
    conf_dir = os.path.dirname(conf_path)
    os.makedirs(conf_dir)

    user = os.environ.get('USER') or 'someuser'
    
    conf = {
        'prod':{
            URL: 'http://prod.nexus.corp.com/nexus',
            USERNAME: user,
            PASSWORD: '@oracle:eval:pass rcm-nexus-prod',
            EA_PROMOTE_PROFILE: "123",
            GA_PROMOTE_PROFILE: "456",
        },
        'stage':{
            URL: 'http://stage.nexus.corp.com/nexus',
            USERNAME: user,
            PASSWORD: '@oracle:eval:pass rcm-nexus-stage',
            EA_PROMOTE_PROFILE: "321",
            GA_PROMOTE_PROFILE: "654",
        }
    }

    profile_data = {
        'MYPRODUCT': {
            GA_PROFILE: '0123456789',
            EA_PROFILE: '9876543210'
        }
    }

    with open(conf_path, 'w') as f:
        yml = yaml.safe_dump(conf)
        f.write("# For more information see: https://mojo.redhat.com/docs/DOC-1010179\n\n")
        f.write(yml)

    for e in conf.keys():
        profile_path = os.path.join(conf_dir, "%s.yaml" % e)
        with open(profile_path, 'w') as f:
            yml = yaml.safe_dump(profile_data)
            f.write("# For more information see: https://mojo.redhat.com/docs/DOC-1010179\n\n")
            f.write(yml)

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
    - the value of $RCM_NEXUS_YAML if set
    - $XDG_CONFIG_HOME/rcm-nexus/config.yaml if exists
    - ~/.rcm-nexus/config.yaml if exists
    - <dir>/rcm-nexus/config.yaml if exists, for dir in $XDG_CONFIG_DIRS
    - $XDG_CONFIG_HOME/rcm-nexus/config.yaml otherwise
    """
    if os.environ.get(RCM_NEXUS_YAML):
        return os.environ[RCM_NEXUS_YAML]
    xdg_config_home = (
        os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
    xdg_config_dirs = (
        (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':'))
    paths = [
        os.path.join(xdg_config_home, 'rcm-nexus', 'config.yaml'),
        os.path.expanduser("~/.rcm-nexus/config.yaml")]
    paths += [
        os.path.join(d, 'rcm-nexus', 'config.yaml') for d in xdg_config_dirs]
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]
#
# END Bugwarrior code.
###############################################################################