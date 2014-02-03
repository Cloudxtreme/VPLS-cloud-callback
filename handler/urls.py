# Django utilities
from django.conf.urls import patterns, url

# Load the response handler
from handler.views import ResponseHandler

# 404 error handler
handler404 = 'handler.views.error_404'

# 500 error handler
handler500 = 'handler.views.error_500'

# URL pattern matching
urlpatterns = patterns('',
    url(r'^.*$', ResponseHandler.as_view())
)