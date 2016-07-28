#!/usr/bin/env python3

# distutils have no entry_points, fail if setuptools are not available
from setuptools import setup
import os
import hq_hotel_mart

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# Full list of classifiers can be found here:
# https://pypi.python.org/pypi?%3Aaction=list_classifiers
CLS = \
 [ 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
 , 'Development Status :: 3 - Alpha'
 , 'Environment :: Web Environment'
 , 'Framework :: Django'
 , 'Intended Audience :: System Administrators'
 , 'Operating System :: Unix'
 , 'Programming Language :: Python'
 , 'Topic :: Database :: Database Engines/Servers'
 ]

REQS = [
      'django >= 1.9'
    , 'pytz >= 2016.1'
    ]

CONSOLE_SCRIPTS = [
      'hqm-reload=hq_hotel_mart.command_line:reload_mart'
    ]

setup(
      name             = hq_stage.pkgname
    , description      = hq_stage.__description__
    , version          = hq_stage.__version__
    , author           = hq_stage.__author__
    , author_email     = hq_stage.__author_email__
    , license          = hq_stage.__license__
    , url              = hq_stage.__url__
    , long_description = read('README')
    , packages         = [ 'hq_hotel_mart' ]
    , classifiers      = CLS
    , install_requires = REQS
    , entry_points     = {
          'console_scripts' : CONSOLE_SCRIPTS
        }
    )

