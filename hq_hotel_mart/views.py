from django.shortcuts import get_object_or_404
from django import http
from django.views import generic
from django.conf import settings

import datetime

from . import models
from .util import JSONResponseMixin


class DocView(generic.TemplateView):
    template_name = 'hq_hotel_mart/doc.html'


class HqHotelMartListView(generic.ListView):
    template_name = 'hq_main/list.html'
    context_object_name = 'object_list'
    paginate_by = 12  # I just like the number 12


class CurrencyListView(HqHotelMartListView):
    model = models.Currency


class OfferListView(HqHotelMartListView):
    model = models.Offer


class HourListView(HqHotelMartListView):
    model = models.Hour


class HotelOfferListView(HqHotelMartListView):
    model = models.HotelOffer


class CurrencyView(generic.DetailView):
    model = models.Currency
    template_name = 'hq_hotel_mart/currency.html'
    context_object_name = 'currency'


class OfferView(generic.DetailView):
    model = models.Offer
    template_name = 'hq_hotel_mart/offer.html'
    context_object_name = 'offer'


class HourView(generic.DetailView):
    model = models.Hour
    template_name = 'hq_hotel_mart/hour.html'
    context_object_name = 'hour'


class HotelOfferView(generic.DetailView):
    model = models.HotelOffer
    template_name = 'hq_hotel_mart/hotel_offer.html'
    context_object_name = 'hotel_offer'


class HotelOfferView(generic.DetailView):
    model = models.HotelOffer
    template_name = 'hq_hotel_mart/hotel_offer.html'
    context_object_name = 'hotel_offer'


class ApiView(JSONResponseMixin, generic.View):
    '''
    Our API endpoint.  Uses GET for queries since data state never changes upon
    queries, POST (and, just in case, PUT) is explicitly disabled.
    '''

    def post(self, request, *args, **kwargs):
        return http.HttpResponseForbidden()  # 403

    def put(self, request, *args, **kwargs):
        return http.HttpResponseForbidden()  # 403

    def get(self, request, *args, **kwargs):
        '''
        Be forgiving with argument naming.  But do not forgive logical errors
        in the requests as:

        *   check into a hotel for zero or negative number of days
        *   query an offer in the past (query_at after check dates)
        '''
        query_at = (  request.GET.get('queryAt')
                   or request.GET.get('queryat')
                   or request.GET.get('query_at') )
        hotel_id = (  request.GET.get('hotelId')
                   or request.GET.get('hotelid')
                   or request.GET.get('hotel_id') )
        checkin = (  request.GET.get('checkinDate')
                  or request.GET.get('checkindate')
                  or request.GET.get('checkin_date') )
        checkout = (  request.GET.get('checkoutDate')
                   or request.GET.get('checkoutdate')
                   or request.GET.get('checkout_date') )
        if not query_at or not hotel_id or not checkin or not checkout:
            return http.HttpResponseBadRequest()  # 400
        try:
            # all these raise value error
            self.query_at = datetime.datetime.strptime(query_at, '%Y-%m-%dT%H')
            self.hotel_id = int(hotel_id)
            dt = datetime.datetime.strptime(checkin, '%Y-%m-%d')
            self.checkin = dt.date()
            dt = datetime.datetime.strptime(checkout, '%Y-%m-%d')
            self.checkout = dt.date()
        except ValueError:
            return http.HttpResponseBadRequest()  # 400
        # Sanity checks
        self.days = (self.checkout - self.checkin).days
        if 0 >= self.days:
            return http.HttpResponseBadRequest()  # 400
        in_advance = (self.checkin - self.query_at.date()).days
        if 0 > in_advance:
            return http.HttpResponseBadRequest()  # 400
        context = self.get_context_data()
        if not dict == type(context):
            # This is an HTTP response!  Dump it back
            return context
        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        '''
        Queries the database for records.  It performs as little number of
        queries as it can, but sometimes we do as many as three.

        First we do a trivial sanity query, in SQL terms:

            SELECT COUNT(*)
            FROM hq_hotel_mart_hour
            WHERE day  = self.query_at.date()
            AND   hour = self.query_at.time().hour

        If we have data for that hour we try an exact match (from now on we
        assume that all tables are prepended with hq_hotel_mart_), in SQL
        terms:

            SELECT offer.id
                 , offer.hotel_id
                 , offer.price_usd
                 , offer.original_price
                 , offer.breakfast_included
                 , offer.valid_from_date
                 , offer.valid_to_date
                 , offer.valid_from_time
                 , offer.valid_to_time
                 , offer.checkin_date
                 , offer.checkout_date
                 , currency.id
                 , currency.code
                 , currency.name
                 , hotel_hour.id
                 , hotel_hour.hour
                 , hotel_hour.hotel_id
                 , hotel_hour.days
                 , hotel_hour.offer_id
            FROM hotel_offer
               , currency
               , offer
               , hour
            -- We already have hour.id from the previous query
            WHERE hotel_offer.hour        = <hour.id>
            AND   hotel_offer.offer_id    = offer.id
            AND   offer.original_currency = currency.id
            -- And here we match
            AND   offer.checkin_date  = <self.checkin>
            AND   offer.checkout_date = <self.checkout>
            AND   offer.hotel_id      = <self.hotel_id>
            -- Finally the order by gets us the cheapest offer
            ORDER BY offer.price_usd ASC
            LIMIT 1

        If we cannot match anything we try some fuzzy matching, something like:

            SELECT offer.id
                 -- the SELECT part is absolutely the same as above
            FROM hotel_offer
               , currency
               , offer
               , hour
            -- We already have hour.id from the previous query
            WHERE hotel_offer.hour        = <hour.id>
            AND   hotel_offer.offer_id    = offer.id
            AND   offer.original_currency = currency.id
            -- And here we match (this is different from the previous query)
            AND   hotel_hour.days     = <self.days>
            AND   offer.hotel_id      = <self.hotel_id>
            -- Finally the order by gets us the cheapest offer
            ORDER BY offer.price_usd ASC
            LIMIT 1

        Otherwise we just mock an answer.  In reality we should have some
        standard fares for each hotel.
        '''
        # generic.View has no get_context_data, do not call super
        try:
            # We need to check if this is a query valid for what times we have
            # loaded in the mart.  This is a trivial query.
            hour = models.Hour.objects.get( day=self.query_at.date()
                                          , hour=self.query_at.time().hour )
        except models.Hour.DoesNotExist:
            # Don't bother (also, need a better json constructor for this)
            err = { 'error' : 'Time query not in range' }
            return http.HttpResponseNotFound(str(err)+'\n')  # 404
        # And now the difficult query, build a queryset don't query yet
        qs = hour.hotel_offers.filter(hotel_id=self.hotel_id)
        # Try a full match
        exact_qs = qs.filter( hotel_id=self.hotel_id
                            , offer_id__checkin_date=self.checkin
                            , offer_id__checkout_date=self.checkout
                            ).order_by('offer_id__price_usd')
        match = exact_qs.select_related().first()  # Query the DB!
        if not match:
            # OK, we got nothing, let's try some fuzzy matching.
            # We try to find an offer that is valid during the moment the query
            # is made and for the correct number of days.  The assumption here
            # is that hotels would define a standard rate as an offer that is
            # valid always, but the check-in and check-out dates would not
            # match.  (This is probably wrong, but it is nice heuristic)
            fuzzy_qs = qs.filter( hotel_id=self.hotel_id
                                , days=self.days
                                ).order_by('offer_id__price_usd')
            match = fuzzy_qs.select_related().first()  # Try this query
        if match:
            cin = match.offer_id.checkin_date.strftime('%Y-%m-%d')
            cout = match.offer_id.checkout_date.strftime('%Y-%m-%d')
            context = {
                  'offerId'      : match.offer_id.id
                , 'hotelId'      : self.hotel_id
                , 'checkinDate'  : cin
                , 'checkoutDate' : cout
                , 'sellingPrice' : match.offer_id.original_price
                , 'currencyCode' : match.offer_id.original_currency.code
                }
            return context
        # We cannot find anything!  In the real world we should have data from
        # the hotels to check standard fares.  But we do not have such data.
        # Instead, mock a standard price per day:
        cin = self.checkin.strftime('%Y-%m-%d')
        cout = self.checkout.strftime('%Y-%m-%d')
        context = {
              'offerId'      : None
            , 'hotelId'      : self.hotel_id
            , 'checkinDate'  : cin
            , 'checkoutDate' : cout
            , 'sellingPrice' : settings.HQ_DW_DAY_PRICE * self.days
            , 'currencyCode' : settings.HQ_DW_DEFAULT_CURRECNY
            }
        return context

