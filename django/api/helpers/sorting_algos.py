# helpers/sorting_algos.py
from django.utils import timezone

def update_hot_score(post):
    hours_since_post = (timezone.now() - post.created_at).total_seconds() / 3600
    score_margin = post.upvote - post.downvote
    
    # Hot Score (Time Decay)
    post.hot_score = score_margin / (hours_since_post + 2)
    
    # Trending Score (Activity focus)
    # Using your idea: (recent_votes * 2) + total_votes
    # Simplified here as: (upvotes * 2) + total_votes
    total_votes = post.upvote + post.downvote
    post.trending_score = (post.upvote * 2) + total_votes
    
    post.save(update_fields=['hot_score', 'trending_score'])