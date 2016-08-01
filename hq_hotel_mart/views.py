from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.views import generic

from . import models
from .util import JSONResponseMixin


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

    def post(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def put(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data)

    def get_context_data(self, *args, **kwargs):
        context = super(ApiView, self).get_context_data(*args, **kwargs)
        # TODO: this is the place where the query needs to happen
        self.query = get_object_or_404( models.HotelOffer
                                      , hour=kwargs['']
                                      , hotel_id=kwargs['hotel_id'] )
        return context

