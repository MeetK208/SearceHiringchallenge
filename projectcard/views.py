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

logger = logging.getLogger(__name__)

# Helper to get the user from cookies and check authentication
def get_authenticated_user(request):
    user_id = request.COOKIES.get('userId')
    if not user_id:
        return None
    return user_id

# Helper to get the project and verify ownership/collaborator status
def get_project_and_authorize(user_id, project_id):
    try:
        project = Project.objects.get(projectId=int(project_id))
        if project.user_id == int(user_id):
            return project, True
        else:
            is_collaborator = ProjectUser.objects.filter(Q(projectId=project) & Q(userId=int(user_id))).exists()
            if is_collaborator:
                return project, True
        return None, False
    except Project.DoesNotExist:
        return None, False


@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def getAllProject(request):
    user_id = get_authenticated_user(request)

    if not user_id:
        return Response({'status': 'error', 'message': 'User not authenticated'})

    try:
        # Fetch projects owned by the user
        user_projects = Project.objects.filter(user_id=user_id)

        # Fetch project IDs where the user is a collaborator
        collaborator_projects_ids = ProjectUser.objects.filter(userId=user_id).values_list('projectId', flat=True)
        collaborator_projects = Project.objects.filter(projectId__in=collaborator_projects_ids)

        # Combine the projects owned by the user and projects they are a collaborator on
        all_projects = (user_projects | collaborator_projects).distinct()

        # Prepare the final result including owner and collaborator details
        project_data = []

        for project in all_projects:
            # Check if the user is the owner of the project by checking `is_owner` in ProjectUser
            is_owner = ProjectUser.objects.filter(userId=user_id, projectId=project.projectId, is_owner=True).exists()

            # Fetch project owner details
            owner = User.objects.filter(userId=project.user.userId).values('userId', 'username', 'email').first()

            # Fetch collaborators for the project, including their `is_owner` status
            collaborators = ProjectUser.objects.filter(projectId=project.projectId).exclude(userId=user_id)

            collaborator_details = []
            for collaborator in collaborators:
                # Fetch user details for each collaborator
                user = User.objects.filter(userId=collaborator.userId.userId).values('userId', 'username', 'email').first()

                if user:
                    collaborator_details.append({
                        'userId': user['userId'],
                        'name': user['username'],
                        'email': user['email'],
                        'is_owner': collaborator.is_owner  # Add the is_owner field here
                    })

            # Serialize project details and include owner and collaborators
            serialized_project = ProjectSerializer(project).data
            serialized_project['owner'] = {
                'userId': owner['userId'],
                'name': owner['username'],
                'email': owner['email']
            }  # Add owner details
            serialized_project['collaborators'] = collaborator_details  # Add collaborator details
            serialized_project['is_owner'] = is_owner  # Add ownership flag for the current user

            project_data.append(serialized_project)

        return Response({ 
            'status': 'success',
            'message': 'Projects retrieved successfully',
            'userid': user_id,
            'email': request.COOKIES.get('email'),
            'projects': project_data
        })

    except Exception as e:
        logger.error(f"Error retrieving projects for user {user_id}: {e}")
        return Response({'status': 'error', 'message': str(e)})

@api_view(['POST'])
@decorator_from_middleware(AuthenticationMiddleware)
def createProject(request):
    user_id = get_authenticated_user(request)
    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    coplanners = request.data.get('coplanners')  # This is the array of userIds

    required_fields = ['projectName', 'budget', 'totalPosition']
    if not all(request.data.get(field) for field in required_fields):
        return Response({'status': 'error', 'message': 'Provide all required fields'})

    try:
        user = User.objects.get(pk=user_id)

        new_project = Project.objects.create(
            projectName=request.data.get('projectName'),
            projectDesc=request.data.get('projectDesc', ''),
            user=user,
            budget=request.data.get('budget'),
            totalPosition=request.data.get('totalPosition'),
            role=request.data.get('role', 'CEO'),
            last_edited_by_userId= user
        )

        project_data = ProjectSerializer(new_project).data
        
        print("coplanners",coplanners)
        if coplanners:
            for useridAdd in coplanners:
                useradd = User.objects.get(pk=useridAdd)
                ProjectUser.objects.create(projectId=new_project, userId=useradd)
        
        # Creating ProjectUser instance for the owner
        owner_project_user = ProjectUser.objects.create(userId=user, projectId=new_project, is_owner=True)

        # Optional: Explicitly save the object if needed (usually not required with create())
        owner_project_user.save()
        print(owner_project_user)
        # project_user_data = ProjectUserSerializer(new_project_user).data

        return  Response({ 
            'status': 'success',
            'message': 'Project created successfully',
            'project': project_data,
        })

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found.")
        return Response({'status': 'error', 'message': 'User not found'})

    except Exception as e:
        logger.error(f"Error creating project for user {user_id}: {e}")
        return Response({'status': 'error', 'message': 'Failed to create project'})


@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def getOneProjectCard(request):
    user_id = get_authenticated_user(request)
    projectId = request.query_params.get('projectId')

    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    if not projectId:
        return Response({'status': 'error', 'message': 'Please provide a valid projectId'})

    try:
        project, authorized = get_project_and_authorize(user_id, projectId)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to view this project'})

        project_data = ProjectSerializer(project).data

        return  Response({ 
             'status': 'success',
            'message': 'Project found successfully',
            'project': project_data
        })
    except Exception as e:
        logger.error(f"Error fetching project {projectId} for user {user_id}: {e}")
        return Response({'status': 'error', 'message': 'Failed to retrieve project'})


@api_view(['PUT'])
@decorator_from_middleware(AuthenticationMiddleware)
def editOneProjectCard(request):
    user_id = get_authenticated_user(request)
    project_id = request.query_params.get('projectId')

    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    if not project_id:
        return Response({'status': 'error', 'message': 'Project ID is required'})

    try:
        # Retrieve project and check authorization
        project, authorized = get_project_and_authorize(user_id, project_id)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to edit this project'})
        
        # Update 'last_edited_by_userId'
        request.data['last_edited_by_userId'] = user_id
        
        # Serialize and update project
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            updated_project = serializer.save()
            project_data = ProjectSerializer(updated_project).data
            return Response({
                'status': 'success',
                'message': 'Project updated successfully',
                'project': project_data
            })
        return Response({'status': 'error', 'message': serializer.errors})

    except Project.DoesNotExist:
        logger.error(f"Project {project_id} does not exist for user {user_id}")
        return Response({'status': 'error', 'message': 'Project not found'})
    except Exception as e:
        logger.error(f"Error updating project {project_id} for user {user_id}: {e}")
        return Response({'status': 'error', 'message': 'Failed to update project'})


@api_view(['DELETE'])
@decorator_from_middleware(AuthenticationMiddleware)
def deleteOneProjectCard(request):
    user_id = get_authenticated_user(request)
    projectId = request.query_params.get('projectId')

    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    if not projectId:
        return Response({'status': 'error', 'message': 'Please provide a valid projectId'})

    try:
        project, authorized = get_project_and_authorize(user_id, projectId)
        if not authorized:
            return Response({'status': 'error', 'message': 'You are not authorized to delete this project'})

        project.delete()
        return Response({'status': 'success', 'message': 'Project deleted successfully'})

    except Exception as e:
        logger.error(f"Error deleting project {projectId} for user {user_id}: {e}")
        return Response({'status': 'success', 'message': 'Failed to delete project'})

@api_view(['GET'])
@decorator_from_middleware(AuthenticationMiddleware)
def all_usersList(request):
    print("Herr")
    user_id = get_authenticated_user(request)
    if not user_id:
        Response({'status': 'error', 'message': 'User not authenticated'})

    try:
        # Fetch all users except the authenticated user
        all_users = User.objects.exclude(userId=user_id).values('userId', 'username', 'email')
        
        return Response({
            'status': 'success', 
            'message': 'Collaborators retrieved successfully',
            'all_users': list(all_users)  # Ensure it’s a list
        })
    except Exception as e:
        logger.error(f"Error retrieving collaborators for user {user_id}: {e}")
        return Response({'status': 'success',  'message': 'Failed to retrieve collaborators'})




# from django.shortcuts import render
# from django.shortcuts import render
# from rest_framework.response import Response
# from rest_framework.decorators import api_view
# from .models import *
# from .serializers import *
# from passlib.hash import pbkdf2_sha256
# import logging
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from django.utils.decorators import decorator_from_middleware
# from register.middleware import AuthenticationMiddleware
# from django.db.models import Q

# logger = logging.getLogger(__name__)

# @api_view(['GET'])
# @decorator_from_middleware(AuthenticationMiddleware)
# def getAllProject(request):
#     user_id = request.COOKIES.get('userId')  # Get user ID from cookies

#     if not user_id:
#         Response({'status': 'error', 'message': 'User not authenticated'})

#     try:
#         # Projects directly associated with the user
#         user_projects = Project.objects.filter(user_id=user_id)
        
#         # Projects associated with the user through ProjectUser
#         collaborator_projects_ids = ProjectUser.objects.filter(userId_id=user_id).values_list('projectId', flat=True)
#         collaborator_projects = Project.objects.filter(projectId__in=collaborator_projects_ids)

#         # Combine both querysets and remove duplicates
#         all_projects = user_projects | collaborator_projects
#         unique_projects = all_projects.distinct()  # Ensure no duplicate projects

#         # Serialize the combined queryset
#         serializer = ProjectSerializer(unique_projects, many=True)

#         return Response({
#             'status': 200,
#             'message': 'Projects retrieved successfully',
#             'userid': user_id,
#             'email': request.COOKIES.get('email'),
#             'projects': serializer.data
#         })

#     except Project.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Projects not found'})
#     except Exception as e:
#         return Response({'status': 'error', 'message': str(e)})


# @api_view(['POST'])
# @decorator_from_middleware(AuthenticationMiddleware)
# def createProject(request):
#     user_id = request.COOKIES.get('userId')  # Get user ID from cookies

#     if not user_id:
#         Response({'status': 'error', 'message': 'User not authenticated'})

#     # Check if all required fields are present
#     if not request.data.get('projectName') or not request.data.get('budget') or not request.data.get('totalPosition'):
#         return Response({'status': 'error', 'message': 'Provide all required fields'})

#     try:
#         user = User.objects.get(pk=user_id)  # Assuming you have the userId from cookies

#         # Create the project
#         new_project = Project.objects.create(
#             projectName=request.data.get('projectName'),
#             projectDesc=request.data.get('projectDesc', ''),
#             user=user,
#             budget = request.data.get('budget'),
#             totalPosition=request.data.get('totalPosition'),
#             role=request.data.get('role', 'CEO')
#         )

#         # Serialize the created project
#         project_data = ProjectSerializer(new_project).data

#         # Create a new ProjectUser entry
#         new_project_user = ProjectUser.objects.create(
#             userId=user,
#             projectId=new_project
#         )

#         project_user_data = ProjectUserSerializer(new_project_user).data

#         return Response({
#             'status': 200,
#             'message': 'Project created successfully',
#             'project': project_data,  # Serialized project data
#             'projectUser': project_user_data  # Serialized project-user data
#         })

#     except User.DoesNotExist:
#         return Response({'status': 'error', 'message': 'User not found'})

#     # Return errors if the request data is invalid
#     return Response({
#         'status': 'error',
#         'error': 'Invalid data'
#     })



# @api_view(['GET'])
# @decorator_from_middleware(AuthenticationMiddleware)
# def getOneProjectCard(request):
#     user_id = request.COOKIES.get('userId')  # Get user ID from cookies
#     print("GetOne")
#     if not user_id:
#         Response({'status': 'error', 'message': 'User not authenticated'})

#     projectId = request.query_params.get('projectId')
    
#     if not projectId:
#         return Response({'status': 'error', 'message': 'Please provide a valid projectId'})
    
#     try:
#         project = Project.objects.get(projectId=int(projectId))
        
#         if project.user_id != int(user_id):
#             is_collaborator = ProjectUser.objects.filter(
#                 Q(projectId=project) & Q(userId=int(user_id))
#             ).exists()

#             if not is_collaborator:
#                 return Response({'status': 'error', 'message': 'You are Not Authorized to View This Project!! Please Check ProjectId'})

        
#         project_data = ProjectSerializer(project).data

#         # Optionally, if you need to include associated project-user data
#         project_users = ProjectUser.objects.filter(projectId=project)
#         project_user_data = ProjectUserSerializer(project_users, many=True).data

#         return Response({
#             'status': 200,
#             'message': 'Project found successfully',
#             'project': project_data,  # Serialized project data
#             # 'projectUser': project_user_data  # Serialized project-user data (optional)
#         })
#     except Project.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Project not found'})
    
    
    

# @api_view(['PUT'])  # Use PUT for updates, not UPDATE
# @decorator_from_middleware(AuthenticationMiddleware)
# def editOneProjectCard(request):
#     user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    
#     if not user_id:
#         Response({'status': 'error', 'message': 'User not authenticated'})
    
#     project_id = request.query_params.get('projectId')
#     if not project_id:
#         return Response({'status': 'error', 'message': 'Project ID is required'})
    
#     try:
#         project = Project.objects.get(projectId=int(project_id))
#         if project.user_id != int(user_id):
#             is_collaborator = ProjectUser.objects.filter(
#                 Q(projectId=project) & Q(userId=int(user_id))
#             ).exists()

#             if not is_collaborator:
#                 return Response({'status': 'error', 'message': 'You are Not Authorized to Edit This Project!! Please Check ProjectId'})
#     except Project.DoesNotExist:
#         Response({'status': 'error', 'message': 'Project not found'})
    
#     serializer = ProjectSerializer(project, data=request.data, partial=True)  # Use partial=True for partial updates

#     if serializer.is_valid():
#         updated_project = serializer.save()  # Save the updated project
#         project_data = ProjectSerializer(updated_project).data
        
#         return Response({
#             'status': 200,
#             'message': 'Project updated successfully',
#             'project': project_data,  # Serialized project data
#         })
    
#     return Response({
#         'status': 'error',
#         , 'message': serializer.errors
#     })



# @api_view(['DELETE'])
# @decorator_from_middleware(AuthenticationMiddleware)
# def deleteOneProjectCard(request):
#     user_id = request.COOKIES.get('userId')  # Get user ID from cookies
    
#     if not user_id:
#         Response({'status': 'error', 'message': 'User not authenticated'})

    
#     projectId = request.query_params.get('projectId')
    
    
#     if not projectId:
#         return Response({'status': 'error', 'message': 'Please provide a valid projectId'})
    
#     try:
#         project = Project.objects.get(projectId=int(projectId))
        
#         if project.user_id != int(user_id):
#             return Response({'status': 'error', 'message': 'You are Not Authorized to delete'})
        
#         project.delete()  # Delete the project
        
#         return Response({'status': 'success', 'message': 'Project deleted successfully'})
    
#     except Project.DoesNotExist:
#         Response({'status': 'error', 'message': 'Project not found'})



