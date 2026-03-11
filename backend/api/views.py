from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Post
from .serializers import PostSerializer
from .helpers.ip import get_user_ip

class PostView(APIView):
    def get(self,request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        user = getattr(request, 'device_user', None) # Get the user from the request
        if user is None:
            return JsonResponse({"error": "Device ID not found."})
        
        if user.is_blacklisted:
            return JsonResponse({"error": "You are banned"}, status=403)
        
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    