from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Holiday, LeaveTracker, LeaveRequest, CustomUser
from .serializers import (HolidaySerializer, LoginSerializer, RegisterSerializer, LeaveTrackerSerializer,
LeaveRequestSerializer, UserSerializer, LeaveApproveSerializer)
from rest_framework import status, mixins, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .filters import HolidayCustomFilter, LeaveRequestCustomFilter, TeamLeaveTrackerCustomFilter
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from .pagination import CustomPagination

class RegisterView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    # permission_classes = [IsAdminUser]
    serializer_class = RegisterSerializer

class LoginView(viewsets.GenericViewSet):
    serializer_class = LoginSerializer

    @extend_schema(
            request=LoginSerializer,
            responses=LoginSerializer,              #-->not using model, so explicitly mentioning the extend_schema
            description="login schema"
    )
    @action(methods=["post"], detail=False,) #-->to have custom endpoints fot 'methods' oprations
    def get_tokens(self, request):
        # serializer = LoginSerializer(data = request.data)
        serializer = self.get_serializer(data = request.data)
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
        # breakpoint()
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
    permission_classes = [IsAuthenticated] # same thing applies here @permission classes line in LeaveTrackerView
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
        user = self.request.user #--> reporting manager user
        team_members = user.team_members.all()
        team_members_id = []
        for member in team_members:
            team_members_id.append(member.id)
        return LeaveRequest.objects.filter(user__in = team_members_id)
    
    def get_object(self):
        leave_id = self.kwargs.get('leave_pk')
        queryset = self.get_queryset()
        return queryset.get(id = leave_id)
    
    def create(self, request, **kwargs):
        pk = kwargs.get('leave_pk')
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

        output_serializer = self.get_serializer(leave_request) #-->will serialize the leave request instance to get status as output
        return Response(output_serializer.data, status=status.HTTP_200_OK)
    

class TeamMembersView(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = TeamLeaveTrackerCustomFilter

    def get_queryset(self):
        user = self.request.user
        team_members = user.team_members.all()
        team_members_ids = []  #--> all team members of logged in user
        for member in team_members:
            team_members_ids.append(member.id)
        team_member_id = int(self.kwargs.get('user_pk')) #--> team member id from url
        if team_member_id in team_members_ids:
            return LeaveTracker.objects.filter(user = team_member_id)
        else:
            return LeaveTracker.objects.none()
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset.count() == 0:
            return Response({"message": "The entered user is not in your team."})
        
        return super().list(request, *args, **kwargs)
    
class TeamMembersLeavesView(mixins.ListModelMixin, mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] # same
    serializer_class = LeaveRequestSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['status']
    ordering = ['-id']
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        team_members = user.team_members.all()
        team_members_id = []
        for member in team_members:  #--> team memebers id's
            team_members_id.append(member.id)
        team_member_user_id = int(self.kwargs.get('user_pk')) #--->team member user_id
        if team_member_user_id in team_members_id: #checking whether given user's id is in team members user id's
            return LeaveRequest.objects.filter(user_id = team_member_user_id)
        else:
            return LeaveRequest.objects.none()
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset.count() == 0:
            return Response({"message": "The entered user is not in your team or The user dont have any leave history"})
        
        return super().list(request, *args, **kwargs)