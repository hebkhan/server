import sys
import subprocess
import os
import optparse
import datetime
import urllib2
import webbrowser
import getpass
import re

import commands
dev_appserver_path = os.path.realpath(commands.getoutput("which dev_appserver.py"))
gae_path = os.path.dirname(dev_appserver_path)

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(gae_path))
sys.path.append(os.path.abspath("../offline/"))
import compress
import npm

try:
    import secrets
    hipchat_deploy_token = secrets.hipchat_deploy_token
except Exception, e:
    print "Exception raised while trying to import secrets. Attempting to continue..."
    print repr(e)
    hipchat_deploy_token = None

try:
    from secrets_dev import app_engine_username, app_engine_password
except Exception, e:
    (app_engine_username, app_engine_password) = (None, None)

if hipchat_deploy_token:
    import hipchat.room
    import hipchat.config
    hipchat.config.manual_init(hipchat_deploy_token)

def popen_results(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    return proc.communicate()[0]

def popen_return_code(args, input=None):
    proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    proc.communicate(input)
    return proc.returncode

def get_app_engine_credentials():
    if app_engine_username and app_engine_password:
        print "Using password for %s from secrets.py" % app_engine_username
        return (app_engine_username, app_engine_password)
    else:
        email = raw_input("App Engine Email: ")
        password = getpass.getpass("Password for %s: " % email)
        return (email, password)

def get_app_id():
    f = open("app.yaml", "r")
    contents = f.read()
    f.close()

    app_re = re.compile("^application:\s+(.+)$", re.MULTILINE)
    match = app_re.search(contents)

    return match.groups()[0]

def git_status():
    output = popen_results(['git', 'status', '-s'])
    return len(output) > 0

def git_pull():
    # Pull latest
    popen_results(['git', 'pull'])

    # # Hg up and make sure we didn't hit a merge
    # output = popen_results(['hg', 'up'])
    # lines = output.split("\n")
    # if len(lines) != 2 or lines[0].find("files updated") < 0:
    #     # Ran into merge or other problem
    #     return -1

    return git_version()

def git_version():
    # grab the tip changeset hash
    return popen_results(['git', 'rev-parse', 'HEAD']).strip()[:6]

def git_revision_msg(revision_id):
    return popen_results(['git', 'show', '-s', '--pretty=format:%s', revision_id]).strip()

def check_secrets():
    content = ""

    try:
        f = open("secrets.py", "r")
        content = f.read()
        f.close()
    except:
        return False

    # Try to find the beginning of our production facebook app secret
    # to verify deploy is being sent from correct directory.
    regex = re.compile("^facebook_app_secret = '4362.+'$", re.MULTILINE)
    return regex.search(content)

def check_deps():
    """Check if npm and friends are installed"""
    return npm.check_dependencies()

def compile_handlebar_templates():
    print "Compiling handlebar templates"
    return 0 == popen_return_code([sys.executable,
                                   'deploy/compile_handlebar_templates.py'])

def compress_js():
    print "Compressing javascript"
    compress.compress_all_javascript()

def compress_css():
    print "Compressing stylesheets"
    compress.compress_all_stylesheets()

def compress_exercises():
    print "Compressing exercises"
    subprocess.check_call(["ruby", "khan-exercises/build/pack.rb"])

def compile_templates():
    print "Compiling jinja templates"
    return 0 == popen_return_code([sys.executable, 'deploy/compile_templates.py'])

def prime_cache(version):
    try:
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/autocomplete?q=calc" % (version, get_app_id()))
        resp.read()
        resp = urllib2.urlopen("http://%s.%s.appspot.com/api/v1/topics/library/compact" % (version, get_app_id()))
        resp.read()
        print "Primed cache"
    except urllib2.HTTPError, e:
        print "Error when priming cache"
        print e.read()

def open_browser_to_ka_version(version):
    webbrowser.open("http://%s.%s.appspot.com" % (version, get_app_id()))

def deploy(version, email, password):
    print "Deploying version " + str(version)
    return 0 == popen_return_code(['appcfg.py', '-V', str(version), "-e", email, "--passin", "update", "."], "%s\n" % password)

def main():

    start = datetime.datetime.now()

    parser = optparse.OptionParser()

    parser.add_option('-f', '--force',
        action="store_true", dest="force",
        help="Force deploy even with local changes", default=False)

    parser.add_option('-v', '--version',
        action="store", dest="version",
        help="Override the deployed version identifier", default=git_version())

    parser.add_option('-x', '--no-up',
        action="store_true", dest="noup",
        help="Don't hg pull/up before deploy", default="")

    parser.add_option('-s', '--no-secrets',
        action="store_true", dest="nosecrets",
        help="Don't check for production secrets.py file before deploying", default="")

    parser.add_option('-d', '--dryrun',
        action="store_true", dest="dryrun",
        help="Dry run without the final deploy-to-App-Engine step", default=False)

    parser.add_option('-r', '--report',
        action="store_true", dest="report",
        help="Generate a report that displays minified, gzipped file size for each package element",
            default=False)

    parser.add_option('-n', '--no-npm',
        action="store_false", dest="node",
        help="Don't check for local npm modules and don't install/update them",
        default=True)

    options, args = parser.parse_args()

    if options.node:
        print "Checking for node and dependencies"
        if not check_deps():
            return

    if options.report:
        print "Generating file size report"
        compile_handlebar_templates()
        compress.file_size_report()
        return

    includes_local_changes = git_status()
    if not options.force and includes_local_changes:
        print "Local changes found in this directory, canceling deploy."
        return

    version = -1

    if not options.noup:
        version = git_pull()
        if version <= 0:
            print "Could not find version after 'hg pull', 'hg up', 'hg tip'."
            return

    if not options.nosecrets:
        if not check_secrets():
            print "Stopping deploy. It doesn't look like you're deploying from a directory with the appropriate secrets.py."
            return

    if not compile_templates():
        print "Failed to compile jinja templates, bailing."
        return

    if not compile_handlebar_templates():
        print "Failed to compile handlebars templates, bailing."
        return

    compress_js()
    compress_css()
    compress_exercises()

    if options.version:
        version = options.version
    elif options.noup:
        print 'You must supply a version when deploying with --no-up'
        return

    print "Deploying version " + str(version)

    if not options.dryrun:
        (email, password) = get_app_engine_credentials()
        success = deploy(version, email, password)
        if success:
            open_browser_to_ka_version(version)
            prime_cache(version)

    end = datetime.datetime.now()
    print "Done. Duration: %s" % (end - start)

if __name__ == "__main__":
    main()
