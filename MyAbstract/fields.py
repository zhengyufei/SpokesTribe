from django.db import models
from drf_extra_fields.fields import Base64ImageField

class IntegerRangeField(models.IntegerField):
    def __init__(self, verbose_name=None, name=None, min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)
    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value':self.max_value}
        defaults.update(kwargs)
        return super(IntegerRangeField, self).formfield(**defaults)

from MyAbstract.graphics import Graphics

class CompressBase64ImageField(Base64ImageField):
    def to_internal_value(self, data):
        temp = super(CompressBase64ImageField, self).to_internal_value(data)
        return Graphics.resize_by_size_mine_file(temp, 100)