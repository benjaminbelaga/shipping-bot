# UPS API Integration Guide - YOYAKU Pricing Engine

**Status:** ✅ PRODUCTION READY (2025-11-20)
**Version:** 1.0
**Author:** Benjamin Belaga

---

## 📋 Overview

Complete integration of UPS API for real-time shipping rate calculation with negotiated rates for YOYAKU.IO.

### Key Features

- ✅ **Negotiated Rates:** All quotes return negotiated pricing (💰)
- ✅ **Automatic Fallback:** If "Shop" method fails (error 111100), automatically falls back to individual service codes
- ✅ **Dual API Support:**
  - **STANDARD API:** European destinations (UPS Standard service)
  - **WWE API (Worldwide Express):** Rest of world (Express services)
- ✅ **Comprehensive Logging:** Full debug logs with sanitized credentials
- ✅ **Production Tested:** USA 🇺🇸, Japan 🇯🇵, Germany 🇩🇪 validated

---

## 🔧 Technical Implementation

### File Structure

```
repos/pricing-engine/
├── src/integrations/ups_api.py          # Main UPS API integration
├── debug_ups_api.py                      # Standalone testing tool
├── logs/                                 # Debug logs directory
│   ├── ups_debug_*.log                   # Detailed API interaction logs
│   └── ups_test_*.json                   # Test result JSON files
└── docs/
    ├── UPS-API-INTEGRATION-GUIDE.md      # This file
    └── UPS-INTEGRATION-FINAL-WORKING.md  # Technical deep dive
```

### Core Function

```python
def get_ups_rates(
    country_code: str,
    weight_kg: float,
    city: Optional[str] = None,
    postal_code: Optional[str] = None
) -> list[dict]
```

**Returns:** List of shipping options sorted by price (cheapest first)

```json
[
  {
    "carrier": "UPS",
    "service": "UPS Standard",
    "service_code": "11",
    "transit_days": "2-3 days",
    "price_eur": 9.04,
    "currency": "EUR",
    "is_negotiated": true
  }
]
```

---

## 🌍 API Selection Logic

### STANDARD API (Europe)
**Endpoint:** `https://onlinetools.ups.com/api/rating/v1/Rate`
**Countries:** EU member states, Norway, Switzerland, UK
**Services:** `11` (UPS Standard), `65` (UPS Express Saver)

### WWE API (Worldwide Express)
**Endpoint:** `https://onlinetools.ups.com/api/rating/v1/Shop`
**Countries:** Rest of world (Americas, Asia, Oceania, Africa)
**Services:** `07` (Worldwide Express), `08` (Worldwide Expedited), `65` (Express Saver)

---

## 🔑 Authentication & Credentials

**Location:** `~/.credentials/yoyaku/api-keys/ups.env`

```bash
# UPS OAuth2
UPS_CLIENT_ID=your_client_id
UPS_CLIENT_SECRET=your_client_secret

# Account Details
UPS_ACCOUNT_NUMBER=your_account_number
UPS_SHIPPER_NUMBER=your_shipper_number  # Same as account number
```

### Token Management

```python
# Automatic OAuth2 token refresh
self._get_token()  # Called automatically before each API request
# Token cached in memory, refreshed when expired
```

---

## 🚨 Known Issues & Solutions

### Error 111100: "RequestOption is invalid"

**Problem:** UPS rejects `RequestOption="Shop"` for WWE API
**Solution:** Automatic fallback to individual service codes

```python
# First attempt: RequestOption="Shop"
request = {"RequestOption": "Shop"}
# If fails with 111100 → Automatic retry with individual codes
for service_code in ["07", "08", "65"]:
    request = {"RequestOption": service_code}
```

**Impact:** Zero user impact - fallback is transparent

### StateProvinceCode for Non-US/CA Destinations

**Problem:** API rejects requests with StateProvinceCode for countries outside US/Canada
**Solution:** Conditional inclusion

```python
if country_code in ["US", "CA"]:
    address["StateProvinceCode"] = "XX"  # Required
else:
    # Omit StateProvinceCode completely
```

### Negotiated Rates Not Returned

**Problem:** Missing `<RateInformation><NegotiatedRatesIndicator/></RateInformation>`
**Solution:** Always include this element in API requests

```python
payload = {
    "RateRequest": {
        "RateInformation": {
            "NegotiatedRatesIndicator": ""  # Critical for negotiated rates
        }
    }
}
```

---

## 🧪 Testing

### Debug Tool Usage

```bash
cd ~/repos/pricing-engine

# Test Europe (STANDARD API)
python3 debug_ups_api.py --country DE --weight 1.0 --production --city Berlin --postal 10115

# Test USA (WWE API)
python3 debug_ups_api.py --country US --weight 1.0 --production

# Test Japan (WWE API)
python3 debug_ups_api.py --country JP --weight 1.5 --production

# Sandbox testing
python3 debug_ups_api.py --country FR --weight 2.0 --sandbox
```

### Test Results (2025-11-20)

| Destination    | Weight | API      | Best Rate               | Negotiated | Status |
|----------------|--------|----------|-------------------------|------------|--------|
| 🇩🇪 Germany   | 1.0kg  | STANDARD | 9.04 EUR (Standard)     | ✅ Yes     | ✅ Pass |
| 🇺🇸 USA       | 1.0kg  | WWE      | 40.58 EUR (Express Saver)| ✅ Yes     | ✅ Pass |
| 🇯🇵 Japan     | 1.5kg  | WWE      | 47.96 EUR (Express Saver)| ✅ Yes     | ✅ Pass |

**Success Rate:** 100% with negotiated rates

---

## 📝 Logging

### Debug Logs

**Location:** `~/repos/pricing-engine/logs/ups_debug_*.log`

**Content:**
- Full API requests (sanitized credentials)
- API responses (formatted JSON)
- Error details and retry attempts
- Negotiated rate indicators

**Example:**
```
2025-11-20 16:42:41 - INFO - [UPS_STANDARD] Fetching rates for Germany (DE), Weight: 1.0 kg
2025-11-20 16:42:42 - INFO - [UPS_STANDARD] Got 2 rates (all negotiated: True)
2025-11-20 16:42:42 - INFO - ✅ UPS Standard: €9.04 (negotiated) - Transit: 2-3 days
```

### JSON Test Results

**Location:** `~/repos/pricing-engine/logs/ups_test_*.json`

```json
{
  "timestamp": "2025-11-20T16:42:42",
  "success": true,
  "country": "DE",
  "weight_kg": 1.0,
  "rates_count": 2,
  "best_rate": {
    "service": "UPS Standard",
    "price_eur": 9.04,
    "is_negotiated": true
  }
}
```

---

## 🚀 Production Deployment

### Prerequisites

1. **Credentials Setup:**
```bash
source ~/.credentials/yoyaku/api-keys/ups.env
# Verify: echo $UPS_CLIENT_ID
```

2. **Python Dependencies:**
```bash
pip install requests python-dotenv
```

3. **Test Connection:**
```bash
python3 debug_ups_api.py --country US --weight 1.0 --production
```

### Integration Example

```python
from src.integrations.ups_api import UPSRateAPI

# Initialize
ups_api = UPSRateAPI(use_production=True)

# Get rates
rates = ups_api.get_ups_rates(
    country_code="US",
    weight_kg=1.5
)

# Process results
if rates:
    best_rate = rates[0]  # Already sorted by price
    print(f"Best option: {best_rate['service']} - {best_rate['price_eur']} EUR")
```

---

## 🔒 Security Notes

1. **Credential Storage:** Store `ups.env` in `~/.credentials/yoyaku/api-keys/` (encrypted)
2. **Log Sanitization:** All debug logs sanitize Bearer tokens and account numbers
3. **Production Flag:** Always use `use_production=True` for live traffic
4. **Token Caching:** OAuth2 tokens cached in memory only (not persisted)

---

## 📚 Resources

- **UPS Rating API Documentation:** https://developer.ups.com/api/reference/rating
- **Service Codes:** https://www.ups.com/us/en/support/shipping-support/shipping-services/service-codes.page
- **Country Codes:** ISO 3166-1 alpha-2
- **Currency:** All rates returned in EUR (converted from USD by UPS API)

---

## 🐛 Troubleshooting

### No Rates Returned

1. **Check logs:** `tail -f logs/ups_debug_*.log`
2. **Verify credentials:** `source ~/.credentials/yoyaku/api-keys/ups.env && env | grep UPS_`
3. **Test connectivity:** `python3 debug_ups_api.py --country US --weight 1.0 --production`

### Error 111100

**Expected behavior:** Automatic fallback to individual service codes
**Action required:** None - fallback is automatic

### Rates Not Negotiated (is_negotiated: false)

**Check:** `RateInformation.NegotiatedRatesIndicator` present in request
**Fix:** Ensure `ups_api.py` includes this element (already implemented)

---

## ✅ Validation Checklist

- [x] OAuth2 authentication working
- [x] STANDARD API returns negotiated rates (Europe)
- [x] WWE API returns negotiated rates (Rest of world)
- [x] Automatic fallback on error 111100
- [x] Correct StateProvinceCode handling (US/CA only)
- [x] Currency conversion to EUR
- [x] Transit days parsing
- [x] Comprehensive logging
- [x] Production tested (3 continents)

---

**Last Updated:** 2025-11-20
**Tested By:** Benjamin Belaga
**Production Status:** ✅ READY
