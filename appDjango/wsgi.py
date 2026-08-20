"""
WSGI config for appDjango project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# from COMMON.getmqtt import *

# from appDjango.COMMON import getmqtt

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appDjango.settings')

application = get_wsgi_application()

# mqtt_run()