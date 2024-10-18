from django.forms import Form
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from .models import Profile

        
class NewUserForm(UserCreationForm):
	email = forms.EmailField(required=True)

	class Meta:
		model = User
		fields = ("username", "email", "password1", "password2")

	def save(self, commit=True):
		user = super(NewUserForm, self).save(commit=False)
		user.email = self.cleaned_data['email']
		if commit:
			user.save()
		return user

class ProfileForm(forms.ModelForm):
    # username = forms.CharField(max_length=100)
    # email = forms.EmailField()
    current_password = forms.CharField(widget=forms.PasswordInput(), label='Current Password', required=False)
    new_password = forms.CharField(widget=forms.PasswordInput(), label='New Password', required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label='Confirm Password', required=False)

    class Meta:
        model = Profile
        fields = ['profile_picture', 'first_name', 'last_name', 'username', 'email', 'address', 'contact']
        
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
       
        self.fields['username'].initial = self.instance.user.username
        self.fields['email'].initial = self.instance.user.email

class ProfilePasswordChangeForm(PasswordChangeForm):
    class Meta:
        model = User
        fields = []