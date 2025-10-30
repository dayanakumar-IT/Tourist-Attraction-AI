# Tourism AI – Multi-Agent Travel Optimization System 🌍✈️

An intelligent multi-agent AI system built with **Gemini LLM API** and the **LangGraph + LangChain framework**, designed to make travel planning smarter, safer, and more personalized.

---

## 🌟 Overview  

HelloLanka is your **next-gen travel companion**.  
Instead of scrolling through dozens of blogs, reviews, and apps, this system uses **specialized AI agents** that collaborate to design **personalized itineraries**—optimizing attractions, budgets, safety, inclusivity, and accessibility.  

Whether you're a family planning a vacation, a solo traveler, or a travel agency offering tailored packages, Tourism AI provides **efficient, reliable, and transparent travel solutions**.  
---

## 🤖 Agents in Action

We built multiple specialized agents that work together to produce a smart, Sri Lanka–aware itinerary:

🧭**Pre-Agent (pre_agent.py)** → Understands free-text interests, normalizes them to themes (e.g., beach, culture), and infers traveler profile.

🗺️ **Planner Agent (planner_agent.py)** → Geocodes places, picks POIs, sequences days, and generates 1–3 draft itineraries.

🌤️**Weather & Food Agent (weather_food_agent.py)** → Adds realistic weather hints, best-time-to-visit, and nearby restaurants from Google Places.

☔ **Weather-Aware Planner (weather_aware_planner.py)** → Adapts plans to weather (e.g., swap beaches on rainy days to museums/spa).

🚗 **Transport Agent (transport_agent.py)** → Optimizes travel legs between activities, estimates duration, distance, and cost (LKR).

🚆 **Train Booking Agent (train_booking_agent.py)** → Injects scenic Sri Lanka Railways options (Kandy ↔ Ella, Colombo ↔ Galle, etc.) with tips and class info.

🧭**Cultural Tips Agent (cultural_tips_agent.py)** → Adds dress code, etiquette, timing, and safety reminders tailored to activity and location.

---

## 💼 Commercial Pitch  

Tourism AI can transform how the travel industry operates:  

- **Travel Agencies** → Integrate as a SaaS platform to provide instant, AI-driven personalized itineraries.  
- **Online Travel Platforms (OTAs)** → License our API for smarter attraction & accommodation recommendations.  
- **Independent Travelers** → Subscription-based model for advanced trip planning and real-time updates.  
- **Government & Tourism Boards** → Use AI for safe, inclusive, and scam-free tourism promotion.  

👉 **The value?** Less planning time, safer travel, higher customer satisfaction, and better trust in tourism services.  

---

## ⚙️ How It Works  

1. User enters **destination + group preferences**.  
2. Each agent processes its **specialized task** (budget, safety, accessibility, etc.).  
3. Agents collaborate using **AutoGen’s multi-agent communication**.  
4. Final optimized plan is produced → **balanced, safe, and enjoyable itinerary**.  

---

## 🔮 Future Scope  

- Integration with **Google Maps & Booking APIs**  
- Dynamic **group conflict resolution** (e.g., mixing adventure + relaxation in a single day)  
- **Mobile app & chatbot** interfaces  
- 🧩 Personalized AI Chat Companion: Chatbot-style guide (web + mobile) to answer travel questions and adjust itineraries on the go.
- Smart Budget Prediction & Currency Conversion: AI forecasts real-time prices and suggests budget-friendly swaps using live exchange rates.
- AI Photography & Memory Journal: Uses generative AI to create visual travel logs, auto-tag photos, and suggest captions.
  
---

## 🏆 Tech Stack  

- **LLM:** Gemini API  
- **Framework:** LangChain & LangGraph
- **Language:** Python  
- **Environment:** Virtualenv
- **Backend Framework:** FastAPI
- **Frontend:** React
