
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentCreateSerializer, AppointmentListSerializer
from token_queue.models import QueueToken
from token_queue.services import QueueService


class AppointmentListCreateView(generics.ListCreateAPIView):
    """API endpoint for listing and creating appointments"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient=user).order_by('-booking_time')
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor__user=user).order_by('-booking_time')
        elif user.role == 'admin' or user.role == 'receptionist':
            return Appointment.objects.all().order_by('-booking_time')
        return Appointment.objects.none()
    
    def perform_create(self, serializer):
        appointment = serializer.save()
        # Generate token for the appointment
        QueueService.generate_token_for_appointment(appointment)


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint for retrieving, updating, and deleting an appointment"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]


class MyAppointmentsView(generics.ListAPIView):
    """API endpoint for getting current user's appointments"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient=user).order_by('-booking_time')
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor__user=user).order_by('-booking_time')
        return Appointment.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_appointment(request):
    """Book an appointment and get token"""
    serializer = AppointmentCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        appointment = serializer.save()
        
        # Generate token
        token = QueueService.generate_token_for_appointment(appointment)
        
        return Response({
            'appointment': AppointmentSerializer(appointment).data,
            'token': {
                'id': token.id,
                'token_display': token.token_display,
                'priority': token.priority,
                'estimated_wait_time': token.get_estimated_wait_time()
            },
            'message': 'Appointment booked successfully'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, pk):
    """Cancel an appointment"""
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
    
    # Check if already completed
    if appointment.status == 'completed':
        return Response({'error': 'Cannot cancel a completed appointment'}, status=status.HTTP_400_BAD_REQUEST)
    
    appointment.status = 'cancelled'
    appointment.save()
    
    # Cancel associated token if exists
    QueueToken.objects.filter(appointment=appointment, status='waiting').update(status='cancelled')
    
    return Response({'message': 'Appointment cancelled successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_detail(request, pk):
    """Get appointment details with token info"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Check permission
    user = request.user
    if user.role == 'patient' and appointment.patient != user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    if user.role == 'doctor' and appointment.doctor.user != user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    data = AppointmentSerializer(appointment).data
    
    # Add token info if exists
    token = QueueToken.objects.filter(appointment=appointment).first()
    if token:
        data['token_info'] = {
            'id': token.id,
            'token_display': token.token_display,
            'status': token.status,
            'patients_ahead': token.get_patients_ahead(),
            'estimated_wait_time': token.get_estimated_wait_time()
        }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today_appointments(request):
    """Get today's appointments"""
    today = timezone.now().date()
    user = request.user
    
    if user.role == 'patient':
        appointments = Appointment.objects.filter(
            patient=user,
            booking_time__date=today
        ).order_by('booking_time')
    elif user.role == 'doctor':
        appointments = Appointment.objects.filter(
            doctor__user=user,
            booking_time__date=today
        ).order_by('booking_time')
    elif user.role == 'admin' or user.role == 'receptionist':
        appointments = Appointment.objects.filter(
            booking_time__date=today
        ).order_by('booking_time')
    else:
        appointments = Appointment.objects.none()
    
    serializer = AppointmentSerializer(appointments, many=True)
    return Response(serializer.data)

