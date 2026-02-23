"""
Data models for payment processing.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class PaymentStatus(str, Enum):
    """Payment status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    """Payment method types"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"  # Apple Pay, Google Pay, etc.
    OTHER = "other"


class CreditPackage(BaseModel):
    """Credit package definition"""
    id: str
    name: str
    credits: int = Field(gt=0)
    price_usd: float = Field(gt=0)
    price_cents: int = Field(gt=0)  # Always store in cents to avoid floating point issues
    discount_percent: Optional[float] = Field(default=0, ge=0, le=100)
    popular: bool = False
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('price_cents', pre=True, always=True)
    def calculate_price_cents(cls, v, values):
        """Calculate price in cents from USD if not provided"""
        if v is None and 'price_usd' in values:
            return int(values['price_usd'] * 100)
        return v
    
    @property
    def cost_per_credit(self) -> float:
        """Calculate cost per credit in USD"""
        return self.price_usd / self.credits
    
    class Config:
        use_enum_values = True


class Coupon(BaseModel):
    """Coupon/promo code definition"""
    code: str
    discount_type: str = Field(...)  # 'percentage' or 'fixed_amount'
    discount_value: float = Field(gt=0)
    min_purchase: Optional[float] = Field(default=None, ge=0)
    max_discount: Optional[float] = Field(default=None, ge=0)
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = Field(default=None, gt=0)
    current_uses: int = Field(default=0, ge=0)
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('discount_type')
    def validate_discount_type(cls, v):
        """Validate discount type"""
        if v not in ['percentage', 'fixed_amount']:
            raise ValueError("discount_type must be 'percentage' or 'fixed_amount'")
        return v
    
    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        """Validate discount value based on type"""
        if 'discount_type' in values:
            if values['discount_type'] == 'percentage' and v > 100:
                raise ValueError("Percentage discount cannot exceed 100%")
        return v
    
    def is_valid(self) -> bool:
        """Check if coupon is valid"""
        if not self.active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def calculate_discount(self, amount: float) -> float:
        """
        Calculate discount amount for given purchase amount.
        
        Args:
            amount: Purchase amount in USD
            
        Returns:
            Discount amount in USD
        """
        if not self.is_valid():
            return 0.0
        
        if self.min_purchase and amount < self.min_purchase:
            return 0.0
        
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
        else:  # fixed_amount
            discount = self.discount_value
        
        # Apply max discount if set
        if self.max_discount:
            discount = min(discount, self.max_discount)
        
        # Ensure discount doesn't exceed purchase amount
        discount = min(discount, amount)
        
        return round(discount, 2)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CheckoutSession(BaseModel):
    """Checkout session for credit purchase"""
    id: str
    user_id: str
    package_id: str
    credits: int = Field(gt=0)
    amount_usd: float = Field(gt=0)
    amount_cents: int = Field(gt=0)
    coupon_code: Optional[str] = None
    discount_amount: float = Field(default=0, ge=0)
    final_amount_cents: int = Field(gt=0)
    status: PaymentStatus = PaymentStatus.PENDING
    checkout_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('final_amount_cents', pre=True, always=True)
    def calculate_final_amount(cls, v, values):
        """Calculate final amount after discount"""
        if v is None and 'amount_cents' in values and 'discount_amount' in values:
            discount_cents = int(values['discount_amount'] * 100)
            return max(values['amount_cents'] - discount_cents, 0)
        return v
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaymentIntent(BaseModel):
    """Payment intent record"""
    id: str
    user_id: str
    session_id: str
    amount_cents: int = Field(gt=0)
    currency: str = "usd"
    status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    failure_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def amount_usd(self) -> float:
        """Get amount in USD"""
        return self.amount_cents / 100
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookEvent(BaseModel):
    """Webhook event from payment provider"""
    id: str
    type: str
    provider: str
    payload: Dict[str, Any]
    signature: Optional[str] = None
    verified: bool = False
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaymentHistory(BaseModel):
    """Paginated payment history"""
    payments: List[PaymentIntent]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(gt=0)
    has_more: bool
    
    @validator('has_more', pre=True, always=True)
    def calculate_has_more(cls, v, values):
        """Calculate if there are more pages"""
        if 'payments' in values and 'total_count' in values and 'page' in values and 'page_size' in values:
            loaded = values['page'] * values['page_size']
            return loaded < values['total_count']
        return v
