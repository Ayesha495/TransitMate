# TransitMate - AI-Enhanced Transportation Recommendation System

> Intelligent route planning powered by Machine Learning and real-time routing data

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18.x-61dafb.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-30%20passing-success.svg)](tests/)

## About

TransitMate is an intelligent transportation recommendation platform that helps travelers in Pakistan find the best routes between cities. Using **Machine Learning** and **OpenRouteService API**, it provides personalized recommendations for Bus, Metro, RideShare, and Taxi options based on time, cost, and user preferences.

### Key Features

- **ML-Powered Recommendations** - Random Forest model learns from user feedback
- **Real-Time Routing** - Live route data from OpenRouteService API
- **Cost Estimation** - Accurate pricing in Pakistani Rupees (PKR)
- **Interactive Maps** - Leaflet-based visualization with route polylines
- **Feedback Loop** - Continuous learning from user ratings
- **Modern UI** - Responsive React interface with Tailwind CSS
- **Model Retraining** - Background training on accumulated feedback

---

## Screenshots

### Search Interface
<img width="554" height="258" alt="image" src="https://github.com/user-attachments/assets/281235fc-596d-4eda-b639-e904a10fc716" />
<img width="553" height="276" alt="image" src="https://github.com/user-attachments/assets/0f61d489-a1a6-4df6-b2f7-8b508f761437" />

### Recommendations with Interactive Map


### Feedback Modal
<img width="553" height="263" alt="image" src="https://github.com/user-attachments/assets/11c65370-66fe-42f5-9333-80d78a495d8d" />


---

## Architecture

```
┌─────────────────┐
│   React SPA     │  ← User Interface
└────────┬────────┘
         │ REST API
         ▼
┌─────────────────┐
│  Django Backend │  ← Business Logic
└────────┬────────┘
         │
    ┌────┴────┬─────────┬────────────┐
    ▼         ▼         ▼            ▼
[SQLite] [ML Model] [ORS API] [Leaflet Maps]
```

### Tech Stack

**Frontend:**
- React 18 + Vite
- Tailwind CSS
- Lucide React Icons
- Leaflet.js Maps

**Backend:**
- Python 3.10+
- Django 4.2
- Django REST Framework
- OpenRouteService Client

**Machine Learning:**
- scikit-learn (Random Forest)
- pandas & numpy
- joblib (Model persistence)

**Database:**
- SQLite (Development)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn
- Git

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/Ayesha495/TransitMate.git
cd TransitMate
```

#### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
# Add to transitmate/settings.py:
ORS_API_KEY = 'your-openrouteservice-api-key'

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start Django server
python manage.py runserver
```

Backend runs at `http://localhost:8000`

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at `http://localhost:5173`

#### 4. Get OpenRouteService API Key

1. Visit [OpenRouteService](https://openrouteservice.org/dev/#/signup)
2. Create free account
3. Generate API key
4. Add to `settings.py`

**Free Tier:** 2,000 requests/day, no credit card required

---

## Usage

### Basic Trip Search

1. Enter **origin** and **destination** (e.g., "Islamabad" → "Lahore")
2. Select **transportation modes** (Bus, Metro, RideShare, Taxi)
3. Optionally set **preferred time**
4. Click **"Get Routes"**
5. View ranked recommendations with ETA, cost, and ML confidence score

### View Route Map

1. Click **"Map"** button on any recommendation
2. View interactive map with route polyline
3. See start/end markers and distance info

### Provide Feedback

1. Click **"Rate"** button on recommendation
2. Select rating (1-5 stars)
3. Optionally add comment
4. Submit to help improve ML model

---

## Testing

Run comprehensive test suite:

```bash
# Run all tests
python manage.py test recommend

```

**Test Coverage:** 85%+ (30 test cases)

Tests include:
- Model tests (UserProfile, TripRequest, Recommendation, Feedback)
- Feature engineering tests
- API endpoint tests
- ML recommendation engine tests
- Integration tests

---

## API Documentation

### Base URL
```
http://localhost:8000/api
```

### Endpoints

#### Create Trip Request
```http
POST /api/trip_requests/
Content-Type: application/json

{
  "origin": "Islamabad",
  "destination": "Lahore",
  "preferred_time": "09:00",
  "mode_preferences": "bus,metro,rideshare"
}
```

#### Get Recommendations
```http
GET /api/recommendations/?trip_id={id}&use_ml=true
```

#### Submit Feedback
```http
POST /api/feedback/
Content-Type: application/json

{
  "trip_id": 1,
  "mode": "Bus",
  "rating": 5,
  "comment": "Excellent route!",
  "eta_minutes": 240,
  "cost": 1200.0,
  "score": 0.87
}
```

#### Get Map Data
```http
GET /api/map-data/?trip_id={id}&mode=Bus
```

#### Retrain Model
```http
POST /api/retrain/
```

---

## Machine Learning

### Model Architecture

- **Algorithm:** Random Forest Regressor
- **Features:** 11 engineered features (origin/dest length, airport flag, hour, mode preferences, normalized ETA/cost)
- **Target:** User satisfaction score (0-1 scale from 1-5 star ratings)
- **Training:** Supervised learning on user feedback data

### Feature Engineering

```python
Features = [
    origin_length,           # Proxy for city size
    destination_length,      # Proxy for city size
    airport_flag,           # Binary: airport in route?
    departure_hour,         # Time of day (0-23)
    mode_index,             # Encoded mode (0-3)
    pref_bus,               # User preference flags
    pref_metro,
    pref_rideshare,
    pref_taxi,
    eta_normalized,         # Minutes/60, capped at 2.0
    cost_normalized         # PKR/5000, capped at 2.0
]
```

### Training Pipeline

```bash
# Trigger retraining (requires 20+ feedback samples)
python -m recommend.train_recommender

# Or via API
curl -X POST http://localhost:8000/api/retrain/
```

Model saved to `models/recommender.pkl`

---

## Project Structure

```
transitmate/
├── recommend/              # Django app
│   ├── models.py          # Database models
│   ├── views.py           # API views & ML logic
│   ├── serializers.py     # DRF serializers
│   ├── tests.py           # Test suite (30 tests)
│   └── train_recommender.py  # ML training script
├── frontend/              # React app
│   ├── src/
│   │   ├── App.jsx        # Main component
│   │   └── index.css      # Tailwind styles
│   └── package.json
├── models/                # ML models
│   ├── recommender.pkl    # Trained model
│   └── recommender-meta.json
├── docs/                  # Documentation
│   ├── SRS.md            # IEEE Requirements
│   ├── UseCases.md       # Use case diagrams
│   └── API_DOCS.md       # API documentation
├── requirements.txt       # Python dependencies
├── manage.py             # Django management
└── README.md             # This file
```

---

##  Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Development Guidelines

- Follow PEP 8 (Python) and Airbnb (JavaScript) style guides
- Write tests for new features
- Update documentation
- Maintain >80% test coverage

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## Author

**Ayesha**
- GitHub: [@Ayesha495](https://github.com/Ayesha495)
- Institution: Riphah
- Course: Generative AI Software Development
- Semester: Fall 2025

---

##  Project Stats

- **Lines of Code:** ~3,000+ (Python + JavaScript)
- **Test Coverage:** 85%+
- **API Endpoints:** 5
- **ML Features:** 11
- **Development Time:** 8 weeks
- **Tests:** 30 comprehensive test cases

---

## Star History

If you find this project useful, please consider giving it a ⭐!

---

**Made with ❤️ using Django, React, and Machine Learning** "React".
