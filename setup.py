from setuptools import setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop
import os


def _post_install(libname, libpath):
    from JumpScale9 import j  # here its still the boostrap JumpScale9
    j.tools.jsloader.copyPyLibs()

    # ensure plugins section in config
    if 'plugins' not in j.application.config:
        j.application.config['plugins'] = {}

    # add this plugin to the config
    c = j.core.state.configGet('plugins', defval={})
    c[libname] = libpath
    j.core.state.configSet('plugins', c)

    j.tools.jsloader.generatePlugins()
    j.tools.executorLocal.executeRaw('apt-get install net-tools')


class install(_install):

    def run(self):
        _install.run(self)
        libname = self.config_vars['dist_name']
        libpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), libname)
        self.execute(_post_install, (libname, libpath), msg="Running post install task")


class develop(_develop):

    def run(self):
        _develop.run(self)
        libname = self.config_vars['dist_name']
        libpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), libname)
        self.execute(_post_install, (libname, libpath), msg="Running post install task")


setup(
    name='JumpScale9',
    version='9.0.0',
    description='Automation framework for cloud workloads',
    url='https://github.com/Jumpscale/core9',
    author='GreenItGlobe',
    author_email='info@gig.tech',
    license='Apache',
    packages=['JumpScale9'],
    install_requires=[
        'g8core>=1.0.0',
        'GitPython>=2.1.3',
        'click>=6.7',
        'colored_traceback',
        'colorlog>=2.10.0',
        'httplib2>=0.10.3',
        'ipython>=6.0.0',
        'libtmux>=0.7.1',
        'netaddr>=0.7.19',
        'path.py>=10.3.1',
        'pystache>=0.5.4',
        'python-dateutil>=2.6.0',
        'pytoml>=0.1.12',
        'redis>=2.10.5',
        'requests>=2.13.0'
    ],
    cmdclass={
        'install': install,
        'develop': develop,
        'developement': develop
    },
    scripts=[
        'cmds/js9_code',
        'cmds/js9_docker',
        'cmds/js9_docs',
    ],
)
