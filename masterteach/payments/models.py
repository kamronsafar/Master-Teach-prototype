from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Payment(models.Model):
    PAYMENT_TYPES = (
        ('film_purchase', 'Film Purchase'),
        ('premium_subscription', 'Premium Subscription'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    DELIVERY_TYPES = (
        ('standard', 'Standard (24 hours)'),
        ('fast', 'Fast (3-4 hours)'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    coinbase_payment_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tron_wallet_address = models.CharField(max_length=100, blank=True, null=True)
    usdc_amount = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # For film purchases
    film = models.ForeignKey('films.Film', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    film_request = models.ForeignKey('films.FilmRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    delivery_type = models.CharField(max_length=10, choices=DELIVERY_TYPES, default='standard')
    estimated_delivery = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} - {self.user.username} - {self.amount} {self.currency}"

    def calculate_amount(self):
        """Calculate payment amount based on user type and payment type"""
        if self.payment_type == 'premium_subscription':
            return 4.5  # Monthly subscription fee
        
        # Film purchase
        if self.user.premiumsubscription and self.user.premiumsubscription.is_active:
            amount = 0.5  # Premium user film purchase
        else:
            amount = 1.0  # Free user film purchase
        
        if self.delivery_type == 'fast':
            amount += 0.5  # Fast delivery fee
        
        return amount

    def set_estimated_delivery(self):
        """Set the estimated delivery time based on delivery type"""
        if self.delivery_type == 'fast':
            self.estimated_delivery = timezone.now() + timedelta(hours=4)
        else:
            self.estimated_delivery = timezone.now() + timedelta(days=1)
        self.save()

class PremiumSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, related_name='subscription_payment')

    def __str__(self):
        return f"Premium Subscription - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.end_date

    def renew(self, payment):
        self.end_date = timezone.now() + timedelta(days=30)
        self.last_payment = payment
        self.is_active = True
        self.save()

    @property
    def days_remaining(self):
        if not self.is_active:
            return 0
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)

class UserFilmLimit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_watch_date = models.DateTimeField(null=True, blank=True)
    watch_count = models.IntegerField(default=0)

    def can_watch_film(self):
        """Check if user can watch a film based on their tier and limits"""
        if self.user.premiumsubscription and self.user.premiumsubscription.is_active:
            return True
        
        if not self.last_watch_date:
            return True
        
        time_since_last_watch = timezone.now() - self.last_watch_date
        return time_since_last_watch.days >= 3

    def record_watch(self):
        """Record a film watch for the user"""
        self.last_watch_date = timezone.now()
        self.watch_count += 1
        self.save()

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    coinbase_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    tron_wallet_address = models.CharField(max_length=255)
    telegram_wallet_address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.user.username} - {self.amount} {self.currency}"

class WalletAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tron_wallet_address = models.CharField(max_length=255)
    telegram_wallet_address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet Addresses"
