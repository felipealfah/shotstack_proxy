"""
Token Package Configuration - Central definition of available token packages
Provides different token packages that users can purchase via Stripe
"""

from typing import List, Dict, Any, Optional
from enum import Enum

class TokenPackageType(Enum):
    """Token package types for different use cases"""
    STARTER = "starter"
    BASIC = "basic" 
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

# Available token packages configuration
TOKEN_PACKAGES = {
    TokenPackageType.STARTER: {
        "id": "starter_100",
        "name": "Starter Pack",
        "description": "Perfect for trying out video rendering",
        "tokens": 100,
        "price_cents": 999,  # $9.99
        "currency": "usd",
        "features": [
            "100 video render tokens",
            "Basic support",
            "Standard quality renders"
        ],
        "stripe_price_id": "price_starter_100"  # Replace with actual Stripe price ID
    },
    TokenPackageType.BASIC: {
        "id": "basic_500", 
        "name": "Basic Pack",
        "description": "Great for small projects and regular use",
        "tokens": 500,
        "price_cents": 3999,  # $39.99
        "currency": "usd",
        "features": [
            "500 video render tokens",
            "Email support",
            "High quality renders",
            "Priority processing"
        ],
        "stripe_price_id": "price_basic_500"  # Replace with actual Stripe price ID
    },
    TokenPackageType.PROFESSIONAL: {
        "id": "professional_2000",
        "name": "Professional Pack", 
        "description": "Ideal for businesses and content creators",
        "tokens": 2000,
        "price_cents": 14999,  # $149.99
        "currency": "usd", 
        "features": [
            "2,000 video render tokens",
            "Priority support",
            "Premium quality renders",
            "Advanced processing",
            "Extended storage"
        ],
        "stripe_price_id": "price_professional_2000"  # Replace with actual Stripe price ID
    },
    TokenPackageType.ENTERPRISE: {
        "id": "enterprise_10000",
        "name": "Enterprise Pack",
        "description": "For large-scale video production needs",
        "tokens": 10000,
        "price_cents": 49999,  # $499.99
        "currency": "usd",
        "features": [
            "10,000 video render tokens",
            "24/7 dedicated support",
            "Ultra-high quality renders", 
            "Custom processing options",
            "Extended storage & backup",
            "API rate limit increases"
        ],
        "stripe_price_id": "price_enterprise_10000"  # Replace with actual Stripe price ID
    }
}

def get_all_packages() -> List[Dict[str, Any]]:
    """
    Get all available token packages
    
    Returns:
        List of all token package configurations
    """
    return list(TOKEN_PACKAGES.values())

def get_package_by_type(package_type: TokenPackageType) -> Optional[Dict[str, Any]]:
    """
    Get a specific token package by type
    
    Args:
        package_type: The type of package to retrieve
        
    Returns:
        Package configuration dict or None if not found
    """
    return TOKEN_PACKAGES.get(package_type)

def get_package_by_id(package_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a token package by its ID
    
    Args:
        package_id: The package ID to search for
        
    Returns:
        Package configuration dict or None if not found
    """
    for package in TOKEN_PACKAGES.values():
        if package["id"] == package_id:
            return package
    return None

def get_package_by_stripe_price_id(stripe_price_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a token package by its Stripe price ID
    
    Args:
        stripe_price_id: The Stripe price ID to search for
        
    Returns:
        Package configuration dict or None if not found
    """
    for package in TOKEN_PACKAGES.values():
        if package["stripe_price_id"] == stripe_price_id:
            return package
    return None

def validate_package_id(package_id: str) -> bool:
    """
    Validate if a package ID exists
    
    Args:
        package_id: The package ID to validate
        
    Returns:
        True if package exists, False otherwise
    """
    return get_package_by_id(package_id) is not None

def get_package_price(package_id: str) -> Optional[int]:
    """
    Get the price in cents for a package
    
    Args:
        package_id: The package ID
        
    Returns:
        Price in cents or None if package not found
    """
    package = get_package_by_id(package_id)
    return package["price_cents"] if package else None

def get_package_tokens(package_id: str) -> Optional[int]:
    """
    Get the number of tokens for a package
    
    Args:
        package_id: The package ID
        
    Returns:
        Number of tokens or None if package not found  
    """
    package = get_package_by_id(package_id)
    return package["tokens"] if package else None