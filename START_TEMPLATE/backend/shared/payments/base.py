"""
Abstract base class for payment providers.
Defines the interface that all payment providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from .models import (
    CheckoutSession,
    PaymentIntent,
    PaymentStatus,
    Coupon,
    CreditPackage,
    WebhookEvent,
    PaymentHistory
)


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    
    All payment providers (Stripe, PayPal, etc.) must implement this interface.
    """
    
    @abstractmethod
    def create_checkout_session(
        self,
        user_id: str,
        package: CreditPackage,
        success_url: str,
        cancel_url: str,
        coupon_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CheckoutSession:
        """
        Create a checkout session for credit purchase.
        
        Args:
            user_id: User identifier
            package: Credit package to purchase
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancellation
            coupon_code: Optional coupon code
            metadata: Additional metadata
            
        Returns:
            CheckoutSession with checkout URL
            
        Raises:
            InvalidCouponError: If coupon is invalid
            CheckoutError: If session creation fails
        """
        pass
    
    @abstractmethod
    def get_checkout_session(self, session_id: str) -> CheckoutSession:
        """
        Get checkout session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            CheckoutSession object
            
        Raises:
            PaymentError: If session not found or retrieval fails
        """
        pass
    
    @abstractmethod
    def verify_webhook(self, payload: str, signature: str, secret: str) -> WebhookEvent:
        """
        Verify and parse webhook event.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            secret: Webhook secret for verification
            
        Returns:
            Parsed and verified WebhookEvent
            
        Raises:
            WebhookVerificationError: If verification fails
        """
        pass
    
    @abstractmethod
    def handle_payment_succeeded(self, event: WebhookEvent) -> PaymentIntent:
        """
        Handle successful payment webhook.
        
        Args:
            event: Verified webhook event
            
        Returns:
            PaymentIntent with success status
            
        Raises:
            PaymentError: If handling fails
        """
        pass
    
    @abstractmethod
    def handle_payment_failed(self, event: WebhookEvent) -> PaymentIntent:
        """
        Handle failed payment webhook.
        
        Args:
            event: Verified webhook event
            
        Returns:
            PaymentIntent with failed status
        """
        pass
    
    @abstractmethod
    def create_refund(
        self,
        payment_id: str,
        amount_cents: Optional[int] = None,
        reason: Optional[str] = None
    ) -> PaymentIntent:
        """
        Create a refund for a payment.
        
        Args:
            payment_id: Payment identifier
            amount_cents: Amount to refund (None = full refund)
            reason: Refund reason
            
        Returns:
            Updated PaymentIntent with refund status
            
        Raises:
            RefundError: If refund fails
        """
        pass
    
    @abstractmethod
    def validate_coupon(self, coupon_code: str) -> Coupon:
        """
        Validate and retrieve coupon details.
        
        Args:
            coupon_code: Coupon code
            
        Returns:
            Coupon object if valid
            
        Raises:
            InvalidCouponError: If coupon is invalid
        """
        pass
    
    @abstractmethod
    def apply_coupon(self, coupon_code: str, amount: float) -> float:
        """
        Calculate discount for coupon and amount.
        
        Args:
            coupon_code: Coupon code
            amount: Purchase amount in USD
            
        Returns:
            Discount amount in USD
            
        Raises:
            InvalidCouponError: If coupon cannot be applied
        """
        pass
    
    @abstractmethod
    def get_payment_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[PaymentStatus] = None
    ) -> PaymentHistory:
        """
        Get payment history for user.
        
        Args:
            user_id: User identifier
            page: Page number (1-indexed)
            page_size: Items per page
            status: Filter by status (optional)
            
        Returns:
            Paginated PaymentHistory
        """
        pass
    
    @abstractmethod
    def get_payment(self, payment_id: str) -> PaymentIntent:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            PaymentIntent object
            
        Raises:
            PaymentError: If payment not found
        """
        pass
    
    # Optional utility methods
    
    def format_amount(self, cents: int) -> str:
        """
        Format amount for display.
        
        Args:
            cents: Amount in cents
            
        Returns:
            Formatted string (e.g., "$10.00")
        """
        return f"${cents / 100:.2f}"
    
    def cents_to_usd(self, cents: int) -> float:
        """Convert cents to USD"""
        return cents / 100
    
    def usd_to_cents(self, usd: float) -> int:
        """Convert USD to cents"""
        return int(usd * 100)
