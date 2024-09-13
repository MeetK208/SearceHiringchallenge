from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('get-all', views.getAllProject, name = "getAllProject"),
    path('create-project', views.createProject, name = "createProject"),
    path('get-one', views.getOneProjectCard, name = "getOneProjectCard"),
    path('update-one', views.editOneProjectCard, name = "editOneProjectCard"),
    path('delete-one', views.deleteOneProjectCard, name = "deleteOneProjectCard"),
    path('all-user', views.all_usersList, name = "all_usersList"),
]
