import ssl, pycurl, io
from urllib import request,parse
from urllib.parse import quote,urlencode,unquote


class HttpClient(object):
    def get(self, url, second=30):
        return self.postXml(url, second)

    def postXml(self, xml, url, second=30):
        """不使用证书"""
        data = request.urlopen(url, xml.encode(), timeout=second).read()
        return data

    def postXmlSSL(self, url, xml, head=None, cert=None, key=None, post=True):
        """使用证书"""
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.SSL_VERIFYHOST, False)
        self.curl.setopt(pycurl.SSL_VERIFYPEER, False)
        self.curl.setopt(pycurl.URL, url)

        if head:
            self.curl.setopt(pycurl.HTTPHEADER, head)
        else:
            self.curl.setopt(pycurl.HEADER, False)

        # 设置证书
        # 使用证书：cert 与 key 分别属于两个.pem文件
        # 默认格式为PEM，可以注释
        if cert:
            self.curl.setopt(pycurl.SSLKEYTYPE, "PEM")
            self.curl.setopt(pycurl.SSLCERTTYPE, "PEM")
            self.curl.setopt(pycurl.SSLKEY, key)
            self.curl.setopt(pycurl.SSLCERT, cert)

        # post提交方式
        if post:
            self.curl.setopt(pycurl.POST, True)
            self.curl.setopt(pycurl.POSTFIELDS, xml)

        buff = io.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, buff.write)

        self.curl.perform()
        return buff.getvalue()