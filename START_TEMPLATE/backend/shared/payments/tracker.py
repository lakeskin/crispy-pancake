"""
Payment Tracking Service

A database-backed payment tracking system that provides:
- Payment record creation before checkout
- Status updates through the payment lifecycle
- Duplicate payment prevention
- Session-based and ID-based lookups
- Audit trail for all payments

This module is provider-agnostic and works with any database backend
that implements the PaymentStore interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class PaymentRecordStatus(str, Enum):
    """
    Payment record lifecycle status.
    
    Flow:
        PENDING -> PROCESSING -> COMPLETED/FAILED/EXPIRED
        COMPLETED -> REFUNDED/PARTIALLY_REFUNDED
        FAILED -> PENDING (retry)
    """
    PENDING = "pending"           # Checkout created, awaiting payment
    PROCESSING = "processing"     # Payment in progress (webhook received)
    COMPLETED = "completed"       # Payment successful, credits added
    FAILED = "failed"             # Payment failed
    EXPIRED = "expired"           # Checkout session expired
    REFUNDED = "refunded"         # Full refund processed
    PARTIALLY_REFUNDED = "partially_refunded"  # Partial refund
    CANCELLED = "cancelled"       # User cancelled


@dataclass
class PaymentRecord:
    """
    A payment record in the database.
    
    This represents a single payment attempt and tracks it through
    its complete lifecycle.
    """
    id: str
    user_id: str
    amount_cents: int
    amount_usd: float
    credits_to_add: int
    status: PaymentRecordStatus
    
    # Provider info
    provider: str                      # 'stripe', 'paypal', etc.
    provider_session_id: Optional[str] = None   # Checkout session ID
    provider_payment_id: Optional[str] = None   # Payment intent ID
    provider_customer_id: Optional[str] = None  # Customer ID
    
    # Package/product info
    package_id: Optional[str] = None
    package_name: Optional[str] = None
    
    # Discount info
    coupon_code: Optional[str] = None
    discount_cents: int = 0
    original_amount_cents: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Credits tracking
    credits_added: bool = False
    credits_added_at: Optional[datetime] = None
    credit_transaction_id: Optional[str] = None
    
    # Refund tracking
    refund_amount_cents: int = 0
    refund_reason: Optional[str] = None
    refunded_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0
    
    # Metadata for extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        """Check if payment completed successfully"""
        return self.status == PaymentRecordStatus.COMPLETED
    
    @property
    def is_pending(self) -> bool:
        """Check if payment is still pending"""
        return self.status in (PaymentRecordStatus.PENDING, PaymentRecordStatus.PROCESSING)
    
    @property
    def is_expired(self) -> bool:
        """Check if checkout session expired"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return self.status == PaymentRecordStatus.EXPIRED
    
    @property
    def can_add_credits(self) -> bool:
        """Check if credits can be added for this payment"""
        return self.is_completed and not self.credits_added
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount_cents': self.amount_cents,
            'amount_usd': self.amount_usd,
            'credits_to_add': self.credits_to_add,
            'status': self.status.value,
            'provider': self.provider,
            'provider_session_id': self.provider_session_id,
            'provider_payment_id': self.provider_payment_id,
            'provider_customer_id': self.provider_customer_id,
            'package_id': self.package_id,
            'package_name': self.package_name,
            'coupon_code': self.coupon_code,
            'discount_cents': self.discount_cents,
            'original_amount_cents': self.original_amount_cents,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'credits_added': self.credits_added,
            'credits_added_at': self.credits_added_at.isoformat() if self.credits_added_at else None,
            'credit_transaction_id': self.credit_transaction_id,
            'refund_amount_cents': self.refund_amount_cents,
            'refund_reason': self.refund_reason,
            'refunded_at': self.refunded_at.isoformat() if self.refunded_at else None,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'retry_count': self.retry_count,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaymentRecord':
        """Create from dictionary (database row)"""
        def parse_datetime(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val.replace('Z', '+00:00').replace('+00:00', ''))
        
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            amount_cents=data['amount_cents'],
            amount_usd=data.get('amount_usd', data['amount_cents'] / 100),
            credits_to_add=data['credits_to_add'],
            status=PaymentRecordStatus(data['status']),
            provider=data['provider'],
            provider_session_id=data.get('provider_session_id'),
            provider_payment_id=data.get('provider_payment_id'),
            provider_customer_id=data.get('provider_customer_id'),
            package_id=data.get('package_id'),
            package_name=data.get('package_name'),
            coupon_code=data.get('coupon_code'),
            discount_cents=data.get('discount_cents', 0),
            original_amount_cents=data.get('original_amount_cents', 0),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            completed_at=parse_datetime(data.get('completed_at')),
            expires_at=parse_datetime(data.get('expires_at')),
            credits_added=data.get('credits_added', False),
            credits_added_at=parse_datetime(data.get('credits_added_at')),
            credit_transaction_id=data.get('credit_transaction_id'),
            refund_amount_cents=data.get('refund_amount_cents', 0),
            refund_reason=data.get('refund_reason'),
            refunded_at=parse_datetime(data.get('refunded_at')),
            error_message=data.get('error_message'),
            error_code=data.get('error_code'),
            retry_count=data.get('retry_count', 0),
            metadata=data.get('metadata', {}),
        )


@dataclass
class PaymentRecordHistory:
    """Paginated payment history"""
    payments: List[PaymentRecord]
    total_count: int
    page: int
    page_size: int
    
    @property
    def has_more(self) -> bool:
        return (self.page * self.page_size) < self.total_count


# ============================================================================
# ABSTRACT STORE INTERFACE
# ============================================================================

class PaymentStore(ABC):
    """
    Abstract interface for payment record storage.
    
    Implement this for different backends (Supabase, Firebase, PostgreSQL, etc.)
    """
    
    @abstractmethod
    def create(self, payment: PaymentRecord) -> PaymentRecord:
        """Create a new payment record"""
        pass
    
    @abstractmethod
    def get_by_id(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by ID"""
        pass
    
    @abstractmethod
    def get_by_session_id(self, session_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider session ID"""
        pass
    
    @abstractmethod
    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider payment ID"""
        pass
    
    @abstractmethod
    def update(self, payment: PaymentRecord) -> PaymentRecord:
        """Update an existing payment record"""
        pass
    
    @abstractmethod
    def get_user_payments(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[PaymentRecordStatus] = None
    ) -> PaymentRecordHistory:
        """Get paginated payment history for user"""
        pass
    
    @abstractmethod
    def get_pending_payments(
        self,
        older_than_minutes: int = 30
    ) -> List[PaymentRecord]:
        """Get pending payments older than specified minutes (for cleanup/retry)"""
        pass


# ============================================================================
# PAYMENT TRACKER SERVICE
# ============================================================================

class PaymentTracker:
    """
    High-level payment tracking service.
    
    Provides a clean API for tracking payments through their lifecycle.
    Uses a PaymentStore implementation for persistence.
    
    Usage:
        store = SupabasePaymentStore(supabase_client)
        tracker = PaymentTracker(store)
        
        # Before Stripe checkout
        payment = tracker.create_pending_payment(
            user_id='user_123',
            amount_cents=999,
            credits_to_add=150,
            provider='stripe',
            session_id='cs_xxx',
            package_id='creator'
        )
        
        # After webhook confirms payment
        tracker.mark_completed(payment.id, payment_id='pi_xxx')
        tracker.mark_credits_added(payment.id, transaction_id='txn_123')
    """
    
    def __init__(
        self,
        store: PaymentStore,
        session_expiry_minutes: int = 30
    ):
        self.store = store
        self.session_expiry_minutes = session_expiry_minutes
    
    def create_pending_payment(
        self,
        user_id: str,
        amount_cents: int,
        credits_to_add: int,
        provider: str,
        session_id: str,
        package_id: Optional[str] = None,
        package_name: Optional[str] = None,
        coupon_code: Optional[str] = None,
        discount_cents: int = 0,
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentRecord:
        """
        Create a pending payment record before checkout.
        
        Call this BEFORE redirecting to Stripe checkout to ensure
        we have a record of the payment attempt.
        """
        payment = PaymentRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount_cents=amount_cents,
            amount_usd=amount_cents / 100,
            credits_to_add=credits_to_add,
            status=PaymentRecordStatus.PENDING,
            provider=provider,
            provider_session_id=session_id,
            provider_customer_id=customer_id,
            package_id=package_id,
            package_name=package_name,
            coupon_code=coupon_code,
            discount_cents=discount_cents,
            original_amount_cents=amount_cents + discount_cents,
            expires_at=datetime.utcnow() + timedelta(minutes=self.session_expiry_minutes),
            metadata=metadata or {}
        )
        
        return self.store.create(payment)
    
    def get_payment(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by internal ID"""
        return self.store.get_by_id(payment_id)
    
    def get_by_session(self, session_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider session ID (e.g., Stripe checkout session)"""
        return self.store.get_by_session_id(session_id)
    
    def get_by_provider_payment(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider payment ID (e.g., Stripe payment intent)"""
        return self.store.get_by_payment_id(payment_id)
    
    def is_duplicate(self, session_id: str) -> bool:
        """
        Check if a payment for this session already exists and was completed.
        
        Use this to prevent duplicate credit additions.
        """
        existing = self.store.get_by_session_id(session_id)
        if existing and existing.credits_added:
            return True
        return False
    
    def mark_processing(
        self,
        payment_id: str,
        provider_payment_id: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """Mark payment as processing (webhook received)"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentRecordStatus.PROCESSING
        payment.updated_at = datetime.utcnow()
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        
        return self.store.update(payment)
    
    def mark_completed(
        self,
        payment_id: str,
        provider_payment_id: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """Mark payment as completed (payment successful)"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentRecordStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        payment.updated_at = datetime.utcnow()
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        
        return self.store.update(payment)
    
    def mark_completed_by_session(
        self,
        session_id: str,
        provider_payment_id: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """Mark payment as completed using session ID"""
        payment = self.store.get_by_session_id(session_id)
        if not payment:
            return None
        
        return self.mark_completed(payment.id, provider_payment_id)
    
    def mark_credits_added(
        self,
        payment_id: str,
        credit_transaction_id: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """Mark that credits were added for this payment"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.credits_added = True
        payment.credits_added_at = datetime.utcnow()
        payment.credit_transaction_id = credit_transaction_id
        payment.updated_at = datetime.utcnow()
        
        return self.store.update(payment)
    
    def mark_failed(
        self,
        payment_id: str,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """Mark payment as failed"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentRecordStatus.FAILED
        payment.error_message = error_message
        payment.error_code = error_code
        payment.updated_at = datetime.utcnow()
        
        return self.store.update(payment)
    
    def mark_expired(self, payment_id: str) -> Optional[PaymentRecord]:
        """Mark payment as expired"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = PaymentRecordStatus.EXPIRED
        payment.updated_at = datetime.utcnow()
        
        return self.store.update(payment)
    
    def mark_refunded(
        self,
        payment_id: str,
        refund_amount_cents: int,
        reason: Optional[str] = None,
        partial: bool = False
    ) -> Optional[PaymentRecord]:
        """Mark payment as refunded"""
        payment = self.store.get_by_id(payment_id)
        if not payment:
            return None
        
        payment.status = (
            PaymentRecordStatus.PARTIALLY_REFUNDED if partial 
            else PaymentRecordStatus.REFUNDED
        )
        payment.refund_amount_cents = refund_amount_cents
        payment.refund_reason = reason
        payment.refunded_at = datetime.utcnow()
        payment.updated_at = datetime.utcnow()
        
        return self.store.update(payment)
    
    def get_user_payments(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[PaymentRecordStatus] = None
    ) -> PaymentRecordHistory:
        """Get user's payment history"""
        return self.store.get_user_payments(user_id, page, page_size, status)
    
    def cleanup_expired(self) -> int:
        """
        Mark expired pending payments as expired.
        Returns count of payments marked expired.
        """
        pending = self.store.get_pending_payments(older_than_minutes=self.session_expiry_minutes)
        count = 0
        
        for payment in pending:
            if payment.is_expired:
                self.mark_expired(payment.id)
                count += 1
        
        return count
    
    def get_payment_stats(self, user_id: str) -> Dict[str, Any]:
        """Get payment statistics for a user"""
        history = self.store.get_user_payments(user_id, page=1, page_size=1000)
        
        total_spent = 0
        total_credits = 0
        completed_count = 0
        failed_count = 0
        
        for payment in history.payments:
            if payment.status == PaymentRecordStatus.COMPLETED:
                total_spent += payment.amount_cents
                total_credits += payment.credits_to_add
                completed_count += 1
            elif payment.status == PaymentRecordStatus.FAILED:
                failed_count += 1
        
        return {
            'total_spent_cents': total_spent,
            'total_spent_usd': total_spent / 100,
            'total_credits_purchased': total_credits,
            'completed_payments': completed_count,
            'failed_payments': failed_count,
            'total_payments': history.total_count,
        }
