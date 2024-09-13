# myapp/middleware.py
from django.shortcuts import redirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from .models import User
from django.contrib.auth.middleware import get_user
import logging
from django.urls import reverse
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/login/') or request.path.startswith('/static/'):
            return None
        
        user_id = request.COOKIES.get('userId')
        email = request.COOKIES.get('email')
        print("Yews",user_id, email)
        if not user_id or not email:
            login_url = reverse('login')  # This will generate '/auth/login/' assuming 'login' is the URL name
            return redirect(login_url)

        
        try:
            user = User.objects.get(pk=user_id, email=email)
            request.user = user
        except Exception as e:
            return Response({'status': 500, 'error': str(e)})

            # return redirect('/login/')
