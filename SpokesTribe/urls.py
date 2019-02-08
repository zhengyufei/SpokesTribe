"""SpokesTribe URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework.authtoken import views
from SpokesTribe import settings
from django.conf.urls.static import static

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^common/', include('common.urls')),
    url(r'^seller_app/', include('seller_app.urls')),
    url(r'^spokesman/', include('spokesman.urls')),
    url(r'^my_admin/', include('myadmin.urls')),
    url(r'^third_admin/', include('third_admin.urls')),
    url(r'^spoker_mini/', include('spoker_mini.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

