from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from .serializers import *
from passlib.hash import pbkdf2_sha256
import logging
from django.contrib.auth import authenticate, login
from rest_framework import status
from django.utils.decorators import decorator_from_middleware
from register.middleware import AuthenticationMiddleware
import datetime
from utils.authHelper import *
from django.middleware.csrf import get_token

logger = logging.getLogger(__name__)

# Create your views here.
@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def getData(request):
    user_id, email_id = getUserIdEmail(request)
    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})
    data = User.objects.all()
    serializer = UserSerializer(data, many = True)
    return Response({'status': 'success',
        'message': "All Registered Data",
        "Data" : serializer.data
    })


@api_view(['POST'])
def postData(request):
    serializer = UserSerializer(data=request.data)
    
    if not request.data.get('email') or not request.data.get('password') or not request.data.get('role'):
        return Response({'status': 'error', 'message': 'All Feilds are required'})

    # Validate the serializer data
    if serializer.is_valid():
        # Encrypt the password
        enc_password = pbkdf2_sha256.encrypt(serializer.validated_data['password'], rounds=12000, salt_size=32)
        
        # Save the user with the encrypted password
        user = serializer.save(password=enc_password)
        
        # Serialize the user object after saving
        user_data = UserSerializer(user).data
        
        return  Response({ 
            'status': 'success',
            'message': 'User Registered successfully',
            'encrypted_password': enc_password,
            'user': user_data,  # Serialized user data
        })
    
    # Return errors if validation fails
    return Response({
        'status': 'error',
        'message': serializer.errors
    })

@api_view(['POST'])
def loginData(request):
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role')

    if not email or not password:
        return Response({'status': 'error', 'message': 'All fields are required'})

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User does not exist'})
    
    if user.verifyPassword(password):  # Use check_password for hashed passwords
        response = Response({
            'status': 'success',
            'message': 'Login successful',
            'user': {
                'email': user.email,
                'userId': user.userId,
                'role': user.role
            }
        }, status=status.HTTP_200_OK)

        # Set cookies for future requests
        print(user.userId, user.email)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        csrf_token = get_token(request)
        secure = not os.environ.get("DEBUG")  # Set secure based on DEBUG environment variable
        csrf_token = get_token(request)

        response.set_cookie('userId', user.userId, expires=expires_at, httponly=True, samesite='None', secure=secure)
        response.set_cookie('email', user.email, expires=expires_at, httponly=True, samesite='None', secure=secure)
        response.set_cookie('csrfToken', csrf_token, expires=expires_at, httponly=True, samesite='None', secure=secure)
        return response

    else:
        return Response({'status': 'error', 'message': 'Invalid password'})

@api_view(['POST'])
def logoutData(request):
    logout(request)
    return Response({'status': 'success',
        'message': 'Logout successful'
    })
