
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import QueueToken
from .serializers import QueueTokenSerializer, WalkInTokenSerializer, QueueTokenListSerializer
from .services import QueueService
from .time_utils import filter_today
from doctors.models import Doctor


class QueueTokenListCreateView(generics.ListCreateAPIView):
    """API endpoint for listing and creating queue tokens"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WalkInTokenSerializer
        return QueueTokenSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'patient':
            return QueueToken.objects.filter(patient=user).order_by('-created_at')
        elif user.role == 'doctor':
            doctor = get_object_or_404(Doctor, user=user)
            return filter_today(QueueToken.objects.filter(doctor=doctor)).order_by('-priority', 'token_number')
        elif user.role == 'admin' or user.role == 'receptionist':
            doctor_id = self.request.query_params.get('doctor_id')
            queryset = filter_today(QueueToken.objects.all())
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            return queryset.order_by('-priority', 'token_number')
        return QueueToken.objects.none()


class QueueTokenDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint for retrieving, updating, and deleting a queue token"""
    queryset = QueueToken.objects.all()
    serializer_class = QueueTokenSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_walk_in_token(request):
    """Create a walk-in token (for receptionist)"""
    serializer = WalkInTokenSerializer(data=request.data)
    if serializer.is_valid():
        doctor = get_object_or_404(Doctor, id=serializer.validated_data['doctor_id'])
        if request.user.role != 'patient':
            return Response(
                {'error': 'For receptionist/admin use /queue/walk-in/patient/ with patient_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        patient = request.user
        
        token = QueueService.create_walk_in_token(doctor, patient, serializer.validated_data.get('notes', ''))
        
        return Response({
            'token': QueueTokenSerializer(token).data,
            'message': 'Walk-in token generated successfully'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_walk_in_for_patient(request):
    """Create a walk-in token for a patient (for receptionist)"""
    from accounts.models import User
    
    patient_id = request.data.get('patient_id')
    doctor_id = request.data.get('doctor_id')
    notes = request.data.get('notes', '')
    
    if not patient_id or not doctor_id:
        return Response({'error': 'patient_id and doctor_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    patient = get_object_or_404(User, id=patient_id, role='patient')
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    token = QueueService.create_walk_in_token(doctor, patient, notes)
    
    return Response({
        'token': QueueTokenSerializer(token).data,
        'message': 'Walk-in token generated successfully'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_queue(request, doctor_id):
    """Get queue for a specific doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    queue = filter_today(QueueToken.objects.filter(
        doctor=doctor,
        status__in=['waiting', 'called', 'in_consultation']
    )).order_by('-priority', 'token_number')
    
    serializer = QueueTokenSerializer(queue, many=True)
    return Response({
        'doctor': {
            'id': doctor.id,
            'name': f"Dr. {doctor.user.get_full_name()}"
        },
        'queue': serializer.data,
        'total_waiting': queue.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def call_next_patient(request, doctor_id):
    """Call next patient in queue (for doctor or receptionist)"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    token = QueueService.get_next_patient(doctor)
    
    if not token:
        return Response({'error': 'No patients in queue'}, status=status.HTTP_404_NOT_FOUND)
    
    # Update token status
    token.status = 'called'
    token.save()
    
    return Response({
        'token': QueueTokenSerializer(token).data,
        'message': f"Patient {token.token_display} called"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_consultation(request, token_id):
    """Start consultation with a patient"""
    token = get_object_or_404(QueueToken, id=token_id)
    
    # Verify doctor permission
    if request.user.role == 'doctor':
        doctor = get_object_or_404(Doctor, user=request.user)
        if token.doctor != doctor:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    token.status = 'in_consultation'
    token.save()
    
    return Response({
        'token': QueueTokenSerializer(token).data,
        'message': 'Consultation started'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_consultation(request, token_id):
    """Mark consultation as completed"""
    token = get_object_or_404(QueueToken, id=token_id)
    
    # Verify doctor permission
    if request.user.role == 'doctor':
        doctor = get_object_or_404(Doctor, user=request.user)
        if token.doctor != doctor:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    token.status = 'completed'
    token.save()
    
    # Update appointment status if exists
    if token.appointment:
        token.appointment.status = 'completed'
        token.appointment.save()
    
    return Response({
        'token': QueueTokenSerializer(token).data,
        'message': 'Consultation completed'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_no_show(request, token_id):
    """Mark patient as no-show"""
    token = get_object_or_404(QueueToken, id=token_id)
    token.status = 'missed'
    token.save()
    
    return Response({
        'message': 'Patient marked as no-show'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in_patient(request, token_id):
    """Check in a patient (store arrival time)"""
    token = get_object_or_404(QueueToken, id=token_id)
    token.arrival_time = timezone.now()
    token.save()
    
    return Response({
        'token': QueueTokenSerializer(token).data,
        'message': 'Patient checked in successfully'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_token(request):
    """Get current user's token info"""
    user = request.user
    token = QueueToken.objects.filter(
        patient=user,
        status__in=['waiting', 'called', 'in_consultation']
    ).order_by('-created_at').first()
    
    if not token:
        return Response({'error': 'No active token'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = QueueTokenSerializer(token)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_queue_display(request, doctor_id):
    """Get queue display for TV screen (public access)"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    # Get current patient (in consultation or called)
    current = filter_today(QueueToken.objects.filter(
        doctor=doctor,
        status__in=['called', 'in_consultation']
    )).order_by('-priority', 'token_number').first()
    
    # Get waiting queue
    waiting = filter_today(QueueToken.objects.filter(
        doctor=doctor,
        status='waiting'
    )).order_by('-priority', 'token_number')[:5]
    
    return Response({
        'doctor': {
            'id': doctor.id,
            'name': f"Dr. {doctor.user.get_full_name()}",
            'specialization': doctor.specialization
        },
        'current_patient': QueueTokenSerializer(current).data if current else None,
        'waiting_queue': QueueTokenSerializer(waiting, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_queue_for_doctor(request):
    """Get current queue for logged-in doctor"""
    doctor = get_object_or_404(Doctor, user=request.user)
    queue = filter_today(QueueToken.objects.filter(
        doctor=doctor,
    )).order_by('-priority', 'token_number')
    
    # Separate current and waiting
    current = queue.filter(status__in=['called', 'in_consultation']).first()
    waiting = queue.filter(status='waiting')
    
    return Response({
        'current_patient': QueueTokenSerializer(current).data if current else None,
        'waiting_queue': QueueTokenSerializer(waiting, many=True).data,
        'stats': {
            'total': queue.count(),
            'waiting': waiting.count(),
            'completed': queue.filter(status='completed').count()
        }
    })
