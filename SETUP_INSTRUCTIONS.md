# 🔧 Environment Setup Instructions

## Quick Fix for Your Issues

The errors you're seeing are because the `.env` file is not being loaded properly. Here's how to fix it:

### Step 1: Create the .env file

1. **Copy the example file:**
   ```bash
   cd travel_agents
   copy env_example.txt .env
   ```

2. **Edit the .env file** with your actual API keys:
   ```env
   GEMINI_API_KEY=your_actual_gemini_key_here
   GEOCODE_API_KEY=your_actual_opencage_key_here
   AMADEUS_CLIENT_ID=your_actual_amadeus_client_id_here
   AMADEUS_CLIENT_SECRET=your_actual_amadeus_client_secret_here
   DUFFEL_ACCESS_TOKEN=your_actual_duffel_token_here
   ```

### Step 2: Test the fixes

1. **Test country detection:**
   ```bash
   python test_country_detection.py
   ```

2. **Run the application:**
   ```bash
   python main.py --demo
   ```

### Step 3: Get API Keys (if you don't have them)

1. **Gemini API Key** (for AI features):
   - Go to: https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy and paste into .env file

2. **OpenCage Geocoder** (for location detection):
   - Go to: https://opencagedata.com/api
   - Sign up for free account
   - Get your API key
   - Copy and paste into .env file

3. **Amadeus API** (for flights and hotels):
   - Go to: https://developers.amadeus.com/
   - Sign up for free account
   - Get your Client ID and Client Secret
   - Copy and paste into .env file

4. **Duffel API** (optional, for more flight options):
   - Go to: https://duffel.com/
   - Sign up for account
   - Get your access token
   - Copy and paste into .env file

### What I Fixed

1. ✅ **Country Detection**: Improved regex patterns to better extract countries from prompts
2. ✅ **Environment Loading**: Enhanced .env file loading with multiple fallback paths
3. ✅ **Validation Error**: Fixed the None destination issue that was causing Pydantic validation errors
4. ✅ **Error Handling**: Added better error messages and fallback behavior

### Expected Behavior Now

- ✅ "Plan a trip to Sri Lanka" should correctly detect "Sri Lanka"
- ✅ Environment variables should load properly
- ✅ No more validation errors
- ✅ Mock data will be used when APIs are not available
- ✅ Better error messages and debugging info

### If You Still Have Issues

1. **Check the .env file exists** in the `travel_agents` directory
2. **Verify API keys** are correctly set (no extra spaces or quotes)
3. **Run the test**: `python test_country_detection.py`
4. **Check environment**: `python main.py --check-env`

The application will work in demo mode even without real API keys!
