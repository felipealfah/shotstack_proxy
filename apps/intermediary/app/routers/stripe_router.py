"""
Stripe Payment Router - API Endpoints for Stripe Integration
Handles token purchase operations via Stripe Checkout
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import traceback
from pydantic import ValidationError

from app.auth.dependencies import get_current_user
from app.services.stripe_service import StripeService
from app.services.webhook_service import process_stripe_webhook
from app.models.stripe_models import (
    TokenPackage,
    TokenPackageList,
    TokenPackageRequest,
    CheckoutSessionResponse,
    SessionRetrieveResponse,
    TransactionHistoryResponse,
    WebhookResponse,
    StripeErrorResponse,
    TokenPackageType
)
from app.database.supabase_client import get_supabase_client
from app.config import settings

router = APIRouter(prefix="/stripe", tags=["Stripe Payments"])
logger = logging.getLogger(__name__)

# Import token packages from centralized configuration
from app.token_packages import TOKEN_PACKAGES, get_all_packages, get_package_by_type

# ===========================================
# ENDPOINT: LIST TOKEN PACKAGES
# ===========================================

@router.get("/packages", response_model=TokenPackageList)
async def list_token_packages(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TokenPackageList:
    """
    List available token packages for purchase
    
    Returns all available token packages with pricing and details.
    Requires authentication but no specific permissions.
    """
    try:
        logger.info("Listing token packages", extra={"user_id": current_user.get("id")})
        
        packages = get_all_packages()
        
        return TokenPackageList(
            packages=packages,
            total_packages=len(packages)
        )
        
    except Exception as e:
        logger.error(f"Error listing token packages: {str(e)}", extra={
            "user_id": current_user.get("id"),
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token packages"
        )

# ===========================================
# ENDPOINT: CREATE CHECKOUT SESSION
# ===========================================

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: TokenPackageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CheckoutSessionResponse:
    """
    Create a Stripe Checkout Session for token purchase
    
    Creates a secure Stripe Checkout session and stores the transaction
    in the database as 'pending' status.
    """
    try:
        user_id = current_user.get("id")
        user_email = current_user.get("email")
        
        logger.info("Creating Stripe checkout session", extra={
            "user_id": user_id,
            "package_type": request.package_type.value,
            "email": user_email
        })
        
        # Get package details
        try:
            package = get_package_by_type(request.package_type)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid package type: {request.package_type}"
            )
        
        # Create Stripe checkout session
        session_data = StripeService.create_checkout_session(
            package_type=request.package_type.value,
            tokens=package.tokens,
            amount_cents=package.amount_cents,
            user_id=user_id,
            user_email=user_email,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        # Store transaction in database as 'pending'
        supabase = get_supabase_client()
        
        transaction_data = {
            "user_id": user_id,
            "stripe_session_id": session_data["id"],
            "stripe_customer_id": session_data.get("customer_email"),
            "package_type": request.package_type.value,
            "tokens_purchased": package.tokens,
            "amount_cents": package.amount_cents,
            "currency": session_data.get("currency", "usd"),
            "status": "pending",
            "payment_status": session_data.get("payment_status"),
            "metadata": {
                "package_description": package.description,
                "success_url": request.success_url,
                "cancel_url": request.cancel_url
            }
        }
        
        result = supabase.table("stripe_transactions").insert(transaction_data).execute()
        
        if not result.data:
            logger.error("Failed to store transaction in database", extra={
                "user_id": user_id,
                "session_id": session_data["id"]
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create transaction record"
            )
        
        logger.info("Checkout session created successfully", extra={
            "user_id": user_id,
            "session_id": session_data["id"],
            "transaction_id": result.data[0]["id"]
        })
        
        return CheckoutSessionResponse(
            success=True,
            session_id=session_data["id"],
            checkout_url=session_data["url"],
            expires_at=session_data.get("expires_at"),
            amount_total=session_data.get("amount_total"),
            currency=session_data.get("currency", "usd")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}", extra={
            "user_id": current_user.get("id"),
            "package_type": request.package_type.value,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

# ===========================================
# ENDPOINT: RETRIEVE SESSION STATUS
# ===========================================

@router.get("/session/{session_id}", response_model=SessionRetrieveResponse)
async def get_session_status(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SessionRetrieveResponse:
    """
    Retrieve Stripe Checkout Session status
    
    Allows users to check the status of their payment session.
    Only returns sessions that belong to the authenticated user.
    """
    try:
        user_id = current_user.get("id")
        
        logger.info("Retrieving session status", extra={
            "user_id": user_id,
            "session_id": session_id
        })
        
        # Verify session belongs to user
        supabase = get_supabase_client()
        transaction_query = supabase.table("stripe_transactions").select("*").eq("stripe_session_id", session_id).eq("user_id", user_id).execute()
        
        if not transaction_query.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        # Retrieve session from Stripe
        session_data = StripeService.retrieve_session(session_id)
        
        return SessionRetrieveResponse(
            success=True,
            session_id=session_data["id"],
            payment_status=session_data["payment_status"],
            customer_email=session_data.get("customer_email"),
            amount_total=session_data.get("amount_total"),
            currency=session_data.get("currency", "usd"),
            metadata=session_data.get("metadata", {}),
            created=session_data.get("created"),
            expires_at=session_data.get("expires_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session status: {str(e)}", extra={
            "user_id": current_user.get("id"),
            "session_id": session_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session status"
        )

# ===========================================
# ENDPOINT: TRANSACTION HISTORY
# ===========================================

@router.get("/transactions", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TransactionHistoryResponse:
    """
    Get user's Stripe transaction history
    
    Returns paginated list of user's token purchase transactions.
    """
    try:
        user_id = current_user.get("id")
        
        logger.info("Retrieving transaction history", extra={
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        })
        
        supabase = get_supabase_client()
        
        # Get transactions with pagination
        transactions_query = supabase.table("stripe_transactions") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        # Get total count
        count_query = supabase.table("stripe_transactions") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()
        
        total_count = count_query.count or 0
        
        # Calculate totals
        totals_query = supabase.table("stripe_transactions") \
            .select("amount_cents, tokens_purchased") \
            .eq("user_id", user_id) \
            .eq("status", "completed") \
            .execute()
        
        total_spent_cents = sum(t["amount_cents"] for t in totals_query.data)
        total_tokens_purchased = sum(t["tokens_purchased"] for t in totals_query.data)
        
        # Format transaction data
        transactions = []
        for tx in transactions_query.data:
            transactions.append({
                "id": tx["id"],
                "package_type": tx["package_type"],
                "tokens_purchased": tx["tokens_purchased"],
                "amount_cents": tx["amount_cents"],
                "amount_usd": tx["amount_cents"] / 100,
                "status": tx["status"],
                "created_at": tx["created_at"],
                "completed_at": tx.get("completed_at")
            })
        
        return TransactionHistoryResponse(
            success=True,
            transactions=transactions,
            total_transactions=total_count,
            total_spent_usd=total_spent_cents / 100,
            total_tokens_purchased=total_tokens_purchased
        )
        
    except Exception as e:
        logger.error(f"Error retrieving transaction history: {str(e)}", extra={
            "user_id": current_user.get("id"),
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction history"
        )

# ===========================================
# ENDPOINT: STRIPE WEBHOOK
# ===========================================

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for payment events
    
    Processes checkout.session.completed events to complete token purchases.
    Must validate webhook signature for security.
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            logger.warning("Webhook received without signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Validate webhook signature
        event = StripeService.validate_webhook_signature(payload, sig_header)
        
        logger.info(f"Webhook received", extra={
            "event_id": event["id"],
            "event_type": event["type"]
        })
        
        # Process webhook using dedicated service
        success = await process_stripe_webhook(event)
        
        if success:
            return WebhookResponse(
                received=True,
                processed=True,
                event_type=event["type"],
                message=f"Event {event['type']} processed successfully"
            )
        else:
            return WebhookResponse(
                received=True,
                processed=False,
                event_type=event["type"],
                message=f"Failed to process event {event['type']}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

# ===========================================
# ERROR HANDLERS
# Note: Exception handlers should be registered in main.py, not on routers
# ===========================================