"""
Stripe Service - Token Purchase System
Handles all Stripe payment processing operations
"""

import stripe
import logging
from typing import Dict, Any, Optional
from app.config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

class StripeService:
    """Service class for handling Stripe payment operations"""
    
    @staticmethod
    def create_checkout_session(
        package_type: str,
        tokens: int,
        amount_cents: int,
        user_id: str,
        user_email: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session for token purchase
        
        Args:
            package_type: Type of token package (starter, standard, pro, business)
            tokens: Number of tokens to purchase
            amount_cents: Amount in cents (e.g., 999 for $9.99)
            user_id: User ID from Supabase
            user_email: User email for receipt
            success_url: Optional custom success URL
            cancel_url: Optional custom cancel URL
            
        Returns:
            Dict containing session info (id, url, etc.)
        """
        try:
            # Use provided URLs or defaults
            success_redirect = success_url or settings.STRIPE_SUCCESS_URL
            cancel_redirect = cancel_url or settings.STRIPE_CANCEL_URL
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'{package_type.capitalize()} Token Package',
                                'description': f'{tokens} video rendering tokens (≈ {tokens} minutes of video)',
                                'images': [],  # Optional: add product images
                            },
                            'unit_amount': amount_cents,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=f'{success_redirect}?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=cancel_redirect,
                customer_email=user_email,
                metadata={
                    'user_id': user_id,
                    'package_type': package_type,
                    'tokens_quantity': str(tokens),
                    'source': 'video_platform_token_purchase'
                },
                # Optional: Configure payment method options
                payment_intent_data={
                    'metadata': {
                        'user_id': user_id,
                        'package_type': package_type,
                        'tokens_quantity': str(tokens),
                    }
                },
                expires_at=int((stripe.util.convert_to_stripe_timestamp(
                    stripe.util.datetime.datetime.utcnow() + 
                    stripe.util.datetime.timedelta(hours=1)
                )))  # Session expires in 1 hour
            )
            
            logger.info(f"Stripe checkout session created", extra={
                'user_id': user_id,
                'session_id': session.id,
                'package_type': package_type,
                'tokens': tokens,
                'amount_cents': amount_cents
            })
            
            return {
                'id': session.id,
                'url': session.url,
                'expires_at': session.expires_at,
                'customer_email': session.customer_email,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'payment_status': session.payment_status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}", extra={
                'user_id': user_id,
                'package_type': package_type,
                'error_code': getattr(e, 'code', 'unknown'),
                'error_type': type(e).__name__
            })
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {str(e)}", extra={
                'user_id': user_id,
                'package_type': package_type
            })
            raise

    @staticmethod
    def retrieve_session(session_id: str) -> Dict[str, Any]:
        """
        Retrieve a Stripe Checkout Session by ID
        
        Args:
            session_id: Stripe session ID
            
        Returns:
            Dict containing session details
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            return {
                'id': session.id,
                'payment_status': session.payment_status,
                'customer_email': session.customer_email,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'metadata': session.metadata,
                'created': session.created,
                'expires_at': session.expires_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving session: {str(e)}", extra={
                'session_id': session_id,
                'error_code': getattr(e, 'code', 'unknown')
            })
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving session: {str(e)}", extra={
                'session_id': session_id
            })
            raise

    @staticmethod
    def create_customer(user_email: str, user_name: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Stripe Customer for future payments
        
        Args:
            user_email: Customer email
            user_name: Optional customer name
            user_id: Optional internal user ID
            
        Returns:
            Dict containing customer details
        """
        try:
            customer_data = {
                'email': user_email,
                'metadata': {}
            }
            
            if user_name:
                customer_data['name'] = user_name
                
            if user_id:
                customer_data['metadata']['user_id'] = user_id
            
            customer = stripe.Customer.create(**customer_data)
            
            logger.info(f"Stripe customer created", extra={
                'customer_id': customer.id,
                'email': user_email,
                'user_id': user_id
            })
            
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'created': customer.created,
                'metadata': customer.metadata
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}", extra={
                'email': user_email,
                'error_code': getattr(e, 'code', 'unknown')
            })
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {str(e)}", extra={
                'email': user_email
            })
            raise

    @staticmethod
    def list_payment_methods(customer_id: str) -> list:
        """
        List payment methods for a customer
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            List of payment methods
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return payment_methods.data
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing payment methods: {str(e)}", extra={
                'customer_id': customer_id,
                'error_code': getattr(e, 'code', 'unknown')
            })
            raise

    @staticmethod
    def validate_webhook_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Validate Stripe webhook signature
        
        Args:
            payload: Raw webhook payload
            sig_header: Stripe signature header
            
        Returns:
            Validated event data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            
            logger.info(f"Webhook signature validated", extra={
                'event_id': event['id'],
                'event_type': event['type']
            })
            
            return event
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise