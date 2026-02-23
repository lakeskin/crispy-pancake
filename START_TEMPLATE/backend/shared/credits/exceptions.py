"""
Custom exceptions for credit management system.
"""


class CreditManagerError(Exception):
    """Base exception for credit management errors"""
    pass


class InsufficientCreditsError(CreditManagerError):
    """Raised when user doesn't have enough credits"""
    
    def __init__(self, required: int, available: int, user_id: str = None):
        self.required = required
        self.available = available
        self.user_id = user_id
        self.shortage = required - available
        
        message = f"Insufficient credits: need {required}, have {available} (short by {self.shortage})"
        if user_id:
            message = f"User {user_id}: {message}"
        
        super().__init__(message)


class InvalidTransactionError(CreditManagerError):
    """Raised when transaction parameters are invalid"""
    pass


class CreditConfigError(CreditManagerError):
    """Raised when configuration is invalid"""
    pass


class ProviderError(CreditManagerError):
    """Raised when underlying provider (Supabase, etc.) fails"""
    
    def __init__(self, provider: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        message = f"{provider} error: {str(original_error)}"
        super().__init__(message)
