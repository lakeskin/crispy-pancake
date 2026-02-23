/**
 * CreditPackagesModal - Purchase Credits
 * 
 * Shows available credit packages and subscriptions with Stripe checkout.
 * Supports coupon codes for discounts.
 */
import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  Button,
  Stack,
  Card,
  CardContent,
  Chip,
  TextField,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Divider,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StarIcon from '@mui/icons-material/Star';
import apiService from '../../services/api';
import type { CreditPackage, Subscription } from '../../services/api';

interface CreditPackagesModalProps {
  open: boolean;
  onClose: () => void;
  onPurchaseComplete?: () => void;
}

export default function CreditPackagesModal({ open, onClose, onPurchaseComplete }: CreditPackagesModalProps) {
  const [tab, setTab] = useState(0);
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Coupon
  const [couponCode, setCouponCode] = useState('');
  const [couponLoading, setCouponLoading] = useState(false);
  const [couponValid, setCouponValid] = useState<boolean | null>(null);
  const [couponMessage, setCouponMessage] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState<{
    code: string;
    discount_type: string;
    discount_value: number;
  } | null>(null);

  useEffect(() => {
    if (open) {
      loadPackages();
    }
  }, [open]);

  const loadPackages = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getCreditPackages();
      setPackages(data.packages || []);
      setSubscriptions(data.subscriptions || []);
    } catch (err) {
      console.error('Failed to load packages:', err);
      setError('Failed to load credit packages. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleValidateCoupon = async () => {
    if (!couponCode.trim()) return;
    
    setCouponLoading(true);
    setCouponValid(null);
    setCouponMessage('');
    
    try {
      const result = await apiService.validateCoupon(couponCode.toUpperCase());
      
      if (result.valid) {
        setCouponValid(true);
        setAppliedCoupon({
          code: couponCode.toUpperCase(),
          discount_type: result.discount_type,
          discount_value: result.discount_value,
        });
        setCouponMessage(
          result.discount_type === 'percentage'
            ? `${result.discount_value}% discount applied!`
            : `$${result.discount_value} off applied!`
        );
      } else {
        setCouponValid(false);
        setCouponMessage(result.message || 'Invalid coupon code');
        setAppliedCoupon(null);
      }
    } catch (err) {
      console.error('Coupon validation failed:', err);
      setCouponValid(false);
      setCouponMessage('Failed to validate coupon');
      setAppliedCoupon(null);
    } finally {
      setCouponLoading(false);
    }
  };

  const handlePurchasePackage = async (pkg: CreditPackage) => {
    setPurchasing(pkg.id);
    setError(null);
    
    try {
      const result = await apiService.createPackageCheckout(
        pkg.id,
        appliedCoupon?.code || null
      );
      
      if (result.checkout_url) {
        // Redirect to Stripe
        window.location.href = result.checkout_url;
      } else {
        throw new Error('No checkout URL returned');
      }
    } catch (err) {
      console.error('Checkout failed:', err);
      setError('Failed to start checkout. Please try again.');
      setPurchasing(null);
    }
  };

  const handlePurchaseSubscription = async (sub: Subscription) => {
    setPurchasing(sub.id);
    setError(null);
    
    try {
      const result = await apiService.createSubscriptionCheckout(
        sub.id,
        appliedCoupon?.code || null
      );
      
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else {
        throw new Error('No checkout URL returned');
      }
    } catch (err) {
      console.error('Subscription checkout failed:', err);
      setError('Failed to start checkout. Please try again.');
      setPurchasing(null);
    }
  };

  const calculateDiscountedPrice = (price: number): number | null => {
    if (!appliedCoupon) return null;
    
    if (appliedCoupon.discount_type === 'percentage') {
      return price * (1 - appliedCoupon.discount_value / 100);
    } else if (appliedCoupon.discount_type === 'fixed') {
      return Math.max(0, price - appliedCoupon.discount_value);
    }
    return null;
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3, maxHeight: '90vh' }
      }}
    >
      <DialogTitle sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        pb: 1
      }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            🪙 Get More Credits
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose a package or subscribe for monthly credits
          </Typography>
        </Box>
        <IconButton onClick={onClose} edge="end">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Coupon Input */}
        <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.100', borderRadius: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <LocalOfferIcon color="primary" fontSize="small" />
            <Typography variant="body2" fontWeight={600}>Have a coupon code?</Typography>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
            <TextField
              size="small"
              placeholder="Enter code"
              value={couponCode}
              onChange={(e) => {
                setCouponCode(e.target.value.toUpperCase());
                setCouponValid(null);
                setCouponMessage('');
                setAppliedCoupon(null);
              }}
              sx={{ flex: 1 }}
              inputProps={{ style: { textTransform: 'uppercase' } }}
            />
            <Button
              variant="outlined"
              onClick={handleValidateCoupon}
              disabled={!couponCode.trim() || couponLoading}
            >
              {couponLoading ? <CircularProgress size={20} /> : 'Apply'}
            </Button>
          </Stack>
          {couponMessage && (
            <Typography 
              variant="caption" 
              sx={{ 
                mt: 1, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 0.5,
                color: couponValid ? 'success.main' : 'error.main' 
              }}
            >
              {couponValid ? <CheckCircleIcon fontSize="small" /> : null}
              {couponMessage}
            </Typography>
          )}
        </Box>

        {/* Tabs */}
        <Tabs 
          value={tab} 
          onChange={(_, v) => setTab(v)}
          sx={{ mb: 3 }}
          centered
        >
          <Tab label="📦 Credit Packages" />
          <Tab label="✨ Subscriptions" />
        </Tabs>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Packages Tab */}
            {tab === 0 && (
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
                {packages.map((pkg) => {
                  const discountedPrice = calculateDiscountedPrice(pkg.price);
                  const isPopular = pkg.id === 'creator';
                  
                  return (
                    <Card 
                      key={pkg.id}
                      variant="outlined"
                      sx={{ 
                        position: 'relative',
                        borderColor: isPopular ? 'primary.main' : undefined,
                        borderWidth: isPopular ? 2 : 1,
                      }}
                    >
                      {isPopular && (
                        <Chip 
                          label="Most Popular"
                          color="primary"
                          size="small"
                          icon={<StarIcon />}
                          sx={{ 
                            position: 'absolute', 
                            top: -12, 
                            left: '50%', 
                            transform: 'translateX(-50%)',
                          }}
                        />
                      )}
                      <CardContent sx={{ textAlign: 'center', pt: isPopular ? 3 : 2 }}>
                        <Typography variant="h6" fontWeight={700}>
                          {pkg.name}
                        </Typography>
                        <Typography variant="h3" fontWeight={800} color="primary" sx={{ my: 1 }}>
                          {pkg.credits}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          credits
                        </Typography>
                        
                        {pkg.bonus_credits > 0 && (
                          <Chip 
                            label={`+${pkg.bonus_credits} bonus`}
                            color="success"
                            size="small"
                            sx={{ mb: 2 }}
                          />
                        )}
                        
                        <Divider sx={{ my: 2 }} />
                        
                        <Box sx={{ mb: 2 }}>
                          {discountedPrice !== null ? (
                            <>
                              <Typography 
                                variant="body2" 
                                sx={{ textDecoration: 'line-through', color: 'text.disabled' }}
                              >
                                ${pkg.price.toFixed(2)}
                              </Typography>
                              <Typography variant="h5" fontWeight={700} color="success.main">
                                ${discountedPrice.toFixed(2)}
                              </Typography>
                            </>
                          ) : (
                            <Typography variant="h5" fontWeight={700}>
                              ${pkg.price.toFixed(2)}
                            </Typography>
                          )}
                        </Box>
                        
                        <Button
                          variant={isPopular ? 'contained' : 'outlined'}
                          fullWidth
                          onClick={() => handlePurchasePackage(pkg)}
                          disabled={purchasing === pkg.id}
                        >
                          {purchasing === pkg.id ? (
                            <CircularProgress size={24} />
                          ) : (
                            'Buy Now'
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            )}

            {/* Subscriptions Tab */}
            {tab === 1 && (
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
                {subscriptions.map((sub) => {
                  const discountedPrice = calculateDiscountedPrice(sub.price);
                  
                  return (
                    <Card key={sub.id} variant="outlined">
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h6" fontWeight={700}>
                          {sub.name}
                        </Typography>
                        <Typography variant="h3" fontWeight={800} color="primary" sx={{ my: 1 }}>
                          {sub.credits_per_month}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          credits / month
                        </Typography>
                        
                        {sub.trial_days > 0 && (
                          <Chip 
                            label={`${sub.trial_days}-day free trial`}
                            color="info"
                            size="small"
                            sx={{ mb: 2 }}
                          />
                        )}
                        
                        <Divider sx={{ my: 2 }} />
                        
                        <Box sx={{ mb: 2 }}>
                          {discountedPrice !== null ? (
                            <>
                              <Typography 
                                variant="body2" 
                                sx={{ textDecoration: 'line-through', color: 'text.disabled' }}
                              >
                                ${sub.price.toFixed(2)}/{sub.interval}
                              </Typography>
                              <Typography variant="h5" fontWeight={700} color="success.main">
                                ${discountedPrice.toFixed(2)}/{sub.interval}
                              </Typography>
                            </>
                          ) : (
                            <Typography variant="h5" fontWeight={700}>
                              ${sub.price.toFixed(2)}/{sub.interval}
                            </Typography>
                          )}
                        </Box>
                        
                        <Button
                          variant="contained"
                          fullWidth
                          onClick={() => handlePurchaseSubscription(sub)}
                          disabled={purchasing === sub.id}
                        >
                          {purchasing === sub.id ? (
                            <CircularProgress size={24} />
                          ) : (
                            'Subscribe'
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            )}
          </>
        )}

        {/* Footer note */}
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 3 }}>
          Secure payment powered by Stripe. Cancel anytime.
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
