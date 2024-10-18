from django.shortcuts import render,redirect
from django.contrib.auth import login, authenticate,logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import NewUserForm
from .models import WeatherData, BusinessData, RiskAssessment
import requests,pandas as pd
from datetime import datetime, timedelta


# Create your views here.
def register_request(request):
    if request.method == "POST":
        print(request.POST)
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('/home')
        else:
            print(form.errors)
    else:
        form = NewUserForm()

    # Display form errors
    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, f"Error in {field}: {error}")
            
    return render(request,"WeatherApp/signup.html",{"form":form})

def userlogin(request):
    if request.user.is_authenticated:
        return redirect('/home')
    else:
        if request.method == 'POST':
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                user=authenticate(request,username=username,password=password)
                if user is not None:
                    login(request,user)
                    if 'admin_access' in request.POST and request.POST['admin_access'] == 'on':
                        # If the user is an admin, redirect to the Django admin site
                        return redirect('/admin')
                    messages.success(request, 'Login successful.')
                    return redirect('/home')  
            else:
                messages.error(request,'Login Failed !!. Please correct the errors') 
        else:
            form = AuthenticationForm()
    
        return render(request, 'WeatherApp/login.html', {'form': form})

def logoutUser(request):
    logout(request)
    return redirect('login')



# API for pulling weather data
# def fetch_weather_data(city):
#     city="coimbatore"
#     api_key = '39e988e2fb55418c89445738230912'
#     url = f'https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=1&aqi=no&alerts=yes'
#     response = requests.get(url)
#     data = response.json()
#     weather = {
#         'city': data['name'],
#         'temperature': data['main']['temp'],
#         'humidity': data['main']['humidity'],
#         'wind_speed': data['wind']['speed'],
#         'description': data['weather'][0]['description'],
#     }
#     return weather


# def dashboard(request):
#     weather_data = WeatherData.objects.all()
#     business_data = BusinessData.objects.all()
#     risk_assessment = RiskAssessment.objects.all()
    
#     context = {
#         'weather_data': weather_data,
#         'business_data': business_data,
#         'risk_assessment': risk_assessment,
#     }
    
#     return render(request, 'weatherApp/home.html', context)


# def update_weather(request, city):
#     weather = fetch_weather_data(city)
#     WeatherData.objects.create(
#         city=weather['city'],
#         temperature=weather['temperature'],
#         humidity=weather['humidity'],
#         wind_speed=weather['wind_speed'],
#         description=weather['description']
#     )
#     return dashboard(request)


def fetch_weather_data(city="Coimbatore"):
    api_key = '39e988e2fb55418c89445738230912'  
    api_endpoint = f'https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=1&aqi=no&alerts=yes'
    response = requests.get(api_endpoint)
    data = response.json()

    hourly_forecast = []
    hourlyForecast = []
    for forecast in data['forecast']['forecastday'][0]['hour']:
        time_utc = datetime.strptime(forecast['time'], '%Y-%m-%d %H:%M')
        utc_offset = data.get('location', {}).get('utc_offset', 0)
        time_local = time_utc + timedelta(hours=utc_offset)
        formatted_time = time_local.strftime('%I:%M %p - ') + (time_local + timedelta(hours=1)).strftime('%I:%M %p')
        
        weather_info = {
            'time': formatted_time,
            'temperature': forecast['temp_c'],
            'chance_of_rain': forecast.get('chance_of_rain', 0),
            'wind_speed': forecast['wind_kph'],
            'uv_index': forecast.get('uv', 0),
        }
        hourly_forecast.append(weather_info)
        
        weatherInfo = {
            'time': forecast['time'],
            'temperature': forecast['temp_c'],
            'chance_of_rain': forecast.get('chance_of_rain', 0),
            'wind_speed': forecast['wind_kph'],
            'uv_index': forecast.get('uv', 0),
        }
        hourlyForecast.append(weatherInfo)
    
    # Convert to DataFrame for further processing
    df = pd.DataFrame(hourlyForecast)
    df['time'] = pd.to_datetime(df['time'])
    
    # Scoring system
    temperatureWeightScores = {0: 40, 1: 50, 2: 60, 3: 70, 4: 80, 5: 100, 6: 80, 7: 50, 8: 40}
    uvIndexWeightScores = {0: 100, 1: 90, 2: 80, 3: 70, 4: 60}
    rainWeight = 0.65
    temperatureWeight = 0.15
    windSpeedWeight = 0.05
    uvIndexWeight = 0.1

    # Calculate the score for each time interval
    df['score'] = (
        (100 - df['chance_of_rain']) * rainWeight +
        df['temperature'].apply(lambda x: temperatureWeightScores[next(i for i, v in enumerate([3, 7, 12, 17, 22, 27, 32, 35, 37]) if x < v)]) * temperatureWeight +
        (10 - df['wind_speed']) * windSpeedWeight +
        df['uv_index'].apply(lambda x: uvIndexWeightScores[next((i for i, v in enumerate([2, 5, 7, 10]) if x <= v), len(uvIndexWeightScores) - 1)]) * uvIndexWeight
    )

    # Normalize the score
    minScore = df['score'].min()
    maxScore = df['score'].max()
    df['normalized_score'] = ((df['score'] - minScore) / (maxScore - minScore)) * 100

    # Select best time intervals based on the score
    startHour = 7
    endHour = 17
    topHours = 8
    percentageRadius = 10
    currentDate = datetime.now().strftime('%Y-%m-%d')
    startTimeStr = f'{currentDate} {startHour:02d}:00'
    endTimeStr = f'{currentDate} {endHour:02d}:00'

    bestTimeDf = df[df['time'].between(startTimeStr, endTimeStr)]
    bestTimeDf = bestTimeDf.sort_values(by='normalized_score', ascending=False)
    selectedHours = bestTimeDf.head(topHours)

    # Get top time intervals for display
    selectedIntervals = selectedHours.sort_values(by='time', ascending=True)
    selectedIntervals['intTime'] = selectedIntervals['time'].dt.hour

    # Get sorted time intervals
    timeIntervals = []
    for _, row in selectedIntervals.iterrows():
        timeIntervals.append(row['time'].strftime('%I:%M %p - ') + (row['time'] + timedelta(hours=1)).strftime('%I:%M %p'))

    return hourly_forecast, timeIntervals

# Dashboard view
def dashboard(request):
    weather_data = WeatherData.objects.all()
    business_data = BusinessData.objects.all()
    risk_assessment = RiskAssessment.objects.all()

    # Fetch weather forecast and best time intervals
    hourly_forecast, time_intervals = fetch_weather_data()

    context = {
        'weather_data': weather_data,
        'business_data': business_data,
        'risk_assessment': risk_assessment,
        'hourly_forecast': hourly_forecast,  # Send hourly forecast data to the template
        'time_intervals': time_intervals,    # Best time intervals for weather conditions
    }
    
    return render(request, 'weatherApp/home.html', context)
