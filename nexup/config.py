import yaml
import getpass
import subprocess
import os
import sys

NEXUP_YAML='NEXUP_YAML'

URL='url'
USERNAME='username'
PASSWORD='password'
SSL_VERIFY='ssl-verify'
PREEMPTIVE_AUTH='preemptive-auth'
INTERACTIVE='interactive'

class NexusConfig(object):
    def __init__(self, data):
        self.url = data[URL]
        self.ssl_verify = data.get(SSL_VERIFY, True)
        self.preemptive_auth = data.get(PREEMPTIVE_AUTH, False)
        self.username = data.get(USERNAME, None)
        self.password = data.get(PASSWORD, None)
        self.interactive = data.get(INTERACTIVE, True)

    def get_password(self):
        if self.password and self.password.startswith("@oracle:"):
            return eval_password(self.username, oracle=self.password, interactive=self.interactive)
        return self.password

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

	return NexusConfig(data)


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
    - the value of $NEXUP_YAML if set
    - $XDG_CONFIG_HOME/nexup/config.yaml if exists
    - ~/.nexup/config.yaml if exists
    - <dir>/nexup/config.yaml if exists, for dir in $XDG_CONFIG_DIRS
    - $XDG_CONFIG_HOME/nexup/config.yaml otherwise
    """
    if os.environ.get(NEXUP_YAML):
        return os.environ[NEXUP_YAML]
    xdg_config_home = (
        os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'))
    xdg_config_dirs = (
        (os.environ.get('XDG_CONFIG_DIRS') or '/etc/xdg').split(':'))
    paths = [
        os.path.join(xdg_config_home, 'nexup', 'config.yaml'),
        os.path.expanduser("~/.nexup/config.yaml")]
    paths += [
        os.path.join(d, 'nexup', 'config.yaml') for d in xdg_config_dirs]
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]
#
# END Bugwarrior code.
###############################################################################