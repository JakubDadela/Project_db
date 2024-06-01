from django.urls import path
from .import views

urlpatterns = [
    path('', views.home, name='home'),
    path('project/<str:project_id>/', views.project_view),
    path('add_new_project/', views.add_project_view),
    path('project/<str:project_id>/add_new_task/', views.addTaskView),
    path('add_labels/', views.addLabelView),
    path('users/', views.usersView, name='users'),
    path('users/create/', views.createUserView),
    path('users/<str:user_id>/delete/',views.deleteUser, name='user-delete'),
    path('users/<str:user_id>/edit/',views.editUser, name='user-edit'),
    path('project/<str:project_id>/task/<str:task_id>/', views.taskView),
    path('add-label/task/<str:task_id>/',views.addNewLabelView),
    path('delete-label/task/<str:task_id>/', views.deleteLabelView),
    path('project/<str:project_id>/add_user/', views.add_user_to_project_view, name='add_user_to_project'),
    path('project/<str:project_id>/remove_user/', views.remove_user_from_project_view, name='remove_user_from_project')
]