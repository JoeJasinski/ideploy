from __future__ import with_statement
import os
from StringIO import StringIO
from fabric.api import local, settings, abort, run, cd, put, env
from fabric.colors import green, red
from jinja2 import Environment, PackageLoader, FileSystemLoader
#python_requirements = ['django','south','django-extensions','django-debug-toolbar',]

class BaseSetup(object):

    DIR_STRUCTURE = {
      'project_dir':'proj',
      'etc_dir':'etc',
      'etc_django_dir':['etc', 'django'],
      'etc_nginx_dir':['etc', 'nginx'],
      'etc_nginx_conf_dir':['etc', 'nginx','conf'],
      'log_dir':'log',
      'lib_dir':'lib',
      'bin_dir':'bin',
      'pid_dir':'pid',
    }

    CREATE_DIRS = ('project_dir', 'etc_dir','etc_django_dir',
                   'etc_nginx_dir', 'etc_nginx_conf_dir', 'log_dir','pid_dir',) 

    PATH_SEPARATOR = os.path.sep

    def __init__(self, *args, **kwargs):
        self.local_skel_dir = os.path.join(os.path.dirname(os.path.abspath( __file__ )), 'skel')
        self.jinja_env = Environment(loader=FileSystemLoader(self.local_skel_dir))
        

    def render_template(self, template_path, context): 
        template = self.jinja_env.get_template(template_path)  
        template_file = StringIO()
        template_file.write(template.render(**context))
        template_file.seek(0)
        return template_file

    def run(self, env_name, user=None, group="worker", remote_sites_path="/home/joe/testenv/"):
        self.env_name = env_name
        self.user = user
        self.group = group
        self.remote_sites_path = remote_sites_path 

        self.remote_environment_dir = os.path.join(remote_sites_path, env_name)
        self.remote_proj_dir = os.path.join(self.remote_environment_dir, 
                                            self.DIR_STRUCTURE['project_dir'])

        self.setup_venv()
        self.setup_requirements()
        self.setup_nginx()
        
    def setup_venv(self):
        with settings(warn_only=True):
            if run("test -d %s" % self.remote_sites_path).failed:
                abort("SIte path must exist before proceeding.")
        with cd(self.remote_sites_path): 
            run("whoami")
            run("pwd")
            run("mkdir %s" % self.env_name)
            #sudo("useradd %s" % user)
        with cd(self.remote_environment_dir):
            print(green("Creating Environment Structure.")) 
            run("virtualenv --no-site-packages .")
            new_dir_dict = dict((k,self.DIR_STRUCTURE[k]) for k in self.CREATE_DIRS if k in self.DIR_STRUCTURE).items()
            for name, path_part in  new_dir_dict:
                if hasattr(path_part, '__iter__'):
                    local_path = self.PATH_SEPARATOR.join(path_part)
                else: 
                    local_path = path_part
                run("mkdir -p %s"  % (local_path) )

            #run("git init proj/")
            #run("echo '%s' > proj/requirements.pip" % '\n'.join(python_requirements))

    def setup_requirements(self):
       print(green("Setup Requirements file.")) 
       rel_template_path="requirements.pip"
       rendered_template = self.render_template(template_path=rel_template_path, context={})
       put(rendered_template, os.path.join(self.remote_environment_dir, rel_template_path), mode=0775) 

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
       )
       context = {'ENVIRONMENT_DIR':self.remote_environment_dir,
                  'WEB_USER':self.user, 'GROUP':self.group,
                 }
       for rel_template_path, mode in rel_template_paths:
           print(green("    - %s") % rel_template_path)
           rendered_template = self.render_template(template_path=rel_template_path, context=context)
           put(rendered_template, os.path.join(self.remote_environment_dir, rel_template_path), mode=0644) 





def env_setup(env_name, user=None, group="worker", remote_sites_path="/Users/jjasinsk/ideploy/"):
    bs = BaseSetup()
    bs.run(env_name, user, group, remote_sites_path)

