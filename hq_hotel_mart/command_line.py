#!/usr/bin/env python3

import os, sys, getopt, csv, datetime
from pytz import timezone

def settings_path():
    '''
    Before we can call django.setup() we need to know the path to the project
    configuration.  If we cannot find the configuration we can do nothing since
    we cannot even connect to the database.
    '''
    project_path = os.environ.get('HQ_DW_CONF_PATH')
    if not project_path:
        print( 'ERROR: You need to set HQ_DW_CONF_PATH environment variable '
             + 'to the path of the main django project (hq-dw).'
             )
        sys.exit(1)
    sys.path.append(project_path)
    settings = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not settings:
        print( 'ERROR: You need to set DJANGO_SETTINGS_MODULE environment '
             + 'variable to the settings module in the main project (hq-dw).'
             )
        sys.exit(1)

def mart_reload_tables(models, settings):
    pass

def reload_mart():
    '''
    Set up the needed environment, scrutinise the parameters, and, if
    everything went alright call the actual function that will load the table
    data from a file.

    We check that the file exists but it is the responsibility of the called
    function to verify if the file is in the correct format.
    '''
    settings_path()
    import django
    django.setup()
    from django.conf import settings
    from hq_stage import models

    usage = 'hqm-reload [-h]'
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h')
    except getopt.GetopetError as e:
        print(e)
        print(usage)
        sys.exit(2)
    for o, a in opts:
        if '-h' == o:
            print(usage)
            sys.exit(0)
        else:
            assert False, 'unhandled option [%s]' % o

    mart_reload_tables(models, settings)

