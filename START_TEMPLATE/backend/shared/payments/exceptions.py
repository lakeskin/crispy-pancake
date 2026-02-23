"""
Custom exceptions for payment processing.
"""


class PaymentError(Exception):
    """Base exception for payment-related errors"""
    
    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self):
        parts = [self.message]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.error_code:
            parts.append(f"Code: {self.error_code}")
        return " | ".join(parts)


class InvalidCouponError(PaymentError):
    """Raised when coupon is invalid, expired, or cannot be applied"""
    
    def __init__(self, coupon_code: str, reason: str):
        self.coupon_code = coupon_code
        self.reason = reason
        message = f"Invalid coupon '{coupon_code}': {reason}"
        super().__init__(message)


class WebhookVerificationError(PaymentError):
    """Raised when webhook signature verification fails"""
    
    def __init__(self, reason: str):
        message = f"Webhook verification failed: {reason}"
        super().__init__(message, error_code="webhook_verification_failed")


class CheckoutError(PaymentError):
    """Raised when checkout session creation fails"""
    pass


class RefundError(PaymentError):
    """Raised when refund processing fails"""
    
    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        message = f"Refund failed for payment {payment_id}: {reason}"
        super().__init__(message)


class PaymentMethodError(PaymentError):
    """Raised when payment method is invalid or failed"""
    pass
