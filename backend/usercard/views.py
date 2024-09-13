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
        # Convert totalBudget to a float, ensuring it's numeric
        totalBudget, currency_type = totalBudget.split()
        print(totalBudget,currency_type )
        # Create DataFrame
        df = pd.DataFrame(data)
        # Ensure 'budget' column exists
        if 'budget' not in df.columns:
            raise KeyError("'budget' column is missing in the data")

        # Extract budget information
        df[['rupees', 'currency_type']] = df['budget'].apply(lambda x: pd.Series(extract_budget_info(x)))
        
        # Ensure rupees are numeric
        df['rupees'] = pd.to_numeric(df['rupees'], errors='coerce').fillna(0)
        
        # Convert 'Cr' to actual amount in rupees
        df['rupeese'] = df.apply(lambda row: row['rupees'] * 100 if row['currency_type'] == 'Cr' else row['rupees'], axis=1)
        
        print(df)
        # Group by department and sum
        grouped_df = df.groupby('department')['rupeese'].sum().reset_index()
        print(grouped_df)
        # Calculate percentage used
        grouped_df['percentage_used'] = round((grouped_df['rupeese'] / (int(totalBudget) * 100)) * 100)
        print("Lakhs",df['rupeese'].sum())
        # Convert to JSON
        json_result = grouped_df.to_json(orient='records')
        return json_result, df['rupeese'].sum()

    except KeyError as e:
        logger.error(f"Missing key in data: {e}")
        return json.dumps([])  # Return empty JSON if there's an error
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return json.dumps([])  # Return empty JSON if there's an error
    except TypeError as e:
        logger.error(f"Type error: {e}")
        return json.dumps([])  # Return empty JSON if there's an error
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps([])  # Return empty JSON if there's an error

@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def getAllUserCard(request):
    user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params

    if not user_id:
        return Response({'status': 400, 'error': 'User not authenticated'})

    if not projectId:
        return Response({'status': 400, 'error': 'Project ID is required'})

    try:
        # Fetch all ProjectCardUser entries related to the given project ID
        project_users = ProjectCardUser.objects.filter(projectCard=int(projectId))
        if not project_users.exists():
            return Response({'status': 404, 'error': 'No user cards found for this project'})

        # Serialize the data of ProjectCardUser
        serializer = ProjectCardUserSerializer(project_users, many=True)
        ProjectData = Project.objects.filter(projectId=int(projectId))
        totalBudget = 1
        if ProjectData.exists():
            totalBudget = ProjectData.first().budget
        ruppese, currency = totalBudget.split()
        DashboardMatrix, usedBudget = KPILogic(serializer.data, totalBudget)

        if (currency.lower() == "lakhs"):
            usedBudget = str(usedBudget) + " lakhs"
        else:
            usedBudget = str(usedBudget/100) + " Cr"
        
        return Response({
            'status': 200,
            'message': 'User cards retrieved successfully',
            'userId': user_id,
            'email': request.COOKIES.get('email'),
            'projectId': projectId,
            'userCards': serializer.data,
            "DashboardMatrix": json.loads(DashboardMatrix),
            "totalBudget": totalBudget,
            "usedBudget" : usedBudget
        })

    except Exception as e:
        logger.error(f"Error in getAllUserCard view: {e}")
        return Response({'status': 500, 'error': 'An error occurred while retrieving user cards'})


@api_view(['POST'])
@decorator_from_middleware(AuthenticationMiddleware)
def CreateUserCard(request):
    user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params

    if not user_id:
        return Response({'status': 400, 'error': 'User not authenticated'})
    
    if not projectId:
        return Response({'status': 400, 'error': 'Project ID is required'})

    required_fields = ['designation', 'department', 'budget', 'location']
    if not all(field in request.data for field in required_fields):
        return Response({'status': 400, 'error': 'Provide all required fields'})

    try:
        project = Project.objects.get(projectId=int(projectId))
        if project.user_id != int(user_id):
            is_collaborator = ProjectUser.objects.filter(
                Q(projectId=project) & Q(userId=int(user_id))
            ).exists()

            if not is_collaborator:
                return Response({'status': 400, 'message': 'You are not authorized to add a card to this project'})
        
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
                'status': 200,
                'message': 'Project Card User created successfully',
                'project_card_user': serializer.data,
                "user_id": user_id
            })
        else:
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response({
                'status': 400,
                'errors': serializer.errors
            })
    
    except Project.DoesNotExist:
        return Response({'status': 404, 'error': 'Project not found'})
    except Exception as e:
        logger.error(f"Error in CreateUserCard view: {e}")
        return Response({'status': 500, 'error': 'An error occurred while creating the user card'})
  

@api_view(['PUT'])
@decorator_from_middleware(AuthenticationMiddleware)
def updateOneUserCard(request):
    user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    projectId = request.query_params.get('projectId')  # Get project ID from query params

    if not user_id:
        return Response({'status': 400, 'error': 'User not authenticated'})
    
    if not projectId:
        return Response({'status': 400, 'error': 'Project ID is required'})
    
    try:
        project_card_user = ProjectCardUser.objects.filter(Q(user_id=user_id) & Q(projectCard=projectId)).first()

        if not project_card_user:
            return Response({'status': 404, 'error': 'User card not found or you do not have permission to update'})

        serializer = ProjectCardUserSerializer(project_card_user, data=request.data, partial=True)

        if serializer.is_valid():
            updated_project_card_user = serializer.save()
            project_card_user_data = ProjectCardUserSerializer(updated_project_card_user).data
            return Response({
                'status': 200,
                'message': 'User card updated successfully',
                'userCard': project_card_user_data
            })

        return Response({
            'status': 400,
            'errors': serializer.errors
        })

    except Exception as e:
        logger.error(f"Error in updateOneUserCard view: {e}")
        return Response({'status': 500, 'error': 'An error occurred while updating the user card'})


@api_view(['DELETE'])
@decorator_from_middleware(AuthenticationMiddleware)
def deleteOneUserCard(request):
    user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    
    if not user_id:
        return Response({'status': 400, 'error': 'User not authenticated'})

    project_id = request.query_params.get('projectId')
    
    if not project_id:
        return Response({'status': 400, 'error': 'Please provide a valid projectId'})

    try:
        project_user_card = ProjectUserCard.objects.get(projectId=project_id, userId=user_id)
        project_user_card.delete()
        return Response({'status': 200, 'message': 'User card deleted successfully'})
    
    except ProjectUserCard.DoesNotExist:
        return Response({'status': 404, 'error': 'User card not found'})

    except Exception as e:
        logger.error(f"Error in deleteOneUserCard view: {e}")
        return Response({'status': 500, 'error': 'An error occurred while deleting the user card'})


@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def updateBudget(request):
    user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    
    if not user_id:
        return Response({'status': 400, 'error': 'User not authenticated'})

    project_id = request.query_params.get('projectId')
    
    if not project_id:
        return Response({'status': 400, 'error': 'Please provide a valid projectId'})
    
    try:
        updatedBudget = request.data.get('budget')
        if not updatedBudget:
            return Response({'status': 400, 'error': 'Please provide a valid Total Budget'})
        
        # Convert project_id to integer
        project_id = int(project_id)
        
        # Fetch the project
        project = Project.objects.get(projectId=project_id)
        
        # Update the budget
        project.budget = updatedBudget
        project.save()
        
        return Response({'status': 200, 'message': 'Budget updated successfully'})
    
    except Project.DoesNotExist:
        return Response({'status': 404, 'error': 'Project not found'})
    except ValueError:
        return Response({'status': 400, 'error': 'Invalid projectId or budget value'})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response({'status': 500, 'error': 'An error occurred while updating the budget'})
