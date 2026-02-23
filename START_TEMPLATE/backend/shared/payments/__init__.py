"""
Payment system for credit purchases.

This module provides:
1. Payment provider abstraction (Stripe, PayPal, etc.)
2. Payment tracking service for database-backed payment lifecycle management
3. Models for checkout sessions, payment intents, and webhooks

Usage:
    # For payment provider operations (create checkout, process webhook)
    from shared.payments import get_payment_provider
    provider = get_payment_provider('stripe')
    
    # For payment tracking (database records)
    from shared.payments import get_payment_tracker
    tracker = get_payment_tracker()
    payment = tracker.create_pending_payment(...)
"""

from .base import PaymentProvider
from .models import (
    CheckoutSession,
    PaymentStatus,
    PaymentIntent,
    PaymentMethod,
    Coupon,
    CreditPackage,
    WebhookEvent
)
from .exceptions import (
    PaymentError,
    InvalidCouponError,
    WebhookVerificationError
)
from .tracker import (
    PaymentTracker,
    PaymentStore,
    PaymentRecord,
    PaymentRecordStatus,
    PaymentRecordHistory
)

__all__ = [
    # Factory functions
    'get_payment_provider',
    'get_payment_tracker',
    
    # Payment provider interface
    'PaymentProvider',
    
    # Payment tracking
    'PaymentTracker',
    'PaymentStore',
    'PaymentRecord',
    'PaymentRecordStatus',
    'PaymentRecordHistory',
    
    # Provider models
    'CheckoutSession',
    'PaymentStatus',
    'PaymentIntent',
    'PaymentMethod',
    'Coupon',
    'CreditPackage',
    'WebhookEvent',
    
    # Exceptions
    'PaymentError',
    'InvalidCouponError',
    'WebhookVerificationError'
]


def get_payment_provider(provider: str = 'stripe', **kwargs):
    """
    Factory function to get payment provider instance.
    
    Args:
        provider: Provider name ('stripe', 'paypal', etc.)
        **kwargs: Provider-specific configuration
        
    Returns:
        PaymentProvider instance
        
    Examples:
        # Default Stripe provider
        provider = get_payment_provider()
        
        # With custom config
        provider = get_payment_provider('stripe', config_path='config/payments.yaml')
        
        # With API keys
        provider = get_payment_provider('stripe', api_key='sk_test_...')
    """
    if provider == 'stripe':
        # NOTE: For Stripe payment operations, use shared.credits.get_stripe_service()
        # This provider interface is reserved for future expansion
        raise NotImplementedError(
            "Stripe provider not implemented in shared.payments. "
            "Use shared.credits.get_stripe_service() instead."
        )
    elif provider == 'paypal':
        raise NotImplementedError("PayPal provider not yet implemented")
    else:
        raise ValueError(f"Unknown payment provider: {provider}")


def get_payment_tracker(
    store_type: str = 'supabase',
    supabase_client=None,
    session_expiry_minutes: int = 30,
    **kwargs
) -> PaymentTracker:
    """
    Factory function to get a payment tracker instance.
    
    The payment tracker handles database-backed payment lifecycle management,
    including creating payment records, updating status, and preventing duplicates.
    
    Args:
        store_type: Backend type ('supabase', 'firebase', etc.)
        supabase_client: Supabase client instance (optional, will try to auto-detect)
        session_expiry_minutes: How long checkout sessions are valid
        **kwargs: Additional store-specific configuration
        
    Returns:
        PaymentTracker instance
        
    Examples:
        # Auto-detect Supabase client
        tracker = get_payment_tracker()
        
        # With explicit client
        tracker = get_payment_tracker(supabase_client=my_client)
        
        # Custom session expiry
        tracker = get_payment_tracker(session_expiry_minutes=60)
    """
    if store_type == 'supabase':
        from .stores.supabase import SupabasePaymentStore
        store = SupabasePaymentStore(
            supabase_client=supabase_client,
            table_name=kwargs.get('table_name', 'payment_transactions')
        )
        return PaymentTracker(store, session_expiry_minutes)
    elif store_type == 'firebase':
        raise NotImplementedError("Firebase payment store not yet implemented")
    else:
        raise ValueError(f"Unknown store type: {store_type}")

