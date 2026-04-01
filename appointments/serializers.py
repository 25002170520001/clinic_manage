
from rest_framework import serializers
from .models import Appointment
from doctors.serializers import DoctorListSerializer
from django.contrib.auth import get_user_model
from accounts.serializers import UserSerializer

User = get_user_model()


class PatientSerializer(serializers.ModelSerializer):
    """Serializer for patient info"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'phone']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model"""
    patient = UserSerializer(read_only=True)
    doctor = DoctorListSerializer(read_only=True)
    patient_id = serializers.IntegerField(write_only=True)
    doctor_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_id', 'doctor', 'doctor_id', 'booking_time', 
                  'status', 'status_display', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating appointments"""
    doctor_id = serializers.IntegerField()
    
    class Meta:
        model = Appointment
        fields = ['doctor_id', 'notes']
    
    def create(self, validated_data):
        patient = self.context['request'].user
        doctor = validated_data['doctor_id']
        
        # Check if doctor exists
        from doctors.models import Doctor
        doctor = Doctor.objects.get(id=doctor)
        
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            notes=validated_data.get('notes', ''),
            status='pending'
        )
        
        return appointment


class AppointmentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing appointments"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient_name', 'doctor_name', 'booking_time', 'status']

