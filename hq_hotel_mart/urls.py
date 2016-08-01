from django.conf.urls import url

from . import views


app_name = 'hq_hotel_mart'
urlpatterns = [
      url( r'^currency/(?P<pk>\d+)/'
         , views.CurrencyView.as_view()
         , name='currency'
         )
    , url( r'^currency/$'
         , views.CurrencyListView.as_view()
         , name='currency_list'
         )
    , url( r'^offer/(?P<pk>\d+)/'
         , views.OfferView.as_view()
         , name='offer'
         )
    , url( r'^offer/$'
         , views.OfferListView.as_view()
         , name='offer_list'
         )
    , url( r'^hour/(?P<pk>\d+)/'
         , views.HourView.as_view()
         , name='hour'
         )
    , url( r'^hour/$'
         , views.HourListView.as_view()
         , name='hour_list'
         )
    , url( r'^hotel/(?P<pk>\d+)/'
         , views.HotelOfferView.as_view()
         , name='hotel'
         )
    , url( r'^hotel/$'
         , views.HotelOfferView.as_view()
         , name='hotel_list'
         )
    , url( r'^api/$'
         , views.ApiView.as_view()
         , name='api'
         )
]

