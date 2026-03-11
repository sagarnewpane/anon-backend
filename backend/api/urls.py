from django.urls import path
from .views import PostView,VoteView


urlpatterns = [
    path('posts/', PostView.as_view(), name='posts'),
    path('posts/<int:id>/', VoteView.as_view(), name='vote'),
]