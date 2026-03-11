from django.db import models

class DeviceUser(models.Model):
    device_id = models.UUIDField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_blacklisted = models.BooleanField(default=False) # For banning bad actors

class Post(models.Model):
    user_id = models.ForeignKey(DeviceUser,on_delete=models.CASCADE)
    title = models.CharField(max_length=200,)
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField()
    # reactions = models.JSONField()
    # upvote = models.IntegerField()
    # downvote = models.IntegerField()
    

class Vote(models.Model):
    user_id = models.ForeignKey(DeviceUser,on_delete=models.CASCADE)
    post = models.ForeignKey(Post,on_delete=models.CASCADE)
    upvote = models.BooleanField()
    downvote = models.BooleanField()
    reaction = models.CharField()