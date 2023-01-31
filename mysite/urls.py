from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('gather/', include('gather.urls')),
    path('admin/', admin.site.urls),
]
