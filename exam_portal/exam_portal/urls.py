from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mcq.urls')),             # your app routes
    path('explorer/', include('explorer.urls')),  # add explorer here
]
