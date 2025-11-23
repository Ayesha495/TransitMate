"""Train a recommender model using real user feedback data

Run from project root:
  python -m recommend.train_recommender
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transitmate.settings')  # Change 'config' to your project name

import django
django.setup()

# NOW we can import Django models
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

from recommend.models import TripRequest, Recommendation, Feedback  # Changed from .models

# Rest of your code stays the same...
# Get project root
project_root = Path(__file__).resolve().parent.parent
MODELS_DIR = project_root / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODELS_DIR / 'recommender.pkl'
META_PATH = MODELS_DIR / 'recommender-meta.json'


def feature_from_feedback(trip, recommendation, mode_pref_flags):
    """Extract features from real trip and recommendation data"""
    origin_len = len(trip.origin or '')
    dest_len = len(trip.destination or '')
    
    text = f"{trip.origin} {trip.destination}".lower()
    airport = 1 if 'airport' in text else 0
    
    try:
        hour = int((trip.preferred_time or '12:00').split(':')[0])
    except Exception:
        hour = 12
    
    mode_idx = {'Bus': 0, 'Metro': 1, 'RideShare': 2, 'Taxi': 3}.get(recommendation.mode, 4)
    
    pref_bus = 1 if mode_pref_flags.get('bus') else 0
    pref_metro = 1 if mode_pref_flags.get('metro') else 0
    pref_rideshare = 1 if mode_pref_flags.get('rideshare') else 0
    pref_taxi = 1 if mode_pref_flags.get('taxi') else 0
    
    eta_minutes = recommendation.eta_minutes or 0
    cost = float(recommendation.cost or 0.0)
    
    eta_normalized = min(eta_minutes / 60.0, 2.0)
    cost_normalized = min(cost / 20.0, 2.0)
    
    return [
        origin_len, dest_len, airport, hour, mode_idx,
        pref_bus, pref_metro, pref_rideshare, pref_taxi,
        eta_normalized, cost_normalized
    ]


def load_feedback_data():
    """Load real feedback data from database"""
    feedbacks = Feedback.objects.select_related('recommendation', 'recommendation__trip').all()
    
    if feedbacks.count() == 0:
        print("\n❌ ERROR: No feedback data found in database!")
        print("\nYou need to:")
        print("1. Start your Django server: python manage.py runserver")
        print("2. Open the TransitMate UI")
        print("3. Create trip requests")
        print("4. Get recommendations")
        print("5. Provide feedback (rate recommendations)")
        print("6. Then run this training script again")
        print("\nFor now, I'll create a baseline model with synthetic data...")
        return None, None, None
    
    print(f"✓ Found {feedbacks.count()} feedback records")
    
    samples = []
    for fb in feedbacks:
        rec = fb.recommendation
        trip = rec.trip
        
        mode_pref_flags = {}
        if trip.mode_preferences:
            for part in trip.mode_preferences.split(','):
                key = part.strip().lower()
                if key:
                    mode_pref_flags[key] = True
        
        features = feature_from_feedback(trip, rec, mode_pref_flags)
        score = (fb.rating - 1) / 4.0
        
        samples.append({
            'features': features,
            'score': score,
            'mode': rec.mode,
            'rating': fb.rating
        })
    
    df = pd.DataFrame(samples)
    feature_names = [
        'origin_len', 'dest_len', 'airport', 'hour', 'mode_idx',
        'pref_bus', 'pref_metro', 'pref_rideshare', 'pref_taxi',
        'eta_normalized', 'cost_normalized'
    ]
    
    X = pd.DataFrame(df['features'].tolist(), columns=feature_names)
    y = df['score']
    
    return X, y, df


def generate_synthetic_data(n=500):
    """Generate synthetic training data as fallback"""
    import random
    
    print("\nGenerating synthetic training data...")
    
    samples = []
    modes = ['Bus', 'Metro', 'RideShare', 'Taxi']
    places = ['Central Station', 'City Airport', 'North Park', 'East Mall', 'West End', 'University']
    
    for _ in range(n):
        origin = random.choice(places)
        destination = random.choice([p for p in places if p != origin])
        hour = random.randint(6, 22)
        
        mode_prefs = {
            'bus': random.choice([True, False]),
            'metro': random.choice([True, False]),
            'rideshare': random.choice([True, False]),
            'taxi': random.choice([True, False]),
        }
        
        for mode in modes:
            origin_len = len(origin)
            dest_len = len(destination)
            airport = 1 if 'airport' in (origin + destination).lower() else 0
            mode_idx = {'Bus': 0, 'Metro': 1, 'RideShare': 2, 'Taxi': 3}.get(mode, 4)
            
            # Synthetic ETA and cost
            eta = random.randint(15, 60)
            cost = random.uniform(1.5, 15.0)
            eta_norm = min(eta / 60.0, 2.0)
            cost_norm = min(cost / 20.0, 2.0)
            
            # Synthetic score
            score = 0.5
            if mode == 'Metro':
                score += 0.2
            if mode == 'Taxi' and airport:
                score += 0.3
            if eta < 25:
                score += 0.1
            if cost < 5:
                score += 0.1
            
            score = max(0.0, min(1.0, score))
            
            features = [
                origin_len, dest_len, airport, hour, mode_idx,
                1 if mode_prefs['bus'] else 0,
                1 if mode_prefs['metro'] else 0,
                1 if mode_prefs['rideshare'] else 0,
                1 if mode_prefs['taxi'] else 0,
                eta_norm, cost_norm
            ]
            
            samples.append({'features': features, 'score': score})
    
    df = pd.DataFrame(samples)
    feature_names = [
        'origin_len', 'dest_len', 'airport', 'hour', 'mode_idx',
        'pref_bus', 'pref_metro', 'pref_rideshare', 'pref_taxi',
        'eta_normalized', 'cost_normalized'
    ]
    
    X = pd.DataFrame(df['features'].tolist(), columns=feature_names)
    y = df['score']
    
    return X, y, df


def train():
    print('\n🚀 TransitMate Model Training')
    print('=' * 50)
    
    # Try to load real feedback data
    X, y, df = load_feedback_data()
    
    # If no real data, use synthetic
    if X is None:
        X, y, df = generate_synthetic_data()
        data_source = 'synthetic'
    else:
        data_source = 'real'
        print(f"✓ Training samples: {len(X)}")
        print(f"✓ Average rating: {df['rating'].mean():.2f}")
        print(f"✓ Mode distribution:\n{df['mode'].value_counts()}")
        
        if len(X) < 20:
            print(f"\n⚠️  WARNING: Only {len(X)} samples available.")
            print("   Model may not be very accurate. Collect more feedback!")
    
    # Split data
    if len(X) >= 10:
        test_size = min(0.2, max(0.1, 5 / len(X)))
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
        print("⚠️  Too few samples for train/test split. Using all data for both.")
    
    print(f'\n🔧 Training RandomForestRegressor on {len(X_train)} samples...')
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=max(2, min(5, len(X_train) // 10)),
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    train_preds = model.predict(X_train)
    test_preds = model.predict(X_test)
    train_mse = mean_squared_error(y_train, train_preds)
    test_mse = mean_squared_error(y_test, test_preds)
    
    print(f'\n📊 Results:')
    print(f'   Training MSE: {train_mse:.5f}')
    print(f'   Test MSE: {test_mse:.5f}')
    
    # Feature importance
    if data_source == 'real':
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print('\n📈 Top Feature Importance:')
        print(feature_importance.head(5).to_string(index=False))
    
    # Save model
    joblib.dump(model, MODEL_PATH)
    
    # Save metadata
    import json
    meta = {
        'features': list(X.columns),
        'mode_mapping': {'Bus': 0, 'Metro': 1, 'RideShare': 2, 'Taxi': 3},
        'training_samples': len(X),
        'test_mse': float(test_mse),
        'data_source': data_source,
        'trained_at': pd.Timestamp.now().isoformat()
    }
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f'\n✅ Model saved to: {MODEL_PATH}')
    print(f'✅ Metadata saved to: {META_PATH}')
    print(f'\n🎉 Training complete! Model is ready to use.')
    
    if data_source == 'synthetic':
        print('\n💡 TIP: This is a baseline model trained on synthetic data.')
        print('   Collect real user feedback and retrain for better results!')


if __name__ == '__main__':
    train()