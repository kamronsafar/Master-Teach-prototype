from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create/', views.create_payment, name='create_payment'),
    path('webhook/', views.webhook, name='webhook'),
    path('success/', views.payment_success, name='payment_success'),
    path('failed/', views.payment_failed, name='payment_failed'),
    path('initiate/', views.initiate_payment, name='initiate_payment'),
    path('status/<int:transaction_id>/', views.get_transaction_status, name='transaction_status'),
    path('verify-tron/<int:payment_id>/', views.verify_tron_payment, name='verify_tron_payment'),
    path('premium/', views.premium_subscription, name='premium_subscription'),
    path('purchase/<int:film_id>/', views.purchase_film, name='purchase_film'),
] 