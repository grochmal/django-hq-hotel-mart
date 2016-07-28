from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

import datetime
from pytz import timezone


class Currency(models.Model):
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
    hotel_id = models.PositiveIntegerField(
          _('hotel id')
        , help_text=_('the hotel providing the offer')
        )
    price_usd = models.Decimal(
          _('prince in usd')
        , max_digits=9
        , decimal_places=3  # leave extra resolution for forex
        , help_text=_('price converted to american dollars')
        )
    original_price = models.Decimal(
          _('original price')
        , max_digits=9
        , decimal_places=4  # some currencies may have 4 decimal places
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
    valid_from = models.DateTimeField(
          _('valid from date')
        , help_text=_('date from which this offer is valid')
        )
    valid_to = models.DateTimeField(
          _('valid to date')
        , help_text=_('date when this offer becomes invalid')
        )

    def __str__(self):
        return ( str(self.hotel_id)
               + ' @ '
               + self.valid_from.strftime('%Y%m%d%H%M')
               + ' - '
               + self.valid_to.strftime('%Y%m%d%H%M')
               )

    def get_absolute_url(self):
        return reverse('hq_hotel_mart:valid', kwargs={ 'pk' : self.id })

    class Meta:
        index_together = [
              ( 'hotel_id' , 'valid_from' )
            , ( 'hotel_id' , 'valid_to'   )
            ]
        unique_together = ( 'hotel_id'   , 'breakfast_included'
                          , 'valid_from' , 'valid_to'           )
        verbose_name = _('valid offer')
        verbose_name_plural = _('valid offers')


class Hour(models.Model):
    '''
    Pre-populated date and hour table, used for cross-linking with the Hotel
    Offer table.  This table is not needed in the warehouse it is needed in a
    data mart where it is used as a window cache for user queries.
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
        index_together = [ ( 'day' , 'hour' ) ]
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
    '''
    hour = models.ForeignKey(
          Hour
        , verbose_name=_('hour')
        , related_name='hotel_offer'
        , help_text=_('hour on which this offer is valid')
        )
    # the hotel_id is here so we can make a better index
    hotel_id = models.PositiveIntegerField(
          _('hotel id')
        , help_text=_('the hotel providing the offer')
        )
    offer_id = models.ForeignKey(
          ValidOffer
        , verbose_name=_('offer')
        , related_name='offer_hours'
        , help_text=_('')
        )

