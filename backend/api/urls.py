from django.urls import path
from .views import PostView,VoteView,CategoryView,ReportView


urlpatterns = [
    path('posts/', PostView.as_view(), name='posts'),
    path('posts/<int:id>/vote/', VoteView.as_view(), name='vote'),
    path('posts/category/', CategoryView.as_view(), name='category'),
    path('report/', ReportView.as_view(), name='report'),
]