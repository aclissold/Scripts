#!/usr/bin/python 
import os
import sys
import shutil
import argparse 
import platform
import threading
import Queue
import subprocess
import logging
import logging.config
import time
import zipfile
import tarfile
import fnmatch
from distutils import dir_util

portlets={ \
    'announcements':'Announcements.war', \
    'courses/courses-portlet-webapp':'CoursesPortlet.war', \
    'calendar':'CalendarPortlet.war', \
    'feedback':'FeedbackPortlet.war', \
    'finaid':'finaid.war', \
    'map':'MapPortlet.war', \
    'mydetails':'mydetails.war', \
    'password':'password.war', \
    'progress':'CourseSchedulePortlet.war', \
    'tester':'uPortalTester.war'}

# prefix
PFX='[build] '

# arguments
parser = argparse.ArgumentParser(description='Tool used to rebuild and deploy uPortal.')
parser.add_argument('--env', help='Set environment.')
parser.add_argument('--build_ant_target', help='Set ant target.')
parser.add_argument('--build_portlet', help='Build specific portlet.')
parser.add_argument('--build_uportal', help='Build uPortal.', action='store_true')
parser.add_argument('--add_admin', help='Add specified user as a uPortal admin.')
parser.add_argument('--clean_tomcat', help='Deletes current Tomcat setup and configures a new setup.')
parser.add_argument('--build_portlets', help='Build specific portlet.', action='store_true')
parser.add_argument('--maven_tests', help='Do maven tests.', action='store_true')
parser.add_argument('--run_updates', help='Do a git pull and update.groovy.', action='store_true')
parser.add_argument('--setup_tomcat', help='Configures Tomcat to work with uPortal.', action='store_true')

args = parser.parse_args()
    
UPORTAL=os.getcwd()

def build():

    # set ENV
    # local is default
    if args.env: ENV=args.env
    else: ENV='local'

    # program[0]=tomcat, program[1]=mvn, program[2]=ant, program[3]=groovy
    programs = check_programs()

    if args.run_updates:
        run_updates(programs[3])

    check_for_files(ENV, programs[0])

    # cleaning tomcat
    if args.setup_tomcat or args.clean_tomcat:
        tomcat_setup(programs[0])

    # adding admin
    if args.add_admin:
        add_an_admin()

    # start uportal build
    if args.build_portlets:
        for portlet in portlets:
            build_portlet(programs, ENV, portlet)

    if args.build_portlet:
        build_portlet(programs, ENV, args.build_portlet)

    if args.build_uportal or args.build_ant_target:
        build_uportal(programs[2], ENV)


def build_uportal(ant, ENV):
    print PFX+'Building & deploying uPortal.'
    print PFX+'Calling on uPortal''s build & deploy process.'
    if args.build_ant_target:
        run_subprocess(ant+' -Denv='+ENV+' '+args.build_ant_target)
    else:
        run_subprocess(ant+' -Denv='+ENV+' '+'clean deploy-ear')
    
    print PFX+'uPortal built successfully.'



def add_an_admin():
    print PFX+'Adding '+args.add_admin+' as a uPortal administrator.'
    os.chdir('uportal-war/src/main/data')
    if args.add_admin not in open('default_entities/group_membership/Portal_Administrators.group-membership.xml').read():
        replace_into_file('<children>\n    <literal>'+args.add_admin+'</literal>','<children>','default_entities/group_membership/Portal_Administrators.group-membership.xml')
    else:
        print PFX+'Admin already exists in uportal-war/src/main/data/default_entities/group_membership/Portal_Administrators.group-membership.xml.'

    if args.add_admin not in open('quickstart_entities/group_membership/Portal_Administrators.group-membership.xml').read():
        replace_into_file('<children>\n    <literal>'+args.add_admin+'</literal>','<children>','quickstart_entities/group_membership/Portal_Administrators.group-membership.xml')
    else:
        print PFX+'Admin already exists in uportal-war/src/main/data/quickstart_entities/group_membership/Portal_Administrators.group-membership.xml.'

    if args.add_admin not in open('quickstart_entities/group_membership/Announcements_Administrators.group-membership.xml').read():
        replace_into_file('<children>\n    <literal>'+args.add_admin+'</literal>','<children>','quickstart_entities/group_membership/Announcements_Administrators.group-membership.xml')
    else:
        print PFX+'Admin already exists in uportal-war/src/main/data/quickstart_entities/group_membership/Announcements_Administrators.group-membership.xml.'

    os.chdir(UPORTAL)


def check_for_files(ENV, tomcat):
    # check for filters/ENV.properties
    if not os.path.isfile('filters/'+ENV+'.properties'):
        print PFX+'filters/'+ENV+'.properties does not exist or cannot be found.'
        sys.exit()
    # check for build.ENV.properties
    if not os.path.isfile('build.'+ENV+'.properties'):
        print PFX+'Cannot find build.'+ENV+'.properties; generating it.'
        shutil.copyfile('build.properties.sample','build.'+ENV+'.properties')
        replace_into_file(programs[0],'@server.home@','build.'+ENV+'.properties')


def run_updates(groovy):
    print PFX+'Running git pull.'
    run_subprocess('git pull')
    print PFX+'Running update.groovy...'
    run_subprocess(groovy+' update.groovy')
    

def build_portlet(programs, ENV, portlet):
    """Builds a portlet."""
    print PFX+'Deploying: '+portlet
    if os.path.exists('work/'+portlet):
        print PFX+'Removing directory work/'+portlet
        shutil.rmtree('work/'+portlet)
        print PFX+'Copying jasig/'+portlet+' to work/'+portlet
        shutil.copytree('jasig/'+portlet,'work/'+portlet)
    else:
        print PFX+'Copying jasig/'+portlet+' to work/'+portlet
        shutil.copytree('jasig/'+portlet,'work/'+portlet)

    if os.path.exists('overlay/'+portlet):
        print PFX+'Copying overlay/'+portlet+' to work/'+portlet
        dir_util.copy_tree('overlay/'+portlet,'work/'+portlet, preserve_mode=True, preserve_times=False)
    
    if portlet == 'courses/courses-portlet-webapp': 
        mvncommand='clean install'
        if args.maven_tests:
            mvncommand+=' -Dmaven.test.skip=false'
        else:
            mvncommand+=' -Dmaven.test.skip=true'
    else: 
        mvncommand='clean package'
        if args.maven_tests:
            mvncommand+=' -Dmaven.test.skip=false'
        else:
            mvncommand+=' -Dmaven.test.skip=true'

    os.chdir('work/'+portlet)
    print PFX+'Now running '+programs[1]+' -Denv='+ENV+' -Dfilters.file='+UPORTAL+'filters/'+ENV+'.properties '+mvncommand
    run_subprocess(programs[1]+' -Denv='+ENV+' -Dfilters.file='+UPORTAL+'/filters/'+ENV+'.properties '+mvncommand)

    os.chdir(UPORTAL)
    print PFX+'Now running '+programs[2]+' -Denv='+ENV+' deployPortletApp -DportletApp=work/'+portlet+'/target/'+portlets[portlet]
    run_subprocess(programs[2]+' -Denv='+ENV+' deployPortletApp -DportletApp=work/'+portlet+'/target/'+portlets[portlet])

    return True

def tomcat_setup(tomcat):
    """Configure Tomcat for uPortal."""
    slash='\\' if 'Windows' in platform.system() else '/'

    if args.clean_tomcat:
        if os.path.exists(tomcat):
            print PFX+'Backing up Tomcat.'
            os.chdir(tomcat+slash)
            os.chdir('..')
            os.rename(tomcat, tomcat+'_bak')

        if zipfile.is_zipfile(args.clean_tomcat):
            try:
                print PFX+'Unzipping '+args.clean_tomcat
                zipp = zipfile.ZipFile(args.clean_tomcat)
                zipp.extractall()
                extracted = zipp.namelist()[0].split(slash)[0]
                zipp.close()
            except:
                print PFX+'Error unzipping file.'
                os.rename(tomcat+'_bak', tomcat)
                sys.exit()
        else:
            try:
                print PFX+'Untarring '+args.clean_tomcat
                tar = tarfile.open(args.clean_tomcat)
                tar.extractall()
                extracted = tar.getnames()[0].split(slash)[0]
                tar.close()
            except:
                print PFX+'Error untarring file.'
                os.rename(tomcat+'_bak', tomcat)
                sys.exit()

        if extracted:
            print PFX+'A fresh copy of Tomcat is being configured.'
            if os.path.exists(tomcat+'_bak'):
                shutil.rmtree(tomcat+'_bak')
            os.rename(extracted, tomcat)

    print PFX+'Updating catalina.properties.'
    os.chdir(tomcat+slash+'conf')
    catalina_prop = find(tomcat, 'catalina.properties')
    if not catalina_prop:
        print PFX+'Cannot find catalina.properties.'
    replace_into_file('shared.loader=${catalina.base}/shared/classes,${catalina.base}/shared/lib/*.jar','shared.loader=', catalina_prop)
    os.remove('catalina.properties_bak')

    print PFX+'Updating context.xml.'
    context_xml = find(tomcat, 'context.xml')
    if not context_xml:
        print PFX+'Cannot find context.xml'
    replace_into_file('<Context sessionCookiePath=\"/\">','<Context>', context_xml)
    os.remove('context.xml_bak')

    print
    os.chdir(UPORTAL)


def check_programs():
    """Check that programs exist and get paths"""

    tomcat=os.getenv('TOMCAT_HOME')
    mvn=os.getenv('M2_HOME')+'/bin/'
    mvn+='mvn.bat' if 'Windows' in platform.system() else 'mvn'
    ant=os.getenv('ANT_HOME')+'/bin/'
    ant+='ant.bat' if 'Windows' in platform.system() else 'ant'
    groovy=os.getenv('GROOVY_HOME')+'/bin/'
    groovy+='groovy.bat' if 'Windows' in platform.system() else 'groovy'

    if not tomcat or \
       not mvn or \
       not ant or \
       not groovy:
        print PFX+'Missing build requirements. Are the TOMCAT_HOME, M2_HOME, ANT_HOME and GROOVY_HOME environmental variables set?'
        sys.exit()
    else:
        print PFX+'Using '+tomcat
        print PFX+'Using '+mvn
        print PFX+'Using '+ant
        print PFX+'Using '+groovy

    return tomcat, mvn, ant, groovy


# Written by Brandon Powell
class AsynQueueRead(threading.Thread):
    """Allows a subprocess to be logged async."""

    def __init__(self, fd, queue):
        assert isinstance(queue, Queue.Queue)
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self.fd=fd
        self.queue=queue

    def run(self):
        for line in iter(self.fd.readline, ''):
            if line[-1]=='\n':
                line=line[:-1]

            self.queue.put(line)

    def done(self):
        return not self.is_alive() and self.queue.empty()


# Written by Brandon Powell
def run_subprocess(cmd):
    #logging.config.fileConfig(os.path.dirname(os.path.realpath(__file__)) + '/logging.conf')
    logging.config.fileConfig(UPORTAL+'/logging.conf')
    log=logging.getLogger('uportal')
    proc=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    queue=Queue.Queue()
    async_queue_stdout=AsynQueueRead(proc.stdout,queue)
    async_queue_stderr=AsynQueueRead(proc.stderr,queue)
    async_queue_stdout.start()
    async_queue_stderr.start()

    while not async_queue_stdout.done() and not async_queue_stderr.done():
        while not queue.empty():
            line=queue.get()
            log.warning(line)

        time.sleep(1)

    async_queue_stdout.join()
    async_queue_stderr.join()
    proc.stdout.close()
    proc.stderr.close()

    proc.poll()

    if proc.returncode:
        print PFX+cmd + ' didn''t quite work.'
        sys.exit()
    return proc.returncode

def find(path, search):
    if not os.path.isdir(path):
        raise IOError

    matches = []
    for root, dirnames, filenames in os.walk(path):
        for fn in fnmatch.filter(filenames, search):
            matches.append(os.path.join(root,fn))

    return matches

# Written by Brandon Powell
def replace_into_file(text, text_to_replace, filenames):
    if not type(filenames) is list:
        tmp = filenames
        filenames = [tmp]

    for filename in filenames:
        if not os.path.isfile(filename):
            raise IOError

        try:
            backup_file(filename)
        except:
            raise IOError

        with open(filename+'_bak') as backup, open(filename,'w') as modified:
            content = backup.readlines()
            for line in content:
                if text_to_replace in line:
                    modified.write(line.replace(text_to_replace, text))
                else:
                    modified.write(line)

# Written by Brandon Powell
def backup_file(filename):
    if not os.path.isfile(filename):
        raise IOError

    shutil.copy2(filename, filename+'_bak')

if __name__ == "__main__":
    build()
