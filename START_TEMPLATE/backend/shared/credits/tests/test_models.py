"""
Unit tests for credit system models.
Tests data validation, type safety, and business logic.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from shared.credits.models import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    CostBreakdown,
    CostEstimate,
    TransactionHistory
)


class TestCreditBalance:
    """Test CreditBalance model"""
    
    def test_valid_balance(self):
        """Test creating valid credit balance"""
        balance = CreditBalance(
            user_id="user123",
            credits=100
        )
        assert balance.user_id == "user123"
        assert balance.credits == 100
        assert isinstance(balance.last_updated, datetime)
    
    def test_negative_balance_rejected(self):
        """Test that negative credits are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CreditBalance(user_id="user123", credits=-10)
        assert "greater than or equal to 0" in str(exc_info.value)
    
    def test_zero_balance_allowed(self):
        """Test that zero credits are allowed"""
        balance = CreditBalance(user_id="user123", credits=0)
        assert balance.credits == 0
    
    def test_json_serialization(self):
        """Test JSON serialization"""
        balance = CreditBalance(user_id="user123", credits=50)
        json_data = balance.dict()
        assert json_data['user_id'] == "user123"
        assert json_data['credits'] == 50
        assert 'last_updated' in json_data


class TestCreditTransaction:
    """Test CreditTransaction model"""
    
    def test_valid_transaction(self):
        """Test creating valid transaction"""
        txn = CreditTransaction(
            user_id="user123",
            amount=-10,
            balance_before=50,
            balance_after=40,
            transaction_type=TransactionType.DEDUCTION,
            description="Image generation"
        )
        assert txn.user_id == "user123"
        assert txn.amount == -10
        assert txn.balance_before == 50
        assert txn.balance_after == 40
    
    def test_balance_calculation_validation(self):
        """Test that balance_after must match calculation"""
        with pytest.raises(ValidationError) as exc_info:
            CreditTransaction(
                user_id="user123",
                amount=-10,
                balance_before=50,
                balance_after=45,  # Wrong! Should be 40
                transaction_type=TransactionType.DEDUCTION,
                description="Test"
            )
        assert "Balance mismatch" in str(exc_info.value)
    
    def test_positive_amount_transaction(self):
        """Test adding credits"""
        txn = CreditTransaction(
            user_id="user123",
            amount=100,
            balance_before=0,
            balance_after=100,
            transaction_type=TransactionType.PURCHASE,
            description="Bought credits"
        )
        assert txn.amount == 100
        assert txn.balance_after == 100
    
    def test_metadata_storage(self):
        """Test metadata field"""
        txn = CreditTransaction(
            user_id="user123",
            amount=-5,
            balance_before=50,
            balance_after=45,
            transaction_type=TransactionType.DEDUCTION,
            description="Generation",
            metadata={
                'model': 'flux-dev',
                'images': 3,
                'prompt': 'A sunset'
            }
        )
        assert txn.metadata['model'] == 'flux-dev'
        assert txn.metadata['images'] == 3


class TestCostBreakdown:
    """Test CostBreakdown model"""
    
    def test_valid_breakdown(self):
        """Test creating valid cost breakdown"""
        breakdown = CostBreakdown(
            model="flux-dev",
            cost_per_unit=2,
            quantity=5,
            subtotal=10
        )
        assert breakdown.model == "flux-dev"
        assert breakdown.cost_per_unit == 2
        assert breakdown.quantity == 5
        assert breakdown.subtotal == 10
    
    def test_subtotal_validation(self):
        """Test that subtotal must match cost_per_unit * quantity"""
        with pytest.raises(ValidationError) as exc_info:
            CostBreakdown(
                model="sdxl",
                cost_per_unit=1,
                quantity=10,
                subtotal=15  # Wrong! Should be 10
            )
        assert "Subtotal mismatch" in str(exc_info.value)
    
    def test_zero_quantity_rejected(self):
        """Test that quantity must be >= 1"""
        with pytest.raises(ValidationError):
            CostBreakdown(
                model="model",
                cost_per_unit=1,
                quantity=0,
                subtotal=0
            )
    
    def test_metadata_field(self):
        """Test metadata storage"""
        breakdown = CostBreakdown(
            model="veo-3-1",
            cost_per_unit=10,
            quantity=1,
            subtotal=10,
            metadata={'duration': 5, 'resolution': '1080p'}
        )
        assert breakdown.metadata['duration'] == 5


class TestCostEstimate:
    """Test CostEstimate model"""
    
    def test_valid_estimate(self):
        """Test creating valid cost estimate"""
        breakdowns = [
            CostBreakdown(model="flux-dev", cost_per_unit=2, quantity=3, subtotal=6),
            CostBreakdown(model="sdxl", cost_per_unit=1, quantity=5, subtotal=5)
        ]
        
        estimate = CostEstimate(
            breakdown=breakdowns,
            subtotal=11,
            discount_amount=0,
            final_cost=11
        )
        
        assert len(estimate.breakdown) == 2
        assert estimate.subtotal == 11
        assert estimate.final_cost == 11
    
    def test_subtotal_validation(self):
        """Test that subtotal must match sum of breakdowns"""
        breakdowns = [
            CostBreakdown(model="model1", cost_per_unit=2, quantity=3, subtotal=6),
            CostBreakdown(model="model2", cost_per_unit=1, quantity=5, subtotal=5)
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            CostEstimate(
                breakdown=breakdowns,
                subtotal=15,  # Wrong! Should be 11
                discount_amount=0,
                final_cost=15
            )
        assert "Subtotal mismatch" in str(exc_info.value)
    
    def test_final_cost_validation(self):
        """Test that final_cost = subtotal - discount_amount"""
        breakdowns = [
            CostBreakdown(model="model", cost_per_unit=10, quantity=1, subtotal=10)
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            CostEstimate(
                breakdown=breakdowns,
                subtotal=10,
                discount_amount=2,
                final_cost=10  # Wrong! Should be 8
            )
        assert "Final cost mismatch" in str(exc_info.value)
    
    def test_discount_application(self):
        """Test applying discounts"""
        breakdowns = [
            CostBreakdown(model="model", cost_per_unit=10, quantity=5, subtotal=50)
        ]
        
        estimate = CostEstimate(
            breakdown=breakdowns,
            subtotal=50,
            discounts=[{'type': 'bulk', 'percentage': 0.10}],
            discount_amount=5,
            final_cost=45
        )
        
        assert estimate.discount_amount == 5
        assert estimate.final_cost == 45
        assert len(estimate.discounts) == 1


class TestTransactionHistory:
    """Test TransactionHistory model"""
    
    def test_valid_history(self):
        """Test creating transaction history"""
        txns = [
            CreditTransaction(
                user_id="user123",
                amount=-10,
                balance_before=50,
                balance_after=40,
                transaction_type=TransactionType.DEDUCTION,
                description="Test"
            )
        ]
        
        history = TransactionHistory(
            transactions=txns,
            total_count=100,
            page=1,
            page_size=50,
            has_more=True
        )
        
        assert len(history.transactions) == 1
        assert history.total_count == 100
        assert history.has_more is True
    
    def test_total_pages_calculation(self):
        """Test total pages property"""
        history = TransactionHistory(
            transactions=[],
            total_count=125,
            page=1,
            page_size=50,
            has_more=True
        )
        
        assert history.total_pages == 3  # 125 / 50 = 2.5 -> 3
    
    def test_empty_history(self):
        """Test empty transaction history"""
        history = TransactionHistory(
            transactions=[],
            total_count=0,
            page=1,
            page_size=50,
            has_more=False
        )
        
        assert len(history.transactions) == 0
        assert history.total_count == 0
        assert history.total_pages == 0


class TestTransactionType:
    """Test TransactionType enum"""
    
    def test_all_types_accessible(self):
        """Test that all transaction types are defined"""
        assert TransactionType.PURCHASE == "purchase"
        assert TransactionType.SIGNUP_BONUS == "signup_bonus"
        assert TransactionType.REFERRAL_BONUS == "referral_bonus"
        assert TransactionType.DEDUCTION == "deduction"
        assert TransactionType.REFUND == "refund"
        assert TransactionType.ADMIN_ADJUSTMENT == "admin_adjustment"
        assert TransactionType.PROMOTION == "promotion"
    
    def test_enum_in_transaction(self):
        """Test using enum in transaction"""
        txn = CreditTransaction(
            user_id="user123",
            amount=100,
            balance_before=0,
            balance_after=100,
            transaction_type=TransactionType.SIGNUP_BONUS,
            description="Welcome bonus"
        )
        assert txn.transaction_type == TransactionType.SIGNUP_BONUS
        assert txn.transaction_type.value == "signup_bonus"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
