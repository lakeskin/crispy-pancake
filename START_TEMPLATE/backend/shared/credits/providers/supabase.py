"""
Supabase provider implementation for credit management.

This module provides a concrete implementation of the CreditManager interface
using Supabase as the backend storage and computation provider.
"""

import os
import yaml
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from supabase import Client

from shared.credits.base import CreditManager
from shared.credits.models import (
    CreditBalance,
    CreditTransaction,
    TransactionType,
    TransactionHistory
)
from shared.credits.exceptions import (
    InsufficientCreditsError,
    InvalidTransactionError,
    ProviderError
)


class SupabaseCreditManager(CreditManager):
    """
    Supabase implementation of credit management.
    
    Uses Supabase RPC functions and direct table queries for credit operations.
    Requires the following database schema:
    
    Tables:
    - user_profiles: Contains credits column
    - credit_transactions: Transaction history
    
    RPC Functions:
    - deduct_user_credits(user_id, amount, description, metadata)
    - add_user_credits(user_id, amount, transaction_type, description, metadata)
    - adjust_user_balance(user_id, amount, description, admin_id, metadata)
    - refund_user_transaction(user_id, transaction_id, amount, reason)
    """
    
    def __init__(
        self,
        supabase_client: Optional[Client] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize Supabase credit manager.
        
        Args:
            supabase_client: Existing Supabase client (optional)
            config_path: Path to config file (optional)
        """
        self.client = supabase_client
        self.config = self._load_config(config_path)
        
        # Get table names from config
        self.profiles_table = self.config.get('database', {}).get('profiles_table', 'user_profiles')
        self.transactions_table = self.config.get('database', {}).get('transactions_table', 'credit_transactions')
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if config_path is None:
            # Default to shared credits config
            config_path = Path(__file__).parent.parent / 'config.yaml'
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ProviderError('supabase', f"Failed to load config: {e}")
    
    def _ensure_client(self):
        """Ensure Supabase client is available"""
        if self.client is None:
            # Try to import and initialize client
            try:
                from shared.auth.supabase import get_supabase_client
                self.client = get_supabase_client()
            except Exception as e:
                raise ProviderError('supabase', f"Failed to initialize client: {e}")
    
    def get_balance(self, user_id: str) -> CreditBalance:
        """
        Get current credit balance for user using RPC function.
        
        Args:
            user_id: User ID
            
        Returns:
            CreditBalance object
        """
        self._ensure_client()
        
        try:
            # Use RPC function which has SECURITY DEFINER to bypass RLS
            response = self.client.rpc(
                'get_user_balance',
                {'p_user_id': user_id}
            ).execute()
            
            # The RPC returns a single integer
            credits = response.data if response.data is not None else 0
            
            return CreditBalance(
                user_id=user_id,
                credits=credits,
                last_updated=datetime.utcnow()
            )
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to get balance: {e}")
    
    def check_sufficient_credits(self, user_id: str, required: int) -> bool:
        """
        Check if user has sufficient credits.
        
        Args:
            user_id: User ID
            required: Required credits
            
        Returns:
            True if sufficient, False otherwise
        """
        balance = self.get_balance(user_id)
        return balance.credits >= required
    
    def deduct_credits(
        self,
        user_id: str,
        amount: int,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user's balance.
        
        Args:
            user_id: User ID
            amount: Amount to deduct (positive number)
            description: Transaction description
            metadata: Additional metadata
            
        Returns:
            CreditTransaction object
            
        Raises:
            InvalidTransactionError: If amount is invalid
            InsufficientCreditsError: If insufficient credits
        """
        if amount <= 0:
            raise InvalidTransactionError("Deduction amount must be positive")
        
        self._ensure_client()
        
        try:
            # Call Supabase RPC function
            response = self.client.rpc(
                'deduct_user_credits',
                {
                    'p_user_id': user_id,
                    'p_amount': amount,
                    'p_description': description or 'Credit deduction',
                    'p_metadata': metadata or {}
                }
            ).execute()
            
            if not response.data:
                raise ProviderError('supabase', "RPC function returned no data")
            
            data = response.data[0] if isinstance(response.data, list) else response.data
            
            # Check if operation was successful
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                if 'insufficient' in error_msg.lower():
                    # Parse error message to get amounts
                    raise InsufficientCreditsError(
                        required=amount,
                        available=data.get('current_balance', 0),
                        user_id=user_id
                    )
                raise ProviderError('supabase', error_msg)
            
            # Build transaction object from response
            return CreditTransaction(
                id=data.get('transaction_id'),
                user_id=user_id,
                amount=-amount,
                balance_before=data.get('balance_before', 0),
                balance_after=data.get('balance_after', 0),
                transaction_type=TransactionType.DEDUCTION,
                description=description,
                metadata=metadata or {},
                created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else datetime.utcnow()
            )
        
        except InsufficientCreditsError:
            raise
        except Exception as e:
            raise ProviderError('supabase', f"Failed to deduct credits: {e}")
    
    def add_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Add credits to user's balance.
        
        Args:
            user_id: User ID
            amount: Amount to add (positive number)
            transaction_type: Type of transaction
            description: Transaction description
            metadata: Additional metadata
            
        Returns:
            CreditTransaction object
            
        Raises:
            InvalidTransactionError: If amount is invalid
        """
        if amount <= 0:
            raise InvalidTransactionError("Addition amount must be positive")
        
        self._ensure_client()
        
        try:
            # Call Supabase RPC function
            response = self.client.rpc(
                'add_user_credits',
                {
                    'p_user_id': user_id,
                    'p_amount': amount,
                    'p_transaction_type': transaction_type.value,
                    'p_description': description or f'Credit {transaction_type.value}',
                    'p_metadata': metadata or {}
                }
            ).execute()
            
            if not response.data:
                raise ProviderError('supabase', "RPC function returned no data")
            
            data = response.data[0] if isinstance(response.data, list) else response.data
            
            # Check if operation was successful
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                raise ProviderError('supabase', error_msg)
            
            # Build transaction object from response
            return CreditTransaction(
                id=data.get('transaction_id'),
                user_id=user_id,
                amount=amount,
                balance_before=data.get('balance_before', 0),
                balance_after=data.get('balance_after', 0),
                transaction_type=transaction_type,
                description=description,
                metadata=metadata or {},
                created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else datetime.utcnow()
            )
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to add credits: {e}")
    
    def get_transaction_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        transaction_type: Optional[TransactionType] = None
    ) -> TransactionHistory:
        """
        Get transaction history for user.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            transaction_type: Filter by type (optional)
            
        Returns:
            TransactionHistory object
        """
        self._ensure_client()
        
        try:
            # Build query
            query = self.client.table(self.transactions_table)\
                .select('*', count='exact')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)
            
            # Filter by type if specified
            if transaction_type:
                query = query.eq('transaction_type', transaction_type.value)
            
            # Calculate offset
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)
            
            response = query.execute()
            
            # Parse transactions
            transactions = []
            for row in response.data:
                transactions.append(
                    CreditTransaction(
                        id=row.get('id'),
                        user_id=row.get('user_id'),
                        amount=row.get('amount'),
                        balance_before=row.get('balance_before'),
                        balance_after=row.get('balance_after'),
                        transaction_type=TransactionType(row.get('transaction_type')),
                        description=row.get('description', ''),
                        metadata=row.get('metadata', {}),
                        created_at=datetime.fromisoformat(row.get('created_at')) if row.get('created_at') else datetime.utcnow()
                    )
                )
            
            # Get total count
            total_count = response.count if response.count is not None else len(transactions)
            
            return TransactionHistory(
                transactions=transactions,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_more=(offset + page_size) < total_count
            )
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to get transaction history: {e}")
    
    def get_total_spent(self, user_id: str) -> int:
        """
        Get total credits spent by user.
        
        Args:
            user_id: User ID
            
        Returns:
            Total spent (absolute value)
        """
        self._ensure_client()
        
        try:
            response = self.client.table(self.transactions_table)\
                .select('amount')\
                .eq('user_id', user_id)\
                .lt('amount', 0)\
                .execute()
            
            total = sum(abs(row['amount']) for row in response.data)
            return total
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to get total spent: {e}")
    
    def get_total_earned(self, user_id: str) -> int:
        """
        Get total credits earned by user.
        
        Args:
            user_id: User ID
            
        Returns:
            Total earned
        """
        self._ensure_client()
        
        try:
            response = self.client.table(self.transactions_table)\
                .select('amount')\
                .eq('user_id', user_id)\
                .gt('amount', 0)\
                .execute()
            
            total = sum(row['amount'] for row in response.data)
            return total
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to get total earned: {e}")
    
    def adjust_balance(
        self,
        user_id: str,
        amount: int,
        reason: str,
        admin_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Admin adjustment of user balance.
        
        Args:
            user_id: User ID
            amount: Amount to adjust (can be positive or negative)
            reason: Reason for adjustment
            admin_id: ID of admin making adjustment
            metadata: Additional metadata
            
        Returns:
            CreditTransaction object
        """
        self._ensure_client()
        
        try:
            # Call Supabase RPC function
            response = self.client.rpc(
                'adjust_user_balance',
                {
                    'p_user_id': user_id,
                    'p_amount': amount,
                    'p_reason': reason,
                    'p_admin_id': admin_id,
                    'p_metadata': metadata or {}
                }
            ).execute()
            
            if not response.data:
                raise ProviderError('supabase', "RPC function returned no data")
            
            data = response.data[0] if isinstance(response.data, list) else response.data
            
            # Check if operation was successful
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                raise ProviderError('supabase', error_msg)
            
            # Build transaction object from response
            return CreditTransaction(
                id=data.get('transaction_id'),
                user_id=user_id,
                amount=amount,
                balance_before=data.get('balance_before', 0),
                balance_after=data.get('balance_after', 0),
                transaction_type=TransactionType.ADMIN_ADJUSTMENT,
                description=f"Admin adjustment: {reason}",
                metadata={**(metadata or {}), 'admin_id': admin_id},
                created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else datetime.utcnow()
            )
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to adjust balance: {e}")
    
    def refund_transaction(
        self,
        user_id: str,
        transaction_id: str,
        amount: int,
        reason: str
    ) -> CreditTransaction:
        """
        Refund a previous transaction.
        
        Args:
            user_id: User ID
            transaction_id: Original transaction ID
            amount: Amount to refund
            reason: Refund reason
            
        Returns:
            CreditTransaction object for refund
        """
        self._ensure_client()
        
        try:
            # Call Supabase RPC function
            response = self.client.rpc(
                'refund_user_transaction',
                {
                    'p_user_id': user_id,
                    'p_transaction_id': transaction_id,
                    'p_amount': amount,
                    'p_reason': reason
                }
            ).execute()
            
            if not response.data:
                raise ProviderError('supabase', "RPC function returned no data")
            
            data = response.data[0] if isinstance(response.data, list) else response.data
            
            # Check if operation was successful
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                raise ProviderError('supabase', error_msg)
            
            # Build transaction object from response
            return CreditTransaction(
                id=data.get('transaction_id'),
                user_id=user_id,
                amount=amount,
                balance_before=data.get('balance_before', 0),
                balance_after=data.get('balance_after', 0),
                transaction_type=TransactionType.REFUND,
                description=f"Refund: {reason}",
                metadata={'original_transaction_id': transaction_id},
                created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else datetime.utcnow()
            )
        
        except Exception as e:
            raise ProviderError('supabase', f"Failed to refund transaction: {e}")
    
    def bulk_deduct(
        self,
        operations: list[tuple[str, int, str, Optional[Dict[str, Any]]]]
    ) -> list[CreditTransaction]:
        """
        Deduct credits from multiple users in a batch.
        
        Args:
            operations: List of (user_id, amount, description, metadata) tuples
            
        Returns:
            List of CreditTransaction objects
        """
        transactions = []
        for user_id, amount, description, metadata in operations:
            try:
                txn = self.deduct_credits(user_id, amount, description, metadata)
                transactions.append(txn)
            except Exception as e:
                # Log error but continue with other operations
                print(f"Failed to deduct credits for {user_id}: {e}")
        
        return transactions
