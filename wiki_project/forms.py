from django import forms

class myform(forms.Form):
    search = forms.CharField(label="search")