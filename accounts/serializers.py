
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import PatientProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone', 'address', 'date_of_birth', 'created_at']
        read_only_fields = ['id', 'created_at']


class PatientProfileSerializer(serializers.ModelSerializer):
    """Serializer for PatientProfile model"""
    
    class Meta:
        model = PatientProfile
        fields = ['blood_group', 'emergency_contact', 'medical_history', 'allergies']


class PatientRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for patient self-registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    allergies = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'blood_group', 'emergency_contact', 'medical_history', 'allergies']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        
        # Extract profile data
        blood_group = validated_data.pop('blood_group', None)
        emergency_contact = validated_data.pop('emergency_contact', None)
        medical_history = validated_data.pop('medical_history', None)
        allergies = validated_data.pop('allergies', None)
        
        # Create user with patient role
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=password,
            role='patient',
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone'),
            address=validated_data.get('address'),
            date_of_birth=validated_data.get('date_of_birth'),
        )
        
        # Create patient profile
        PatientProfile.objects.create(
            user=user,
            blood_group=blood_group,
            emergency_contact=emergency_contact,
            medical_history=medical_history,
            allergies=allergies,
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for login"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

