# coding=utf-8
from PIL import Image
import shutil
import os
import math
from io import StringIO, BytesIO
from django.core.files.base import ContentFile

class Graphics:
    #infile = 'D:\\myimg.jpg'
    #outfile = 'D:\\adjust_img.jpg'

    def __init__(self, infile, outfile):
        self.infile = infile
        self.outfile = outfile

    def fixed_size(self, width, height):
        """按照固定尺寸处理图片"""
        im = Image.open(self.infile)
        out = im.resize((width, height), Image.ANTIALIAS)
        out.save(self.outfile)

    def resize_by_width(self, w_divide_h):
        """按照宽度进行所需比例缩放"""
        im = Image.open(self.infile)
        (x, y) = im.size
        x_s = x
        y_s = x / w_divide_h
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out.save(self.outfile)

    def resize_by_height(self, w_divide_h):
        """按照高度进行所需比例缩放"""
        im = Image.open(self.infile)
        (x, y) = im.size
        x_s = y * w_divide_h
        y_s = y
        out = im.resize((x_s, y_s), Image.ANTIALIAS)
        out.save(self.outfile)

    def resize_by_size(self, size):
        """按照生成图片文件大小进行处理(单位KB)"""
        size *= 1024
        im = Image.open(self.infile)
        size_tmp = os.path.getsize(self.infile)
        q = 5
        while size_tmp > size and q > 0:
            print(q)
            out = im.resize(im.size, Image.ANTIALIAS)
            out.save(self.outfile, quality=q)
            size_tmp = os.path.getsize(self.outfile)
            print(size_tmp)
            q -= 1
        if q == 100:
            shutil.copy(self.infile, self.outfile)

    def cut_by_ratio(self, width, height):
        """按照图片长宽比进行分割"""
        im = Image.open(self.infile)
        width = float(width)
        height = float(height)
        (x, y) = im.size
        if width > height:
            region = (0, int((y - (y * (height / width))) / 2), x, int((y + (y * (height / width))) / 2))
        elif width < height:
            region = (int((x - (x * (width / height))) / 2), 0, int((x + (x * (width / height))) / 2), y)
        else:
            region = (0, 0, x, y)

            # 裁切图片
        crop_img = im.crop(region)
        # 保存裁切后的图片
        crop_img.save(self.outfile)

    @classmethod
    def resize_by_size_mine(self, infile, size):
        """按照生成图片文件大小进行处理(单位KB)"""
        size *= 1024
        im = Image.open(infile)
        size_tmp = os.path.getsize(infile)

        if size_tmp > size:
            temp = math.sqrt(size_tmp/size)
            out = im.resize((round(im.size[0] / temp), round(im.size[1] / temp)), Image.ANTIALIAS)
            out.save(infile)

        return infile

    @classmethod
    def resize_by_size_jpg(self, infile, size):
        """按照生成图片文件大小进行处理(单位KB)"""
        size *= 1024
        im = Image.open(infile)
        if 'JPEG' != im.format:
            outfile = infile[:infile.rfind('.')] + '.jpg'
            im.save(outfile, 'JPEG')
            im = Image.open(outfile)
            print(im.format, im.size, im.mode)
        else:
            outfile = infile

        size_tmp = os.path.getsize(outfile)

        if size_tmp > size:
            temp = math.sqrt(size_tmp/size)
            out = im.resize((round(im.size[0] / temp), round(im.size[1] / temp)), Image.ANTIALIAS)
            out.save(outfile, 'JPEG')

        return outfile

    @classmethod
    def resize_by_size_mine_file(self, infile, size):
        """按照生成图片文件大小进行处理(单位KB)"""
        size *= 1024
        im = Image.open(infile)
        size_tmp = infile.size

        if size_tmp > size:
            temp = math.sqrt(size_tmp / size)
            out = im.resize((round(im.size[0] / temp), round(im.size[1] / temp)), Image.ANTIALIAS)
            imgOut = BytesIO()
            out.save(imgOut, 'JPEG')
            return ContentFile(imgOut.getbuffer(), name=infile.name)

        return infile

def test(infile):
    infile.find('')
    Graphics(infile)