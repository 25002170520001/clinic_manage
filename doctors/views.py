
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Doctor
from .serializers import DoctorSerializer, DoctorListSerializer, DoctorCreateSerializer


class DoctorListCreateView(generics.ListCreateAPIView):
    """API endpoint for listing and creating doctors"""
    queryset = Doctor.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DoctorCreateSerializer
        return DoctorListSerializer
    
    def get_queryset(self):
        queryset = Doctor.objects.filter(is_available=True)
        specialization = self.request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)
        return queryset


class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint for retrieving, updating, and deleting a doctor"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]


class AvailableDoctorsView(generics.ListAPIView):
    """API endpoint for listing available doctors"""
    queryset = Doctor.objects.filter(is_available=True)
    serializer_class = DoctorListSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_doctor_availability(request, pk):
    """Toggle doctor availability"""
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_available = not doctor.is_available
    doctor.save()
    return Response({
        'id': doctor.id,
        'is_available': doctor.is_available,
        'message': f"Doctor is now {'available' if doctor.is_available else 'unavailable'}"
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_by_user(request, user_id):
    """Get doctor profile by user ID"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    doctor = get_object_or_404(Doctor, user=user)
    serializer = DoctorSerializer(doctor)
    return Response(serializer.data)

