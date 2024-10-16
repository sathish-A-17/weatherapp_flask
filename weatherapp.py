import geocoder
from flask import Flask, render_template, request
import requests
import datetime
from datetime import timezone

app = Flask(__name__)

API_KEY = 'your_api_key'
API_URL = 'http://api.openweathermap.org/data/2.5/weather?'
FORECAST_URL = 'http://api.openweathermap.org/data/2.5/forecast?'

def get_weather_by_city(city):
    params = {
        'appid': API_KEY,
        'q': city,
        'units': 'metric'
    }
    response = requests.get(API_URL, params=params)
    return response.json()

def get_weather_by_location(latitude, longitude):
    complete_url = f"{API_URL}lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric"
    response = requests.get(complete_url)
    return response.json()


def get_user_location():
    g = geocoder.ip('me')
    location = g.latlng
    latitude = location[0]
    longitude = location[1]
    return latitude, longitude


def get_forecast(city):
    forecast_url = f"{FORECAST_URL}q={city}&appid={API_KEY}&units=metric"
    response = requests.get(forecast_url)
    return response.json()


def extract_hourly_forecast(forecast_data):
    current_time = datetime.datetime.now(timezone.utc)
    hourly_forecast = []

    if 'list' in forecast_data:
        for forecast in forecast_data['list']:
            forecast_time = datetime.datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            forecast_time = forecast_time.replace(tzinfo=timezone.utc)

            if forecast_time <= current_time + datetime.timedelta(hours=24):
                hourly_forecast.append({
                    'time': forecast_time.strftime("%H:%M"),
                    'temp': round(forecast['main']['temp'], 1),
                    'weather': forecast['weather'][0]['description'],
                    'icon': forecast['weather'][0]['icon'],
                    'wind_speed': forecast['wind']['speed'],
                    'gust': forecast['wind'].get('gust', 'N/A'),
                })

    return hourly_forecast[:5]


def extract_daily_forecast(forecast_data):
    daily_forecast = {}

    if 'list' in forecast_data:
        for forecast in forecast_data['list']:
            forecast_time = datetime.datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            date_str = forecast_time.date()

            if len(daily_forecast) >= 5:
                break

            if date_str not in daily_forecast:
                daily_forecast[date_str] = {
                    'temp_max': round(forecast['main']['temp_max']),
                    'temp_min': round(forecast['main']['temp_min']),
                    'weather': forecast['weather'][0]['description'],
                    'icon': forecast['weather'][0]['icon'],
                    'humidity': forecast['main']['humidity'],
                    'wind_speed': forecast['wind']['speed'],
                    'gust': forecast['wind'].get('gust', 'N/A'),
                }
            else:
                daily_forecast[date_str]['temp_max'] = max(daily_forecast[date_str]['temp_max'],
                                                           round(forecast['main']['temp_max'], 1))
                daily_forecast[date_str]['temp_min'] = min(daily_forecast[date_str]['temp_min'],
                                                           round(forecast['main']['temp_min'], 1))

    return [{'date': date, **details} for date, details in daily_forecast.items() if
            date <= datetime.datetime.now().date() + datetime.timedelta(days=5)]


@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = None
    latitude, longitude = get_user_location()
    weather_data = get_weather_by_location(latitude, longitude)
    forecast_data = get_forecast(weather_data['name'])
    hourly_forecast = extract_hourly_forecast(forecast_data)
    daily_forecast = extract_daily_forecast(forecast_data)
    if request.method == 'POST':
        city = request.form.get('city')
        selected_date = request.form.get('date')
        if city:
            weather_data = get_weather_by_city(city)
            forecast_data = get_forecast(city)
            hourly_forecast = extract_hourly_forecast(forecast_data)
            daily_forecast = extract_daily_forecast(forecast_data)

    if weather_data and weather_data.get('cod') != 200:
        error_message = weather_data.get('message', 'An error occurred while retrieving weather data.')

    return render_template('index.html', weather=weather_data, hourly_forecast=hourly_forecast,
                       daily_forecast=daily_forecast, error=error_message)


if __name__ == '__main__':
    app.run(debug=True)

