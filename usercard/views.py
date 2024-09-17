from django.shortcuts import render
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import *
from .serializers import *
from passlib.hash import pbkdf2_sha256
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import decorator_from_middleware
from register.middleware import AuthenticationMiddleware
from django.db.models import Q
from projectcard.models import *
import pandas as pd
import json
from utils.authHelper import *
from rest_framework.pagination import PageNumberPagination
from math import ceil

logger = logging.getLogger(__name__)

def extract_budget_info(budget):
    try:
        amount, currency = budget.split()
        amount = int(amount)
        return amount, currency
    except Exception as e:
        logger.error(f"Error extracting budget info: {e}")
        return 0, 'Unknown'

def KPILogic(data, totalBudget):
    try:
        # Split totalBudget to extract the numeric value and the currency type
        totalBudget, currency_type = totalBudget.split()
        totalBudget = int(totalBudget)

        # Create DataFrame
        df = pd.DataFrame(data)

        # Ensure 'budget' column exists
        if 'budget' not in df.columns:
            raise KeyError("'budget' column is missing in the data")

        # Extract budget information from each entry
        df[['rupees', 'currency_type']] = df['budget'].apply(lambda x: pd.Series(extract_budget_info(x)))

        # Ensure rupees are numeric
        df['rupees'] = pd.to_numeric(df['rupees'], errors='coerce').fillna(0)

        # Convert 'Cr' to actual amount in rupees
        df['rupeese'] = df.apply(lambda row: row['rupees'] * 100 if row['currency_type'] == 'Cr' else row['rupees'], axis=1)

        # Group by department and sum
        grouped_df = df.groupby('department')['rupeese'].sum().reset_index()

        # Calculate percentage of the budget used by department
        grouped_df['percentage_used'] = round((grouped_df['rupeese'] / (totalBudget * 100)) * 100)

        # Convert to JSON
        json_result = grouped_df.to_json(orient='records')
        return json_result, df['rupeese'].sum()

    except KeyError as e:
        logger.error(f"Missing key in data: {e}")
        return json.dumps([])  # Return empty JSON if there's an error
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps([])  # Return empty JSON if there's an error

def get_project_and_authorize(user_id, project_id):
    try:
        # Check if the user is the project owner
        project = Project.objects.get(projectId=int(project_id))
        if project.user_id == int(user_id):
            return project, True

        # Check if the user is a collaborator on the project
        is_collaborator = ProjectUser.objects.filter(Q(projectId=project) & Q(userId=int(user_id))).exists()
        if is_collaborator:
            return project, True

        return None, False

    except Project.DoesNotExist:
        return None, False

class CustomPagination(PageNumberPagination):
    page_size = 10  # You can override the global setting here if needed
    page_size_query_param = 'page_size'  # Allow the user to control the page size
    max_page_size = 20  # Max limit for page size

@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def getAllUserCard(request):
    
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params

    if not user_id:
        return Response({'status': 'error', 'message': 'User not authenticated'})

    if not projectId:
        return Response({'status': 'error', 'message': 'Project ID is required'})

    try:
        # Check if the user is authorized as either an owner or collaborator
        project, authorized = get_project_and_authorize(user_id, projectId)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})
         
        # Fetch all ProjectCardUser entries related to the given project ID
        project_users = ProjectCardUser.objects.filter(projectCard=int(projectId)).order_by('carduserId')
        ProjectData = Project.objects.filter(projectId=int(projectId)) 
        project_name = ProjectData.name
        totalBudget = "0 cr"
        if ProjectData.exists(): 
            totalBudget = ProjectData.first().budget 
        rupees, currency = totalBudget.split()
        if not project_users.exists(): 
            usedBudget = str(0) + currency
            return Response({ 
                "count": 0,
                "next": None,
                "previous": None,
                "results":{
                'status': 'success',
                'message': 'User cards Not Found',
                'userId': user_id,
                'email': email_id, 
                'projectId': projectId,
                'projectName': project_name,
                'userCards': [] ,
                'DashboardMatrix': [] ,
                'totalBudget' : totalBudget,
                'usedBudget': usedBudget,
                'total_pages': 0 ,
                'total_records': 0 ,
                }
            })
        
        total_records = project_users.count()

        # Serialize the data of ProjectCardUser
        serializer = ProjectCardUserSerializer(project_users, many=True)
       

        # Split the budget value and currency
        DashboardMatrix, usedBudget = KPILogic(serializer.data, totalBudget)

        # Adjust budget output based on currency type
        
        # Apply pagination
        paginator = CustomPagination()
        paginated_users = paginator.paginate_queryset(project_users, request)

        # Serialize the paginated data of ProjectCardUser
        serializer = ProjectCardUserSerializer(paginated_users, many=True)

        # Calculate the total number of pages based on the user-specified page size
        page_size = int(request.query_params.get('page_size', paginator.page_size))
        total_pages = ceil(total_records / page_size)
        
        usedBudget = str(usedBudget) + currency
        # Return the successful paginated response with user card data and budget details
        return paginator.get_paginated_response({ 
            'status': 'success',
            'message': 'User cards retrieved successfully',
            'userId': user_id,
            'email': email_id,
            'projectId': projectId,
            'projectName': project_name,
            'userCards': serializer.data,
            'DashboardMatrix': json.loads(DashboardMatrix),
            'totalBudget': totalBudget,
            'usedBudget': usedBudget,
            'total_pages': total_pages,
            'total_records': total_records,
        })

    except Exception as e:
        logger.error(f"Error in getAllUserCard view: {e}")
        return Response({'status': 'error', 'message': 'An error occurred while retrieving user cards'})

@api_view(['POST'])
@decorator_from_middleware(AuthenticationMiddleware)
def CreateUserCard(request):
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params

    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})
    
    if not projectId:
        return Response({'status': 'error', 'message': 'Project ID is required'})

    required_fields = ['designation', 'department', 'budget', 'location']
    if not all(field in request.data for field in required_fields):
        return Response({'status': 'error', 'message': 'Provide all required fields'})

    try:
        
        project, authorized = get_project_and_authorize(user_id, projectId)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})
        
        project = Project.objects.get(projectId=int(projectId))
        if project.user_id != int(user_id):
            is_collaborator = ProjectUser.objects.filter(
                Q(projectId=project) & Q(userId=int(user_id))
            ).exists()

            if not is_collaborator:
                return Response({'status': 'error', 'message': 'You are not authorized to add a card to this project'})
        
        data = {
            'projectCard': projectId,
            'designation': request.data.get('designation'),
            'department': request.data.get('department'),
            'budget': request.data.get('budget'),
            'location': request.data.get('location'),
            'last_edited_by_userId': user_id
        }

        serializer = ProjectCardUserSerializer(data=data)

        if serializer.is_valid():
            project_card_user = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Project Card User created successfully',
                'project_card_user': serializer.data,
                "user_id": user_id
            })
        else:
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response({
                'status': 'success',
                'message': serializer.errors
            })
    
    except Project.DoesNotExist:
        Response({'status': 'error', 'message': 'Project not found'})
    except Exception as e:
        logger.error(f"Error in CreateUserCard view: {e}")
        return Response({'status': 'error', 'message': 'An error occurred while creating the user card'})
  

@api_view(['PUT'])
@decorator_from_middleware(AuthenticationMiddleware)
def updateOneUserCard(request):
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params
    usercard_Id = request.query_params.get('cardId')  # Get project ID from query params

    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})
    
    if not projectId:
        return Response({'status': 'error', 'message': 'Project ID is required'})
    
    try:
        project, authorized = get_project_and_authorize(user_id, projectId)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})

        project_card_user = ProjectCardUser.objects.filter(Q(carduserId=int(usercard_Id)) & Q(projectCard=int(projectId))).first()

        if not project_card_user:
            return Response({'status': 'error', 'message': 'User card not found or you do not have permission to update'})

        serializer = ProjectCardUserSerializer(project_card_user, data=request.data, partial=True)

        if serializer.is_valid():
            updated_project_card_user = serializer.save()
            project_card_user_data = ProjectCardUserSerializer(updated_project_card_user).data
            return Response({
                'status': 'success',
                'message': 'User card updated successfully',
                'userCard': project_card_user_data
            })

        return Response({
            'status': 'error',
            'message': serializer.errors
        })

    except Exception as e:
        logger.error(f"Error in updateOneUserCard view: {e}")
        return Response({'status': 'error', 'message': 'An error occurred while updating the user card'})


@api_view(['DELETE'])
@decorator_from_middleware(AuthenticationMiddleware)
def deleteOneUserCard(request):
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies
    usercard_Id = request.query_params.get('cardId')
    
    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    project_id = request.query_params.get('projectId')
    
    if not project_id or not usercard_Id:
        return Response({'status': 'error', 'message': 'Please provide a valid projectId or UsercardId'})

    try:
        project, authorized = get_project_and_authorize(user_id, project_id)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})

        project_user_card = ProjectCardUser.objects.get(projectCard=project_id, carduserId=usercard_Id)
        project_user_card.delete()
        return Response({'status': 'success', 'message': 'User card deleted successfully'})
    
    except ProjectCardUser.DoesNotExist:
        return Response({'status': 'error', 'message': 'User card not found'})

    except Exception as e:
        logger.error(f"Error in deleteOneUserCard view: {e}")
        return Response({'status': 'error', 'message': 'An error occurred while deleting the user card'})


@api_view(['PUT'])
@decorator_from_middleware(AuthenticationMiddleware)
def updateBudget(request):
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies
    
    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    project_id = request.query_params.get('projectId')
    
    if not project_id:
        return Response({'status': 'error', 'message': 'Please provide a valid projectId'})
    
    try:
        project, authorized = get_project_and_authorize(user_id, project_id)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})

        updatedBudget = request.data.get('budget')
        if not updatedBudget:
            return Response({'status': 'error', 'message': 'Please provide a valid Total Budget'})
        
        # Convert project_id to integer
        project_id = int(project_id)
        
        # Fetch the project
        project = Project.objects.get(projectId=project_id)
        
        # Update the budget
        project.budget = updatedBudget
        project.save()
        
        return Response({'status': 'success', 'message': 'Budget updated successfully'})
    
    except Project.DoesNotExist:
        Response({'status': 'error', 'message': 'Project not found'})
    except ValueError:
        return Response({'status': 'error', 'message': 'Invalid projectId or budget value'})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response({'status': 'error', 'message': 'An error occurred while updating the budget'})



from math import ceil

@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def searchUserCard(request):
    user_id, email_id = getUserIdEmail(request)  # Get user ID from cookies

    if not user_id:
        return Response({'status': 'error', 'message': 'User not authenticated'})

    project_id = request.query_params.get('projectId')
    
    if not project_id:
        return Response({'status': 'error', 'message': 'Please provide a valid projectId'})

    try:
        project, authorized = get_project_and_authorize(user_id, project_id)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})

        # Search functionality
        department = request.query_params.get('department')
        designation = request.query_params.get('designation')
        location = request.query_params.get('location')
        
        filters = Q(projectCard=int(project_id))

        # Apply search filters based on the query parameters
        if department:
            filters &= Q(department__icontains=department)
        if designation:
            filters &= Q(designation__icontains=designation)
        if location:
            filters &= Q(location__icontains=location)

        # Retrieve matching records
        search_results = ProjectCardUser.objects.filter(filters).order_by('carduserId')
        
        # If no records are found, return the default structure with empty or None values
        if not search_results.exists():
            return Response({
                "count": 0,
                "next": None,
                "previous": None,
                "results": {
                    'status': 'success',
                    'message': 'User cards Not Found',
                    'userId': user_id,
                    'email': email_id,
                    'projectId': project_id,
                    'userCards': [],
                    'DashboardMatrix': [],
                    'totalBudget': "0",
                    'usedBudget': "0.0",
                    'total_pages': 0,
                    'total_records': 0
                }
            })

        # Get the user-specified page size or use a default value
        page_size = int(request.query_params.get('page_size', 10))
        total_records = search_results.count()

        # Calculate the total number of pages
        total_pages = ceil(total_records / page_size)

        # Apply pagination
        paginator = CustomPagination()
        paginated_results = paginator.paginate_queryset(search_results, request)

        # Serialize the paginated results
        serializer = ProjectCardUserSerializer(paginated_results, many=True)

        # Return paginated response with total number of pages
        return Response({
            "count": total_records,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": {
                'status': 'success',
                'message': 'User cards retrieved successfully',
                'userId': user_id,
                'email': email_id,
                'projectId': project_id,
                'userCards': serializer.data,
                'DashboardMatrix': [],  # Add logic here to calculate if applicable
                'totalBudget': "0",  # Example total budget; adjust as needed
                'usedBudget': "0",  # Example used budget; adjust as needed
                'total_pages': total_pages,
                'total_records': total_records
            }
        })

    except Exception as e:
        return Response({'status': 'error', 'message': str(e)})
