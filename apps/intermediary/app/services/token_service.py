from typing import Optional
from supabase import create_client, Client
import logging
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    async def get_user_tokens(self, user_id: str) -> int:
        """
        Get user's current token balance from Supabase
        """
        try:
            response = self.supabase.table('credit_balance').select('balance').eq('user_id', user_id).execute()
            
            if response.data:
                return response.data[0].get('balance', 0)
            else:
                logger.warning(f"User {user_id} not found in credit_balance table")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting tokens for user {user_id}: {e}")
            return 0
    
    async def consume_tokens(self, user_id: str, amount: int, description: str = None, api_key_id: str = None) -> bool:
        """
        Consume tokens for a user and create transaction record
        """
        try:
            # Get current balance
            current_balance = await self.get_user_tokens(user_id)
            
            # Check if user has enough tokens
            if current_balance < amount:
                logger.warning(f"Insufficient tokens for user {user_id}. Required: {amount}, Available: {current_balance}")
                return False
            
            new_balance = current_balance - amount
            
            # Update user balance
            update_response = self.supabase.table('credit_balance').update({
                'balance': new_balance
            }).eq('user_id', user_id).execute()
            
            if not update_response.data:
                logger.error(f"Failed to update token balance for user {user_id}")
                return False
            
            # Create transaction record
            transaction_data = {
                'user_id': user_id,
                'amount': -amount,  # Negative for consumption
                'transaction_type': 'consumption',
                'description': description or f'Video rendering - {amount} tokens consumed',
                'balance_before': current_balance,
                'balance_after': new_balance,
                'api_key_id': api_key_id
            }
            
            transaction_response = self.supabase.table('token_transactions').insert(transaction_data).execute()
            
            if not transaction_response.data:
                logger.warning(f"Failed to create transaction record for user {user_id}")
                # Don't return False here as the balance was already updated
            
            logger.info(f"Successfully consumed {amount} tokens for user {user_id}. New balance: {new_balance}")
            return True
            
        except Exception as e:
            logger.error(f"Error consuming tokens for user {user_id}: {e}")
            return False
    
    async def add_tokens(self, user_id: str, amount: int, description: str = None, transaction_type: str = 'purchase') -> bool:
        """
        Add tokens to a user's balance and create transaction record
        """
        try:
            # Get current balance
            current_balance = await self.get_user_tokens(user_id)
            new_balance = current_balance + amount
            
            # Update user balance
            update_response = self.supabase.table('credit_balance').update({
                'balance': new_balance
            }).eq('user_id', user_id).execute()
            
            if not update_response.data:
                logger.error(f"Failed to update token balance for user {user_id}")
                return False
            
            # Create transaction record
            transaction_data = {
                'user_id': user_id,
                'amount': amount,  # Positive for addition
                'transaction_type': transaction_type,
                'description': description or f'Token {transaction_type} - {amount} tokens added',
                'balance_before': current_balance,
                'balance_after': new_balance
            }
            
            transaction_response = self.supabase.table('token_transactions').insert(transaction_data).execute()
            
            if not transaction_response.data:
                logger.warning(f"Failed to create transaction record for user {user_id}")
                # Don't return False here as the balance was already updated
            
            logger.info(f"Successfully added {amount} tokens for user {user_id}. New balance: {new_balance}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding tokens for user {user_id}: {e}")
            return False
    
    async def calculate_tokens_for_duration(self, duration_seconds: int) -> int:
        """
        Calculate required tokens based on video duration
        Business rule: 1 token = 1 minute of video
        """
        # Convert seconds to minutes and round up
        import math
        duration_minutes = math.ceil(duration_seconds / 60)
        return max(1, duration_minutes)  # Minimum 1 token
    
    async def get_user_transaction_history(self, user_id: str, limit: int = 50) -> list:
        """
        Get user's token transaction history
        """
        try:
            response = self.supabase.table('token_transactions').select('*').eq(
                'user_id', user_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting transaction history for user {user_id}: {e}")
            return []