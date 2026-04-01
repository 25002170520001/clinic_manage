from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import UserSerializer
from doctors.serializers import DoctorListSerializer

from .models import QueueToken
from .time_utils import filter_today

User = get_user_model()


class QueueTokenSerializer(serializers.ModelSerializer):
    """Serializer for QueueToken model"""

    patient = UserSerializer(read_only=True)
    doctor = DoctorListSerializer(read_only=True)
    patient_id = serializers.IntegerField(write_only=True, required=False)
    doctor_id = serializers.IntegerField(write_only=True, required=False)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patients_ahead = serializers.SerializerMethodField()
    estimated_wait_time = serializers.SerializerMethodField()

    class Meta:
        model = QueueToken
        fields = [
            "id",
            "patient",
            "patient_id",
            "doctor",
            "doctor_id",
            "appointment",
            "token_number",
            "token_display",
            "priority",
            "notes",
            "arrival_time",
            "status",
            "status_display",
            "patients_ahead",
            "estimated_wait_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_patients_ahead(self, obj):
        return obj.get_patients_ahead()

    def get_estimated_wait_time(self, obj):
        return obj.get_estimated_wait_time()


class QueueTokenCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating queue tokens"""

    doctor_id = serializers.IntegerField()
    patient_id = serializers.IntegerField(required=False)

    class Meta:
        model = QueueToken
        fields = ["doctor_id", "patient_id", "notes"]

    def create(self, validated_data):
        from doctors.models import Doctor

        doctor = Doctor.objects.get(id=validated_data["doctor_id"])

        # A create call through this serializer is considered a walk-in.
        patient = User.objects.get(id=validated_data["patient_id"])
        priority = 1
        token_type = "W"

        last_token = filter_today(QueueToken.objects.filter(doctor=doctor)).order_by("-token_number").first()
        token_number = (last_token.token_number + 1) if last_token else 1

        token_display = f"{token_type}-{token_number:02d}"

        return QueueToken.objects.create(
            patient=patient,
            doctor=doctor,
            token_number=token_number,
            token_display=token_display,
            priority=priority,
            status="waiting",
            notes=validated_data.get("notes", ""),
        )


class WalkInTokenSerializer(serializers.ModelSerializer):
    """Serializer for creating walk-in tokens"""

    doctor_id = serializers.IntegerField()

    class Meta:
        model = QueueToken
        fields = ["doctor_id", "notes"]


class QueueTokenListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing queue tokens"""

    patient_name = serializers.CharField(source="patient.get_full_name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.user.get_full_name", read_only=True)
    patients_ahead = serializers.SerializerMethodField()
    estimated_wait_time = serializers.SerializerMethodField()

    class Meta:
        model = QueueToken
        fields = [
            "id",
            "patient_name",
            "doctor_name",
            "token_display",
            "priority",
            "status",
            "patients_ahead",
            "estimated_wait_time",
        ]

    def get_patients_ahead(self, obj):
        return obj.get_patients_ahead()

    def get_estimated_wait_time(self, obj):
        return obj.get_estimated_wait_time()
