from rest_framework import serializers
from .models import Holiday, CustomUser, LeaveTracker, LeaveRequest
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['name', 'date']

    def validate_date(self, date):
        # breakpoint()
        try:
            holiday = Holiday.objects.get(date=date)
        except:
            return date
        raise serializers.ValidationError("A holiday is already created on this date")
    
    
class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only = True)
    access = serializers.CharField(read_only = True)
    refresh = serializers.CharField(read_only = True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'access', 'refresh']
        read_only_fields = ['id']

    def validate(self, data):
        # breakpoint()
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("invalid credentials")
        refresh = RefreshToken.for_user(user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['id']=user.id
        return data
        
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True) #--->for securing password
    confirm_password = serializers.CharField(write_only = True)

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'confirm_password', 'reporting_manager']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("passwords must match")
        return data
    
    def validate_reporting_manager(self, reporting_manager):
        if not CustomUser.objects.filter(id = reporting_manager.id): #checking by object's value
            raise serializers.ValidationError("reporting manager does not exist")
        return reporting_manager
    
    def create(self, validated_data):
        username = validated_data['username']
        password = validated_data['password']
        reporting_manager = validated_data['reporting_manager']
        user = CustomUser.objects.create_user(username=username, password=password, reporting_manager = reporting_manager)
        return user
    
class LeaveTrackerSerializer(serializers.ModelSerializer):
    leaves_left = serializers.IntegerField(read_only = True)
    class Meta:
        model = LeaveTracker
        fields = ['user', 'total_leaves', 'leaves_taken', 'leaves_left']

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'days', 'applied_at', 'reviewed_by',]
    
    def validate_start_date(self, start_date):
        today = date.today()
        if start_date < today:
            raise serializers.ValidationError("start date cannot be before todays date")
        return start_date

    def validate(self, data):
        # breakpoint()
        leave_requests = LeaveRequest.objects.filter(user = self.context.get('request').user, status__in = ['approved', 'pending'])
        for leave in leave_requests:
            if leave.start_date <= data['start_date'] <=leave.end_date:
                raise serializers.ValidationError("start_date overlaps with existing request")
            if leave.start_date <= data['end_date'] <=leave.end_date:
                raise serializers.ValidationError("end_date overlaps with existing request")
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("end_date cannot be before start_date")
            
            days = (data['end_date'] - data['start_date']).days + 1
            leave_tracker = LeaveTracker.objects.get(user = self.context['request'].user)
            if days > leave_tracker.leaves_left():
                raise serializers.ValidationError("you dont have enough leaves to apply")
        return data
    
    def create(self, validated_data):
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']
        reason = validated_data.get('reason')
        user = self.context['request'].user
        days = (end_date - start_date).days + 1
        leave = LeaveRequest.objects.create(
            user=user, start_date=start_date, end_date=end_date, reason=reason, days=days
        )
        return leave
    
class UserSerializer(serializers.ModelSerializer):
    # leave_requests = LeaveRequestSerializer(many=True, read_only = True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'reporting_manager',]

class LeaveApproveSerializer(serializers.ModelSerializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'], write_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = ['status', 'action']
        read_only_fields = ['status']

    def validate(self, data):
        pk = self.context.get('pk')
        # breakpoint()
        user = self.context.get('request').user
        try:
            leave_request = LeaveRequest.objects.get(pk=pk)
        except:
            raise serializers.ValidationError('leave request not found')
        reporting_manager = leave_request.user.reporting_manager

        if leave_request.status in ['approved', 'rejected']:
            raise serializers.ValidationError("the leave request is already reviewed") #-->checking if that leave request is not reviewed already 
        
        ManagerleaveRequests = LeaveRequest.objects.filter(user=leave_request.user.reporting_manager, status='approved') #--> if reporting manager is on leave, his reporting manager can approve leave
        for leaves in ManagerleaveRequests:
            if leaves.start_date <= date.today() <=leaves.end_date:
                reporting_manager = leaves.user.reporting_manager
                break

        if reporting_manager != user:
            raise serializers.ValidationError("you are not the reporting manager of this leave request")  #--> checking logged in user is reporting manager of that leave request
    
        return data
