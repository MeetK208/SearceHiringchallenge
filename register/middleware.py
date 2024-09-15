# myapp/middleware.py
from django.shortcuts import redirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from .models import User
from django.contrib.auth.middleware import get_user
import logging
from django.urls import reverse
from rest_framework.response import Response
from utils.authHelper import *

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/login/') or request.path.startswith('/static/'):
            return None
        user_id, email_id = getUserIdEmail(request)
        if not user_id or not email_id:
            login_url = reverse('login')  # This will generate '/auth/login/' assuming 'login' is the URL name
            return redirect(login_url)

        
        try:
            user = User.objects.get(pk=user_id)
            request.user = user
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)})