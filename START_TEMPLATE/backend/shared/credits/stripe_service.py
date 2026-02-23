"""
Stripe Service

Handles all Stripe interactions for the credit system:
- One-time checkout sessions
- Subscription checkout sessions  
- Webhook processing
- Customer management

Supports both dynamic pricing and pre-created Stripe prices.
"""

import os
import stripe
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .config_loader import get_credits_config, CreditsConfigLoader
from .pricing_service import get_pricing_service, PricingService


@dataclass
class CheckoutResult:
    """Result of creating a checkout session"""
    success: bool
    session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WebhookResult:
    """Result of processing a webhook"""
    success: bool
    event_type: str
    action_taken: Optional[str] = None
    user_id: Optional[str] = None
    credits_added: int = 0
    error: Optional[str] = None


class StripeService:
    """
    Handles all Stripe payment operations.
    
    Features:
    - One-time credit package purchases
    - Subscription management
    - Dynamic pricing (no Stripe dashboard setup required)
    - Optional pre-created prices for subscriptions
    - Webhook verification and processing
    - Coupon application via Stripe
    
    Usage:
        stripe_service = StripeService()
        result = stripe_service.create_package_checkout(
            user_id="user_123",
            package_id="creator",
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel"
        )
    """
    
    def __init__(
        self,
        config: Optional[CreditsConfigLoader] = None,
        pricing: Optional[PricingService] = None
    ):
        """Initialize Stripe service"""
        self.config = config or get_credits_config()
        self.pricing = pricing or get_pricing_service(self.config)
        
        # Initialize Stripe
        self._init_stripe()
    
    def _init_stripe(self):
        """Initialize Stripe with API key"""
        api_key = os.getenv('STRIPE_SECRET_KEY')
        
        if not api_key:
            # Check if we're in sandbox mode with test key
            if self.config.get_setting('stripe.mode', 'sandbox') == 'sandbox':
                api_key = os.getenv('STRIPE_TEST_SECRET_KEY')
        
        if not api_key:
            raise ValueError(
                "Stripe API key not found. "
                "Set STRIPE_SECRET_KEY (or STRIPE_TEST_SECRET_KEY for sandbox) in environment."
            )
        
        stripe.api_key = api_key
    
    # ========================================================================
    # ONE-TIME PACKAGE CHECKOUT
    # ========================================================================
    
    def create_package_checkout(
        self,
        user_id: str,
        user_email: str,
        package_id: str,
        success_url: str,
        cancel_url: str,
        coupon_code: Optional[str] = None,
        is_first_purchase: bool = False
    ) -> CheckoutResult:
        """
        Create a Stripe Checkout session for a one-time package purchase.
        
        Uses dynamic pricing (price_data) - no Stripe dashboard setup required.
        """
        try:
            # Get package and calculate price
            package = self.config.get_package(package_id)
            if not package:
                return CheckoutResult(success=False, error="Package not found")
            
            if not package.active:
                return CheckoutResult(success=False, error="Package is not available")
            
            # Calculate final price with any discounts
            price_calc = self.pricing.calculate_package_price(
                package_id, 
                coupon_code, 
                is_first_purchase
            )
            
            if not price_calc:
                return CheckoutResult(success=False, error="Failed to calculate price")
            
            # Convert to cents for Stripe
            amount_cents = int(price_calc.final_price * 100)
            
            # Build product name with bonus info
            product_name = f"{package.name} - {package.credits} Credits"
            if price_calc.bonus_credits > 0:
                product_name += f" (+{price_calc.bonus_credits} bonus)"
            
            # Create checkout session with dynamic pricing
            session = stripe.checkout.Session.create(
                mode='payment',
                customer_email=user_email,
                line_items=[{
                    'price_data': {
                        'currency': price_calc.currency.lower(),
                        'unit_amount': amount_cents,
                        'product_data': {
                            'name': product_name,
                            'description': package.description,
                        },
                    },
                    'quantity': 1,
                }],
                metadata={
                    'type': 'package',
                    'user_id': user_id,
                    'package_id': package_id,
                    'credits': package.credits,
                    'bonus_credits': price_calc.bonus_credits,
                    'total_credits': price_calc.total_credits,
                    'coupon_code': coupon_code or '',
                    'is_first_purchase': str(is_first_purchase),
                },
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
            )
            
            return CheckoutResult(
                success=True,
                session_id=session.id,
                checkout_url=session.url
            )
            
        except stripe.error.StripeError as e:
            return CheckoutResult(success=False, error=str(e))
        except Exception as e:
            return CheckoutResult(success=False, error=f"Unexpected error: {str(e)}")
    
    # ========================================================================
    # SUBSCRIPTION CHECKOUT
    # ========================================================================
    
    def create_subscription_checkout(
        self,
        user_id: str,
        user_email: str,
        subscription_id: str,
        success_url: str,
        cancel_url: str,
        coupon_code: Optional[str] = None
    ) -> CheckoutResult:
        """
        Create a Stripe Checkout session for a subscription.
        
        Supports both:
        - Pre-created Stripe prices (if stripe_price_id is set in config)
        - Dynamic prices (if stripe_price_id is null)
        """
        try:
            subscription = self.config.get_subscription(subscription_id)
            if not subscription:
                return CheckoutResult(success=False, error="Subscription not found")
            
            if not subscription.active:
                return CheckoutResult(success=False, error="Subscription is not available")
            
            # Determine if using pre-created price or dynamic
            if subscription.stripe_price_id:
                # Use pre-created Stripe price
                line_items = [{
                    'price': subscription.stripe_price_id,
                    'quantity': 1,
                }]
            else:
                # Create dynamic recurring price
                amount_cents = int(subscription.price_usd * 100)
                
                line_items = [{
                    'price_data': {
                        'currency': self.config.get_currency().lower(),
                        'unit_amount': amount_cents,
                        'recurring': {
                            'interval': subscription.interval,
                            'interval_count': subscription.interval_count,
                        },
                        'product_data': {
                            'name': subscription.name,
                            'description': subscription.description,
                        },
                    },
                    'quantity': 1,
                }]
            
            # Build session params
            session_params = {
                'mode': 'subscription',
                'customer_email': user_email,
                'line_items': line_items,
                'metadata': {
                    'type': 'subscription',
                    'user_id': user_id,
                    'subscription_id': subscription_id,
                    'credits_per_period': subscription.credits_per_period,
                    'coupon_code': coupon_code or '',
                },
                'success_url': success_url + '?session_id={CHECKOUT_SESSION_ID}',
                'cancel_url': cancel_url,
            }
            
            # Add trial period if configured
            if subscription.trial_days > 0:
                session_params['subscription_data'] = {
                    'trial_period_days': subscription.trial_days,
                }
            
            session = stripe.checkout.Session.create(**session_params)
            
            return CheckoutResult(
                success=True,
                session_id=session.id,
                checkout_url=session.url
            )
            
        except stripe.error.StripeError as e:
            return CheckoutResult(success=False, error=str(e))
        except Exception as e:
            return CheckoutResult(success=False, error=f"Unexpected error: {str(e)}")
    
    # ========================================================================
    # WEBHOOK PROCESSING
    # ========================================================================
    
    def verify_webhook(self, payload: bytes, signature: str) -> Optional[Dict]:
        """
        Verify and parse a Stripe webhook.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header value
            
        Returns:
            Parsed event dict or None if verification fails
        """
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET not set in environment")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError:
            return None
    
    def process_webhook(self, event: Dict, add_credits_callback) -> WebhookResult:
        """
        Process a verified Stripe webhook event.
        
        Args:
            event: Verified Stripe event dict
            add_credits_callback: Function to call to add credits
                                  Signature: (user_id, credits, type, description) -> bool
        
        Returns:
            WebhookResult with action taken
        """
        event_type = event.get('type', '')
        data = event.get('data', {}).get('object', {})
        
        # Handle one-time payment completed
        if event_type == 'checkout.session.completed':
            return self._handle_checkout_completed(data, add_credits_callback)
        
        # Handle subscription invoice paid (recurring)
        elif event_type == 'invoice.paid':
            return self._handle_invoice_paid(data, add_credits_callback)
        
        # Handle subscription created
        elif event_type == 'customer.subscription.created':
            return self._handle_subscription_created(data)
        
        # Handle subscription cancelled
        elif event_type == 'customer.subscription.deleted':
            return self._handle_subscription_deleted(data)
        
        # Handle payment failed
        elif event_type == 'invoice.payment_failed':
            return self._handle_payment_failed(data)
        
        # Unhandled event
        return WebhookResult(
            success=True,
            event_type=event_type,
            action_taken="Event type not handled"
        )
    
    def _handle_checkout_completed(self, session: Dict, add_credits_callback) -> WebhookResult:
        """Handle completed checkout session"""
        metadata = session.get('metadata', {})
        purchase_type = metadata.get('type')
        user_id = metadata.get('user_id')
        
        if not user_id:
            return WebhookResult(
                success=False,
                event_type='checkout.session.completed',
                error="No user_id in metadata"
            )
        
        # Handle one-time package purchase
        if purchase_type == 'package':
            total_credits = int(metadata.get('total_credits', 0))
            package_id = metadata.get('package_id', '')
            
            if total_credits > 0:
                success = add_credits_callback(
                    user_id,
                    total_credits,
                    'purchase',
                    f"Purchased {package_id} package"
                )
                
                return WebhookResult(
                    success=success,
                    event_type='checkout.session.completed',
                    action_taken=f"Added {total_credits} credits for package {package_id}",
                    user_id=user_id,
                    credits_added=total_credits if success else 0
                )
        
        # Handle subscription (initial credits)
        elif purchase_type == 'subscription':
            credits = int(metadata.get('credits_per_period', 0))
            subscription_id = metadata.get('subscription_id', '')
            
            if credits > 0:
                # Use 'purchase' type for database constraint compatibility
                success = add_credits_callback(
                    user_id,
                    credits,
                    'purchase',  # Use 'purchase' instead of 'subscription' for DB constraint
                    f"Subscription started: {subscription_id}"
                )
                
                return WebhookResult(
                    success=success,
                    event_type='checkout.session.completed',
                    action_taken=f"Added {credits} credits for subscription {subscription_id}",
                    user_id=user_id,
                    credits_added=credits if success else 0
                )
        
        return WebhookResult(
            success=True,
            event_type='checkout.session.completed',
            action_taken="No credits to add"
        )
    
    def _handle_invoice_paid(self, invoice: Dict, add_credits_callback) -> WebhookResult:
        """Handle paid invoice (subscription renewal)"""
        
        # Skip if this is the first invoice (handled by checkout.session.completed)
        billing_reason = invoice.get('billing_reason', '')
        if billing_reason == 'subscription_create':
            return WebhookResult(
                success=True,
                event_type='invoice.paid',
                action_taken="Initial subscription invoice - handled by checkout"
            )
        
        # Get subscription details
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return WebhookResult(
                success=True,
                event_type='invoice.paid',
                action_taken="No subscription ID - not a subscription invoice"
            )
        
        # Fetch subscription to get metadata
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            metadata = subscription.get('metadata', {})
            user_id = metadata.get('user_id')
            credits = int(metadata.get('credits_per_period', 0))
            plan_id = metadata.get('subscription_id', '')
            
            if user_id and credits > 0:
                # Use 'purchase' type for database constraint compatibility
                success = add_credits_callback(
                    user_id,
                    credits,
                    'purchase',  # Use 'purchase' instead of 'subscription' for DB constraint
                    f"Monthly credits: {plan_id}"
                )
                
                return WebhookResult(
                    success=success,
                    event_type='invoice.paid',
                    action_taken=f"Added {credits} monthly credits",
                    user_id=user_id,
                    credits_added=credits if success else 0
                )
        except Exception as e:
            return WebhookResult(
                success=False,
                event_type='invoice.paid',
                error=str(e)
            )
        
        return WebhookResult(
            success=True,
            event_type='invoice.paid',
            action_taken="No action needed"
        )
    
    def _handle_subscription_created(self, subscription: Dict) -> WebhookResult:
        """Handle new subscription created"""
        metadata = subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_id = metadata.get('subscription_id')
        
        # Store subscription ID for user (would need database call)
        # For now, just log it
        
        return WebhookResult(
            success=True,
            event_type='customer.subscription.created',
            action_taken=f"Subscription {plan_id} created for user {user_id}",
            user_id=user_id
        )
    
    def _handle_subscription_deleted(self, subscription: Dict) -> WebhookResult:
        """Handle subscription cancelled/deleted"""
        metadata = subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_id = metadata.get('subscription_id')
        
        # Update user's subscription status (would need database call)
        # For now, just log it
        
        return WebhookResult(
            success=True,
            event_type='customer.subscription.deleted',
            action_taken=f"Subscription {plan_id} cancelled for user {user_id}",
            user_id=user_id
        )
    
    def _handle_payment_failed(self, invoice: Dict) -> WebhookResult:
        """Handle failed payment"""
        customer_email = invoice.get('customer_email')
        
        # Would typically send notification to user
        # For now, just log it
        
        return WebhookResult(
            success=True,
            event_type='invoice.payment_failed',
            action_taken=f"Payment failed for {customer_email}"
        )
    
    # ========================================================================
    # CUSTOMER MANAGEMENT
    # ========================================================================
    
    def get_or_create_customer(self, user_id: str, email: str) -> Optional[str]:
        """Get existing Stripe customer or create new one"""
        try:
            # Search for existing customer
            customers = stripe.Customer.list(email=email, limit=1)
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                metadata={'user_id': user_id}
            )
            return customer.id
            
        except stripe.error.StripeError:
            return None
    
    def get_customer_subscriptions(self, customer_id: str) -> list:
        """Get active subscriptions for a customer"""
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='active'
            )
            return subscriptions.data
        except stripe.error.StripeError:
            return []
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """Cancel a subscription"""
        try:
            if at_period_end:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError:
            return False
    
    # ========================================================================
    # PAYMENT VERIFICATION / WEBHOOK RECOVERY
    # ========================================================================
    
    def verify_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """
        Verify a checkout session and retrieve its details.
        
        Use this to manually verify payments when webhooks fail.
        
        Args:
            session_id: The Stripe checkout session ID (cs_xxx)
            
        Returns:
            Dict with session details including payment status and metadata
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            return {
                'success': True,
                'session_id': session.id,
                'payment_status': session.payment_status,
                'status': session.status,
                'mode': session.mode,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'customer_email': session.customer_email,
                'metadata': dict(session.metadata) if session.metadata else {},
                'created_at': datetime.fromtimestamp(session.created).isoformat(),
                'is_paid': session.payment_status == 'paid',
            }
            
        except stripe.error.InvalidRequestError as e:
            return {
                'success': False,
                'error': f"Invalid session ID: {str(e)}",
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': f"Stripe error: {str(e)}",
            }
    
    def process_missed_payment(
        self, 
        session_id: str, 
        add_credits_callback
    ) -> WebhookResult:
        """
        Process a payment that may have missed its webhook.
        
        This is a recovery mechanism for when Stripe CLI disconnects.
        Verifies the payment was successful before adding credits.
        
        Args:
            session_id: The checkout session ID
            add_credits_callback: Function to add credits
            
        Returns:
            WebhookResult indicating if credits were added
        """
        # First verify the session
        verification = self.verify_checkout_session(session_id)
        
        if not verification.get('success'):
            return WebhookResult(
                success=False,
                event_type='manual_recovery',
                error=verification.get('error', 'Failed to verify session')
            )
        
        if not verification.get('is_paid'):
            return WebhookResult(
                success=False,
                event_type='manual_recovery',
                error=f"Payment not completed. Status: {verification.get('payment_status')}"
            )
        
        # Payment is verified - process it like a webhook
        metadata = verification.get('metadata', {})
        
        # Check if already processed (this needs database tracking ideally)
        # For now, we'll just process it
        
        # Create a fake session object for the handler
        session_data = {
            'id': session_id,
            'metadata': metadata,
            'payment_status': 'paid',
        }
        
        return self._handle_checkout_completed(session_data, add_credits_callback)
    
    def list_recent_payments(self, email: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        List recent checkout sessions (for debugging/admin).
        
        Args:
            email: Filter by customer email (optional)
            limit: Maximum sessions to return
            
        Returns:
            Dict with list of recent sessions
        """
        try:
            params = {
                'limit': limit,
                'expand': ['data.line_items'],
            }
            
            sessions = stripe.checkout.Session.list(**params)
            
            result = []
            for session in sessions.data:
                # Filter by email if provided
                if email and session.customer_email != email:
                    continue
                    
                result.append({
                    'session_id': session.id,
                    'status': session.status,
                    'payment_status': session.payment_status,
                    'amount': session.amount_total / 100 if session.amount_total else 0,
                    'currency': session.currency,
                    'email': session.customer_email,
                    'metadata': dict(session.metadata) if session.metadata else {},
                    'created': datetime.fromtimestamp(session.created).isoformat(),
                })
            
            return {
                'success': True,
                'sessions': result,
                'count': len(result),
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }


# ============================================================================
# BILLING PORTAL
# ============================================================================

@dataclass
class BillingPortalResult:
    """Result of creating a billing portal session"""
    success: bool
    portal_url: Optional[str] = None
    error: Optional[str] = None


class BillingPortalMixin:
    """
    Mixin for billing portal functionality.
    Added to StripeService via composition.
    """
    
    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> BillingPortalResult:
        """
        Create a Stripe Billing Portal session for subscription management.
        
        The billing portal allows customers to:
        - View their subscription details
        - Update payment methods
        - Cancel subscriptions
        - View billing history
        
        Args:
            customer_id: Stripe customer ID (cus_xxx)
            return_url: URL to redirect after portal session
            
        Returns:
            BillingPortalResult with portal URL or error
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            return BillingPortalResult(
                success=True,
                portal_url=session.url
            )
            
        except stripe.error.StripeError as e:
            return BillingPortalResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            return BillingPortalResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def get_or_create_customer(
        self,
        user_id: str,
        user_email: str
    ) -> Optional[str]:
        """
        Get existing Stripe customer or create a new one.
        
        Args:
            user_id: Internal user ID
            user_email: User's email address
            
        Returns:
            Stripe customer ID (cus_xxx) or None on error
        """
        try:
            # First, try to find existing customer by email
            customers = stripe.Customer.list(email=user_email, limit=1)
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    'user_id': user_id,
                }
            )
            
            return customer.id
            
        except stripe.error.StripeError:
            return None
    
    def get_customer_subscriptions(
        self,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Get all subscriptions for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Dict with subscriptions list and status
        """
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='all',
                limit=10
            )
            
            result = []
            for sub in subscriptions.data:
                result.append({
                    'id': sub.id,
                    'status': sub.status,
                    'current_period_start': datetime.fromtimestamp(sub.current_period_start).isoformat(),
                    'current_period_end': datetime.fromtimestamp(sub.current_period_end).isoformat(),
                    'cancel_at_period_end': sub.cancel_at_period_end,
                    'canceled_at': datetime.fromtimestamp(sub.canceled_at).isoformat() if sub.canceled_at else None,
                    'plan': {
                        'amount': sub.plan.amount / 100 if sub.plan else 0,
                        'interval': sub.plan.interval if sub.plan else None,
                    } if sub.plan else None,
                    'metadata': dict(sub.metadata) if sub.metadata else {},
                })
            
            return {
                'success': True,
                'subscriptions': result,
                'has_active': any(s['status'] == 'active' for s in result),
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            cancel_immediately: If True, cancel now. If False, cancel at period end.
            
        Returns:
            Dict with cancellation status
        """
        try:
            if cancel_immediately:
                subscription = stripe.Subscription.cancel(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            return {
                'success': True,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end).isoformat(),
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
            }


# Add billing portal methods to StripeService
StripeService.create_billing_portal_session = BillingPortalMixin.create_billing_portal_session
StripeService.get_or_create_customer = BillingPortalMixin.get_or_create_customer
StripeService.get_customer_subscriptions = BillingPortalMixin.get_customer_subscriptions
StripeService.cancel_subscription = BillingPortalMixin.cancel_subscription


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_stripe_service(
    config: Optional[CreditsConfigLoader] = None,
    pricing: Optional[PricingService] = None
) -> StripeService:
    """Get a Stripe service instance"""
    return StripeService(config, pricing)
