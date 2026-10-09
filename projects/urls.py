from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.project_list, name='list'),
    path('create/', views.project_create, name='create'),
    path('categories/', views.category_list, name='categories'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/donate/', views.donate, name='donate'),
    path('<int:pk>/comment/', views.add_comment, name='comment'),
    path('comments/<int:pk>/reply/', views.add_reply, name='reply'),
    path('<int:pk>/rate/', views.rate_project, name='rate'),
    path('<int:pk>/report/', views.report_project, name='report'),
    path('<int:pk>/cancel/', views.cancel_project, name='cancel'),
    path('comments/<int:pk>/report/', views.report_comment, name='report_comment'),
]
