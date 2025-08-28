"""
Stripe Webhook Service
Handles processing of Stripe webhook events
"""

import logging
from typing import Dict, Any, Optional
import traceback

from app.database.supabase_client import get_supabase_client
from app.services.stripe_service import StripeService

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for processing Stripe webhook events"""
    
    @staticmethod
    async def process_checkout_session_completed(event_data: Dict[str, Any]) -> bool:
        """
        Process checkout.session.completed webhook event
        
        This event is triggered when a customer successfully completes
        a Stripe Checkout session for token purchase.
        
        Args:
            event_data: Stripe event data
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            session = event_data["data"]["object"]
            session_id = session["id"]
            metadata = session.get("metadata", {})
            user_id = metadata.get("user_id")
            
            logger.info("Processing checkout.session.completed", extra={
                "session_id": session_id,
                "user_id": user_id,
                "amount_total": session.get("amount_total"),
                "customer_email": session.get("customer_email")
            })
            
            if not user_id:
                logger.error("Missing user_id in session metadata", extra={
                    "session_id": session_id,
                    "metadata": metadata
                })
                return False
            
            # Retrieve full session details from Stripe
            try:
                full_session = StripeService.retrieve_session(session_id)
            except Exception as e:
                logger.error(f"Failed to retrieve session from Stripe: {str(e)}", extra={
                    "session_id": session_id
                })
                return False
            
            # Update Stripe customer record if needed
            customer_email = session.get("customer_email")
            customer_name = session.get("customer_details", {}).get("name")
            
            if customer_email:
                await WebhookService._upsert_stripe_customer(
                    user_id=user_id,
                    stripe_customer_id=session.get("customer"),
                    customer_email=customer_email,
                    customer_name=customer_name
                )
            
            # Complete the transaction using database function
            supabase = get_supabase_client()
            
            # Call the complete_stripe_transaction function
            result = supabase.rpc("complete_stripe_transaction", {
                "session_id": session_id,
                "user_uuid": user_id
            }).execute()
            
            if result.data:
                logger.info("Transaction completed successfully via webhook", extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "tokens_added": metadata.get("tokens_quantity")
                })
                
                # Log the webhook event for audit trail
                await WebhookService._log_webhook_event(
                    event_type="checkout.session.completed",
                    stripe_event_id=event_data.get("id"),
                    user_id=user_id,
                    session_id=session_id,
                    success=True,
                    metadata={
                        "amount_total": session.get("amount_total"),
                        "currency": session.get("currency"),
                        "customer_email": customer_email,
                        "tokens_purchased": metadata.get("tokens_quantity")
                    }
                )
                
                return True
            else:
                logger.error("Database function failed to complete transaction", extra={
                    "session_id": session_id,
                    "user_id": user_id
                })
                
                await WebhookService._log_webhook_event(
                    event_type="checkout.session.completed",
                    stripe_event_id=event_data.get("id"),
                    user_id=user_id,
                    session_id=session_id,
                    success=False,
                    error_message="Database function failed"
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error processing checkout.session.completed: {str(e)}", extra={
                "session_id": session.get("id"),
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            
            await WebhookService._log_webhook_event(
                event_type="checkout.session.completed",
                stripe_event_id=event_data.get("id"),
                session_id=session.get("id"),
                success=False,
                error_message=str(e)
            )
            
            return False
    
    @staticmethod
    async def process_payment_intent_succeeded(event_data: Dict[str, Any]) -> bool:
        """
        Process payment_intent.succeeded webhook event
        
        Args:
            event_data: Stripe event data
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            payment_intent = event_data["data"]["object"]
            payment_intent_id = payment_intent["id"]
            metadata = payment_intent.get("metadata", {})
            
            logger.info("Processing payment_intent.succeeded", extra={
                "payment_intent_id": payment_intent_id,
                "amount": payment_intent.get("amount"),
                "currency": payment_intent.get("currency")
            })
            
            # Update transaction with payment_intent_id
            supabase = get_supabase_client()
            
            update_result = supabase.table("stripe_transactions") \
                .update({
                    "stripe_payment_intent_id": payment_intent_id,
                    "payment_status": "paid",
                    "updated_at": "NOW()"
                }) \
                .eq("stripe_session_id", metadata.get("session_id")) \
                .execute()
            
            if update_result.data:
                logger.info("Payment intent updated successfully", extra={
                    "payment_intent_id": payment_intent_id
                })
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing payment_intent.succeeded: {str(e)}", extra={
                "payment_intent_id": payment_intent.get("id"),
                "error": str(e)
            })
            return False
    
    @staticmethod
    async def process_payment_intent_payment_failed(event_data: Dict[str, Any]) -> bool:
        """
        Process payment_intent.payment_failed webhook event
        
        Args:
            event_data: Stripe event data
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            payment_intent = event_data["data"]["object"]
            payment_intent_id = payment_intent["id"]
            
            logger.warning("Processing payment_intent.payment_failed", extra={
                "payment_intent_id": payment_intent_id,
                "failure_code": payment_intent.get("last_payment_error", {}).get("code"),
                "failure_message": payment_intent.get("last_payment_error", {}).get("message")
            })
            
            # Update transaction status to failed
            supabase = get_supabase_client()
            
            update_result = supabase.table("stripe_transactions") \
                .update({
                    "stripe_payment_intent_id": payment_intent_id,
                    "status": "failed",
                    "payment_status": "failed",
                    "updated_at": "NOW()",
                    "metadata": {
                        "failure_code": payment_intent.get("last_payment_error", {}).get("code"),
                        "failure_message": payment_intent.get("last_payment_error", {}).get("message")
                    }
                }) \
                .eq("stripe_payment_intent_id", payment_intent_id) \
                .execute()
            
            if update_result.data:
                logger.info("Failed payment updated successfully", extra={
                    "payment_intent_id": payment_intent_id
                })
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing payment_intent.payment_failed: {str(e)}", extra={
                "payment_intent_id": payment_intent.get("id"),
                "error": str(e)
            })
            return False
    
    @staticmethod
    async def _upsert_stripe_customer(
        user_id: str,
        stripe_customer_id: Optional[str],
        customer_email: str,
        customer_name: Optional[str] = None
    ) -> bool:
        """
        Create or update Stripe customer record
        
        Args:
            user_id: Internal user ID
            stripe_customer_id: Stripe customer ID
            customer_email: Customer email
            customer_name: Optional customer name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not stripe_customer_id:
                return True  # Nothing to update
            
            supabase = get_supabase_client()
            
            # Use the database function for upsert
            result = supabase.rpc("upsert_stripe_customer", {
                "user_uuid": user_id,
                "stripe_customer_id": stripe_customer_id,
                "customer_email": customer_email,
                "customer_name": customer_name
            }).execute()
            
            if result.data:
                logger.info("Stripe customer record upserted", extra={
                    "user_id": user_id,
                    "stripe_customer_id": stripe_customer_id,
                    "email": customer_email
                })
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error upserting Stripe customer: {str(e)}", extra={
                "user_id": user_id,
                "stripe_customer_id": stripe_customer_id,
                "email": customer_email
            })
            return False
    
    @staticmethod
    async def _log_webhook_event(
        event_type: str,
        stripe_event_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log webhook event for audit trail
        
        Args:
            event_type: Type of webhook event
            stripe_event_id: Stripe event ID
            user_id: Internal user ID
            session_id: Stripe session ID
            success: Whether processing was successful
            error_message: Optional error message
            metadata: Optional additional metadata
        """
        try:
            supabase = get_supabase_client()
            
            log_metadata = {
                "success": success,
                **(metadata or {})
            }
            
            if error_message:
                log_metadata["error"] = error_message
            
            # Use the database function for logging
            supabase.rpc("log_stripe_event", {
                "event_type": event_type,
                "stripe_event_id": stripe_event_id,
                "user_uuid": user_id,
                "session_id": session_id,
                "metadata": log_metadata
            }).execute()
            
            logger.debug("Webhook event logged", extra={
                "event_type": event_type,
                "stripe_event_id": stripe_event_id,
                "success": success
            })
            
        except Exception as e:
            # Don't fail webhook processing if logging fails
            logger.warning(f"Failed to log webhook event: {str(e)}", extra={
                "event_type": event_type,
                "stripe_event_id": stripe_event_id
            })

# Event handler mapping
WEBHOOK_HANDLERS = {
    "checkout.session.completed": WebhookService.process_checkout_session_completed,
    "payment_intent.succeeded": WebhookService.process_payment_intent_succeeded,
    "payment_intent.payment_failed": WebhookService.process_payment_intent_payment_failed,
    # Add more handlers as needed
}

async def process_stripe_webhook(event_data: Dict[str, Any]) -> bool:
    """
    Process Stripe webhook event by routing to appropriate handler
    
    Args:
        event_data: Complete Stripe event data
        
    Returns:
        True if processed successfully, False otherwise
    """
    event_type = event_data.get("type")
    
    if event_type in WEBHOOK_HANDLERS:
        handler = WEBHOOK_HANDLERS[event_type]
        return await handler(event_data)
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")
        return False