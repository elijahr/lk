#!/usr/bin/env python

import sys, os
try:
    from setuptools import setup
    kw = {'entry_points':
          """[console_scripts]\nlk = lk:main\n""",
          'zip_safe': False}
except ImportError:
    from distutils.core import setup
    if sys.platform == 'win32':
        print('Note: without Setuptools installed you will have to use "python -m lk ENV"')
        kw = {}
    else:
        kw = {'scripts': ['scripts/lk']}

setup(name='lk',
      version='1.1',
      description='A programmer\'s search tool, parallel and fast',
      author='Elijah Rutschman',
      author_email='elijahr@gmail.com',
      license='MIT',
      py_modules=['lk'],
      keywords='search tool utility grep',
      classifiers=[
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
      ],
      url='http://github.com/elijahr/lk',
      **kw)
