from django.urls import path, include
from .views import (
    HolidayView, LoginView, RegisterView, LeaveTrackerView, LeaveRequestView,
    LeaveApproveView, TeamMembersView, TeamMembersLeaveTrackerView, TeamMembersLeavesView,
    )
from rest_framework_simplejwt.views import TokenRefreshView

from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter, DefaultRouter
router = DefaultRouter()
router.register('holiday', HolidayView, basename='holidays')
router.register('leaveTracker', LeaveTrackerView, basename='leave-tracker')
router.register('leaveRequest', LeaveRequestView, basename='leave-requests')
router.register('register', RegisterView, basename='register')
router.register('teamMembers', TeamMembersView, basename='team-members')
router.register('teamMembersLeaveTracker', TeamMembersLeaveTrackerView, basename='team-leave-trackers')
router.register('login', LoginView, basename="login") #---> gives access & refresh tokens after login

teamMembers_router = NestedDefaultRouter(router, 'teamMembers', lookup = 'user')
teamMembers_router.register('leaveRequests', TeamMembersLeavesView, basename='team-members-leaves')

urlpatterns = [
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'), #---> takes refresh, returns new access when refresh is valid
    path('leaveApprove/<int:pk>/', LeaveApproveView.as_view({'post': 'create'}), name='leave_approve'),
    path('', include(router.urls)),
    path('', include(teamMembers_router.urls))
]