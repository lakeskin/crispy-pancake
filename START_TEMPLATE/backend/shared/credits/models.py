"""
Data models for credit management system.
Pydantic models for type safety and validation.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class TransactionType(str, Enum):
    """Types of credit transactions"""
    PURCHASE = "purchase"
    SIGNUP_BONUS = "signup_bonus"
    REFERRAL_BONUS = "referral_bonus"
    DEDUCTION = "deduction"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    PROMOTION = "promotion"


class CreditBalance(BaseModel):
    """User's current credit balance"""
    user_id: str
    credits: int = Field(ge=0, description="Current credit balance")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreditTransaction(BaseModel):
    """Individual credit transaction record"""
    id: Optional[str] = None
    user_id: str
    amount: int = Field(description="Credit amount (positive for add, negative for deduct)")
    balance_before: int = Field(ge=0)
    balance_after: int = Field(ge=0)
    transaction_type: TransactionType
    description: str
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('balance_after')
    def validate_balance_after(cls, v, values):
        """Ensure balance calculations are correct"""
        if 'balance_before' in values and 'amount' in values:
            expected = values['balance_before'] + values['amount']
            if v != expected:
                raise ValueError(f"Balance mismatch: {v} != {expected}")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CostBreakdown(BaseModel):
    """Breakdown of costs for a single model/operation"""
    model: str
    cost_per_unit: int = Field(ge=0, description="Cost in credits per unit")
    quantity: int = Field(ge=1, description="Number of units (images, videos, etc.)")
    subtotal: int = Field(ge=0, description="Total cost for this model")
    metadata: Dict = Field(default_factory=dict, description="Additional info (resolution, duration, etc.)")
    
    @validator('subtotal')
    def validate_subtotal(cls, v, values):
        """Ensure subtotal matches cost_per_unit * quantity"""
        if 'cost_per_unit' in values and 'quantity' in values:
            expected = values['cost_per_unit'] * values['quantity']
            if v != expected:
                raise ValueError(f"Subtotal mismatch: {v} != {expected}")
        return v


class CostEstimate(BaseModel):
    """Complete cost estimate for an operation"""
    breakdown: List[CostBreakdown]
    subtotal: int = Field(ge=0, description="Sum of all breakdowns")
    discounts: List[Dict] = Field(default_factory=list, description="Applied discounts")
    discount_amount: int = Field(default=0, ge=0)
    final_cost: int = Field(ge=0, description="Final cost after discounts")
    currency: str = Field(default="credits")
    estimated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('subtotal')
    def validate_subtotal(cls, v, values):
        """Ensure subtotal matches sum of breakdowns"""
        if 'breakdown' in values:
            expected = sum(item.subtotal for item in values['breakdown'])
            if v != expected:
                raise ValueError(f"Subtotal mismatch: {v} != {expected}")
        return v
    
    @validator('final_cost')
    def validate_final_cost(cls, v, values):
        """Ensure final_cost = subtotal - discount_amount"""
        if 'subtotal' in values and 'discount_amount' in values:
            expected = values['subtotal'] - values['discount_amount']
            if v != expected:
                raise ValueError(f"Final cost mismatch: {v} != {expected}")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TransactionHistory(BaseModel):
    """Paginated transaction history"""
    transactions: List[CreditTransaction]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_more: bool
    
    @property
    def total_pages(self) -> int:
        """Calculate total pages"""
        return (self.total_count + self.page_size - 1) // self.page_size
