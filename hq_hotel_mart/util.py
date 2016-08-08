import re
from django.conf import settings
from django.http.response import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder

clear_json = re.compile(b'\n|\r')

class SafeJsonResponse(JsonResponse):
    def __init__(self, data, encoder=DjangoJSONEncoder, safe=True, **kwargs):
        json_params = { 'separators' : (',', ':') }
        if settings.DEBUG:
            json_params = { 'indent' : 4 , 'separators' : (', ', ': ') }
        super(SafeJsonResponse, self).__init__( data
                                              , encoder=encoder
                                              , safe=safe
                                              , json_dumps_params=json_params
                                              , **kwargs
                                              )
        # Someone may include a JSON object as an external javascript file, as
        # in:
        #     <script src='yourdomain.org/your-json-view/'>
        #
        # If the user visiting that website is logged in to your website and
        # that JSON view has authenticated information, it will be fetched and
        # then available to the scripts on the rogue website.  In essence, yet
        # another way to perform XXS.
        #
        # To prevent this, we ensure that the JSON is contained on a single
        # line and a javascript comment is placed in front of that line.  If
        # you are using AJAX you will have no trouble to strip the first two
        # characters of the response, something that cannot be done with the
        # <script src= > rogue method.
        if not settings.DEBUG:
            # self.content is always a bytestring
            self.content = b'//' + clear_json.sub(b'', self.content)
        # be nice with terminal based browsers/downloaders
        self.content += b'\n'


class JSONResponseMixin(object):
    def render_to_response(self, context, **kwargs):
        return SafeJsonResponse(self.get_data(context), **kwargs)

    def get_data(self, context):
        return context

