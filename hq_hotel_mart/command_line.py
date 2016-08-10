#!/usr/bin/env python3

import os, sys, getopt, datetime, re
from pytz import timezone

# Importing static exceptions is alright, even before django.setup()
from django.db import IntegrityError


# Trivial caches, used when we load several offers.
HOURS = {}
CURRENCIES = {}

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

def dict_with_fields(org_dict, fields):
    new_dict = {}
    for f in fields:
        if f in org_dict:
            new_dict[f] = org_dict[f]
        else:
            return {}
    return new_dict

def save_object(params, model):
    '''
    Save the object to the database whilst ignoring duplicates, i.e. if such an
    object is already there consider it to be the same one and return it.
    '''
    try:
        obj = model(**params)
        obj.save()
        return obj
    except IntegrityError:
        # We may have hit a duplicate, check it further
        pass

    # Note: This uses `_unique` which is a django internal,
    # this code may break in new revisions of django.
    uniqf = [ [x.name]
              for x in model._meta.get_fields()
              if hasattr(x, '_unique') and x._unique ]
    uniques = list(model._meta.unique_together) + uniqf
    for uniq in uniques:
        uniq_params = dict_with_fields(params, uniq)
        if not uniq_params:
            # Something horrible happened, fail
            return None
        try:
            obj = model.objects.get(**uniq_params)
            # We have a duplicate, return it
            return obj
        except model.DoesNotExist:
            pass
    return None

def load_currency(mmod, wmod, settings):
    '''
    This is a small table, just load it in full.
    '''
    global CURRENCIES
    qs = wmod.Currency.objects.all()
    for wcur in qs:
        params = { 'code' : wcur.code , 'name' : wcur.name }
        currency = save_object(params, mmod.Currency)
        if currency:
            CURRENCIES[currency.code] = currency
        yield params, currency

def get_hour(dt, mmod):
    '''
    Small cache manager, seriously, we should be using redis for caches.
    '''
    global HOURS
    if dt in HOURS:
        return HOURS[dt]
    try:
        hour = mmod.Hour.objects.get(day=dt.date(), hour=dt.time().hour)
    except mmod.Hour.DoesNotExist:
        # We should never get here!
        return None
    HOURS[dt] = hour
    return hour

def get_currency(wcur, mmod):
    '''
    Cache for warehouse currency to mart currency conversion.
    '''
    global CURRENCIES
    if wcur.code in CURRENCIES:
        return CURRENCIES[wcur.code]
    try:
        mcur = mmod.Currency.objects.get(code=wcur.code)
    except mmod.Currency.DoesNotExist:
        # We should never get here!
        return None
    CURRENCIES[mcur.code] = mcur
    return mcur

def load_hotel_offer(offer, days, date_fr, date_to, mmod, wmod, settings):
    '''
    Build the cache of all offers within each hour.  This will make API
    queries trivial (and quick :) ).
    '''
    dl = datetime.timedelta(hours=1)
    curr = date_fr
    # The end timestamp is already shifted on hour forward,
    # therefore we will alway use an inclusive between.
    while curr < date_to:
        hour = get_hour(curr, mmod)
        if not hour:
            yield None,None
            continue
        params = { 'hour'     : hour
                 , 'hotel_id' : offer.hotel_id
                 , 'days'     : days
                 , 'offer_id' : offer
                 }
        hotel_offer = save_object(params, mmod.HotelOffer)
        yield params, hotel_offer
        curr += dl

def load_offer(mmod, wmod, settings):
    '''
    We only care about the offers that are within the years loaded in the mart,
    older or newer offers are simply ignored.  Once time advances we will need
    to reload the mart with new data, whilst throwing old data away (the data
    is in the warehouse anyway).
    '''
    first_date = mmod.Hour.objects.all().order_by('day', 'hour').first()
    last_date = mmod.Hour.objects.all().order_by('day', 'hour').last()
    if not first_date or not last_date:
        # No dates loaded!  Go load them.
        yield None, None
    df = datetime.datetime.combine( first_date.day
                                  , datetime.time(hour=first_date.hour ) )
    dt = datetime.datetime.combine( last_date.day
                                  , datetime.time(hour=last_date.hour ) )
    # consider the last hour to be always in range
    dt += datetime.timedelta(hours=1)
    for offer in wmod.ValidOffer.objects.filter(invalid=False):
        ofdatef = datetime.datetime.combine( offer.valid_from_date
                                           , offer.valid_from_time )
        ofdatet = datetime.datetime.combine( offer.valid_to_date
                                           , offer.valid_to_time )
        if df > ofdatet or dt < ofdatef:
            # offer too old or too into the future
            continue
        days_delta = offer.checkout_date - offer.checkin_date
        days = days_delta.days
        if 0 >= days:
            # This is an offer of purely statistical value, no need to be here.
            # Maybe we should invalidate these cases in the warehouse already?
            # It would be slightly faster that way.
            continue
        date_fr = ofdatef
        if ofdatef < df:
            date_fr = df
        date_to = ofdatet + datetime.timedelta(hours=1)
        if ofdatet > dt:
            date_to = dt
        # we need to add the fields by hand because the warehouse
        # has extra housekeeping data in the models
        mcurrency = get_currency(offer.original_currency, mmod)
        offer_params = { 'hotel_id'           : offer.hotel_id
                       , 'price_usd'          : offer.price_usd
                       , 'original_price'     : offer.original_price
                       , 'original_currency'  : mcurrency
                       , 'breakfast_included' : offer.breakfast_included
                       , 'valid_from_date'    : offer.valid_from_date
                       , 'valid_to_date'      : offer.valid_to_date
                       , 'valid_from_time'    : offer.valid_from_time
                       , 'valid_to_time'      : offer.valid_to_time
                       , 'checkin_date'       : offer.checkin_date
                       , 'checkout_date'      : offer.checkout_date
                       }
        mart_offer = save_object(offer_params, mmod.Offer)
        if not mart_offer:
            yield offer_params, mart_offer
            continue
        else:
            yield offer_params, mart_offer
        # We have an offer saved to the database, make the hour cache
        for p,hotel_hour in load_hotel_offer( mart_offer
                                            , days
                                            , date_fr
                                            , date_to
                                            , mmod
                                            , wmod
                                            , settings
                                            ):
            yield p,hotel_hour

def mart_load_tables(mmod, wmod, settings):
    for p,cur in load_currency(mmod, wmod, settings):
        yield p,cur
    for p,offer in load_offer(mmod, wmod, settings):
        yield p,offer

def mart_load_year(year, mmod, wmod, settings):
    '''
    Don't bother checking if we already have this year in the database, we will
    not be able to add duplicate dates because of the unique constraints.
    '''
    zone = timezone(settings.TIME_ZONE)
    nzdf = datetime.datetime.strptime('%s-01-01' % year, '%Y-%m-%d')
    nzdt = datetime.datetime.strptime('%s-12-31' % year, '%Y-%m-%d')
    df = zone.localize(nzdf)
    dt = zone.localize(nzdt)
    dt += datetime.timedelta(days=1)
    dl = datetime.timedelta(hours=1)
    curr = df
    while curr < dt:
        yield curr
        curr += dl

def reload_mart():
    '''
    Scrutinise the parameters, and takes data from the warehouse.  Most of the
    time we will want to ignore duplicates and add new rows, but, from time to
    time, it is useful to truncate the tables in the mart to reduce the number
    of rows.
    '''
    settings_path()
    import django
    django.setup()
    from django.conf import settings
    from hq_warehouse import models as wmod
    from hq_hotel_mart import models as mmod

    usage = 'hqm-reload [-hvt]'
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hvt')
    except getopt.GetopetError as e:
        print(e)
        print(usage)
        sys.exit(2)
    truncate = False
    verbose = False
    for o, a in opts:
        if '-h' == o:
            print(usage)
            sys.exit(0)
        elif '-t' == o:
            truncate = True
        elif '-v' == o:
            verbose = True
        else:
            assert False, 'unhandled option [%s]' % o

    if truncate:
        # We cannot use direct SQL because we need the model to route itself to
        # the correct database instance.  Although this may be slow.
        print('WARNING: Truncating tables')
        mmod.Currency.objects.all().delete()
        mmod.Offer.objects.all().delete()
        mmod.HotelOffer.objects.all().delete()
    for p,obj in mart_load_tables(mmod, wmod, settings):
        if obj and verbose:
            print('SUCCESS', obj.__class__.__name__, obj)
        elif not obj:
            print('FAILURE', p)
        # else stay silent

def populate_hours():
    '''
    Builds the hours table for one entire year, several years can be populated
    at the same time in the mart.  It is also possible to truncate the table,
    this is useful when old offers do not make sense anymore to be in the mart.
    '''
    settings_path()
    import django
    django.setup()
    from django.conf import settings
    from hq_warehouse import models as wmod
    from hq_hotel_mart import models as mmod

    usage = 'hqm-pop-hours [-hvt] -y <4 digit year>'
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hvty:')
    except getopt.GetopetError as e:
        print(e)
        print(usage)
        sys.exit(2)
    truncate = False
    verbose = False
    year = None
    for o, a in opts:
        if '-h' == o:
            print(usage)
            sys.exit(0)
        elif '-t' == o:
            truncate = True
        elif '-v' == o:
            verbose = True
        elif '-y' == o:
            if not re.search(r'^\d{4}$', a):
                print(usage)
                sys.exit(1)
            else:
                year = a
        else:
            assert False, 'unhandled option [%s]' % o
    if not year:
        print(usage)
        sys.exit(1)
    if truncate:
        print('WARNING: Truncating tables')
        mmod.Hour.objects.all().delete()
    for date_hour in mart_load_year(year, mmod, wmod, settings):
        hour = save_object( { 'day'  : date_hour.date()
                            , 'hour' : date_hour.time().hour
                            }
                          , mmod.Hour
                          )
        if hour and verbose:
            print('SUCCESS', hour)
        elif not hour:
            print('FAILURE', date_hour.strftime('%Y-%m-%dT%H'))
        # else stay silent

