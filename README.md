# 🌍 Tourist Attraction AI

A comprehensive travel planning assistant that finds flights and hotels based on natural language prompts. This AI-powered system automatically detects destinations from user input and provides the best matching flight and hotel options.

## ✨ Features

- 🤖 **AI-Powered Planning**: Uses Gemini AI for intelligent trip planning
- ✈️ **Flight Search**: Integrates with Amadeus and Duffel APIs for comprehensive flight options
- 🏨 **Hotel Search**: Finds accommodations via Amadeus API
- 🌍 **Smart Location Detection**: Automatically identifies countries and cities from natural language
- 📅 **Flexible Date Handling**: Supports various date formats and trip durations
- 💰 **Price Comparison**: Creates optimized packages combining flights and hotels
- 🎯 **Best Match Algorithm**: Ranks options by price and relevance

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Required API keys (see setup section)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Tourist-Attraction-AI
   ```

2. **Install dependencies**
   ```bash
   cd travel_agents
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example file
   cp env_example.txt .env
   
   # Edit .env with your API keys
   nano .env
   ```

4. **Run the application**
   ```bash
   # From the root directory
   python main.py
   
   # Or run in demo mode (no API keys required)
   python main.py --demo
   ```

## 🔧 Setup

### Required API Keys

You'll need the following API keys to use all features:

1. **Gemini API Key** (for AI planning)
   - Get from: [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Set as: `GEMINI_API_KEY`

2. **OpenCage Geocoder API Key** (for location detection)
   - Get from: [OpenCage Geocoder](https://opencagedata.com/api)
   - Set as: `GEOCODE_API_KEY`

3. **Amadeus API Credentials** (for flights and hotels)
   - Get from: [Amadeus for Developers](https://developers.amadeus.com/)
   - Set as: `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET`

4. **Duffel API Token** (optional, for additional flight options)
   - Get from: [Duffel](https://duffel.com/)
   - Set as: `DUFFEL_ACCESS_TOKEN`

### Environment File Example

Create a `.env` file in the `travel_agents` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEOCODE_API_KEY=your_opencage_api_key_here
AMADEUS_CLIENT_ID=your_amadeus_client_id_here
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret_here
DUFFEL_ACCESS_TOKEN=your_duffel_access_token_here
```

## 📖 Usage

### Basic Usage

```bash
python main.py
```

The application will start and prompt you for travel requests in natural language.

### Example Prompts

- "I want to visit Japan for 5 days"
- "Plan a trip to Thailand starting 2024-03-15 for 7 days"
- "Book flights and hotels for Sri Lanka"
- "Find me a vacation package to France for 10 days"

### Command Line Options

```bash
# Show help
python main.py --help

# Check environment setup
python main.py --check-env

# Run in demo mode (no API keys required)
python main.py --demo
```

## 🏗️ Architecture

The application is structured as follows:

```
Tourist-Attraction-AI/
├── main.py                 # Main entry point
├── README.md              # This file
└── travel_agents/
    ├── team_minimal.py    # Core application logic
    ├── schemas.py         # Data models and validation
    ├── requirements.txt   # Python dependencies
    ├── env_example.txt    # Environment variables template
    ├── agents/
    │   ├── flights_agent.py      # Flight search logic
    │   └── accommodation_agent.py # Hotel search logic
    └── providers/
        ├── amadeus.py     # Amadeus API integration
        └── duffel.py      # Duffel API integration
```

### Key Components

1. **Main Interface** (`main.py`): Entry point with environment checking and CLI options
2. **Core Logic** (`team_minimal.py`): Main application flow and user interaction
3. **Data Models** (`schemas.py`): Pydantic models for type safety and validation
4. **Agents**: Specialized modules for flight and hotel search
5. **Providers**: API integration modules for external services

## 🔍 How It Works

1. **Input Processing**: User enters natural language travel request
2. **Location Detection**: AI extracts destination using geocoding APIs
3. **Date Parsing**: System identifies travel dates and duration
4. **Flight Search**: Queries multiple flight APIs for best options
5. **Hotel Search**: Finds accommodations in the destination
6. **Package Creation**: Combines flights and hotels into optimized packages
7. **Results Display**: Shows ranked options with pricing and details

## 🛠️ Development

### Running Tests

```bash
# Check environment setup
python main.py --check-env

# Run in demo mode for testing
python main.py --demo
```

### Adding New Features

1. **New Providers**: Add API integration in `providers/` directory
2. **New Agents**: Create specialized agents in `agents/` directory
3. **Data Models**: Extend schemas in `schemas.py`
4. **UI Improvements**: Modify `team_minimal.py` for better user experience

### Error Handling

The application includes comprehensive error handling:
- API failures gracefully fall back to mock data
- Missing API keys are detected and reported
- Network timeouts are handled with retries
- Invalid user input is validated and corrected

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the correct directory
   - Check that all dependencies are installed

2. **API Key Issues**
   - Verify all API keys are correctly set in `.env`
   - Check API key permissions and quotas

3. **No Results Found**
   - Try different date ranges
   - Check if destination is supported by APIs
   - Use demo mode to test functionality

4. **Network Errors**
   - Check internet connection
   - Verify API endpoints are accessible
   - Try running in demo mode

### Getting Help

- Check the help: `python main.py --help`
- Verify environment: `python main.py --check-env`
- Run demo mode: `python main.py --demo`

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🙏 Acknowledgments

- [AutoGen](https://github.com/microsoft/autogen) for the agent framework
- [Amadeus](https://developers.amadeus.com/) for travel APIs
- [Duffel](https://duffel.com/) for flight search
- [OpenCage](https://opencagedata.com/) for geocoding
- [Google Gemini](https://ai.google.dev/) for AI capabilities

---

**Happy Travels! ✈️🌍**