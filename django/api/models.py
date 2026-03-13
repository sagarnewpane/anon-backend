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
    category = models.CharField(max_length=30)
    upvote = models.IntegerField(default=0)
    downvote = models.IntegerField(default=0)
    reactions = models.JSONField(default=dict)
    hot_score = models.FloatField(default=0.0, db_index=True) # Index for fast sorting
    trending_score = models.IntegerField(default=0, db_index=True)

    
    

class Vote(models.Model):
    user_id = models.ForeignKey(DeviceUser,on_delete=models.CASCADE)
    post_id = models.ForeignKey(Post,on_delete=models.CASCADE)
    vote = models.SmallIntegerField(
        choices=[(1, "Upvote"), (-1, "Downvote")],
        null=True,
        blank=True
    )

    reaction = models.CharField(
        max_length=20,
        choices=[
            ("haha", "haha"),
            ("relatable", "relatable"),
            ("wtf", "wtf"),
            ("ughh", "ughh"),
            ("seriously", "seriously"),
        ],
        null=True,
        blank=True
    )
    class Meta:
        unique_together = ("user_id", "post_id")

class Report(models.Model):
    post_id = models.ForeignKey(Post, on_delete=models.CASCADE)
    user_id = models.ForeignKey(DeviceUser, on_delete=models.CASCADE)
    content = models.CharField(max_length=500)
    reported_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user_id", "post_id")
