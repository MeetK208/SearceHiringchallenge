from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('get-all', views.getAllUserCard, name='getAllUserCard'),
    path('update-user', views.updateOneUserCard,name='updateOneUserCard'),
    path('delete-user', views.deleteOneUserCard,name='deleteOneUserCard'),
    # path('kpi-user', views.KpiGenerate,name='KpiGenerate'),
    path('update-budgate', views.updateBudget,name='updateBudgate'),
    path('create-user', views.CreateUserCard,name='CreateUserCard'),
]
