# Deployment Guide for Render.com

## Prerequisites

1. **kz-table.xlsx** must be in the lipanauto-proxy root directory
2. **Environment variables** must be configured in Render dashboard

---

## Required Environment Variables

### For Kazakhstan Calculations:

**GOOGLE_SHEETS_API_KEY** (Required)
- Get from Google Cloud Console: https://console.cloud.google.com/
- Enable Google Sheets API for your project
- Create API Key and restrict to Google Sheets API
- Spreadsheet ID: `1i3Kj3rA0PVTJrNPL5fzEuN8qjRiOkLgrOpet16r2X5A`
- Reads cells:
  - K7: USD/KRW exchange rate
  - K8: KZT/KRW exchange rate

### Optional:

**CAPSOLVER_API_KEY**
- For CAPTCHA solving in customs calculators
- Get from: https://www.capsolver.com/

**PROXY_AUTH**
- Proxy authentication credentials (format: `username:password`)
- Only needed if using authenticated proxies

---

## Deployment Steps

### 1. Prepare Repository
```bash
# Ensure kz-table.xlsx is in lipanauto-proxy root
ls lipanauto-proxy/kz-table.xlsx

# Commit if not already tracked
git add lipanauto-proxy/kz-table.xlsx
git commit -m "Add KZ price table for deployment"
git push origin main
```

### 2. Configure Render.com

1. Go to Render.com dashboard
2. Select your `lipanauto-proxy` service
3. Navigate to **Environment** tab
4. Add environment variables:
   - Key: `GOOGLE_SHEETS_API_KEY`
   - Value: Your Google Sheets API key

### 3. Deploy

- Render will auto-deploy on git push
- Or manually trigger deploy from Render dashboard

### 4. Verify Deployment

Check the logs for these messages:

**✅ Success indicators:**
```
📂 Looking for KZ price table at: /app/kz-table.xlsx
✅ Loaded 1500+ entries from KZ price table
✅ Google Sheets API initialized with API key
✅ Fetched exchange rates: USD/KRW=1348.5, KZT/KRW=2.73
✅ All services initialized successfully
```

**⚠️ Warning indicators:**
```
⚠️  KZ price table not loaded - Kazakhstan calculations will fail
⚠️  Google Sheets API not configured - using fallback exchange rates
```

---

## Testing Endpoints

After deployment, test these endpoints:

### 1. Exchange Rates
```bash
curl https://your-app.onrender.com/api/exchange-rates
```

Expected response:
```json
{
  "usd_krw": 1348.5,
  "kzt_krw": 2.73,
  "timestamp": 1699123456,
  "is_fallback": false
}
```

### 2. KZ Price Table Lookup
```bash
curl "https://your-app.onrender.com/api/kz-price-table/lookup?manufacturer=BMW&model=3-Series&volume=2.0&year=2025"
```

Expected response:
```json
{
  "success": true,
  "price_usd": 45000,
  "manufacturer": "BMW",
  "model": "3-Series",
  "volume": 2.0,
  "year": 2025,
  "match_type": "exact"
}
```

### 3. Kazakhstan Customs Calculation
```bash
curl -X POST https://your-app.onrender.com/api/customs/calculate-kazakhstan \
  -H "Content-Type: application/json" \
  -d '{
    "manufacturer": "BMW",
    "model": "3-Series",
    "price_krw": 60900000,
    "year": 2025,
    "engine_volume": 2.998
  }'
```

Expected response: Full calculation breakdown with turnkey price in KZT.

---

## Troubleshooting

### "KZ price table not loaded"

**Cause:** kz-table.xlsx file not found

**Solutions:**
1. Check file exists in repository:
   ```bash
   ls lipanauto-proxy/kz-table.xlsx
   ```
2. Check file is committed to git
3. Check Render logs for file path:
   ```
   📂 Looking for KZ price table at: /app/kz-table.xlsx
   ```
4. Verify file permissions (should be readable)

---

### "Using fallback exchange rates"

**Cause:** GOOGLE_SHEETS_API_KEY not configured

**Solutions:**
1. Go to Render dashboard → Environment
2. Add `GOOGLE_SHEETS_API_KEY` variable
3. Service will auto-restart
4. Check logs for: `✅ Google Sheets API initialized with API key`

---

### HTTP 400 on Kazakhstan endpoints

**Cause:** One or both of the above issues

**Solutions:**
1. Fix KZ price table loading
2. Add Google Sheets API key
3. Check logs for specific error messages
4. Verify request data is valid:
   - manufacturer and model are non-empty strings
   - engine_volume >= 0.5L
   - year is between 1990-2030

---

### HTTP 502 Bad Gateway

**Cause:** Backend service crashed or unavailable

**Solutions:**
1. Check Render logs for error messages
2. Check service health: `https://your-app.onrender.com/health`
3. Restart service from Render dashboard
4. Check if free tier service is sleeping (takes ~30s to wake up)

---

## File Structure

```
lipanauto-proxy/
├── kz-table.xlsx              # ← Must exist for deployment
├── main.py                    # FastAPI app with endpoints
├── requirements.txt           # Python dependencies
├── services/
│   ├── exchange_rate_service.py
│   ├── kz_price_table_service.py
│   └── kazakhstan_customs_service.py
├── schemas/
│   └── kazakhstan.py
└── DEPLOYMENT.md             # This file
```

---

## Google Sheets API Setup

### Step-by-Step:

1. **Create/Select Project**
   - Go to: https://console.cloud.google.com/
   - Create new project or select existing

2. **Enable Google Sheets API**
   - Go to: APIs & Services → Library
   - Search for "Google Sheets API"
   - Click "Enable"

3. **Create API Key**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → API Key
   - Copy the API key

4. **Restrict API Key** (Recommended)
   - Click on the created API key
   - Under "API restrictions" → "Restrict key"
   - Select "Google Sheets API" only
   - Save

5. **Add to Render**
   - Render Dashboard → Environment
   - Add: `GOOGLE_SHEETS_API_KEY=your_key_here`

---

## Monitoring

### Health Check Endpoint
```bash
curl https://your-app.onrender.com/health
```

Returns service status, proxy info, and performance metrics.

### Log Monitoring

Watch Render logs for:
- Service initialization messages
- Request/response patterns
- Error messages
- Performance metrics

---

## Support

For issues or questions:
- Check this deployment guide first
- Review Render logs for specific errors
- Check environment variable configuration
- Verify file paths and permissions
