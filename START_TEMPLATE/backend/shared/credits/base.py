"""
Abstract base class for credit management.
Defines the interface that all credit providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime

from .models import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    TransactionHistory
)
from .exceptions import InsufficientCreditsError, InvalidTransactionError


class CreditManager(ABC):
    """
    Abstract base class for credit management.
    
    All credit providers (Supabase, Firebase, etc.) must implement this interface.
    Ensures consistency across different backends.
    """
    
    @abstractmethod
    def get_balance(self, user_id: str) -> CreditBalance:
        """
        Get user's current credit balance.
        
        Args:
            user_id: User identifier
            
        Returns:
            CreditBalance with current credits and metadata
            
        Raises:
            ProviderError: If underlying provider fails
        """
        pass
    
    @abstractmethod
    def check_sufficient_credits(self, user_id: str, required: int) -> bool:
        """
        Check if user has sufficient credits.
        
        Args:
            user_id: User identifier
            required: Required credit amount
            
        Returns:
            True if user has enough credits, False otherwise
        """
        pass
    
    @abstractmethod
    def deduct_credits(
        self,
        user_id: str,
        amount: int,
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user account.
        
        Args:
            user_id: User identifier
            amount: Number of credits to deduct (positive integer)
            description: Human-readable description of transaction
            metadata: Additional context (model name, generation params, etc.)
            
        Returns:
            CreditTransaction record with transaction details
            
        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            InvalidTransactionError: If amount <= 0 or other validation fails
            ProviderError: If underlying provider fails
        """
        pass
    
    @abstractmethod
    def add_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> CreditTransaction:
        """
        Add credits to user account.
        
        Args:
            user_id: User identifier
            amount: Number of credits to add (positive integer)
            transaction_type: Type of transaction (purchase, bonus, etc.)
            description: Human-readable description
            metadata: Additional context (payment_id, promo_code, etc.)
            
        Returns:
            CreditTransaction record with transaction details
            
        Raises:
            InvalidTransactionError: If amount <= 0 or other validation fails
            ProviderError: If underlying provider fails
        """
        pass
    
    @abstractmethod
    def get_transaction_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        transaction_type: Optional[TransactionType] = None
    ) -> TransactionHistory:
        """
        Get user's credit transaction history.
        
        Args:
            user_id: User identifier
            page: Page number (1-indexed)
            page_size: Number of transactions per page
            transaction_type: Filter by transaction type (optional)
            
        Returns:
            TransactionHistory with paginated transactions
            
        Raises:
            ProviderError: If underlying provider fails
        """
        pass
    
    @abstractmethod
    def get_total_spent(self, user_id: str) -> int:
        """
        Get total credits spent by user (all deductions).
        
        Args:
            user_id: User identifier
            
        Returns:
            Total credits spent (absolute value)
        """
        pass
    
    @abstractmethod
    def get_total_earned(self, user_id: str) -> int:
        """
        Get total credits earned by user (purchases, bonuses, etc.).
        
        Args:
            user_id: User identifier
            
        Returns:
            Total credits earned
        """
        pass
    
    # Optional: Admin/Support methods
    
    def adjust_balance(
        self,
        user_id: str,
        amount: int,
        reason: str,
        admin_id: str
    ) -> CreditTransaction:
        """
        Admin adjustment to user balance (can be positive or negative).
        
        Args:
            user_id: User identifier
            amount: Credits to add (positive) or remove (negative)
            reason: Reason for adjustment
            admin_id: Admin who made the adjustment
            
        Returns:
            CreditTransaction record
        """
        metadata = {'admin_id': admin_id, 'reason': reason}
        
        if amount > 0:
            return self.add_credits(
                user_id,
                amount,
                TransactionType.ADMIN_ADJUSTMENT,
                f"Admin adjustment: {reason}",
                metadata
            )
        else:
            return self.deduct_credits(
                user_id,
                abs(amount),
                f"Admin adjustment: {reason}",
                metadata
            )
    
    def refund_transaction(
        self,
        user_id: str,
        original_transaction_id: str,
        amount: int,
        reason: str = "Refund"
    ) -> CreditTransaction:
        """
        Refund a previous transaction.
        
        Args:
            user_id: User identifier
            original_transaction_id: ID of transaction being refunded
            amount: Amount to refund
            reason: Reason for refund
            
        Returns:
            CreditTransaction record for refund
        """
        return self.add_credits(
            user_id,
            amount,
            TransactionType.REFUND,
            reason,
            {'original_transaction_id': original_transaction_id}
        )
    
    # Utility methods (can be overridden for optimization)
    
    def bulk_deduct(
        self,
        transactions: List[Dict]
    ) -> List[CreditTransaction]:
        """
        Deduct credits for multiple users in bulk.
        
        Args:
            transactions: List of dicts with user_id, amount, description, metadata
            
        Returns:
            List of CreditTransaction records
            
        Note: Default implementation does individual deductions.
        Override for batch optimization if provider supports it.
        """
        results = []
        for txn in transactions:
            result = self.deduct_credits(
                user_id=txn['user_id'],
                amount=txn['amount'],
                description=txn.get('description', ''),
                metadata=txn.get('metadata')
            )
            results.append(result)
        return results
