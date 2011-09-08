#!/usr/bin/env python
from setuptools import setup
import sys

meta = dict(name='lk',
    version='1.1',
    description='A programmer\'s search tool, parallel and fast',
    author='Elijah Rutschman',
    author_email='elijahr@gmail.com',
    license='MIT',
    install_requires=["setuptools"],
    py_modules=['lk'],
    keywords='search tool utility grep',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
    ],
    url='http://github.com/elijahr/lk',
    scripts = [
        'scripts/lk'
    ],
)

# Automatic conversion for Python 3 requires distribute.
if False and sys.version_info >= (3,):
    meta.update(dict(
        use_2to3=True,
    ))

setup(**meta)
