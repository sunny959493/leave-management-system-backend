from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    reporting_manager = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='team_members'
        )
    
class Holiday(models.Model):
    name = models.CharField(max_length=50)
    date = models.DateField()

class LeaveTracker(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='leave_tracker')
    total_leaves = models.IntegerField(default=20)
    leaves_taken = models.IntegerField(default=0)
    
    def leaves_left(self):
        return (self.total_leaves - self.leaves_taken)
    
class LeaveRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status_choices = [
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('rejected', 'rejected')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='pending') # know the diff of passing choices as choices and directly using choiceField
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.CharField(max_length=150, null=True, blank=True)
    days = models.IntegerField(null=True, blank=True)
