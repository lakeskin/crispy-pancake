"""
Credit Management System - Shared Module
=========================================

Provider-agnostic credit management for multi-app projects.
Supports multiple backends (Supabase, Firebase, custom DB).

Usage:
    from shared.credits import get_credit_manager
    
    manager = get_credit_manager('supabase', config_path='credit_config.yaml')
    balance = manager.get_balance(user_id)
    manager.deduct_credits(user_id, amount, metadata={'action': 'generate_image'})

Pricing and Stripe:
    from shared.credits import get_credits_config, get_pricing_service, get_stripe_service
    
    config = get_credits_config()
    pricing = get_pricing_service()
    stripe_svc = get_stripe_service()
"""

from .base import CreditManager
from .models import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    TransactionHistory,
    CostBreakdown,
    CostEstimate
)
from .exceptions import (
    InsufficientCreditsError,
    InvalidTransactionError,
    ProviderError
)
from .providers import SupabaseCreditManager

# Config-driven pricing system
from .config_loader import (
    get_credits_config,
    CreditsConfigLoader,
    Package,
    Subscription,
    Coupon,
    Promotion
)
from .pricing_service import (
    get_pricing_service,
    PricingService,
    PriceCalculation,
    CostEstimate as PricingCostEstimate
)

# Stripe service - lazy import to avoid import errors if stripe not installed
def get_stripe_service(config=None, pricing=None):
    """Lazy import of stripe service"""
    from .stripe_service import get_stripe_service as _get_stripe_service
    return _get_stripe_service(config, pricing)

__all__ = [
    # Credit manager
    'get_credit_manager',
    'CreditManager',
    'SupabaseCreditManager',
    'CreditBalance',
    'CreditTransaction',
    'TransactionType',
    'TransactionHistory',
    'CostBreakdown',
    'CostEstimate',
    'InsufficientCreditsError',
    'InvalidTransactionError',
    'ProviderError',
    # Config and pricing
    'get_credits_config',
    'CreditsConfigLoader',
    'Package',
    'Subscription',
    'Coupon',
    'Promotion',
    'get_pricing_service',
    'PricingService',
    'PriceCalculation',
    'PricingCostEstimate',
    # Stripe (lazy loaded)
    'get_stripe_service',
]


def get_credit_manager(provider: str = 'supabase', **kwargs):
    """
    Factory function to get credit manager instance.
    
    Args:
        provider: Provider name ('supabase', 'firebase', 'custom')
        **kwargs: Additional configuration (config_path, supabase_client, etc.)
        
    Returns:
        CreditManager instance
        
    Examples:
        # Use default provider (Supabase)
        manager = get_credit_manager()
        
        # Use with custom client
        from shared.auth.supabase import get_supabase_client
        client = get_supabase_client()
        manager = get_credit_manager('supabase', supabase_client=client)
        
        # Use with custom config
        manager = get_credit_manager('supabase', config_path='config/credits.yaml')
    """
    if provider == 'supabase':
        return SupabaseCreditManager(**kwargs)
    elif provider == 'firebase':
        raise NotImplementedError("Firebase provider not yet implemented")
    elif provider == 'custom':
        raise NotImplementedError("Custom provider not yet implemented")
    else:
        raise ValueError(f"Unknown provider: {provider}")
