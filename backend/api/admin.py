from django.contrib import admin
from django.db.models import Count, Sum, Q, Avg, F, ExpressionWrapper, FloatField
from django.db.models.functions import TruncDate, TruncHour
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from datetime import timedelta
import json

from .models import DeviceUser, Post, Vote, Report


# ── Inline for Votes on a Post ──────────────────────────────────────
class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ('user_id', 'vote', 'reaction')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ReportInline(admin.TabularInline):
    model = Report
    extra = 0
    readonly_fields = ('user_id', 'content', 'reported_time')
    can_delete = False
    fk_name = 'post_id'

    def has_add_permission(self, request, obj=None):
        return False


# ── DeviceUser Admin ─────────────────────────────────────────────────
@admin.register(DeviceUser)
class DeviceUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_id', 'created_at', 'is_blacklisted', 'post_count', 'report_count')
    list_filter = ('is_blacklisted', 'created_at')
    search_fields = ('device_id',)
    readonly_fields = ('device_id', 'created_at')
    actions = ['blacklist_users', 'unblacklist_users']
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _post_count=Count('post', distinct=True),
            _report_count=Count('report', distinct=True),
        )

    def post_count(self, obj):
        return obj._post_count
    post_count.short_description = 'Posts'
    post_count.admin_order_field = '_post_count'

    def report_count(self, obj):
        return obj._report_count
    report_count.short_description = 'Reports Filed'
    report_count.admin_order_field = '_report_count'

    @admin.action(description='Ban selected users')
    def blacklist_users(self, request, queryset):
        updated = queryset.update(is_blacklisted=True)
        self.message_user(request, f'{updated} user(s) banned.')

    @admin.action(description='Unban selected users')
    def unblacklist_users(self, request, queryset):
        updated = queryset.update(is_blacklisted=False)
        self.message_user(request, f'{updated} user(s) unbanned.')


# ── Post Admin ───────────────────────────────────────────────────────
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'short_title', 'category', 'upvote', 'downvote',
        'net_score', 'hot_score_display', 'reaction_summary', 'report_count', 'created_at',
    )
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('user_id', 'upvote', 'downvote', 'reactions', 'hot_score', 'trending_score', 'created_at')
    inlines = [VoteInline, ReportInline]
    list_per_page = 30
    actions = ['delete_reported_posts']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _report_count=Count('report', distinct=True),
        )

    def short_title(self, obj):
        return obj.title[:50] + '…' if len(obj.title) > 50 else obj.title
    short_title.short_description = 'Title'

    def net_score(self, obj):
        return obj.upvote - obj.downvote
    net_score.short_description = 'Net'

    def hot_score_display(self, obj):
        return f'{obj.hot_score:.2f}'
    hot_score_display.short_description = 'Hot'

    def reaction_summary(self, obj):
        if not obj.reactions:
            return '—'
        return ', '.join(f'{k}: {v}' for k, v in obj.reactions.items())
    reaction_summary.short_description = 'Reactions'

    def report_count(self, obj):
        return obj._report_count
    report_count.short_description = 'Reports'
    report_count.admin_order_field = '_report_count'

    @admin.action(description='Delete posts with 3+ reports')
    def delete_reported_posts(self, request, queryset):
        reported = queryset.filter(_report_count__gte=3)
        count = reported.count()
        reported.delete()
        self.message_user(request, f'{count} heavily-reported post(s) deleted.')


# ── Vote Admin ───────────────────────────────────────────────────────
@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'post_id', 'vote', 'reaction')
    list_filter = ('vote', 'reaction')
    search_fields = ('user_id__device_id',)
    list_per_page = 50


# ── Report Admin ─────────────────────────────────────────────────────
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'post_id', 'user_id', 'short_content', 'reported_time')
    list_filter = ('reported_time',)
    search_fields = ('content', 'post_id__title')
    readonly_fields = ('post_id', 'user_id', 'content', 'reported_time')
    list_per_page = 30
    actions = ['ban_reported_users', 'delete_reported_posts']

    def short_content(self, obj):
        return obj.content[:80] + '…' if len(obj.content) > 80 else obj.content
    short_content.short_description = 'Reason'

    @admin.action(description='Ban authors of reported posts')
    def ban_reported_users(self, request, queryset):
        post_ids = queryset.values_list('post_id', flat=True)
        user_ids = Post.objects.filter(id__in=post_ids).values_list('user_id', flat=True)
        updated = DeviceUser.objects.filter(id__in=user_ids).update(is_blacklisted=True)
        self.message_user(request, f'{updated} user(s) banned.')

    @admin.action(description='Delete the reported posts')
    def delete_reported_posts(self, request, queryset):
        post_ids = queryset.values_list('post_id', flat=True).distinct()
        count = Post.objects.filter(id__in=post_ids).delete()[0]
        self.message_user(request, f'{count} post(s) deleted.')


# ── Helper: percent change ──────────────────────────────────────────
def _pct_change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


# ── Custom Analytics Dashboard ───────────────────────────────────────
def get_analytics_context():
    """Compute all analytics data for the dashboard."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    last_7 = now - timedelta(days=7)
    prev_7 = now - timedelta(days=14)
    last_30 = now - timedelta(days=30)
    last_24h = now - timedelta(hours=24)

    # ── Overview cards ──
    total_posts = Post.objects.count()
    total_users = DeviceUser.objects.count()
    total_votes = Vote.objects.count()
    total_reports = Report.objects.count()
    banned_users = DeviceUser.objects.filter(is_blacklisted=True).count()
    active_users = DeviceUser.objects.filter(is_blacklisted=False).count()
    posts_today = Post.objects.filter(created_at__gte=today_start).count()
    posts_yesterday = Post.objects.filter(created_at__gte=yesterday_start, created_at__lt=today_start).count()
    posts_this_week = Post.objects.filter(created_at__gte=last_7).count()
    posts_prev_week = Post.objects.filter(created_at__gte=prev_7, created_at__lt=last_7).count()
    users_this_week = DeviceUser.objects.filter(created_at__gte=last_7).count()
    users_prev_week = DeviceUser.objects.filter(created_at__gte=prev_7, created_at__lt=last_7).count()
    votes_this_week = Vote.objects.filter(post_id__created_at__gte=last_7).count()

    # Growth percentages
    posts_today_change = _pct_change(posts_today, posts_yesterday)
    posts_week_change = _pct_change(posts_this_week, posts_prev_week)
    users_week_change = _pct_change(users_this_week, users_prev_week)

    # Engagement rate (votes per post this week)
    engagement_rate = round(votes_this_week / posts_this_week, 1) if posts_this_week > 0 else 0

    # ── Posts per day (last 30 days) ──
    posts_per_day = list(
        Post.objects.filter(created_at__gte=last_30)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    posts_dates = [entry['day'].strftime('%b %d') for entry in posts_per_day]
    posts_counts = [entry['count'] for entry in posts_per_day]

    # ── Users per day (last 30 days) ──
    users_per_day = list(
        DeviceUser.objects.filter(created_at__gte=last_30)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    users_dates = [entry['day'].strftime('%b %d') for entry in users_per_day]
    users_counts = [entry['count'] for entry in users_per_day]

    # ── Votes per day (last 30 days) ──
    votes_per_day = list(
        Vote.objects.filter(post_id__created_at__gte=last_30)
        .annotate(day=TruncDate('post_id__created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    votes_dates = [entry['day'].strftime('%b %d') for entry in votes_per_day]
    votes_counts = [entry['count'] for entry in votes_per_day]

    # ── Category breakdown ──
    categories = list(
        Post.objects.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    cat_labels = [c['category'] for c in categories]
    cat_counts = [c['count'] for c in categories]

    # ── Reaction totals ──
    reaction_types = ['haha', 'relatable', 'wtf', 'ughh', 'seriously']
    reaction_totals = {r: 0 for r in reaction_types}
    for post in Post.objects.exclude(reactions={}).only('reactions'):
        for r, c in post.reactions.items():
            if r in reaction_totals:
                reaction_totals[r] += c
    reaction_labels = list(reaction_totals.keys())
    reaction_counts = list(reaction_totals.values())

    # ── Vote split ──
    upvotes_total = Vote.objects.filter(vote=1).count()
    downvotes_total = Vote.objects.filter(vote=-1).count()

    # ── Top 10 posts by net score ──
    top_posts = list(
        Post.objects.annotate(
            net=F('upvote') - F('downvote'),
            total_votes=F('upvote') + F('downvote'),
        ).order_by('-net')[:10]
    )

    # ── Most reported posts ──
    most_reported = list(
        Post.objects.annotate(rc=Count('report'))
        .filter(rc__gt=0)
        .select_related('user_id')
        .order_by('-rc')[:10]
    )

    # ── Activity last 24h by hour ──
    activity_hours = list(
        Post.objects.filter(created_at__gte=last_24h)
        .annotate(hour=TruncHour('created_at'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    activity_labels = [e['hour'].strftime('%H:%M') for e in activity_hours]
    activity_counts = [e['count'] for e in activity_hours]

    # ── Recent reports (last 10) ──
    recent_reports = list(
        Report.objects.select_related('post_id', 'user_id')
        .order_by('-reported_time')[:10]
    )

    return {
        # Cards
        'total_posts': total_posts,
        'total_users': total_users,
        'total_votes': total_votes,
        'total_reports': total_reports,
        'banned_users': banned_users,
        'active_users': active_users,
        'posts_today': posts_today,
        'posts_this_week': posts_this_week,
        'users_this_week': users_this_week,
        'engagement_rate': engagement_rate,
        # Growth
        'posts_today_change': posts_today_change,
        'posts_week_change': posts_week_change,
        'users_week_change': users_week_change,
        # Posts per day chart
        'posts_dates': json.dumps(posts_dates),
        'posts_counts': json.dumps(posts_counts),
        # Users per day chart
        'users_dates': json.dumps(users_dates),
        'users_counts': json.dumps(users_counts),
        # Votes per day chart
        'votes_dates': json.dumps(votes_dates),
        'votes_counts': json.dumps(votes_counts),
        # Category chart
        'cat_labels': json.dumps(cat_labels),
        'cat_counts': json.dumps(cat_counts),
        # Reactions chart
        'reaction_labels': json.dumps(reaction_labels),
        'reaction_counts': json.dumps(reaction_counts),
        # Vote split
        'upvotes_total': upvotes_total,
        'downvotes_total': downvotes_total,
        # Top posts
        'top_posts': top_posts,
        # Most reported
        'most_reported': most_reported,
        # 24h activity
        'activity_labels': json.dumps(activity_labels),
        'activity_counts': json.dumps(activity_counts),
        # Recent reports
        'recent_reports': recent_reports,
        # Timestamp
        'generated_at': now,
    }


# Inject dashboard view into default admin site
def dashboard_view(request):
    context = get_analytics_context()
    context.update(admin.site.each_context(request))
    context['title'] = 'Analytics Dashboard'
    return TemplateResponse(request, 'admin/analytics_dashboard.html', context)


# Monkey-patch the default admin to add the dashboard URL
original_get_urls = admin.AdminSite.get_urls


def custom_get_urls(self):
    custom_urls = [
        path('dashboard/', self.admin_view(dashboard_view), name='analytics-dashboard'),
    ]
    return custom_urls + original_get_urls(self)


admin.AdminSite.get_urls = custom_get_urls

# Customise admin site headers
admin.site.site_header = 'Anon Confession Admin'
admin.site.site_title = 'Anon Confession'
admin.site.index_title = 'Management Panel'
