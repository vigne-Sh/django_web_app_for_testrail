from django import forms
from django.forms import fields
from .models import update_release, mailer_db

class edit_releaseform(forms.ModelForm):
    class Meta:
        model = update_release
        fields = "__all__"

class edit_mailerinfo(forms.ModelForm):
    class Meta:
        model = mailer_db
        fields = "__all__"
