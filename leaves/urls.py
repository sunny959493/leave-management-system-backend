from django.urls import path, include
from .views import (
    HolidayView, LoginView, RegisterView, LeaveTrackerView, LeaveRequestView,
    LeaveApproveView, TeamMembersView, TeamMembersLeaveTrackerView, TeamMembersLeavesView,
    )
from rest_framework_simplejwt.views import TokenRefreshView

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('holiday', HolidayView, basename='holidays')
router.register('leaveTracker', LeaveTrackerView, basename='leave-tracker')
router.register('leaveRequest', LeaveRequestView, basename='leave-requests')
router.register('register', RegisterView, basename='register')
router.register('teamMembers', TeamMembersView, basename='team-members')
router.register('teamMembersLeaveTracker', TeamMembersLeaveTrackerView, basename='team-leave-trackers')
router.register('teamMembersLeaves', TeamMembersLeavesView, basename='team-members-leaves')
router.register('login', LoginView, basename="login") #---> gives access & refresh tokens after login

urlpatterns = [
    path('', include(router.urls)),
    # path('login/', LoginView.as_view(), name='login'), #---> gives access & refresh tokens after login
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'), #---> takes refresh, returns new access when refresh is valid
    path('leaveApprove/<int:pk>/', LeaveApproveView.as_view({'post': 'create'}), name='leave_approve'),
]