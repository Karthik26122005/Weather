#models.py file

from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    contact = models.CharField(max_length=15)

class WeatherData(models.Model):
    city = models.CharField(max_length=100)
    temperature = models.FloatField()
    humidity = models.FloatField()
    wind_speed = models.FloatField()
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city} - {self.temperature}°C"

class BusinessData(models.Model):
    business_name = models.CharField(max_length=255)
    operation_type = models.CharField(max_length=100)
    revenue_loss = models.FloatField()
    risk_level = models.CharField(max_length=50)
    weather_data = models.ForeignKey(WeatherData, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.business_name} - {self.risk_level}"

class RiskAssessment(models.Model):
    business_data = models.OneToOneField(BusinessData, on_delete=models.CASCADE)
    risk_score = models.FloatField()
    recommendation = models.TextField()

    def __str__(self):
        return f"Risk Score: {self.risk_score} for {self.business_data.business_name}"
