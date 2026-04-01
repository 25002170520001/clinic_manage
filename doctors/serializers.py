
from rest_framework import serializers
from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    """Serializer for Doctor model"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    full_name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='user.phone')
    
    class Meta:
        model = Doctor
        fields = ['id', 'user', 'username', 'email', 'first_name', 'last_name', 'full_name', 
                  'phone', 'specialization', 'qualification', 'experience', 
                  'consultation_fee', 'is_available', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"


class DoctorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing doctors"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = ['id', 'full_name', 'specialization', 'qualification', 'experience', 'consultation_fee', 'is_available']
    
    def get_full_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"


class DoctorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating doctors"""
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Doctor
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone',
                  'specialization', 'qualification', 'experience', 'consultation_fee']
    
    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role='doctor',
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone'),
        )
        
        doctor = Doctor.objects.create(
            user=user,
            specialization=validated_data['specialization'],
            qualification=validated_data['qualification'],
            experience=validated_data.get('experience', 0),
            consultation_fee=validated_data.get('consultation_fee', 0),
        )
        
        return doctor

