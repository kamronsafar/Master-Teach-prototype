from django.shortcuts import render, redirect, get_object_or_404
import json
import hmac
import hashlib
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Payment, PremiumSubscription, UserFilmLimit
from films.models import Film
from coinbase_commerce.client import Client
from coinbase_commerce.error import SignatureVerificationError, WebhookInvalidPayload
from coinbase_commerce.webhook import Webhook
from decimal import Decimal
from .services import PaymentFlowService, PaymentTransaction
from .tron_payment import TronPaymentHandler

# Initialize Coinbase Commerce client
client = Client(settings.COINBASE_COMMERCE_API_KEY)

def calculate_payment_amount(user, film=None, delivery_type='standard'):
    """Calculate payment amount based on user type and payment type"""
    if film:
        # Film purchase
        if user.premiumsubscription and user.premiumsubscription.is_active:
            amount = 0.5  # Premium user film purchase
        else:
            amount = 1.0  # Free user film purchase
        
        if delivery_type == 'fast':
            amount += 0.5  # Fast delivery fee
    else:
        # Premium subscription
        amount = 4.5  # Monthly subscription fee
    
    return amount

@login_required
@require_http_methods(["GET", "POST"])
def create_payment(request):
    is_premium = hasattr(request.user, 'premiumsubscription') and request.user.premiumsubscription.is_active
    
    if request.method == "POST":
        payment_type = request.POST.get('payment_type')
        payment_method = request.POST.get('payment_method')
        
        if payment_type == 'film_purchase':
            film_id = request.POST.get('film_id')
            film = get_object_or_404(Film, id=film_id)
            amount = calculate_payment_amount(request.user, film, request.POST.get('delivery_type'))
        else:  # premium subscription
            amount = Decimal('4.50')
            
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            payment_type=payment_type,
            status='pending'
        )
        
        if payment_method == 'tron':
            # Handle TRON payment
            tron_handler = TronPaymentHandler()
            try:
                payment_data = tron_handler.create_payment(float(amount), payment.id)
                payment.transaction_id = payment_data['tx_id']
                payment.save()
                
                return render(request, 'payments/tron_payment.html', {
                    'payment': payment,
                    'trx_amount': payment_data['trx_amount'],
                    'wallet_address': tron_handler.wallet_address
                })
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating TRON payment: {str(e)}")
                return redirect('payments:failed')
        else:
            # Handle Coinbase payment
            try:
                charge = client.charge.create(
                    name=f"{payment_type.replace('_', ' ').title()}",
                    description=f"Payment for {payment_type.replace('_', ' ')}",
                    local_price={
                        'amount': str(amount),
                        'currency': 'USD'
                    },
                    pricing_type='fixed_price',
                    metadata={
                        'payment_id': payment.id,
                        'user_id': request.user.id,
                        'payment_type': payment_type
                    },
                    redirect_url=request.build_absolute_uri(reverse('payments:success')),
                    cancel_url=request.build_absolute_uri(reverse('payments:failed'))
                )
                
                payment.transaction_id = charge.id
                payment.save()
                
                return redirect(charge.hosted_url)
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating payment: {str(e)}")
                return redirect('payments:failed')
                
    return render(request, 'payments/create_payment.html', {
        'is_premium': is_premium,
        'films': Film.objects.filter(visibility='public')
    })

@csrf_exempt
@require_http_methods(["POST"])
def webhook(request):
    # Get the webhook signature
    signature = request.headers.get('X-CC-Webhook-Signature')
    
    try:
        # Verify the webhook signature
        event = Webhook.construct_event(
            request.body,
            signature,
            settings.COINBASE_COMMERCE_WEBHOOK_SECRET
        )
        
        # Handle the event
        if event.type == 'charge:confirmed':
            payment = Payment.objects.get(coinbase_payment_id=event.data.id)
            payment.status = 'completed'
            payment.usdc_amount = payment.amount
            payment.save()
            
            # Handle different payment types
            if payment.payment_type == 'premium_subscription':
                # Create or update premium subscription
                subscription, created = PremiumSubscription.objects.get_or_create(
                    user=payment.user,
                    defaults={'last_payment': payment}
                )
                if not created:
                    subscription.renew(payment)
            
            elif payment.payment_type == 'film_purchase':
                # Update film status
                if payment.film:
                    payment.film.status = 'processing'
                    payment.film.save()
            
        elif event.type == 'charge:failed':
            payment = Payment.objects.get(coinbase_payment_id=event.data.id)
            payment.status = 'failed'
            payment.save()
            
        return HttpResponse(status=200)
        
    except (SignatureVerificationError, WebhookInvalidPayload) as e:
        return HttpResponse(status=400)
    except Payment.DoesNotExist:
        return HttpResponse(status=404)
    except Exception as e:
        return HttpResponse(status=500)

@login_required
def check_film_access(request, film_id):
    """Check if user can access a film based on their tier and limits"""
    film = get_object_or_404(Film, id=film_id)
    user_limit, created = UserFilmLimit.objects.get_or_create(user=request.user)
    
    if user_limit.can_watch_film():
        user_limit.record_watch()
        return JsonResponse({'can_watch': True})
    
    return JsonResponse({
        'can_watch': False,
        'message': 'You need to wait 3 days between film watches or upgrade to premium.'
    })

@login_required
def payment_success(request):
    return render(request, 'payments/success.html')

@login_required
def payment_failed(request):
    return render(request, 'payments/failed.html')

@login_required
@require_http_methods(["POST"])
def initiate_payment(request):
    try:
        amount = Decimal(request.POST.get('amount', 0))
        currency = request.POST.get('currency', 'USD')

        if amount <= 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid amount'
            }, status=400)

        payment_service = PaymentFlowService(request.user.id)
        transaction = payment_service.process_payment_flow(amount, currency)

        return JsonResponse({
            'status': 'success',
            'transaction_id': transaction.id,
            'status': transaction.status
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_transaction_status(request, transaction_id):
    try:
        transaction = PaymentTransaction.objects.get(
            id=transaction_id,
            user=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'transaction': {
                'id': transaction.id,
                'amount': str(transaction.amount),
                'currency': transaction.currency,
                'status': transaction.status,
                'created_at': transaction.created_at.isoformat()
            }
        })

    except PaymentTransaction.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Transaction not found'
        }, status=404)

def verify_tron_payment(request, payment_id):
    """Verify TRON payment status"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.status == 'completed':
        return JsonResponse({'status': 'completed'})
        
    tron_handler = TronPaymentHandler()
    if tron_handler.verify_payment(payment.transaction_id):
        payment.status = 'completed'
        payment.save()
        
        if payment.payment_type == 'film_purchase':
            # Handle film purchase
            pass
        else:
            # Handle premium subscription
            pass
            
        return JsonResponse({'status': 'completed'})
        
    return JsonResponse({'status': 'pending'})

@login_required
def premium_subscription(request):
    """Handle premium subscription requests"""
    is_premium = hasattr(request.user, 'premiumsubscription') and request.user.premiumsubscription.is_active
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = Decimal('4.50')  # Premium subscription price
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            payment_type='premium_subscription',
            status='pending'
        )
        
        if payment_method == 'tron':
            # Handle TRON payment
            tron_handler = TronPaymentHandler()
            try:
                payment_data = tron_handler.create_payment(float(amount), payment.id)
                payment.transaction_id = payment_data['tx_id']
                payment.save()
                
                return render(request, 'payments/tron_payment.html', {
                    'payment': payment,
                    'trx_amount': payment_data['trx_amount'],
                    'wallet_address': tron_handler.wallet_address
                })
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating TRON payment: {str(e)}")
                return redirect('payments:failed')
        else:
            # Handle Coinbase payment
            try:
                charge = client.charge.create(
                    name="Premium Subscription",
                    description="Monthly premium subscription",
                    local_price={
                        'amount': str(amount),
                        'currency': 'USD'
                    },
                    pricing_type='fixed_price',
                    metadata={
                        'payment_id': payment.id,
                        'user_id': request.user.id,
                        'payment_type': 'premium_subscription'
                    },
                    redirect_url=request.build_absolute_uri(reverse('payments:success')),
                    cancel_url=request.build_absolute_uri(reverse('payments:failed'))
                )
                
                payment.transaction_id = charge.id
                payment.save()
                
                return redirect(charge.hosted_url)
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating payment: {str(e)}")
                return redirect('payments:failed')
    
    return render(request, 'payments/premium_subscription.html', {
        'is_premium': is_premium,
        'subscription_price': settings.PREMIUM_SUBSCRIPTION_PRICE
    })

@login_required
def purchase_film(request, film_id):
    """Handle film purchase requests"""
    film = get_object_or_404(Film, id=film_id)
    is_premium = hasattr(request.user, 'premiumsubscription') and request.user.premiumsubscription.is_active
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        delivery_type = request.POST.get('delivery_type', 'standard')
        amount = calculate_payment_amount(request.user, film, delivery_type)
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            film=film,
            amount=amount,
            payment_type='film_purchase',
            delivery_type=delivery_type,
            status='pending'
        )
        
        if payment_method == 'tron':
            # Handle TRON payment
            tron_handler = TronPaymentHandler()
            try:
                payment_data = tron_handler.create_payment(float(amount), payment.id)
                payment.transaction_id = payment_data['tx_id']
                payment.save()
                
                return render(request, 'payments/tron_payment.html', {
                    'payment': payment,
                    'trx_amount': payment_data['trx_amount'],
                    'wallet_address': tron_handler.wallet_address
                })
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating TRON payment: {str(e)}")
                return redirect('payments:failed')
        else:
            # Handle Coinbase payment
            try:
                charge = client.charge.create(
                    name=f"Film Purchase: {film.title}",
                    description=f"Purchase of {film.title}",
                    local_price={
                        'amount': str(amount),
                        'currency': 'USD'
                    },
                    pricing_type='fixed_price',
                    metadata={
                        'payment_id': payment.id,
                        'user_id': request.user.id,
                        'film_id': film.id,
                        'payment_type': 'film_purchase'
                    },
                    redirect_url=request.build_absolute_uri(reverse('payments:success')),
                    cancel_url=request.build_absolute_uri(reverse('payments:failed'))
                )
                
                payment.transaction_id = charge.id
                payment.save()
                
                return redirect(charge.hosted_url)
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                messages.error(request, f"Error creating payment: {str(e)}")
                return redirect('payments:failed')
    
    return render(request, 'payments/create_payment.html', {
        'film': film,
        'is_premium': is_premium,
        'delivery_types': [
            ('standard', 'Standard Delivery (24 hours)'),
            ('fast', 'Fast Delivery (3-4 hours) - $0.50 extra')
        ]
    })
