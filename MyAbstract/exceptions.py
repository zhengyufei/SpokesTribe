from __future__ import unicode_literals

from django.utils import six
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException, _get_error_details
from Logger.logger import Logger

class ValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail, code=None, status=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if status is not None:
            self.status_code = status

        # For validation failures, we may collect may errors together, so the
        # details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)

    def __str__(self):
        return six.text_type(self.detail)

class ValidationDict211Error(ValidationError):
    def __init__(self, detail, detail_en=None, code=None, status=211):
        if status is not None:
            self.status_code = status
        Logger.Log('warning', detail)
        if detail_en:
            Logger.Log('warning', detail_en)
        self.detail = {'error_code': self.status_code, 'error_string': detail}