from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Holiday, LeaveTracker, LeaveRequest, CustomUser
from .serializers import (HolidaySerializer, LoginSerializer, RegisterSerializer, LeaveTrackerSerializer,
LeaveRequestSerializer, UserSerializer, LeaveApproveSerializer)
from rest_framework import status, mixins, generics, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .filters import HolidayCustomFilter, LeaveRequestCustomFilter, TeamLeaveTrackerCustomFilter
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

class RegisterView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    # permission_classes = [IsAdminUser]
    serializer_class = RegisterSerializer

class LoginView(viewsets.ViewSet):
    @extend_schema(
            request=LoginSerializer,
            responses=LoginSerializer, 
            description="login schema"
    )
    @action(detail=False, methods=["post"])
    def get_tokens(self, request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HolidayView(
            mixins.ListModelMixin, 
            mixins.CreateModelMixin, 
            mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):

    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = HolidayCustomFilter
    search_fields = ['name', 'date'] #-->drf search filters
    ordering_fields = ['date', 'name'] #-->drf ordering fields
    ordering = ['date'] #-->default ordering

    def get_permissions(self):
        if self.action in ['create','update','destroy']:
            self.permission_classes=[IsAdminUser]
        else:
            self.permission_classes=[IsAuthenticated]
        return super().get_permissions()


class LeaveTrackerView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] # if a user is not having reporting manager then this is not needed
    serializer_class = LeaveTrackerSerializer

    def get_queryset(self):
        return LeaveTracker.objects.filter(user = self.request.user)

    
class LeaveRequestView(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] # same this applies here @permission classes line in LeaveTrackerView
    serializer_class = LeaveRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reason']
    ordering = ['start_date']
    filterset_class = LeaveRequestCustomFilter

    def get_queryset(self):
        return LeaveRequest.objects.filter(user = self.request.user)


class LeaveApproveView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveApproveSerializer

    def get_queryset(self):
        user = self.request.user
        team_members = user.team_members.all()
        team_members_id = []
        for member in team_members:
            team_members_id.append(member.id)
        return LeaveRequest.objects.filter(user__in = team_members_id)

    @extend_schema(
            request=LeaveApproveSerializer,
            description="reporing manager reviewing the leave request"
    )
    def create(self, request, **kwargs):
        pk = kwargs.get('pk')
        # breakpoint()
        serializer = self.get_serializer(data=request.data, context={"pk":pk, "request":request})
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data.get('action')
        leave_request = self.get_object()
        
        if action=='approve':
            leave_tracker = LeaveTracker.objects.get(user = leave_request.user)
            leave_request.status = 'approved'
            leave_request.reviewed_by = request.user.username
            leave_tracker.leaves_taken+=leave_request.days
            leave_tracker.save()
        elif action=='reject':
            leave_request.status = 'rejected'
            leave_request.reviewed_by = request.user.username
        leave_request.save()
        return Response({'status': leave_request.status})
    

class TeamMembersView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] # same here 
    serializer_class = UserSerializer

    def get_queryset(self):
        # breakpoint()
        user = self.request.user
        Team_members = user.team_members.all()
        return Team_members


class TeamMembersLeaveTrackerView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] #same
    serializer_class = LeaveTrackerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamLeaveTrackerCustomFilter

    def get_queryset(self):
        user = self.request.user
        team_members = user.team_members.all()
        team_members_ids = []
        for member in team_members:
            team_members_ids.append(member.id)
        return LeaveTracker.objects.filter(user__in = team_members_ids)
    
class TeamMembersLeavesView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] # same
    serializer_class = LeaveRequestSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        team_members = user.team_members.all()
        team_members_id = []
        for member in team_members:
            team_members_id.append(member.id)
        return LeaveRequest.objects.filter(user__in = team_members_id)