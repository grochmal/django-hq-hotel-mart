from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

import datetime
from pytz import timezone


class Currency(models.Model):
    '''
    The currency data in the mart can be assumed to be correct since it comes
    from the warehouse, there are no fields indicating provenance.

    All fields are exactly the same as the Currency model in the warehouse.
    '''
    code = models.CharField(
          _('code')
        , max_length=3
        , help_text=_('iso 4217 currency code')
        )
    name = models.CharField(
          _('name')
        , max_length=64
        , help_text=_('plain text name of the currency')
        )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('hq_hotel_mart:currency', kwargs={ 'pk' : self.id })

    class Meta:
        verbose_name = _('currency')
        verbose_name_plural = _('currencies')


class Offer(models.Model):
    '''
    The fields are the same as in the warehouse but the indexes are quite
    different.
    '''
    hotel_id = models.PositiveIntegerField(
          _('hotel id')
        , help_text=_('the hotel providing the offer')
        )
    price_usd = models.DecimalField(
          _('prince in usd')
        , max_digits=20
        , decimal_places=10
        , help_text=_('price converted to american dollars')
        )
    original_price = models.DecimalField(
          _('original price')
        , max_digits=20
        , decimal_places=10
        , help_text=_('original price of the offer')
        )
    original_currency = models.ForeignKey(
          Currency
        , verbose_name=_('original currency')
        , related_name='%(class)s_set'
        , help_text=_('currency of the original price')
        )
    breakfast_included = models.BooleanField(
          _('breakfast included')
        , help_text=_('whether breakfast is included in the price')
        )
    valid_from_date = models.DateField(
          _('valid from date')
        , help_text=_('date from which this offer is valid')
        )
    valid_to_date = models.DateField(
          _('valid to date')
        , help_text=_('date when this offer becomes invalid')
        )
    valid_from_time = models.TimeField(
          _('valid from time')
        , help_text=_('time of the day this offer becomes valid')
        )
    valid_to_time = models.TimeField(
        _('valid to time')
        , help_text=_('time of day this offer becomes invalid')
        )
    checkin_date = models.DateField(
          _('check-in date')
        , help_text=_('date the guest must check-in')
        )
    checkout_date = models.DateField(
          _('check-out date')
        , help_text=_('date the guest must check-out')
        )

    def __str__(self):
        return ( str(self.hotel_id)
               + ' @ '
               + self.valid_from.strftime('%Y%m%d%H%M')
               + ' - '
               + self.valid_to.strftime('%Y%m%d%H%M')
               )

    def get_absolute_url(self):
        return reverse('hq_hotel_mart:offer', kwargs={ 'pk' : self.id })

    class Meta:
        # The first two indexes may be useful is we want to join two offers
        # together.  For example if we query for a check-in 2016-11-12 and
        # check-out 2016-11-30 we may query:
        #
        #     Query 1: hotel_id == 3 AND check-in  == 2016-11-12
        #     Query 2: hotel_id == 3 AND check-out == 2016-11-12
        #
        # And then join both queries to find two separate offers that fit the
        # bill:
        #
        #     Query 1.check-out == Query 2.check-in
        #
        # This would be a very useful feature to have.
        index_together = [
              ( 'hotel_id' , 'checkin_date'  )
            , ( 'hotel_id' , 'checkout_date' )
            , ( 'hotel_id' , 'checkin_date'  , 'checkout_date' )
            ]
        unique_together = ( 'hotel_id'     , 'breakfast_included'
                          , 'checkin_date' , 'checkout_date'      )
        verbose_name = _('offer')
        verbose_name_plural = _('offers')


class Hour(models.Model):
    '''
    Pre-populated date and hour table, used for cross-linking with the Hotel
    Offer table.  This table is not needed in the warehouse it is needed in a
    data mart where it is used as a window cache for user queries.

    This tables is only used to populate Hotel Offer, the cache table.
    '''
    day = models.DateField(
          _('day')
        , help_text=_('the day for links')
        )
    hour = models.PositiveSmallIntegerField(
          _('hour')
        , help_text=_('the hour of the day')
        )

    def __str__(self):
        return str(self.day) + '@' + ('%02i' % self.hour)

    def get_absolute_url(self):
        return reverse('hq_hotel_mart:hour', kwargs={ 'pk' : self.id })

    class Meta:
        # unique together produces an index on the columns
        unique_together = [ ( 'day' , 'hour' ) ]
        verbose_name = _('hour')
        verbose_name_plural = _('hours')


class HotelOffer(models.Model):
    '''
    This is heavily modified from the assignment, since the uniqueness
    condition in there (check-in, check-out, source, breakfast) has long been
    lost (check-in and check-out only exist in the staging area).

    Instead of making a single flag for the existence of an offer, we link the
    offers.  And, instead of populating this table for all hours we put the
    date-hour pair in their own table (Hour).  This way we can walk the Hour
    table and join against all available offers for the period.

    This is not the type of query that needs to be performed in a warehouse,
    this table is needed for data marts to copy from.

    This table is pretty much a huge cache.
    '''
    hour = models.ForeignKey(
          Hour
        , verbose_name=_('hour')
        , related_name='hotel_offers'
        , help_text=_('hour on which this offer is valid')
        )
    # the hotel_id is here so we can make a better index
    hotel_id = models.PositiveIntegerField(
          _('hotel id')
        , help_text=_('the hotel providing the offer')
        )
    offer_id = models.ForeignKey(
          Offer
        , verbose_name=_('offer')
        , related_name='offer_hours'
        , help_text=_('the offer that is valid at this point in time')
        )

    def __str__(self):
        return str(self.hotel_id) + ' on ' + str(hour)

    def get_absolute_url(self):
        return reverse('hq_hotel_mart:hotel', kwargs={ 'pk' : self.id })

    class Meta:
        # this table is a huge cache we only need one index,
        # the query entry point
        unique_together = [ ( 'hour' , 'hotel_id' , 'offer_id' ) ]
        verbose_name = _('hotel offer')
        verbose_name_plural = _('hotel offers')

