import yaml
import getpass
import subprocess
import os
import sys

RCM_NEXUS_YAML='RCM_NEXUS_YAML'

URL='url'
USERNAME='username'
PASSWORD='password'
SSL_VERIFY='ssl-verify'
PREEMPTIVE_AUTH='preemptive-auth'
INTERACTIVE='interactive'
PROFILE_MAP = 'profile-map'

GA_PROFILE = 'ga'
EA_PROFILE = 'ea'

class NexusConfig(object):
    def __init__(self, name, data):
        self.name = name
        self.url = data[URL]
        self.ssl_verify = data.get(SSL_VERIFY, True)
        self.preemptive_auth = data.get(PREEMPTIVE_AUTH, False)
        self.username = data.get(USERNAME, None)
        self.password = data.get(PASSWORD, None)
        self.interactive = data.get(INTERACTIVE, True)
        self.profile_map = data.get(PROFILE_MAP, {})

    def get_password(self):
        if self.password and self.password.startswith("@oracle:"):
            return eval_password(self.username, oracle=self.password, interactive=self.interactive)
        return self.password

    def get_profile_id(self, product, is_ga):
        profiles = self.profile_map.get(product)
        if profiles is None:
            raise Exception( "Product %s not configured in 'profile-maps' of configuration: %s (case-sensitive)" % (product, config.name) )

        quality_level = GA_PROFILE if is_ga is True else EA_PROFILE
        profile_id = profiles.get(quality_level)
        if profile_id is None:
            raise Exception( 
                "ProfileID not configured for quality level: %s in 'profile-maps' of configuration: %s for the product: '%s' (case-sensitive)" % 
                (quality_level, config.name, product) )

        return profile_id


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

def load(environment, cli_overrides=None):
	config_path = get_config_path()
	data = None
	with open(config_path) as f:
		dataMap = yaml.safe_load(f)
		data=dataMap.get(environment)

	if data is None:
		die("Missing configuration for environment: %s (config file: %s)" % (environment, config_path))

	if cli_overrides is not None:
		data.update(cli_overrides)

	return NexusConfig(environment, data)


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