#import random
#def createNoncestr(length=32):
#    """产生随机字符串，不长于32位"""
#    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
#    strs = []
#    for x in range(length):
#        strs.append(chars[random.randrange(0, len(chars))])
#    return "".join(strs)
#print(createNoncestr())

#from Bankcard.bankcard import verify_bankcard
#print(verify_bankcard('6227003818060419'))

#from common.function import isidcard
#print(isidcard('152104198710210013'))
#print(isidcard('511502199105074551'))

#temp = './20170211145425.png'
#temp = './153_161124155344_2.jpg'
#from common.graphics import Graphics

#Graphics.resize_by_size_jpg(temp, 150)
#Graphics.resize_by_size_mine(temp, 150)

#import datetime
#time_now = datetime.datetime.now()
#print(time_now.strftime('%Y%m%d%H%M%S')+str(int(time_now.microsecond/100)))

import base64

temp = '''<xml>
<merch_date>20160808</merch_date>
<merch_time>143408</merch_time>
<merch_serial>20160808CMB1470638048969</merch_serial>
<bank_addr>深圳</bank_addr>
<bank_name>招商银行</bank_name>
<merch_prod>出租车</merch_prod>
<currency_no>RMB</currency_no>
<acc_no>6212760000012013</acc_no>
<acc_name>爱理财九</acc_name>
<payee_acc>755915921210906</payee_acc>
<payee_name>XX公司</payee_name>
<trn_amt>188</trn_amt>
<merch_abs>一网通账户</merch_abs>
<back_addr>back.dididache.com</back_addr>
</xml>'''

#temp = base64.b64encode(str.encode(temp))
#temp = bytes.decode(temp)
#print(type(temp), temp)
from PIL import Image
import glob, os

def test():
    size = 128, 128

    '''
    for infile in glob.glob("./media/shop_ico/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

    for infile in glob.glob("./media/shop_photo/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

    for infile in glob.glob("./media/shop_goods/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

    for infile in glob.glob("./media/comment/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

    for infile in glob.glob("./media/user_ico/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")
    '''
    for infile in glob.glob("./media/shop_combo_ico/*.jpg"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

    for infile in glob.glob("./media/user_ico/*.png"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        im.thumbnail(size, Image.ANTIALIAS)
        im.save(file + "_thumbnail.jpg", "JPEG")

from django.utils import timezone
import datetime

from SpokesTribe.settings import BASE_DIR

import uuid, time

if __name__ == "__main__":
    pass

def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return [b"Hello World"]