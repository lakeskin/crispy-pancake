"""
Unit tests for credit system base classes and interfaces.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from shared.credits.base import CreditManager
from shared.credits.models import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    TransactionHistory
)
from shared.credits.exceptions import (
    InsufficientCreditsError,
    InvalidTransactionError
)


class MockCreditManager(CreditManager):
    """Mock implementation for testing abstract base class"""
    
    def __init__(self):
        self.balances = {}  # user_id -> credits
        self.transactions = []
    
    def get_balance(self, user_id: str) -> CreditBalance:
        credits = self.balances.get(user_id, 0)
        return CreditBalance(user_id=user_id, credits=credits)
    
    def check_sufficient_credits(self, user_id: str, required: int) -> bool:
        current = self.balances.get(user_id, 0)
        return current >= required
    
    def deduct_credits(self, user_id: str, amount: int, description: str = "", metadata=None) -> CreditTransaction:
        if amount <= 0:
            raise InvalidTransactionError("Amount must be positive")
        
        current = self.balances.get(user_id, 0)
        if current < amount:
            raise InsufficientCreditsError(required=amount, available=current, user_id=user_id)
        
        self.balances[user_id] = current - amount
        
        txn = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            balance_before=current,
            balance_after=current - amount,
            transaction_type=TransactionType.DEDUCTION,
            description=description,
            metadata=metadata or {}
        )
        self.transactions.append(txn)
        return txn
    
    def add_credits(self, user_id: str, amount: int, transaction_type: TransactionType, 
                   description: str = "", metadata=None) -> CreditTransaction:
        if amount <= 0:
            raise InvalidTransactionError("Amount must be positive")
        
        current = self.balances.get(user_id, 0)
        self.balances[user_id] = current + amount
        
        txn = CreditTransaction(
            user_id=user_id,
            amount=amount,
            balance_before=current,
            balance_after=current + amount,
            transaction_type=transaction_type,
            description=description,
            metadata=metadata or {}
        )
        self.transactions.append(txn)
        return txn
    
    def get_transaction_history(self, user_id: str, page: int = 1, 
                               page_size: int = 50, transaction_type=None) -> TransactionHistory:
        user_txns = [t for t in self.transactions if t.user_id == user_id]
        if transaction_type:
            user_txns = [t for t in user_txns if t.transaction_type == transaction_type]
        
        start = (page - 1) * page_size
        end = start + page_size
        page_txns = user_txns[start:end]
        
        return TransactionHistory(
            transactions=page_txns,
            total_count=len(user_txns),
            page=page,
            page_size=page_size,
            has_more=end < len(user_txns)
        )
    
    def get_total_spent(self, user_id: str) -> int:
        return sum(abs(t.amount) for t in self.transactions 
                  if t.user_id == user_id and t.amount < 0)
    
    def get_total_earned(self, user_id: str) -> int:
        return sum(t.amount for t in self.transactions 
                  if t.user_id == user_id and t.amount > 0)


class TestCreditManagerInterface:
    """Test CreditManager abstract base class"""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that CreditManager cannot be instantiated directly"""
        with pytest.raises(TypeError):
            CreditManager()
    
    def test_mock_implementation_works(self):
        """Test that mock implementation satisfies interface"""
        manager = MockCreditManager()
        assert isinstance(manager, CreditManager)


class TestCreditManagerBasicOperations:
    """Test basic credit operations"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = MockCreditManager()
        self.user_id = "test_user_123"
    
    def test_get_balance_new_user(self):
        """Test getting balance for new user"""
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 0
        assert balance.user_id == self.user_id
    
    def test_add_credits(self):
        """Test adding credits"""
        txn = self.manager.add_credits(
            self.user_id,
            100,
            TransactionType.PURCHASE,
            "Bought 100 credits"
        )
        
        assert txn.amount == 100
        assert txn.balance_before == 0
        assert txn.balance_after == 100
        
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 100
    
    def test_deduct_credits(self):
        """Test deducting credits"""
        # Add some credits first
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        
        # Deduct credits
        txn = self.manager.deduct_credits(
            self.user_id,
            30,
            "Image generation"
        )
        
        assert txn.amount == -30
        assert txn.balance_before == 100
        assert txn.balance_after == 70
        
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 70
    
    def test_insufficient_credits_error(self):
        """Test error when insufficient credits"""
        self.manager.add_credits(self.user_id, 10, TransactionType.PURCHASE)
        
        with pytest.raises(InsufficientCreditsError) as exc_info:
            self.manager.deduct_credits(self.user_id, 50, "Too expensive")
        
        error = exc_info.value
        assert error.required == 50
        assert error.available == 10
        assert error.shortage == 40
    
    def test_check_sufficient_credits(self):
        """Test checking credit sufficiency"""
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        
        assert self.manager.check_sufficient_credits(self.user_id, 50) is True
        assert self.manager.check_sufficient_credits(self.user_id, 100) is True
        assert self.manager.check_sufficient_credits(self.user_id, 101) is False
    
    def test_invalid_amount_errors(self):
        """Test that invalid amounts are rejected"""
        with pytest.raises(InvalidTransactionError):
            self.manager.add_credits(self.user_id, 0, TransactionType.PURCHASE)
        
        with pytest.raises(InvalidTransactionError):
            self.manager.add_credits(self.user_id, -10, TransactionType.PURCHASE)
        
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        
        with pytest.raises(InvalidTransactionError):
            self.manager.deduct_credits(self.user_id, 0)
        
        with pytest.raises(InvalidTransactionError):
            self.manager.deduct_credits(self.user_id, -10)


class TestTransactionHistory:
    """Test transaction history features"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = MockCreditManager()
        self.user_id = "test_user_123"
    
    def test_empty_history(self):
        """Test history for user with no transactions"""
        history = self.manager.get_transaction_history(self.user_id)
        assert len(history.transactions) == 0
        assert history.total_count == 0
        assert history.has_more is False
    
    def test_transaction_history_order(self):
        """Test that history maintains order"""
        # Create several transactions
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        self.manager.deduct_credits(self.user_id, 10, "Gen 1")
        self.manager.deduct_credits(self.user_id, 20, "Gen 2")
        self.manager.add_credits(self.user_id, 50, TransactionType.BONUS)
        
        history = self.manager.get_transaction_history(self.user_id)
        assert len(history.transactions) == 4
        assert history.total_count == 4
    
    def test_pagination(self):
        """Test paginated history"""
        # Create many transactions
        self.manager.add_credits(self.user_id, 1000, TransactionType.PURCHASE)
        for i in range(10):
            self.manager.deduct_credits(self.user_id, 1, f"Gen {i}")
        
        # Get first page
        page1 = self.manager.get_transaction_history(self.user_id, page=1, page_size=5)
        assert len(page1.transactions) == 5
        assert page1.has_more is True
        
        # Get second page
        page2 = self.manager.get_transaction_history(self.user_id, page=2, page_size=5)
        assert len(page2.transactions) == 5
        assert page2.has_more is True
        
        # Get third page
        page3 = self.manager.get_transaction_history(self.user_id, page=3, page_size=5)
        assert len(page3.transactions) == 1  # Only 1 left (total 11)
        assert page3.has_more is False
    
    def test_filter_by_transaction_type(self):
        """Test filtering history by type"""
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        self.manager.add_credits(self.user_id, 10, TransactionType.SIGNUP_BONUS)
        self.manager.deduct_credits(self.user_id, 5, "Gen")
        self.manager.deduct_credits(self.user_id, 5, "Gen")
        
        # Filter purchases only
        purchases = self.manager.get_transaction_history(
            self.user_id,
            transaction_type=TransactionType.PURCHASE
        )
        assert len(purchases.transactions) == 1
        
        # Filter deductions only
        deductions = self.manager.get_transaction_history(
            self.user_id,
            transaction_type=TransactionType.DEDUCTION
        )
        assert len(deductions.transactions) == 2


class TestAdvancedFeatures:
    """Test advanced credit manager features"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = MockCreditManager()
        self.user_id = "test_user_123"
    
    def test_get_total_spent(self):
        """Test calculating total spent"""
        self.manager.add_credits(self.user_id, 1000, TransactionType.PURCHASE)
        self.manager.deduct_credits(self.user_id, 100, "Gen 1")
        self.manager.deduct_credits(self.user_id, 50, "Gen 2")
        self.manager.deduct_credits(self.user_id, 75, "Gen 3")
        
        total_spent = self.manager.get_total_spent(self.user_id)
        assert total_spent == 225
    
    def test_get_total_earned(self):
        """Test calculating total earned"""
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        self.manager.add_credits(self.user_id, 10, TransactionType.SIGNUP_BONUS)
        self.manager.add_credits(self.user_id, 5, TransactionType.REFERRAL_BONUS)
        self.manager.deduct_credits(self.user_id, 20, "Gen")
        
        total_earned = self.manager.get_total_earned(self.user_id)
        assert total_earned == 115
    
    def test_adjust_balance_positive(self):
        """Test admin adjustment (positive)"""
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        
        txn = self.manager.adjust_balance(
            self.user_id,
            50,
            "Compensation for issue",
            admin_id="admin123"
        )
        
        assert txn.amount == 50
        assert txn.transaction_type == TransactionType.ADMIN_ADJUSTMENT
        
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 150
    
    def test_adjust_balance_negative(self):
        """Test admin adjustment (negative)"""
        self.manager.add_credits(self.user_id, 100, TransactionType.PURCHASE)
        
        txn = self.manager.adjust_balance(
            self.user_id,
            -30,
            "Abuse of service",
            admin_id="admin123"
        )
        
        assert txn.amount == -30
        
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 70
    
    def test_refund_transaction(self):
        """Test refunding a transaction"""
        # Original purchase
        original = self.manager.add_credits(
            self.user_id,
            100,
            TransactionType.PURCHASE,
            metadata={'payment_id': 'pay_123'}
        )
        
        # Use some credits
        self.manager.deduct_credits(self.user_id, 30, "Gen")
        
        # Refund original purchase
        refund = self.manager.refund_transaction(
            self.user_id,
            original.id,
            100,
            "Customer requested refund"
        )
        
        assert refund.transaction_type == TransactionType.REFUND
        assert refund.amount == 100
        
        balance = self.manager.get_balance(self.user_id)
        assert balance.credits == 170  # 100 - 30 + 100
    
    def test_metadata_preservation(self):
        """Test that metadata is preserved in transactions"""
        metadata = {
            'model': 'flux-dev',
            'prompt': 'A sunset',
            'variations': 5,
            'session_id': 'session_xyz'
        }
        
        txn = self.manager.deduct_credits(
            self.user_id,
            10,
            "Image generation",
            metadata=metadata
        )
        
        # Retrieve from history
        history = self.manager.get_transaction_history(self.user_id)
        retrieved = history.transactions[0]
        
        assert retrieved.metadata['model'] == 'flux-dev'
        assert retrieved.metadata['variations'] == 5


class TestMultiUserScenarios:
    """Test scenarios with multiple users"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = MockCreditManager()
    
    def test_independent_user_balances(self):
        """Test that user balances are independent"""
        self.manager.add_credits("user1", 100, TransactionType.PURCHASE)
        self.manager.add_credits("user2", 50, TransactionType.PURCHASE)
        
        balance1 = self.manager.get_balance("user1")
        balance2 = self.manager.get_balance("user2")
        
        assert balance1.credits == 100
        assert balance2.credits == 50
        
        # Deduct from user1
        self.manager.deduct_credits("user1", 30, "Gen")
        
        # user2 balance should be unchanged
        balance2_after = self.manager.get_balance("user2")
        assert balance2_after.credits == 50
    
    def test_transaction_history_isolation(self):
        """Test that transaction histories are isolated"""
        self.manager.add_credits("user1", 100, TransactionType.PURCHASE)
        self.manager.add_credits("user2", 50, TransactionType.PURCHASE)
        self.manager.deduct_credits("user1", 10, "Gen")
        
        history1 = self.manager.get_transaction_history("user1")
        history2 = self.manager.get_transaction_history("user2")
        
        assert len(history1.transactions) == 2  # add + deduct
        assert len(history2.transactions) == 1  # add only


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
