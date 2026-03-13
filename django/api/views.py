from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .helpers.sorting_algos import update_hot_score
from .models import Post, Vote
from .serializers import PostSerializer,ReportSerializer
from django.db import transaction, IntegrityError
from django.db.models import F, Count
from django.core.cache import cache

VALID_VOTES = {1, -1}

class PostView(APIView):
    def get(self, request):
        sort = request.query_params.get('sort', 'new') # Default to 'new'
        posts = Post.objects.all()

        if sort == 'new':
            posts = posts.order_by('-created_at')
        elif sort == 'hot':
            posts = posts.order_by('-hot_score')
        elif sort == 'trending':
            posts = posts.order_by('-trending_score')

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
    

class CategoryView(APIView):
    def get(self,request):
        category = request.query_params.get('category')
        if not category:
            return Response({"error": "category parameter is required."}, status=400)
        posts = Post.objects.filter(category=category)
        serializer = PostSerializer(posts, many=True) 
        return Response(serializer.data)
    
class CategoryCountView(APIView):
    def get(self,request):
        category_counts = cache.get('category_counts')
        if not category_counts:
            category_counts = list(Post.objects.values('category').annotate(count=Count('category')))
            cache.set('category_counts', category_counts, timeout=30) # Cache for 5 minutes
        return Response(category_counts)

    

class ReportView(APIView):
    def post(self,request):
        user = getattr(request, 'device_user', None) # Get the user from the request
        if user is None:
            return JsonResponse({"error": "Device ID not found."})
        
        if user.is_blacklisted:
            return JsonResponse({"error": "You are banned"}, status=403)
        
        serializer = ReportSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(user_id=user)
            except IntegrityError:
                return Response({"error": "Already reported"}, status=409)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)



class VoteView(APIView):

    def post(self, request, id):

        user = getattr(request, 'device_user', None)
        if user is None:
            return JsonResponse({"error": "Device ID not found."})
        
        if user.is_blacklisted:
            return JsonResponse({"error": "You are banned"}, status=403)

        # Validate input
        new_vote = request.data.get('vote')
        new_reaction = request.data.get('reaction')

        if new_vote is not None:
            try:
                new_vote = int(new_vote)
            except (ValueError, TypeError):
                return Response({"error": "vote must be 1 or -1."}, status=400)
            if new_vote not in VALID_VOTES:
                return Response({"error": "vote must be 1 or -1."}, status=400)

        with transaction.atomic():
            try:
                post = Post.objects.select_for_update().get(id=id)
                update_hot_score(post)
            except Post.DoesNotExist:
                return Response({"error": "Post not found."}, status=404)

            existing = Vote.objects.filter(user_id=user, post_id=post).first()
            old_vote = existing.vote if existing else None
            old_reaction = existing.reaction if existing else None

            # Toggle: same vote again removes it
            if new_vote == old_vote:
                new_vote = None

            # Update vote counts
            if old_vote != new_vote:
                if old_vote == 1:
                    post.upvote = F('upvote') - 1
                elif old_vote == -1:
                    post.downvote = F('downvote') - 1
                if new_vote == 1:
                    post.upvote = F('upvote') + 1
                elif new_vote == -1:
                    post.downvote = F('downvote') + 1

            # Update reaction counts
            reactions = post.reactions.copy()
            if old_reaction and old_reaction != new_reaction:
                count = reactions.get(old_reaction, 1) - 1
                if count <= 0:
                    reactions.pop(old_reaction, None)
                else:
                    reactions[old_reaction] = count
            if new_reaction and new_reaction != old_reaction:
                reactions[new_reaction] = reactions.get(new_reaction, 0) + 1

            post.reactions = reactions
            post.save()
            post.refresh_from_db()

            # Save the vote record
            Vote.objects.update_or_create(
                user_id=user, post_id=post,
                defaults={'vote': new_vote, 'reaction': new_reaction}
            )

        return Response({"upvote": post.upvote, "downvote": post.downvote, "reactions": post.reactions})


    