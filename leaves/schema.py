import graphene
import graphql_jwt
from graphene_django import DjangoObjectType
from .models import Holiday, LeaveTracker, LeaveRequest, CustomUser
from django.contrib.auth import authenticate
from graphql import GraphQLError
from graphql_jwt.shortcuts import get_token, get_user_by_token
from graphql_jwt.refresh_token.shortcuts import create_refresh_token
from datetime import date
from graphql_jwt.refresh_token.models import RefreshToken
from .permissions import permission_required, IsAdmin, IsAuthenticated

class HolidayType(DjangoObjectType):
    class Meta:
        model = Holiday
        fields = ['name', 'date']

class LeaveTrackerType(DjangoObjectType):
    leaves_left = graphene.Int()
    class Meta:
        model = LeaveTracker
        fields = ['total_leaves', 'leaves_left', 'leaves_taken']
    def resolve_leaves_left(self, info):
        return (self.total_leaves - self.leaves_taken)

class LeaveRequestType(DjangoObjectType):
    class Meta:
        model = LeaveRequest
        fields = '__all__'

class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        # fields = ['id', 'username', 'reporting_manager']
        fields = '__all__'


class Query(graphene.ObjectType):
    holidays = graphene.List(HolidayType) #-->get all holidays list
    leave_tracker = graphene.Field(LeaveTrackerType) #--> get leave tracker of user
    leave_request = graphene.List(LeaveRequestType, 
                                  status=graphene.String(required=False)) #--> all leave requests of that user
    user = graphene.Field(UserType) #-->
    team_members_leaves = graphene.List(LeaveRequestType)
    team_members = graphene.List(UserType)

    @permission_required(IsAuthenticated) #-->using custom authenticators
    def resolve_holidays(self, info):
        # breakpoint()
        return Holiday.objects.all()
    
    @permission_required(IsAuthenticated)
    def resolve_leave_tracker(self, info):
        return LeaveTracker.objects.get(user = info.context.user)
    
    @permission_required(IsAuthenticated)
    def resolve_leave_request(self, info, status=None):
        user = info.context.user
        queryset = LeaveRequest.objects.filter(user = user)
        if status:
            return queryset.filter(status=status)
        return queryset
    
    @permission_required(IsAuthenticated)
    def resolve_team_members_leaves(self, info):
        user = info.context.user
        team_members = user.team_members.all()
        team_members_ids=[]
        for member in team_members:
            team_members_ids.append(member.id)
        return LeaveRequest.objects.filter(user__in = team_members_ids)
    
    @permission_required(IsAuthenticated)
    def resolve_user(self, info):
        user = info.context.user
        return CustomUser.objects.get(id = user.id)
    
    @permission_required(IsAuthenticated)
    def resolve_team_members(self, info):
        user = info.context.user
        team_members = user.team_members.all()
        return team_members
    
#--->mutations

class LoginMutation(graphene.Mutation):
    access = graphene.String()
    refresh = graphene.String()
    user_id = graphene.Int()
    username = graphene.String()
    class Arguments:
        username = graphene.String(required = True)
        password = graphene.String(required = True)

    def mutate(self, info, username, password):
        user = authenticate(username=username, password=password)
        if not user:
            raise GraphQLError('Invalid credentials')
        access = get_token(user)
        refresh = create_refresh_token(user)

        return LoginMutation(access=access, refresh=refresh, user_id=user.id, username=user.username)
    
class LeaveRequestMutation(graphene.Mutation):
    leave_request = graphene.Field(LeaveRequestType)
    class Arguments:
        start_date = graphene.Date(required = True)
        end_date = graphene.Date(required = True)
        reason = graphene.String( required = True)

    permission_required(IsAuthenticated) #-->using custom authenticators
    def mutate(self, info, start_date, end_date, reason):
        user = info.context.user

        if (start_date>end_date):
            raise GraphQLError("end date cannot be before start date")
        
        if start_date<date.today():
            raise GraphQLError("start date cannot be before today's date")
        
        if not reason.strip():
            raise GraphQLError("reason cannot be emplty")
            
        leaves = LeaveRequest.objects.filter(user=info.context.user, status__in = ['approved', 'pending'])
        for leave in leaves:
            if (leave.start_date<=start_date<=leave.end_date) or (leave.start_date<=end_date<=leave.end_date):
                raise GraphQLError("on these days there is already a leave request exists")
        days = (end_date - start_date).days + 1
        leave_tracker = LeaveTracker.objects.get(user=user)

        if days > leave_tracker.leaves_left():
            raise GraphQLError("you dont have enough leaves to apply")
        
        leave_request = LeaveRequest.objects.create(
            user=user, start_date=start_date, end_date=end_date, reason=reason, days=days
        )
        return LeaveRequestMutation(leave_request = leave_request)

class RegisterMutation(graphene.Mutation):
    user = graphene.Field(UserType)

    class Arguments:
        username = graphene.String(required = True)
        password = graphene.String(required = True)
        confirm_password = graphene.String(required = True)
        reporting_manager = graphene.Int(required = True)
    
    # @permission_required(IsAdmin)
    def mutate(self, info, username, password, confirm_password, reporting_manager):
        if password!=confirm_password:
            raise GraphQLError("passwords not matching")
        
        if CustomUser.objects.filter(username=username).exists():
            raise GraphQLError("username already exists")
        
        if not CustomUser.objects.filter(reporting_manager = reporting_manager).exists():
            raise GraphQLError("reporting manager does not exist")
        
        user = CustomUser.objects.create_user(username=username, password=password, reporting_manager=reporting_manager)
        return RegisterMutation(user = user)

class LeaveApproveMutation(graphene.Mutation):
    leave_request = graphene.Field(LeaveRequestType)
    class Arguments:
        id = graphene.Int(required = True)
        action = graphene.String(required = True)

    @permission_required(IsAuthenticated)
    def mutate(self, info, id, action):
        user = info.context.user
        
        leave_request = LeaveRequest.objects.get(id=id)
        reporting_manager = leave_request.user.reporting_manager
        if reporting_manager!=user:
            raise GraphQLError("you are not the reporting manager of this leave request")
        
        leave_tracker = LeaveTracker.objects.get(user=leave_request.user)
        if action=="approve" and leave_request.status=='pending':
            leave_request.status="approved"
            leave_request.reviewed_by = user.username
            leave_tracker.leaves_taken+=leave_request.days
            leave_request.save()
            leave_tracker.save()

        elif action=="reject" and leave_request.status=='pending':
            leave_request.status="rejected"
            leave_request.reviewed_by=user.username
            leave_request.save()

        else:
            raise GraphQLError("action must be in ['approve', 'reject'] or you are trying to modify the reviewed request")

        return LeaveApproveMutation(leave_request=leave_request)
    
class HolidayMutation(graphene.Mutation):
    holiday = graphene.Field(HolidayType)

    class Arguments:
        name = graphene.String(required = True)
        date = graphene.Date(required = True)

    @permission_required(IsAdmin)
    def mutate(self, info, name, date):
        if Holiday.objects.filter(name=name).exists():
            raise GraphQLError("name already exists")
        holiday = Holiday.objects.create(name=name, date=date)
        return HolidayMutation(holiday=holiday)
    
class RefreshMutation(graphene.Mutation):
    access = graphene.String()
    refresh = graphene.String()

    class Arguments:
        refresh = graphene.String(required=True)

    def mutate(self, info, refresh):
        try:
            refresh_obj = RefreshToken.objects.get(token=refresh)
        except RefreshToken.DoesNotExist:
            raise GraphQLError("Invalid or expired refresh token")

        # check if token is blacklisted or expired
        if refresh_obj.revoked:
            raise GraphQLError("This refresh token has been revoked")

        user = refresh_obj.user

        # generate new tokens
        new_access = get_token(user)
        new_refresh_obj = RefreshToken.objects.create(user=user)

        # blacklist the old one (if rotation is enabled)
        refresh_obj.revoke()

        return RefreshMutation(access=new_access, refresh=new_refresh_obj.token)

class Mutation(graphene.ObjectType):
    login = LoginMutation.Field() #--> Generates access and refresh tokens.
    verify_token = graphql_jwt.Verify.Field() #--> To only verify the token and get payload of it.
    refresh = RefreshMutation.Field()#-> Gives new access token
    leave_request = LeaveRequestMutation.Field()#-> apply leaves
    register = RegisterMutation.Field() #--> registering new user
    team_members_leaves_approve = LeaveApproveMutation.Field() #-->reporting manager approving leaves
    holidays = HolidayMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)