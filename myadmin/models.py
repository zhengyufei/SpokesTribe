from django.db import models
from common.models import MyUser

# Create your models here.
class AutoShopCashRecord(models.Model):
    exec_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    result = models.NullBooleanField(null=True)

class CommandsRecord(models.Model):
    user = models.ForeignKey(MyUser, null=True, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=32)
    exec_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    remark = models.TextField(null=True)
    describe = models.TextField(null=True)

    STATUS = (
        ('success', 'SUCCESS'),
        ('fail', 'FAIL'),
        ('refuse', 'REFUSE'),
    )
    status = models.CharField(choices=STATUS, max_length=8)

class Log(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    info = models.TextField()

    LEVEL = (
        ('info', ''),
        ('warning', ''),
        ('error', ''),
        ('critical', '')
    )

    level = models.CharField(choices=LEVEL, max_length=8)
