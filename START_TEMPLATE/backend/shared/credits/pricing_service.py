"""
Pricing Service

Provides pricing calculations, cost estimates, and discount application.
Uses configuration from config_loader.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .config_loader import (
    get_credits_config,
    Package,
    Subscription,
    Coupon,
    CreditsConfigLoader
)


@dataclass
class PriceCalculation:
    """Result of a price calculation"""
    original_price: float
    discount_amount: float
    final_price: float
    credits: int
    bonus_credits: int
    total_credits: int
    coupon_applied: Optional[str] = None
    currency: str = "USD"
    currency_symbol: str = "$"


@dataclass
class CostEstimate:
    """Estimate for a generation job"""
    total_credits: int
    breakdown: List[Dict]
    sufficient_balance: bool
    current_balance: int


class PricingService:
    """
    Handles all pricing calculations for the credit system.
    
    Features:
    - Package and subscription pricing
    - Coupon validation and application
    - Model cost calculations
    - Generation cost estimates
    - First purchase bonuses
    
    Usage:
        pricing = PricingService()
        price = pricing.calculate_package_price("creator", coupon_code="WELCOME10")
        estimate = pricing.estimate_generation_cost(["gpt-image-1", "flux-dev"], 3, user_balance=100)
    """
    
    def __init__(self, config: Optional[CreditsConfigLoader] = None):
        """Initialize pricing service"""
        self.config = config or get_credits_config()
    
    # ========================================================================
    # PACKAGE PRICING
    # ========================================================================
    
    def get_packages(self) -> List[Dict]:
        """Get all active packages with pricing info"""
        packages = self.config.get_packages(active_only=True)
        currency = self.config.get_currency()
        symbol = self.config.get_currency_symbol()
        
        return [
            {
                'id': pkg.id,
                'name': pkg.name,
                'description': pkg.description,
                'credits': pkg.credits,
                'price': pkg.price_usd,
                'price_formatted': f"{symbol}{pkg.price_usd:.2f}",
                'price_per_credit': f"{symbol}{(pkg.price_usd / pkg.credits):.4f}",
                'popular': pkg.popular,
                'badge': pkg.badge,
                'currency': currency,
            }
            for pkg in packages
        ]
    
    def calculate_package_price(
        self,
        package_id: str,
        coupon_code: Optional[str] = None,
        is_first_purchase: bool = False
    ) -> Optional[PriceCalculation]:
        """Calculate final price for a package with optional coupon"""
        
        package = self.config.get_package(package_id)
        if not package or not package.active:
            return None
        
        original_price = package.price_usd
        discount_amount = 0.0
        coupon_applied = None
        bonus_credits = 0
        
        # Apply coupon if provided
        if coupon_code:
            coupon = self.config.get_coupon(coupon_code)
            if coupon and self._is_coupon_valid_for_item(coupon, 'packages', package_id, original_price):
                discount_amount = self._calculate_discount(coupon, original_price)
                coupon_applied = coupon_code
        
        # Calculate first purchase bonus
        if is_first_purchase:
            promos = self.config.get_promotions()
            first_bonus = promos.get('first_purchase_bonus')
            if first_bonus and first_bonus.enabled:
                bonus = int(package.credits * (first_bonus.bonus_percent / 100))
                bonus_credits = min(bonus, first_bonus.max_bonus_credits)
        
        final_price = max(0, original_price - discount_amount)
        
        return PriceCalculation(
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
            credits=package.credits,
            bonus_credits=bonus_credits,
            total_credits=package.credits + bonus_credits,
            coupon_applied=coupon_applied,
            currency=self.config.get_currency(),
            currency_symbol=self.config.get_currency_symbol()
        )
    
    # ========================================================================
    # SUBSCRIPTION PRICING
    # ========================================================================
    
    def get_subscriptions(self) -> List[Dict]:
        """Get all active subscriptions with pricing info"""
        subscriptions = self.config.get_subscriptions(active_only=True)
        currency = self.config.get_currency()
        symbol = self.config.get_currency_symbol()
        
        result = []
        for sub in subscriptions:
            # Calculate monthly equivalent for yearly plans
            if sub.interval == 'year':
                monthly_price = sub.price_usd / 12
                price_display = f"{symbol}{monthly_price:.2f}/mo (billed yearly)"
            else:
                price_display = f"{symbol}{sub.price_usd:.2f}/mo"
            
            result.append({
                'id': sub.id,
                'name': sub.name,
                'description': sub.description,
                'credits_per_period': sub.credits_per_period,
                'price': sub.price_usd,
                'price_formatted': f"{symbol}{sub.price_usd:.2f}",
                'price_display': price_display,
                'interval': sub.interval,
                'interval_count': sub.interval_count,
                'trial_days': sub.trial_days,
                'features': sub.features,
                'popular': sub.popular,
                'badge': sub.badge,
                'currency': currency,
                'stripe_price_id': sub.stripe_price_id,
            })
        
        return result
    
    def calculate_subscription_price(
        self,
        subscription_id: str,
        coupon_code: Optional[str] = None
    ) -> Optional[PriceCalculation]:
        """Calculate final price for a subscription with optional coupon"""
        
        subscription = self.config.get_subscription(subscription_id)
        if not subscription or not subscription.active:
            return None
        
        original_price = subscription.price_usd
        discount_amount = 0.0
        coupon_applied = None
        
        # Apply coupon if provided
        if coupon_code:
            coupon = self.config.get_coupon(coupon_code)
            if coupon and self._is_coupon_valid_for_item(coupon, 'subscriptions', subscription_id, original_price):
                discount_amount = self._calculate_discount(coupon, original_price)
                coupon_applied = coupon_code
        
        final_price = max(0, original_price - discount_amount)
        
        return PriceCalculation(
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
            credits=subscription.credits_per_period,
            bonus_credits=0,  # Subscriptions don't get first purchase bonus
            total_credits=subscription.credits_per_period,
            coupon_applied=coupon_applied,
            currency=self.config.get_currency(),
            currency_symbol=self.config.get_currency_symbol()
        )
    
    # ========================================================================
    # MODEL COSTS
    # ========================================================================
    
    def get_model_costs(self) -> Dict[str, int]:
        """Get all model costs"""
        costs = self.config.get_model_costs()
        # Remove internal _default key for API response
        return {k: v for k, v in costs.items() if not k.startswith('_')}
    
    def get_model_cost(self, model_name: str) -> int:
        """Get cost for a specific model"""
        return self.config.get_model_cost(model_name)
    
    # ========================================================================
    # GENERATION COST ESTIMATION
    # ========================================================================
    
    def estimate_generation_cost(
        self,
        models: List[str],
        num_variations: int = 1,
        user_balance: int = 0
    ) -> CostEstimate:
        """
        Estimate total cost for a generation request.
        
        Args:
            models: List of model names to use
            num_variations: Number of variations per model
            user_balance: User's current credit balance
            
        Returns:
            CostEstimate with breakdown and sufficiency check
        """
        breakdown = []
        total_cost = 0
        
        for model_name in models:
            cost_per_image = self.get_model_cost(model_name)
            model_total = cost_per_image * num_variations
            total_cost += model_total
            
            breakdown.append({
                'model': model_name,
                'cost_per_generation': cost_per_image,
                'variations': num_variations,
                'subtotal': model_total
            })
        
        return CostEstimate(
            total_credits=total_cost,
            breakdown=breakdown,
            sufficient_balance=user_balance >= total_cost,
            current_balance=user_balance
        )
    
    # ========================================================================
    # COUPON HELPERS
    # ========================================================================
    
    def _is_coupon_valid_for_item(
        self,
        coupon: Coupon,
        item_type: str,  # 'packages' or 'subscriptions'
        item_id: str,
        price: float
    ) -> bool:
        """Check if coupon is valid for a specific item"""
        
        # Check if coupon is active
        if not coupon.active:
            return False
        
        # Check applies_to
        if coupon.applies_to != 'all' and coupon.applies_to != item_type:
            return False
        
        # Check valid_items
        if coupon.valid_items and item_id not in coupon.valid_items:
            return False
        
        # Check minimum purchase
        if price < coupon.min_purchase_usd:
            return False
        
        # Check date validity
        now = datetime.now()
        
        if coupon.valid_from:
            valid_from = datetime.fromisoformat(coupon.valid_from)
            if now < valid_from:
                return False
        
        if coupon.valid_until:
            valid_until = datetime.fromisoformat(coupon.valid_until)
            if now > valid_until:
                return False
        
        return True
    
    def _calculate_discount(self, coupon: Coupon, price: float) -> float:
        """Calculate discount amount"""
        if coupon.type == 'percent':
            return price * (coupon.discount / 100)
        elif coupon.type == 'fixed':
            return min(coupon.discount, price)  # Don't discount more than price
        return 0.0
    
    def validate_coupon(
        self,
        coupon_code: str,
        item_type: str,
        item_id: str,
        price: float
    ) -> Tuple[bool, str, Optional[Coupon]]:
        """
        Validate a coupon code.
        
        Returns:
            Tuple of (is_valid, message, coupon_object)
        """
        coupon = self.config.get_coupon(coupon_code)
        
        if not coupon:
            return False, "Invalid coupon code", None
        
        if not coupon.active:
            return False, "This coupon is no longer active", None
        
        if coupon.applies_to != 'all' and coupon.applies_to != item_type:
            return False, f"This coupon cannot be used for {item_type}", None
        
        if coupon.valid_items and item_id not in coupon.valid_items:
            return False, "This coupon is not valid for this item", None
        
        if price < coupon.min_purchase_usd:
            return False, f"Minimum purchase of ${coupon.min_purchase_usd:.2f} required", None
        
        # Check dates
        now = datetime.now()
        
        if coupon.valid_from:
            valid_from = datetime.fromisoformat(coupon.valid_from)
            if now < valid_from:
                return False, "This coupon is not yet active", None
        
        if coupon.valid_until:
            valid_until = datetime.fromisoformat(coupon.valid_until)
            if now > valid_until:
                return False, "This coupon has expired", None
        
        # Calculate discount for message
        if coupon.type == 'percent':
            discount_text = f"{coupon.discount}% off"
        else:
            discount_text = f"${coupon.discount:.2f} off"
        
        return True, f"Coupon applied: {discount_text}", coupon


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_pricing_service(config: Optional[CreditsConfigLoader] = None) -> PricingService:
    """Get a pricing service instance"""
    return PricingService(config)
