
from django.urls import path
from .views import (
    QueueTokenListCreateView,
    QueueTokenDetailView,
    create_walk_in_token,
    create_walk_in_for_patient,
    get_doctor_queue,
    call_next_patient,
    start_consultation,
    complete_consultation,
    mark_no_show,
    check_in_patient,
    get_my_token,
    get_queue_display,
    get_current_queue_for_doctor
)

urlpatterns = [
    path('', QueueTokenListCreateView.as_view(), name='token-list-create'),
    path('<int:pk>/', QueueTokenDetailView.as_view(), name='token-detail'),
    
    # Walk-in
    path('walk-in/', create_walk_in_token, name='create-walk-in'),
    path('walk-in/patient/', create_walk_in_for_patient, name='create-walk-in-patient'),
    
    # Queue management
    path('doctor/<int:doctor_id>/', get_doctor_queue, name='doctor-queue'),
    path('doctor/<int:doctor_id>/call-next/', call_next_patient, name='call-next-patient'),
    path('doctor/my-queue/', get_current_queue_for_doctor, name='my-queue'),
    
    # Token actions
    path('<int:token_id>/start/', start_consultation, name='start-consultation'),
    path('<int:token_id>/complete/', complete_consultation, name='complete-consultation'),
    path('<int:token_id>/no-show/', mark_no_show, name='mark-no-show'),
    path('<int:token_id>/check-in/', check_in_patient, name='check-in'),
    
    # Patient views
    path('my-token/', get_my_token, name='my-token'),
    
    # Public queue display
    path('display/<int:doctor_id>/', get_queue_display, name='queue-display'),
]

