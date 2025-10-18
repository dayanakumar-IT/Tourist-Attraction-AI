# HelloLanka Tourism AI - Multi-Agent Web App

A complete full-stack tourism AI application featuring intelligent multi-agent conversation and real-time data integration.

## 🌟 Features

### Multi-Agent Backend (LangGraph + Gemini)
- **PreAgent**: Normalizes trip requests and preferences
- **PlannerAgent**: Fetches places using Google Places API with intelligent routing
- **WeatherFoodAgent**: Provides weather forecasts and restaurant recommendations
- **TransportAgent**: Optimizes transportation routes and estimates costs
- **WeatherAwarePlanner**: Adapts itineraries based on weather conditions

### Modern React Frontend
- Beautiful, responsive UI with Framer Motion animations
- Real-time agent status indicators during generation
- Comprehensive itinerary display with weather, food, and transport details
- Interactive trip setup wizard
- Context-aware state management

### Live Data Integration
- Google Places API for POI discovery
- Google Maps Platform for routing and distance calculations
- Realistic weather modeling for Sri Lanka
- Restaurant recommendations with ratings
- Cost estimation and budget optimization

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Google Places API key

### 1. Backend Setup
```bash
# Install Python dependencies
cd src
pip install -r requirements.txt

# Set up environment variables
export GOOGLE_PLACES_API_KEY="your_api_key_here"
```

### 2. Frontend Setup
```bash
# Install frontend dependencies
cd sri-lanka-ai-planner
npm install
```

### 3. Run the Complete Application
```bash
# From project root - starts both backend and frontend
python start_app.py
```

Or run separately:

```bash
# Terminal 1 - Backend
cd src
uvicorn server:app --reload --port 8000

# Terminal 2 - Frontend  
cd sri-lanka-ai-planner
npm start
```

## 🎯 How It Works

### 1. User Input Collection
The React frontend collects:
- Trip details (start city, destinations, dates, duration)
- Traveler profile (group type, size, special requirements)
- Budget preferences
- Experience themes (culture, beach, food, nature)

### 2. Multi-Agent Processing
The backend agents work together:

1. **PreAgent** normalizes the input and extracts themes
2. **PlannerAgent** geocodes locations and fetches relevant POIs
3. **WeatherFoodAgent** adds weather forecasts and restaurant data
4. **TransportAgent** optimizes routes and calculates costs
5. **WeatherAwarePlanner** adapts activities based on weather

### 3. Intelligent Output
The system generates:
- Weather-adaptive activity recommendations
- Nearby restaurant suggestions with ratings
- Optimized transportation routes with cost estimates
- Best times to visit each location
- Real-time weather notes and tips

## 🏗️ Architecture

```
Frontend (React)          Backend (FastAPI + LangGraph)
┌─────────────────┐      ┌─────────────────────────────┐
│ TripSetup       │─────▶│ /api/generate-itinerary     │
│ - Form wizard   │      │ - Data validation           │
│ - State mgmt    │      │ - Request conversion        │
└─────────────────┘      └─────────────────────────────┘
                                │
                                ▼
                         ┌─────────────────────────────┐
                         │ Multi-Agent Pipeline        │
                         │ ┌─────────┐ ┌─────────────┐ │
                         │ │PreAgent │ │PlannerAgent │ │
                         │ └─────────┘ └─────────────┘ │
                         │ ┌─────────────┐ ┌─────────┐ │
                         │ │WeatherFood  │ │Transport│ │
                         │ │Agent        │ │Agent    │ │
                         │ └─────────────┘ └─────────┘ │
                         └─────────────────────────────┘
                                │
                                ▼
                         ┌─────────────────────────────┐
                         │ External APIs               │
                         │ - Google Places             │
                         │ - Google Maps Platform      │
                         │ - Weather Data              │
                         └─────────────────────────────┘
                                │
                                ▼
                         ┌─────────────────────────────┐
                         │ ItineraryPage               │
                         │ - Rich display              │
                         │ - Interactive cards         │
                         │ - Weather integration       │
                         └─────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables
```bash
# Backend (.env in src/)
GOOGLE_PLACES_API_KEY=your_google_places_api_key

# Frontend (.env in sri-lanka-ai-planner/)
REACT_APP_API_URL=http://localhost:8000
```

### API Keys Required
- **Google Places API**: For POI discovery and restaurant search
- **Google Maps Platform**: For routing and distance calculations
- **Gemini API**: For LLM-powered agent intelligence

## 📱 User Experience

### Trip Setup Flow
1. **Welcome Screen**: Choose experience themes
2. **Trip Details**: Select start city, destinations, dates
3. **Companions**: Specify group type and requirements  
4. **Budget**: Set daily budget and accommodation preferences
5. **Generation**: Watch agents work in real-time

### Itinerary Display
- **Day-by-day breakdown** with expandable sections
- **Weather integration** with forecasts and recommendations
- **Restaurant suggestions** with ratings and cuisine types
- **Transportation details** with costs and duration
- **Smart timing** recommendations for each activity

## 🎨 Frontend Features

### Components
- `TripSetup`: Multi-step form wizard
- `ItineraryPage`: Rich itinerary display
- `ActivityCard`: Individual activity details
- `TravelLegCard`: Transportation information
- `DayCard`: Collapsible daily plans

### Hooks
- `useItinerary`: API integration and state management
- `useTrip`: Context-based trip data management

### Services
- `apiService`: Backend communication layer

## 🤖 Agent Intelligence

### Weather Adaptation
- Avoids beaches during rain
- Suggests indoor activities for bad weather
- Provides weather-specific tips and notes

### Smart Routing
- Optimizes travel routes between destinations
- Considers traffic and distance
- Provides multiple transport options

### Budget Awareness
- Estimates costs for each activity
- Suggests budget-friendly alternatives
- Tracks total trip expenses

## 🚀 Deployment

### Backend Deployment
```bash
# Using uvicorn
uvicorn src.server:app --host 0.0.0.0 --port 8000

# Using gunicorn
gunicorn src.server:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend Deployment
```bash
# Build for production
cd sri-lanka-ai-planner
npm run build

# Serve static files
npx serve -s build -l 3000
```

## 🔍 Testing

### Backend Testing
```bash
cd src
python -m src.run_langgraph_cli --input src/input_demo.json --trace
```

### Frontend Testing
```bash
cd sri-lanka-ai-planner
npm test
```

## 📊 Performance

- **Backend Response Time**: ~4-6 seconds for complete itinerary
- **Caching**: In-memory caching for POI searches and geocoding
- **API Optimization**: Reduced limits and timeouts for faster responses
- **Frontend**: Optimized with React.memo and efficient re-renders

## 🛠️ Development

### Adding New Agents
1. Create agent class in `src/agents/`
2. Add to LangGraph pipeline in `src/agent_graph.py`
3. Update frontend to display new data

### Customizing UI
- Modify components in `sri-lanka-ai-planner/src/components/`
- Update styles in `sri-lanka-ai-planner/src/App.css`
- Add new pages in `sri-lanka-ai-planner/src/pages/`

## 🎯 Future Enhancements

- Real-time chat interface with agents
- Mobile app development
- Offline itinerary access
- Social sharing features
- Advanced budget tracking
- Integration with booking platforms

---

**Built with ❤️ for Sri Lankan Tourism**
