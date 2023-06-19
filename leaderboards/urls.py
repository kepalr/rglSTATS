from django.urls import path

from . import views

urlpatterns = [
     # ex: /leaderboards/
    path('', views.index, name='index'),
    path('lookup/', views.lookup, name='lookup'),
    path('lookup/<int:player_id>/', views.lookup, name='lookup'),
    path('player/<int:player_id>/', views.stat, name='stat'),
    path('<str:div>/', views.index, name='index'),
    path('<str:div>/<str:c>/', views.index, name='index'),
    # ex: /leaderboards/5/
    
    # ex: /leaderboards/5/name/
    path('<int:player_id>/div/', views.division, name='div'),
    # ex: /leaderboards/5/team/
    # path('<int:player_id>/team/', views.team, name='team'),
]