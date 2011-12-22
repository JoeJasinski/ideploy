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


class Settings(object):

   DIR_STRUCTURE = {}
   MODULES = {}
   REQUIREMEntS = {}
   
   def __init__(self, *args, **kwargs):
       self.DIR_STRUCTURE = {}
       self.MODULES = {}
       self.REQUIREMENTS = {}


class BaseSetup(object):

    plugins = [] 
    
    def __init__(self, env_name, user=None, group="worker", remote_sites_path="", *args, **kwargs):
    
        env_settings = Settings()
        
        env_settings.DIR_STRUCTURE = {
           'project_dir':Directory(path='proj', create=True),
           'etc_dir':Directory(path='etc', create=True),
           'log_dir':Directory(path='log', create=True),
           'lib_dir':Directory(path='lib', create=False),
           'bin_dir':Directory(path='bin', create=False),
           'pid_dir':Directory(path='pid', create=True),
        }
        
        
        env_settings.local_skel_dir = os.path.join(os.path.dirname(os.path.abspath( __file__ )), 'skel')
        env_settings.jinja_env = Environment(loader=FileSystemLoader(env_settings.local_skel_dir))
        env_settings.env_name = env_name
        env_settings.user = user if user else env_name
        env_settings.group = group
        env_settings.remote_sites_path = remote_sites_path 
    
        env_settings.remote_environment_dir = os.path.join(remote_sites_path, env_name)
        env_settings.remote_proj_dir = os.path.join(env_settings.remote_environment_dir, 
                                            env_settings.DIR_STRUCTURE['project_dir'].get_path())
        self.env_settings = env_settings 
    
    def render_template(cls, env_settings, template_path, context): 
        template = env_settings.jinja_env.get_template(template_path)  
        template_file = StringIO()
        template_file.write(template.render(**context))
        template_file.seek(0)
        return template_file
    
    def render_templates(cls, env_settings, rel_template_paths, context):
       for rel_template_path, mode in rel_template_paths:
           print(green("    render template %s") % rel_template_path)
           rendered_template = cls.render_template(template_path=rel_template_path, context=context)
           put(rendered_template, os.path.join(env_settings.remote_environment_dir, rel_template_path), mode=mode) 
    
    def virtualenv(self, env_settings, command):
        with context_managers.cd(env_settings.remote_environment_dir):
            result = run('%s && %s' % (os.path.join(env_settings.remote_environment_dir, 'bin', 'activate'), command))
        return result
    
    def run(self):
        env_settings = self.env_settings 
        unique_cls = []
        for cls in [ action.im_class for action in self.action_list ] :
            if cls not in unique_cls:
                unique_cls.append(cls)
                env_settings = cls.register(env_settings)
        
        self.setup_venv(env_settings)
        self.setup_requirements(env_settings)
        for p in self.action_list:
            p(env_settings)
        
    def setup_venv(self, env_settings):
        with settings(warn_only=True):
            if run("test -d %s" % env_settings.remote_sites_path).failed:
                abort("SIte path must exist before proceeding.")
        with cd(env_settings.remote_sites_path): 
            run("whoami")
            run("pwd")
            run("mkdir %s" % env_settings.env_name)
            #sudo("chown %s:%s %s" % (self.user, self.group, self.env_name))
            sudo("chmod g+ws %s" % (env_settings.env_name))
            #sudo("useradd %s" % user)
        with cd(env_settings.remote_environment_dir):
            print(green("Creating Environment Structure.")) 
            run("virtualenv --no-site-packages .")
            for name,dir in [ (i,j) for i,j in env_settings.DIR_STRUCTURE.items() if j.create ]:
                run("mkdir -p %s"  % (dir.get_path()) )

            #run("git init proj/")
            #run("echo '%s' > proj/requirements.pip" % '\n'.join(python_requirements))

    def setup_requirements(self, env_settings):
        print(green("Setup Requirements file.")) 
        rel_template_path="requirements.pip"
        rendered_template = self.render_template(env_settings, template_path=rel_template_path, context={})
        put(rendered_template, os.path.join(env_settings.remote_environment_dir, rel_template_path), mode=0775) 


class SetupNginxModule(object):
    
    name = "setup_nginx"
    description = "Setup Nginx"
    dir_structure = {
          'etc_nginx_conf_dir':Directory(path=['etc', 'nginx','conf'], create=True),
          'etc_nginx_dir':Directory(path=['etc', 'nginx'], create=True),
    }

    @classmethod
    def register(cls, env_settings, *args, **kwargs):
        env_settings.MODULES.update({cls.name:cls.description})
        env_settings.DIR_STRUCTURE.update(cls.dir_structure) 
        return env_settings


    @classmethod
    def run_core(cls, env_settings):
    
        print(green(cls.description)) 
        
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
        context = {'ENVIRONMENT_DIR':env_settings.remote_environment_dir, 
                  'ENVIRONMENT_NAME':env_settings.env_name, 
                  'WEB_USER':env_settings.user, 'GROUP':env_settings.group,
                 }
        
        cls.render_templates(env_settings, rel_template_paths, context)


class SetupGitModule(object):

    name = "setup_git"
    description = "Setup Git"
	
    @classmethod	
    def register(cls, env_settings, *args, **kwargs):
        env_settings.MODULES.update({cls.name:cls.description})
        return env_settings

    @classmethod	
    def run_core(cls, env_settings):
        print(green(cls.description))
        with cd(env_settings.remote_environment_dir):
            run("git init %s" % env_settings.DIR_STRUCTURE['project_dir'].get_path())
       

class SetupDjangoModule(object):

    name = "setup_django"
    description = "Setup Django"

    dir_structure = {
          'etc_django_dir':Directory(path=['etc', 'django'], create=True),
    }

    @classmethod	
    def register(cls, env_settings, *args, **kwargs):
        env_settings.MODULES.update({cls.name:cls.description})
        env_settings.DIR_STRUCTURE.update(cls.dir_structure) 
        return env_settings 

    @classmethod	
    def run_core(cls, env_settings):
        print(green(cls.description)) 
        rel_template_paths=(
           (os.path.join("bin","start_fastcgi.sh"), 0755),
        )
        context = {'ENVIRONMENT_DIR':env_settings.remote_environment_dir,
                   'WEB_USER':env_settings.user, 'GROUP':env_settings.group,
                 }

        cls.render_templates(env_settings, rel_template_paths, context)


class DefaultSetup(BaseSetup):
    
    action_list = [
        SetupNginxModule.run_core, 
        SetupGitModule.run_core, 
        SetupDjangoModule.run_core
    ]


def env_setup(env_name, user=None, group="worker", remote_sites_path="/Users/jjasinsk/ideploy/"):
    bs = DefaultSetup(env_name, user=user, group=group, remote_sites_path=remote_sites_path)
    bs.run()

