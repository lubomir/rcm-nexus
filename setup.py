#!/usr/bin/env python2

from setuptools import setup, find_packages
import sys

# handle python 3
if sys.version_info >= (3,):
    use_2to3 = True
else:
    use_2to3 = False

version='1.4.0'

f = open('README.rst')
long_description = f.read().strip()
long_description = long_description.split('split here', 1)[1]
f.close()

test_deps=[
    "Mock",
    "nose",
    "responses",
  ]

extras = {
  'test':test_deps,
  'build':['tox'],
  'ci':['coverage']
}

setup(
    zip_safe=True,
    use_2to3=use_2to3,
    name='rcm-nexus',
    version=version,
    long_description=long_description,
    classifiers=[
      "Development Status :: 3 - Alpha",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: GNU General Public License (GPL)",
      "Programming Language :: Python :: 2",
      "Programming Language :: Python :: 3",
      "Topic :: Software Development :: Build Tools",
      "Topic :: Utilities",
    ],
    keywords='nexus maven build java ',
    author='John Casey',
    author_email='jdcasey@commonjava.org',
    url='https://mojo.redhat.com/docs/DOC-1132234',
    license='GPLv3+',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    install_requires=[
      "requests",
      "lxml",
      "click",
      "six",
    ],
    tests_require=test_deps,
    extras_require=extras,
    test_suite="tests",
    entry_points={
      'console_scripts': [
        'nexus-push = rcm_nexus:push',
        'nexus-rollback = rcm_nexus:rollback',
        'nexus-init = rcm_nexus:init',
      ],
    }
)

