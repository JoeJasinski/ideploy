from __future__ import with_statement
import os
from StringIO import StringIO
from fabric.api import local, settings, abort, run, cd, put, env, sudo
from fabric.colors import green, red
from fabric import context_managers
from jinja2 import Environment, PackageLoader, FileSystemLoader
#python_requirements = ['django','south','django-extensions','django-debug-toolbar',]
class Directory(object):

    def __init__(self, path, create=False):
        self.path = path
        self.create = create

    def get_path(self):
        if hasattr(self.path, '__iter__'):
            local_path = os.path.sep.join(self.path)
        else:
            local_path = self.path
        return local_path


class BaseSetup(object):


    DIR_STRUCTURE = {
       'project_dir':Directory(path='proj', create=True),
       'etc_dir':Directory(path='etc', create=True),
       'log_dir':Directory(path='log', create=True),
       'lib_dir':Directory(path='lib', create=False),
       'bin_dir':Directory(path='bin', create=False),
       'pid_dir':Directory(path='pid', create=True),
    } 

    plugins = [] 

    def __init__(self, env_name, user=None, group="worker", remote_sites_path="", *args, **kwargs):
        self.local_skel_dir = os.path.join(os.path.dirname(os.path.abspath( __file__ )), 'skel')
        self.jinja_env = Environment(loader=FileSystemLoader(self.local_skel_dir))
        self.env_name = env_name
        self.user = user if user else env_name
        self.group = group
        self.remote_sites_path = remote_sites_path 

        self.remote_environment_dir = os.path.join(remote_sites_path, env_name)
        self.remote_proj_dir = os.path.join(self.remote_environment_dir, 
                                            self.DIR_STRUCTURE['project_dir'].get_path())


    def render_template(self, template_path, context): 
        template = self.jinja_env.get_template(template_path)  
        template_file = StringIO()
        template_file.write(template.render(**context))
        template_file.seek(0)
        return template_file

    def render_templates(self, rel_template_paths, context):
       for rel_template_path, mode in rel_template_paths:
           print(green("    render template %s") % rel_template_path)
           rendered_template = self.render_template(template_path=rel_template_path, context=context)
           put(rendered_template, os.path.join(self.remote_environment_dir, rel_template_path), mode=mode) 

    def virtualenv(self, command):
        with context_managers.cd(self.remote_environment_dir):
            result = run('%s && %s' % (os.path.join(self.remote_environment_dir, 'bin', 'activate'), command))
        return result

    def run(self):
        self.setup_venv()
        self.setup_requirements()
        for p in self.plugins:
            if hasattr(self, p):
                getattr(self, p)()
        
    def setup_venv(self):
        with settings(warn_only=True):
            if run("test -d %s" % self.remote_sites_path).failed:
                abort("SIte path must exist before proceeding.")
        with cd(self.remote_sites_path): 
            run("whoami")
            run("pwd")
            run("mkdir %s" % self.env_name)
            #sudo("chown %s:%s %s" % (self.user, self.group, self.env_name))
            sudo("chmod g+ws %s" % (self.env_name))
            #sudo("useradd %s" % user)
        with cd(self.remote_environment_dir):
            print(green("Creating Environment Structure.")) 
            run("virtualenv --no-site-packages .")
            for name,dir in [ (i,j) for i,j in self.DIR_STRUCTURE.items() if j.create ]:
                run("mkdir -p %s"  % (dir.get_path()) )

            #run("git init proj/")
            #run("echo '%s' > proj/requirements.pip" % '\n'.join(python_requirements))

    def setup_requirements(self):
       print(green("Setup Requirements file.")) 
       rel_template_path="requirements.pip"
       rendered_template = self.render_template(template_path=rel_template_path, context={})
       put(rendered_template, os.path.join(self.remote_environment_dir, rel_template_path), mode=0775) 


class SetupNginxMixin(object):

    def __init__(self, *args, **kwargs):
        self.plugins.append("setup_nginx")
        self.DIR_STRUCTURE.update({
          'etc_nginx_conf_dir':Directory(path=['etc', 'nginx','conf'], create=True),
          'etc_nginx_dir':Directory(path=['etc', 'nginx'], create=True),
        }) 

        super(SetupNginxMixin, self).__init__(*args, **kwargs)  

    def setup_nginx(self):
       print(green("Setup Nginx config.")) 

       rel_template_paths=(
          (os.path.join("etc","nginx","django.conf"), 0644),
          (os.path.join("etc","nginx","server.conf"), 0644),
          (os.path.join("etc","nginx","locations.conf"), 0644),
          (os.path.join("etc","nginx","nginx.conf"), 0644),
          (os.path.join("etc","nginx","conf","mime.types"), 0644),
          (os.path.join("etc","nginx","conf","proxy.conf"), 0644),
          (os.path.join("etc","nginx","conf","fastcgi.conf"), 0644),
          (os.path.join("bin","start_nginx.sh"), 0755),
       )
       context = {'ENVIRONMENT_DIR':self.remote_environment_dir, 
                  'ENVIRONMENT_NAME':self.env_name, 
                  'WEB_USER':self.user, 'GROUP':self.group,
                 }

       self.render_templates(rel_template_paths, context)


class SetupGitMixin(object):

    def __init__(self, *args, **kwargs):
        self.plugins.append("setup_git")
        super(SetupGitMixin, self).__init__(*args, **kwargs)  

    def setup_git(self):
        print(green("Setup Git"))
        with cd(self.remote_environment_dir):
            run("git init %s" % self.DIR_STRUCTURE['project_dir'].get_path())
       

class SetupDjangoMixin(object):

    def __init__(self, *args, **kwargs):
        self.plugins.append("setup_django")
        self.DIR_STRUCTURE.update({
          'etc_django_dir':Directory(path=['etc', 'django'], create=True),
        }) 
        super(SetupDjangoMixin, self).__init__(*args, **kwargs)  

    def setup_django(self):
        print(green("Setup Django.")) 
        rel_template_paths=(
           (os.path.join("bin","start_fastcgi.sh"), 0755),
        )
        context = {'ENVIRONMENT_DIR':self.remote_environment_dir,
                   'WEB_USER':self.user, 'GROUP':self.group,
                 }

        self.render_templates(rel_template_paths, context)


class DefaultSetup(SetupDjangoMixin, SetupGitMixin, SetupNginxMixin, BaseSetup):
    pass


def env_setup(env_name, user=None, group="worker", remote_sites_path="/Users/jjasinsk/ideploy/"):
    bs = DefaultSetup(env_name, user=user, group=group, remote_sites_path=remote_sites_path)
    bs.run()

