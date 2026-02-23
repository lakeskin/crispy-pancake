"""
Supabase Payment Store Implementation

Implements the PaymentStore interface for Supabase databases.
Handles all CRUD operations for payment records in the payment_transactions table.

BACKWARD COMPATIBILITY:
This implementation supports both OLD and NEW schema column names.

OLD schema (current production):
  - stripe_session_id, stripe_payment_id, credits_purchased

NEW schema (after migration):  
  - provider_session_id, provider_payment_id, credits_to_add, provider, etc.

The store auto-detects which schema is in use.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from supabase import Client

from shared.payments.tracker import (
    PaymentStore,
    PaymentRecord,
    PaymentRecordStatus,
    PaymentRecordHistory
)


class SupabasePaymentStore(PaymentStore):
    """
    Supabase implementation of payment record storage.
    
    Supports both old and new schema versions for backward compatibility.
    
    OLD SCHEMA (v1):
    CREATE TABLE payment_transactions (
        id UUID PRIMARY KEY,
        user_id UUID,
        stripe_payment_id TEXT UNIQUE,
        stripe_session_id TEXT,
        amount_usd DECIMAL(10, 2) NOT NULL,
        credits_purchased INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE,
        updated_at TIMESTAMP WITH TIME ZONE
    );
    
    NEW SCHEMA (v2 - after migration):
    CREATE TABLE payment_transactions (
        id UUID PRIMARY KEY,
        user_id UUID,
        amount_cents INTEGER,
        amount_usd DECIMAL(10, 2),
        credits_to_add INTEGER NOT NULL,
        status TEXT NOT NULL,
        provider TEXT NOT NULL,
        provider_session_id TEXT,
        provider_payment_id TEXT UNIQUE,
        ...additional columns...
    );
    """
    
    # Column name mappings: new_name -> old_name
    COLUMN_MAPPINGS = {
        'credits_to_add': 'credits_purchased',
        'provider_session_id': 'stripe_session_id',
        'provider_payment_id': 'stripe_payment_id',
    }
    
    def __init__(
        self,
        supabase_client: Optional[Client] = None,
        table_name: str = 'payment_transactions'
    ):
        """
        Initialize the Supabase payment store.
        
        Args:
            supabase_client: Supabase client instance. If None, will try to get from shared auth.
            table_name: Name of the payments table (default: 'payment_transactions')
        """
        self.client = supabase_client
        self.table_name = table_name
        self._use_old_schema: Optional[bool] = None  # Auto-detect on first use
    
    def _ensure_client(self):
        """Ensure Supabase client is available"""
        if self.client is None:
            try:
                from shared.auth.supabase import get_supabase_client
                self.client = get_supabase_client()
            except ImportError:
                # Client should be passed in for backend usage
                raise RuntimeError(
                    "No Supabase client available. "
                    "Pass a client to the constructor."
                )
    
    def _detect_schema_version(self):
        """Auto-detect which schema version is in use"""
        if self._use_old_schema is not None:
            return
        
        self._ensure_client()
        
        try:
            # Try inserting with new column name - if it fails, use old schema
            # Actually, let's just query and check what columns exist
            # by looking at the error when we try to select a new column
            response = self.client.table(self.table_name).select('credits_to_add').limit(1).execute()
            # If we get here, new schema is available
            self._use_old_schema = False
        except Exception as e:
            error_str = str(e)
            if 'credits_to_add' in error_str and 'PGRST204' in error_str:
                # Column doesn't exist, use old schema
                self._use_old_schema = True
            else:
                # Some other error - default to old schema to be safe
                self._use_old_schema = True
    
    def _to_db_row(self, payment: PaymentRecord) -> Dict[str, Any]:
        """Convert PaymentRecord to database row format"""
        self._detect_schema_version()
        
        if self._use_old_schema:
            # Use OLD column names
            return {
                'id': payment.id,
                'user_id': payment.user_id,
                'amount_usd': payment.amount_usd or (payment.amount_cents / 100.0 if payment.amount_cents else 0),
                'credits_purchased': payment.credits_to_add,  # old name
                'status': payment.status.value,
                'stripe_session_id': payment.provider_session_id,  # old name
                'stripe_payment_id': payment.provider_payment_id,  # old name
                'metadata': {
                    # Store extra fields in metadata for old schema
                    'provider': payment.provider,
                    'package_id': payment.package_id,
                    'package_name': payment.package_name,
                    'credits_added': payment.credits_added,
                    'amount_cents': payment.amount_cents,
                    **(payment.metadata or {})
                },
            }
        else:
            # Use NEW column names
            return {
                'id': payment.id,
                'user_id': payment.user_id,
                'amount_cents': payment.amount_cents,
                'amount_usd': payment.amount_usd,
                'credits_to_add': payment.credits_to_add,
                'status': payment.status.value,
                'provider': payment.provider,
                'provider_session_id': payment.provider_session_id,
                'provider_payment_id': payment.provider_payment_id,
                'provider_customer_id': payment.provider_customer_id,
                'package_id': payment.package_id,
                'package_name': payment.package_name,
                'coupon_code': payment.coupon_code,
                'discount_cents': payment.discount_cents,
                'original_amount_cents': payment.original_amount_cents,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'updated_at': payment.updated_at.isoformat() if payment.updated_at else None,
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'expires_at': payment.expires_at.isoformat() if payment.expires_at else None,
                'credits_added': payment.credits_added,
                'credits_added_at': payment.credits_added_at.isoformat() if payment.credits_added_at else None,
                'credit_transaction_id': payment.credit_transaction_id,
                'refund_amount_cents': payment.refund_amount_cents,
                'refund_reason': payment.refund_reason,
                'refunded_at': payment.refunded_at.isoformat() if payment.refunded_at else None,
                'error_message': payment.error_message,
                'error_code': payment.error_code,
                'retry_count': payment.retry_count,
                'metadata': payment.metadata,
            }
    
    def _from_db_row(self, row: Dict[str, Any]) -> PaymentRecord:
        """Convert database row to PaymentRecord"""
        self._detect_schema_version()
        
        if self._use_old_schema:
            # Map OLD columns to PaymentRecord fields
            metadata = row.get('metadata') or {}
            
            # Build normalized dict for PaymentRecord
            normalized = {
                'id': row.get('id'),
                'user_id': row.get('user_id'),
                'amount_cents': metadata.get('amount_cents') or int((row.get('amount_usd') or 0) * 100),
                'amount_usd': row.get('amount_usd'),
                'credits_to_add': row.get('credits_purchased'),  # old name
                'status': row.get('status'),
                'provider': metadata.get('provider', 'stripe'),
                'provider_session_id': row.get('stripe_session_id'),  # old name
                'provider_payment_id': row.get('stripe_payment_id'),  # old name
                'package_id': metadata.get('package_id'),
                'package_name': metadata.get('package_name'),
                'credits_added': metadata.get('credits_added', False),
                'created_at': row.get('created_at'),
                'updated_at': row.get('updated_at'),
                'metadata': {k: v for k, v in metadata.items() 
                            if k not in ['provider', 'package_id', 'package_name', 'credits_added', 'amount_cents']},
            }
            return PaymentRecord.from_dict(normalized)
        else:
            # Use new schema directly
            return PaymentRecord.from_dict(row)
    
    def create(self, payment: PaymentRecord) -> PaymentRecord:
        """Create a new payment record in the database"""
        self._ensure_client()
        
        data = self._to_db_row(payment)
        
        try:
            response = self.client.table(self.table_name).insert(data).execute()
            
            if response.data:
                return self._from_db_row(response.data[0])
            else:
                raise RuntimeError("Insert returned no data")
                
        except Exception as e:
            raise RuntimeError(f"Failed to create payment record: {e}")
    
    def get_by_id(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by internal ID"""
        self._ensure_client()
        
        try:
            response = self.client.table(self.table_name) \
                .select('*') \
                .eq('id', payment_id) \
                .limit(1) \
                .execute()
            
            if response.data:
                return self._from_db_row(response.data[0])
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get payment by ID: {e}")
    
    def get_by_session_id(self, session_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider session ID (e.g., Stripe checkout session)"""
        self._ensure_client()
        self._detect_schema_version()
        
        # Use correct column name based on schema version
        column = 'stripe_session_id' if self._use_old_schema else 'provider_session_id'
        
        try:
            response = self.client.table(self.table_name) \
                .select('*') \
                .eq(column, session_id) \
                .limit(1) \
                .execute()
            
            if response.data:
                return self._from_db_row(response.data[0])
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get payment by session ID: {e}")
    
    def get_by_payment_id(self, payment_id: str) -> Optional[PaymentRecord]:
        """Get payment by provider payment ID (e.g., Stripe payment intent)"""
        self._ensure_client()
        self._detect_schema_version()
        
        # Use correct column name based on schema version
        column = 'stripe_payment_id' if self._use_old_schema else 'provider_payment_id'
        
        try:
            response = self.client.table(self.table_name) \
                .select('*') \
                .eq(column, payment_id) \
                .limit(1) \
                .execute()
            
            if response.data:
                return self._from_db_row(response.data[0])
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get payment by payment ID: {e}")
    
    def update(self, payment: PaymentRecord) -> PaymentRecord:
        """Update an existing payment record"""
        self._ensure_client()
        
        data = self._to_db_row(payment)
        
        try:
            response = self.client.table(self.table_name) \
                .update(data) \
                .eq('id', payment.id) \
                .execute()
            
            if response.data:
                return self._from_db_row(response.data[0])
            else:
                raise RuntimeError("Update returned no data")
                
        except Exception as e:
            raise RuntimeError(f"Failed to update payment record: {e}")
    
    def get_user_payments(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[PaymentRecordStatus] = None
    ) -> PaymentRecordHistory:
        """Get paginated payment history for user"""
        self._ensure_client()
        
        try:
            # Build query
            query = self.client.table(self.table_name) \
                .select('*', count='exact') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True)
            
            # Filter by status if specified
            if status:
                query = query.eq('status', status.value)
            
            # Pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)
            
            response = query.execute()
            
            payments = [self._from_db_row(row) for row in (response.data or [])]
            total_count = response.count or len(payments)
            
            return PaymentRecordHistory(
                payments=payments,
                total_count=total_count,
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to get user payments: {e}")
    
    def get_pending_payments(
        self,
        older_than_minutes: int = 30
    ) -> List[PaymentRecord]:
        """Get pending payments older than specified minutes"""
        self._ensure_client()
        
        cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        
        try:
            response = self.client.table(self.table_name) \
                .select('*') \
                .in_('status', [PaymentRecordStatus.PENDING.value, PaymentRecordStatus.PROCESSING.value]) \
                .lt('created_at', cutoff.isoformat()) \
                .execute()
            
            return [self._from_db_row(row) for row in (response.data or [])]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get pending payments: {e}")
    
    def get_recent_by_user(
        self,
        user_id: str,
        limit: int = 10,
        completed_only: bool = False
    ) -> List[PaymentRecord]:
        """Get recent payments for a user"""
        self._ensure_client()
        
        try:
            query = self.client.table(self.table_name) \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit)
            
            if completed_only:
                query = query.eq('status', PaymentRecordStatus.COMPLETED.value)
            
            response = query.execute()
            
            return [self._from_db_row(row) for row in (response.data or [])]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get recent payments: {e}")
    
    def has_completed_payment_for_session(self, session_id: str) -> bool:
        """Check if a completed payment exists for this session"""
        self._ensure_client()
        
        try:
            response = self.client.table(self.table_name) \
                .select('id, status, credits_added') \
                .eq('provider_session_id', session_id) \
                .limit(1) \
                .execute()
            
            if response.data:
                row = response.data[0]
                status = row.get('status')
                credits_added = row.get('credits_added', False)
                
                return status == PaymentRecordStatus.COMPLETED.value and credits_added
            
            return False
            
        except Exception:
            return False


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_supabase_payment_store(
    supabase_client: Optional[Client] = None,
    table_name: str = 'payment_transactions'
) -> SupabasePaymentStore:
    """Get a Supabase payment store instance"""
    return SupabasePaymentStore(supabase_client, table_name)
