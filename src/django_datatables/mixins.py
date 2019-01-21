from datetime import datetime
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, JsonResponse
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.translation import ugettext as _
from django.utils.cache import add_never_cache_headers
from django.utils.html import strip_tags

try:
    try:
        from openpyxl import Workbook
        import openpyxl.writer.excel as ExcelWriter
    except ImportError:
        from .excel import ExcelWriter
except ImportError:
    ExcelWriter = None

LOG = logging.getLogger(__name__)


class LazyEncoder(DjangoJSONEncoder):
    """Encodes django's lazy i18n strings
    """

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)


class DataResponse(object):

    def create_excel_response(self, request):
        """
        Return an excel writer as a response.
        """
        headers = self.get_column_titles()
        rows = self.get_data(request)
        title = getattr(self._meta, "title", "Sheet")

        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title)

        ws.append(headers)
        for row in rows:
            ws.append([strip_tags(c) for c in row])

        response = HttpResponse(
            ExcelWriter.save_virtual_workbook(wb),
            content_type='application/vnd.ms-excel'
        )
        response['Content-Disposition'] = \
            'attachment; filename="{0}"'.format(f'{title}-{datetime.now().strftime("%Y-%m-%d %H%m")}.xlsx')

        return response

    def create_data_response(self, func_val, request):
        try:
            assert isinstance(func_val, dict)
            response = dict(func_val)
            if 'result' not in response:
                response['result'] = 'ok'
        except KeyboardInterrupt:
            # Allow keyboard interrupts through for debugging.
            raise
        except Exception as e:
            LOG.exception('JSON view error: %s', request.path)
            msg = getattr(e, 'message', _('Internal error') + ': ') + str(e)
            response = {'result': 'error', 'sError': msg, 'text': msg}

        return JsonResponse(response)

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        response = None

        if request.GET.get("export") == "excel":
            return self.create_excel_response(request)

        func_val = self.get_context_data(request)
        response = self.create_data_response(func_val, request)

        add_never_cache_headers(response)
        return response
