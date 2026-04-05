from portal.models import UserActivity

def track_visits(request):
    if request.user.is_authenticated:
        # Update or create the last activity for this specific user
        UserActivity.objects.update_or_create(
            user=request.user,
            defaults={'last_activity': request.user.activity.last_activity if hasattr(request.user, 'activity') else None}
            # Note: auto_now=True handles the update automatically on .save() or update_or_create
        )
    return {}
