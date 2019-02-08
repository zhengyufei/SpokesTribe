#coding:utf-8
import base64
import decimal
import json
import random
import time
import urllib
from math import radians, atan, tan, acos, sin, cos, ceil, floor
from xml.etree import ElementTree as ET
import pytz
import rsa
import datetime

from SpokesTribe import settings as settings
from SpokesTribe.settings import TIME_ZONE
from django.db import connection, IntegrityError


def timetuple(t=None):
    if not t:
        return int(time.mktime(datetime.datetime.now().timetuple()))

    return int(time.mktime(t.astimezone(pytz.timezone(TIME_ZONE)).timetuple())) if t else None

def timetuple_utc(t=None):
    if not t:
        return int(time.mktime(datetime.datetime.now().timetuple()))

    return int(time.mktime(t.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(TIME_ZONE)).timetuple())) if t else None

def decimal2string(decimals):
    return str(decimal.Decimal(decimals))


def post(url, post):
    f = urllib.request.urlopen(url, post.encode())
    raw_data = f.read()
    encoding = f.info().get_content_charset('utf8')  # JSON default
    data = json.loads(raw_data.decode(encoding))

    return data


def print_obj_dict(obj):
    for key in obj.__dict__:
        print(key, ':', obj.__dict__[key])


def GetFixedImageUrl(request, path):
    return '{scheme}://{host}{media_url}{path}'.format(scheme=request.scheme,
                                                                 media_url=settings.MEDIA_URL,
                                                                 host=settings.DOMAIN_NAME+':'+request.get_port(),
                                                                 path=path)


def GetAbsoluteImageUrl(request, path):
    return '{scheme}://{host}{media_url}{path}'.format(scheme=request.scheme,
                                                                 media_url=settings.MEDIA_URL,
                                                                 host=request.get_host(),
                                                                 path=path)

# input Lat_A 纬度A
# input Lng_A 经度A
# input Lat_B 纬度B
# input Lng_B 经度B
# output distance 距离(km)
def calcDistance(Lat_A, Lng_A, Lat_B, Lng_B):
    ra = 6378.140  # 赤道半径 (km)
    rb = 6356.755  # 极半径 (km)
    flatten = (ra - rb) / ra  # 地球扁率
    rad_lat_A = radians(Lat_A)
    rad_lng_A = radians(Lng_A)
    rad_lat_B = radians(Lat_B)
    rad_lng_B = radians(Lng_B)
    pA = atan(rb / ra * tan(rad_lat_A))
    pB = atan(rb / ra * tan(rad_lat_B))
    xx = acos(sin(pA) * sin(pB) + cos(pA) * cos(pB) * cos(rad_lng_A - rad_lng_B))
    c1 = (sin(xx) - xx) * (sin(pA) + sin(pB)) ** 2 / cos(xx / 2) ** 2
    if 0 == xx and 0 == c1:
        return 0
    c2 = (sin(xx) + xx) * (sin(pA) - sin(pB)) ** 2 / sin(xx / 2) ** 2
    dr = flatten / 8 * (c1 - c2)
    distance = ra * (xx + dr) * 1000
    return distance


def RandomNumberString(length):
    chars = "0123456789"
    strs = []
    for x in range(length):
        strs.append(chars[random.randrange(0, len(chars))])
    return "".join(strs)


def RandomString(length):
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    strs = []
    for x in range(length):
        strs.append(chars[random.randrange(0, len(chars))])
    return "".join(strs)

from dicttoxml import convert, default_item_func

def toXml(obj, root=True, custom_root='root', ids=False, attr_type=True,
          item_func=default_item_func, cdata=False):
    """Converts a python object into XML.
    Arguments:
    - root specifies whether the output is wrapped in an XML root element
      Default is True
    - custom_root allows you to specify a custom root element.
      Default is 'root'
    - ids specifies whether elements get unique ids.
      Default is False
    - attr_type specifies whether elements get a data type attribute.
      Default is True
    - item_func specifies what function should generate the element name for
      items in a list.
      Default is 'item'
    - cdata specifies whether string values should be wrapped in CDATA sections.
      Default is False
    """
    #LOG.info('Inside dicttoxml(): type(obj) is: "%s", obj="%s"' % (type(obj).__name__, unicode_me(obj)))
    output = []
    addline = output.append
    if root == True:
        #addline('<?xml version="1.0" encoding="UTF-8" ?>')
        addline('<%s>%s</%s>' % (
        custom_root,
        convert(obj, ids, attr_type, item_func, cdata, parent=custom_root),
        custom_root,
        )
    )
    else:
        addline(convert(obj, ids, attr_type, item_func, cdata, parent=''))
    return ''.join(output).encode('utf-8')

def dictToXml(arr, root='xml'):
    #from dicttoxml import dicttoxml
    xml = toXml(arr, custom_root=root, attr_type=False)
    return str(xml, 'utf-8')


def xmlToDict(xml):
    import xmltodict
    array_data = xmltodict.parse(xml)
    return array_data


def privateEncrypt(private, content, type='SHA-1'):
    file_path = private
    f = open(file_path, 'r').read()
    private_key = rsa.PrivateKey.load_pkcs1(f)
    d = rsa.sign(content.encode(), private_key, type)
    b = base64.b64encode(d)
    return str(b, 'utf-8')


def fenceil(money):
    return ceil(money * 100) / decimal.Decimal(100.0)


def fenfloor(money):
    return floor(money * 100) / decimal.Decimal(100.0)


def services_contract(income):
    if income <= 800:
        return income, 0

    if income < 4000:
        pre_tax = income - 800
        tax_rate = decimal.Decimal(0.2)
        tax = fenceil(pre_tax * tax_rate)
        return income - tax, tax

    pre_tax = income * 0.8

    if income < 25000:
        tax_rate = 0.2
        subtrahend = 0
    elif income < 62500:
        tax_rate = 0.3
        subtrahend = 2000
    else:
        tax_rate = 0.4
        subtrahend = 7000

    tax = fenceil(pre_tax * tax_rate) - subtrahend

    return income - tax, tax


def sql_execute(sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    fetchall = cursor.fetchall()

    return fetchall

def liststring_splice(list):
    rtn = ''
    for item in list:
        if item:
            if '' == rtn:
                rtn = item
            else:
                rtn += '\n'
                rtn += item

    return rtn

