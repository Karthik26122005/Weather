import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
from retry_requests import retry
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import joblib

def fetch_historical_weather_data(latitude, longitude, start_date, end_date):
    """Fetch historical weather data using the Open-Meteo API."""
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation", "rain", "wind_speed_10m", "wind_direction_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_hours"],
        "timezone": "auto"
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "precipitation": hourly.Variables(1).ValuesAsNumpy(),
        "rain": hourly.Variables(2).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(3).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(4).ValuesAsNumpy()
    }
    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Process daily data
    daily = response.Daily()
    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        ),
        "temperature_2m_max": daily.Variables(0).ValuesAsNumpy(),
        "temperature_2m_min": daily.Variables(1).ValuesAsNumpy(),
        "precipitation_hours": daily.Variables(2).ValuesAsNumpy()
    }
    daily_dataframe = pd.DataFrame(data=daily_data)

    return hourly_dataframe, daily_dataframe

class WeatherAIModel:
    def __init__(self, hourly_data, daily_data):
        self.hourly_data = hourly_data
        self.daily_data = daily_data
        self.model = None

    def preprocess_data(self):
        # Convert hourly data 'date' to datetime if it's not already
        self.hourly_data['date'] = pd.to_datetime(self.hourly_data['date'])
        
        # Extract date from datetime for joining
        self.hourly_data['date'] = self.hourly_data['date'].dt.date
        self.daily_data['date'] = pd.to_datetime(self.daily_data['date']).dt.date

        # Combine hourly and daily data
        daily_features = self.daily_data.set_index('date')
        self.combined_data = self.hourly_data.join(daily_features, on='date')

        # Create lag features
        for col in ['temperature_2m', 'precipitation', 'wind_speed_10m']:
            self.combined_data[f'{col}_lag_1'] = self.combined_data[col].shift(1)
            self.combined_data[f'{col}_lag_24'] = self.combined_data[col].shift(24)

        # Drop rows with NaN values
        self.combined_data.dropna(inplace=True)

    def train_model(self):
        features = ['temperature_2m', 'precipitation', 'wind_speed_10m', 'wind_direction_10m',
                    'temperature_2m_max', 'temperature_2m_min', 'precipitation_hours',
                    'temperature_2m_lag_1', 'precipitation_lag_1', 'wind_speed_10m_lag_1',
                    'temperature_2m_lag_24', 'precipitation_lag_24', 'wind_speed_10m_lag_24']
        
        target = 'temperature_2m'

        X = self.combined_data[features]
        y = self.combined_data[target]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

        # Evaluate the model
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f"Model Mean Squared Error: {mse}")

    def make_predictions(self, future_data):
        return self.model.predict(future_data)

    def assess_risk(self, predictions):
        risk_levels = []
        for pred in predictions:
            if pred > 35:
                risk_levels.append("High risk of heat-related issues")
            elif pred < 0:
                risk_levels.append("High risk of cold-related issues")
            elif pred > 30:
                risk_levels.append("Moderate risk of heat-related issues")
            elif pred < 5:
                risk_levels.append("Moderate risk of cold-related issues")
            else:
                risk_levels.append("Low risk")
        return risk_levels

    def strategic_decisions(self, predictions, risk_levels):
        decisions = []
        for pred, risk in zip(predictions, risk_levels):
            if "High risk" in risk:
                decisions.append("Issue severe weather warning")
            elif "Moderate risk" in risk:
                decisions.append("Issue weather advisory")
            else:
                decisions.append("No action needed")
        return decisions

    def save_model(self, filename):
        joblib.dump(self.model, filename)

    @staticmethod
    def load_model(filename):
        return joblib.load(filename)

# Main execution
if __name__ == "__main__":
    # Fetch historical weather data
    latitude = 11.0168  # Coimbatore, India
    longitude = 76.9558
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    print("Fetching historical weather data...")
    hourly_data, daily_data = fetch_historical_weather_data(latitude, longitude, start_date, end_date)
    
    print("Creating and training AI model...")
    ai_model = WeatherAIModel(hourly_data, daily_data)
    ai_model.preprocess_data()
    ai_model.train_model()

    # Make predictions for the next 24 hours
    print("Making predictions for the next 24 hours...")
    future_data = ai_model.combined_data.iloc[-24:][ai_model.model.feature_names_in_]
    predictions = ai_model.make_predictions(future_data)
    risk_levels = ai_model.assess_risk(predictions)
    strategic_decisions = ai_model.strategic_decisions(predictions, risk_levels)

    print("\nPredictions for the next 24 hours:")
    for i, (pred, risk, decision) in enumerate(zip(predictions, risk_levels, strategic_decisions)):
        print(f"Hour {i+1}: Predicted temperature: {pred:.2f}°C, Risk: {risk}, Decision: {decision}")

    # Save the model
    ai_model.save_model("weather_ai_model.joblib")
    print("\nModel saved as 'weather_ai_model.joblib'")

    # print("\nTo use the saved model in the future, you can load it with:")
    # print("loaded_model = WeatherAIModel.load_model('weather_ai_model.joblib')")