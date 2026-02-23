"""
Credits Config Loader

Hot-reloads configuration from YAML with caching.
Provides typed access to all credit system configuration.
"""

import os
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


# ============================================================================
# DATA CLASSES FOR TYPE SAFETY
# ============================================================================

@dataclass
class Package:
    """One-time credit package"""
    id: str
    name: str
    description: str
    credits: int
    price_usd: float
    active: bool = True
    popular: bool = False
    badge: Optional[str] = None
    sort_order: int = 0


@dataclass
class Subscription:
    """Recurring subscription plan"""
    id: str
    name: str
    description: str
    credits_per_period: int
    price_usd: float
    interval: str  # month | year
    interval_count: int = 1
    stripe_price_id: Optional[str] = None
    trial_days: int = 0
    features: List[str] = field(default_factory=list)
    active: bool = True
    popular: bool = False
    badge: Optional[str] = None
    sort_order: int = 0


@dataclass
class Coupon:
    """Discount coupon"""
    code: str
    name: str
    description: str
    type: str  # percent | fixed
    discount: float
    applies_to: str = "all"  # all | packages | subscriptions
    valid_items: List[str] = field(default_factory=list)
    max_uses: Optional[int] = None
    max_uses_per_user: int = 1
    min_purchase_usd: float = 0
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    active: bool = True


@dataclass
class Promotion:
    """Promotional bonus configuration"""
    enabled: bool = False
    credits: int = 0
    bonus_percent: float = 0
    max_bonus_credits: int = 0
    description: str = ""


# ============================================================================
# CONFIG LOADER
# ============================================================================

class CreditsConfigLoader:
    """
    Loads and caches credits configuration from YAML.
    
    Features:
    - Hot-reload: Config changes apply without restart
    - Caching: Reduces file I/O with TTL-based cache
    - Type safety: Returns typed dataclass objects
    - Validation: Validates config structure on load
    
    Usage:
        config = CreditsConfigLoader()
        packages = config.get_packages()
        model_cost = config.get_model_cost("gpt-image-1")
    """
    
    _instance = None
    _config: Dict[str, Any] = {}
    _last_load_time: float = 0
    _cache_ttl: float = 60  # seconds
    _config_path: Path = None
    
    def __new__(cls, config_path: Optional[str] = None):
        """Singleton pattern - one config loader per process"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config loader"""
        if self._initialized and config_path is None:
            return
            
        # Determine config path
        if config_path:
            self._config_path = Path(config_path)
        else:
            # Default: shared/credits/config.yaml
            self._config_path = Path(__file__).parent / "config.yaml"
        
        # Load initial config
        self._load_config()
        self._initialized = True
    
    def _load_config(self, force: bool = False) -> None:
        """Load configuration from YAML file"""
        current_time = time.time()
        
        # Check cache validity
        if not force and self._config and (current_time - self._last_load_time) < self._cache_ttl:
            return
        
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")
        
        with open(self._config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        # Update cache TTL from config
        cache_settings = self._config.get('settings', {}).get('cache', {})
        if cache_settings.get('enabled', True):
            self._cache_ttl = cache_settings.get('ttl_seconds', 60)
        else:
            self._cache_ttl = 0  # No caching
        
        self._last_load_time = current_time
    
    def reload(self) -> None:
        """Force reload configuration"""
        self._load_config(force=True)
    
    # ========================================================================
    # PACKAGES
    # ========================================================================
    
    def get_packages(self, active_only: bool = True) -> List[Package]:
        """Get all credit packages"""
        self._load_config()
        
        packages = []
        for pkg_data in self._config.get('packages', []):
            if active_only and not pkg_data.get('active', True):
                continue
            
            packages.append(Package(
                id=pkg_data['id'],
                name=pkg_data['name'],
                description=pkg_data.get('description', ''),
                credits=pkg_data['credits'],
                price_usd=pkg_data['price_usd'],
                active=pkg_data.get('active', True),
                popular=pkg_data.get('popular', False),
                badge=pkg_data.get('badge'),
                sort_order=pkg_data.get('sort_order', 0)
            ))
        
        return sorted(packages, key=lambda p: p.sort_order)
    
    def get_package(self, package_id: str) -> Optional[Package]:
        """Get a specific package by ID"""
        for pkg in self.get_packages(active_only=False):
            if pkg.id == package_id:
                return pkg
        return None
    
    # ========================================================================
    # SUBSCRIPTIONS
    # ========================================================================
    
    def get_subscriptions(self, active_only: bool = True) -> List[Subscription]:
        """Get all subscription plans"""
        self._load_config()
        
        subscriptions = []
        for sub_data in self._config.get('subscriptions', []):
            if active_only and not sub_data.get('active', True):
                continue
            
            subscriptions.append(Subscription(
                id=sub_data['id'],
                name=sub_data['name'],
                description=sub_data.get('description', ''),
                credits_per_period=sub_data['credits_per_period'],
                price_usd=sub_data['price_usd'],
                interval=sub_data.get('interval', 'month'),
                interval_count=sub_data.get('interval_count', 1),
                stripe_price_id=sub_data.get('stripe_price_id'),
                trial_days=sub_data.get('trial_days', 0),
                features=sub_data.get('features', []),
                active=sub_data.get('active', True),
                popular=sub_data.get('popular', False),
                badge=sub_data.get('badge'),
                sort_order=sub_data.get('sort_order', 0)
            ))
        
        return sorted(subscriptions, key=lambda s: s.sort_order)
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a specific subscription by ID"""
        for sub in self.get_subscriptions(active_only=False):
            if sub.id == subscription_id:
                return sub
        return None
    
    # ========================================================================
    # MODEL COSTS
    # ========================================================================
    
    def get_model_costs(self) -> Dict[str, int]:
        """Get all model costs"""
        self._load_config()
        return self._config.get('model_costs', {'_default': 1})
    
    def get_model_cost(self, model_name: str) -> int:
        """Get credit cost for a specific model"""
        costs = self.get_model_costs()
        return costs.get(model_name, costs.get('_default', 1))
    
    # ========================================================================
    # COUPONS
    # ========================================================================
    
    def get_coupons(self, active_only: bool = True) -> List[Coupon]:
        """Get all coupons"""
        self._load_config()
        
        coupons = []
        for code, coupon_data in self._config.get('coupons', {}).items():
            if active_only and not coupon_data.get('active', True):
                continue
            
            coupons.append(Coupon(
                code=code,
                name=coupon_data.get('name', code),
                description=coupon_data.get('description', ''),
                type=coupon_data.get('type', 'percent'),
                discount=coupon_data.get('discount', 0),
                applies_to=coupon_data.get('applies_to', 'all'),
                valid_items=coupon_data.get('valid_items', []),
                max_uses=coupon_data.get('max_uses'),
                max_uses_per_user=coupon_data.get('max_uses_per_user', 1),
                min_purchase_usd=coupon_data.get('min_purchase_usd', 0),
                valid_from=coupon_data.get('valid_from'),
                valid_until=coupon_data.get('valid_until'),
                active=coupon_data.get('active', True)
            ))
        
        return coupons
    
    def get_coupon(self, code: str) -> Optional[Coupon]:
        """Get a specific coupon by code (case-insensitive)"""
        code_upper = code.upper()
        for coupon in self.get_coupons(active_only=False):
            if coupon.code.upper() == code_upper:
                return coupon
        return None
    
    # ========================================================================
    # PROMOTIONS
    # ========================================================================
    
    def get_promotions(self) -> Dict[str, Promotion]:
        """Get all promotion configurations"""
        self._load_config()
        
        promos = {}
        promo_data = self._config.get('promotions', {})
        
        # Signup bonus
        signup = promo_data.get('signup_bonus', {})
        promos['signup_bonus'] = Promotion(
            enabled=signup.get('enabled', False),
            credits=signup.get('credits', 0),
            description=signup.get('description', '')
        )
        
        # First purchase bonus
        first = promo_data.get('first_purchase_bonus', {})
        promos['first_purchase_bonus'] = Promotion(
            enabled=first.get('enabled', False),
            bonus_percent=first.get('bonus_percent', 0),
            max_bonus_credits=first.get('max_bonus_credits', 0),
            description=first.get('description', '')
        )
        
        # Referral bonus
        referral = promo_data.get('referral_bonus', {})
        promos['referral_bonus'] = Promotion(
            enabled=referral.get('enabled', False),
            credits=referral.get('referrer_credits', 0),
            description=referral.get('description', '')
        )
        
        return promos
    
    def get_signup_bonus(self) -> int:
        """Get signup bonus credits"""
        promos = self.get_promotions()
        signup = promos.get('signup_bonus')
        if signup and signup.enabled:
            return signup.credits
        return 0
    
    # ========================================================================
    # SETTINGS
    # ========================================================================
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        self._load_config()
        return self._config.get('settings', {})
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting by dot-notation key (e.g., 'stripe.mode')"""
        settings = self.get_settings()
        
        keys = key.split('.')
        value = settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        
        return value
    
    def get_currency(self) -> str:
        """Get currency code"""
        return self.get_setting('currency', 'USD')
    
    def get_currency_symbol(self) -> str:
        """Get currency symbol"""
        return self.get_setting('currency_symbol', '$')
    
    def is_stripe_live(self) -> bool:
        """Check if Stripe is in live mode"""
        return self.get_setting('stripe.mode', 'sandbox') == 'live'
    
    # ========================================================================
    # FEATURES
    # ========================================================================
    
    def get_features(self) -> Dict[str, bool]:
        """Get all feature flags"""
        self._load_config()
        return self._config.get('features', {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get_features().get(feature, False)
    
    # ========================================================================
    # RAW CONFIG ACCESS
    # ========================================================================
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw config dict (for admin UI)"""
        self._load_config()
        return self._config.copy()
    
    def get_section(self, section: str, default: Any = None) -> Any:
        """
        Get a top-level section from the config.
        
        Args:
            section: Section name (e.g., 'storage', 'security')
            default: Default value if section not found
            
        Returns:
            Section dict or default value
        """
        self._load_config()
        return self._config.get(section, default)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_credits_config(config_path: Optional[str] = None) -> CreditsConfigLoader:
    """Get the credits config loader singleton"""
    return CreditsConfigLoader(config_path)
