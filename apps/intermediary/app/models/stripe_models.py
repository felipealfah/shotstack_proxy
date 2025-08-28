"""
Stripe Models - Pydantic models for Stripe integration
Handles all data validation and serialization for Stripe payments
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, Dict, Any, List
from enum import Enum
from datetime import datetime

class TokenPackageType(str, Enum):
    """Enum for available token package types"""
    STARTER = "starter"
    STANDARD = "standard"
    PRO = "pro"
    BUSINESS = "business"

class TransactionStatus(str, Enum):
    """Enum for transaction status values"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    """Enum for Stripe payment status values"""
    UNPAID = "unpaid"
    PAID = "paid"
    NO_PAYMENT_REQUIRED = "no_payment_required"

# ===========================================
# REQUEST MODELS
# ===========================================

class TokenPackageRequest(BaseModel):
    """Request model for creating a checkout session"""
    package_type: TokenPackageType = Field(..., description="Type of token package to purchase")
    success_url: Optional[str] = Field(None, description="Custom success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Custom cancel redirect URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "package_type": "standard",
                "success_url": "https://mysite.com/success",
                "cancel_url": "https://mysite.com/cancel"
            }
        }

# ===========================================
# TOKEN PACKAGE MODELS
# ===========================================

class TokenPackage(BaseModel):
    """Model representing a token package offer"""
    type: TokenPackageType = Field(..., description="Package type identifier")
    tokens: int = Field(..., gt=0, description="Number of tokens included")
    amount_cents: int = Field(..., gt=0, description="Price in cents (e.g., 999 for $9.99)")
    amount_usd: float = Field(..., gt=0, description="Price in USD for display")
    description: str = Field(..., description="Package description")
    recommended: bool = Field(False, description="Whether this package is recommended")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "standard",
                "tokens": 50,
                "amount_cents": 3999,
                "amount_usd": 39.99,
                "description": "Great for regular video creation",
                "recommended": True
            }
        }

class TokenPackageList(BaseModel):
    """Response model for listing available token packages"""
    packages: List[TokenPackage] = Field(..., description="List of available token packages")
    total_packages: int = Field(..., description="Total number of packages available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "packages": [
                    {
                        "type": "starter",
                        "tokens": 10,
                        "amount_cents": 999,
                        "amount_usd": 9.99,
                        "description": "Perfect for testing",
                        "recommended": False
                    }
                ],
                "total_packages": 4
            }
        }

# ===========================================
# RESPONSE MODELS
# ===========================================

class CheckoutSessionResponse(BaseModel):
    """Response model for checkout session creation"""
    success: bool = Field(True, description="Whether the session was created successfully")
    session_id: str = Field(..., description="Stripe session ID")
    checkout_url: str = Field(..., description="URL to redirect user to Stripe Checkout")
    expires_at: Optional[int] = Field(None, description="Session expiration timestamp")
    amount_total: Optional[int] = Field(None, description="Total amount in cents")
    currency: str = Field("usd", description="Currency code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "cs_test_a1b2c3d4e5f6g7h8i9j0",
                "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
                "expires_at": 1692806400,
                "amount_total": 3999,
                "currency": "usd"
            }
        }

class SessionRetrieveResponse(BaseModel):
    """Response model for session retrieval"""
    success: bool = Field(True, description="Whether the session was retrieved successfully")
    session_id: str = Field(..., description="Stripe session ID")
    payment_status: PaymentStatus = Field(..., description="Payment status")
    customer_email: Optional[str] = Field(None, description="Customer email")
    amount_total: Optional[int] = Field(None, description="Total amount in cents")
    currency: str = Field("usd", description="Currency code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    created: Optional[int] = Field(None, description="Creation timestamp")
    expires_at: Optional[int] = Field(None, description="Expiration timestamp")

# ===========================================
# DATABASE MODELS
# ===========================================

class StripeCustomer(BaseModel):
    """Model for stripe_customers table"""
    id: str = Field(..., description="Internal customer record ID")
    user_id: str = Field(..., description="Supabase user ID")
    stripe_customer_id: str = Field(..., description="Stripe customer ID")
    email: EmailStr = Field(..., description="Customer email")
    name: Optional[str] = Field(None, description="Customer name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class StripeTransaction(BaseModel):
    """Model for stripe_transactions table"""
    id: str = Field(..., description="Internal transaction ID")
    user_id: str = Field(..., description="Supabase user ID")
    stripe_session_id: str = Field(..., description="Stripe session ID")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    stripe_payment_intent_id: Optional[str] = Field(None, description="Stripe PaymentIntent ID")
    
    # Transaction details
    package_type: TokenPackageType = Field(..., description="Token package type")
    tokens_purchased: int = Field(..., gt=0, description="Number of tokens purchased")
    amount_cents: int = Field(..., gt=0, description="Amount paid in cents")
    currency: str = Field("usd", description="Payment currency")
    
    # Status
    status: TransactionStatus = Field(..., description="Internal transaction status")
    payment_status: Optional[PaymentStatus] = Field(None, description="Stripe payment status")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Internal metadata")
    stripe_metadata: Dict[str, Any] = Field(default_factory=dict, description="Stripe metadata")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

# ===========================================
# TRANSACTION HISTORY MODELS
# ===========================================

class TransactionHistoryItem(BaseModel):
    """Model for individual transaction in history"""
    id: str = Field(..., description="Transaction ID")
    package_type: TokenPackageType = Field(..., description="Package type purchased")
    tokens_purchased: int = Field(..., description="Number of tokens purchased")
    amount_cents: int = Field(..., description="Amount paid in cents")
    amount_usd: float = Field(..., description="Amount paid in USD")
    status: TransactionStatus = Field(..., description="Transaction status")
    created_at: datetime = Field(..., description="Purchase date")
    completed_at: Optional[datetime] = Field(None, description="Completion date")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-string",
                "package_type": "standard",
                "tokens_purchased": 50,
                "amount_cents": 3999,
                "amount_usd": 39.99,
                "status": "completed",
                "created_at": "2025-08-23T10:00:00Z",
                "completed_at": "2025-08-23T10:00:30Z"
            }
        }

class TransactionHistoryResponse(BaseModel):
    """Response model for transaction history"""
    success: bool = Field(True, description="Whether the request was successful")
    transactions: List[TransactionHistoryItem] = Field(..., description="List of transactions")
    total_transactions: int = Field(..., description="Total number of transactions")
    total_spent_usd: float = Field(..., description="Total amount spent in USD")
    total_tokens_purchased: int = Field(..., description="Total tokens purchased")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "transactions": [],
                "total_transactions": 5,
                "total_spent_usd": 199.95,
                "total_tokens_purchased": 250
            }
        }

# ===========================================
# WEBHOOK MODELS
# ===========================================

class WebhookEventData(BaseModel):
    """Model for Stripe webhook event data"""
    id: str = Field(..., description="Stripe event ID")
    type: str = Field(..., description="Event type (e.g., checkout.session.completed)")
    data: Dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")
    livemode: bool = Field(..., description="Whether event is from live mode")
    api_version: Optional[str] = Field(None, description="Stripe API version")

class WebhookResponse(BaseModel):
    """Response model for webhook processing"""
    received: bool = Field(True, description="Whether webhook was received")
    processed: bool = Field(..., description="Whether webhook was processed successfully")
    event_type: str = Field(..., description="Type of event processed")
    message: Optional[str] = Field(None, description="Processing message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "received": True,
                "processed": True,
                "event_type": "checkout.session.completed",
                "message": "Transaction completed and tokens added successfully"
            }
        }

# ===========================================
# ERROR MODELS
# ===========================================

class StripeErrorResponse(BaseModel):
    """Model for Stripe-related error responses"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Stripe error code if applicable")
    error_type: Optional[str] = Field(None, description="Stripe error type")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Your card was declined.",
                "error_code": "card_declined",
                "error_type": "card_error",
                "details": {
                    "decline_code": "insufficient_funds"
                }
            }
        }

# ===========================================
# ANALYTICS MODELS
# ===========================================

class RevenueAnalytics(BaseModel):
    """Model for revenue analytics data"""
    period: str = Field(..., description="Time period (daily/monthly)")
    date: datetime = Field(..., description="Date/period start")
    completed_transactions: int = Field(..., description="Number of completed transactions")
    revenue_cents: int = Field(..., description="Total revenue in cents")
    revenue_usd: float = Field(..., description="Total revenue in USD")
    tokens_sold: int = Field(..., description="Total tokens sold")
    avg_order_value_usd: float = Field(..., description="Average order value in USD")

class PackageAnalytics(BaseModel):
    """Model for package popularity analytics"""
    package_type: TokenPackageType = Field(..., description="Package type")
    total_purchases: int = Field(..., description="Total purchase attempts")
    completed_purchases: int = Field(..., description="Completed purchases")
    pending_purchases: int = Field(..., description="Pending purchases")
    failed_purchases: int = Field(..., description="Failed purchases")
    tokens_sold: int = Field(..., description="Total tokens sold")
    revenue_cents: int = Field(..., description="Revenue in cents")
    avg_order_value_usd: Optional[float] = Field(None, description="Average order value in USD")