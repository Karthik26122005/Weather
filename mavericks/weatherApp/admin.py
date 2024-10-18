from django.contrib import admin
from django.db import models
from weatherApp.models import Profile

# Register your models here.
class ProfilesAdmin(admin.ModelAdmin):
    list_display = (
        'user','first_name','last_name','username','email','address','contact','profile_picture'
    )
    list_filter = ('contact','user','first_name','last_name','username')
    search_fields = ('email','first_name','last_name','username','contact')
admin.site.register(Profile,ProfilesAdmin)