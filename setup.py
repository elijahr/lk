#!/usr/bin/env python

from distutils.core import setup
from distutils.command.install import install as _install
from distutils.command.build import build as _build
import os
from stat import S_IEXEC, S_IREAD, S_IWRITE, S_IRGRP, S_IROTH, S_IXGRP, S_IXOTH

class install(_install):
    def run(self, *args, **kwargs):
        _install.run(self, *args, **kwargs)
        script_path = os.path.join(self.install_lib, 'lk.py')
        symlink_path = os.path.join(self.install_scripts, 'lk')
        print 'Making symlink %s -> %s' % (script_path, symlink_path)
        try:
            os.symlink(script_path, symlink_path)
        except:
            pass
        os.chmod(symlink_path, S_IEXEC | S_IREAD | S_IWRITE | S_IRGRP | S_IROTH | S_IXGRP | S_IXOTH)

setup(name='lk',
      version='1.0',
      description='A programmer\'s search tool',
      author='Elijah Rutschman',
      author_email='elijahr@gmail.com',
      license='MIT',
      py_modules=['lk'],
      classifiers=['License :: OSI Approved :: MIT License', 'Topic :: System :: Systems Administration', 'Topic :: Utilities'],
      cmdclass={'install': install},
      url = 'http://github.com/elijahr/lk',
      download_url = 'https://github.com/downloads/elijahr/lk/lk-1.0.tar.gz')
