from django.shortcuts import render
from engine import player

# Create your views here.
def home(request):
    return render(request, 'index.html')

def roster(request):
    template = 'placeholder.html'
    return render(request, template)

def trade(request):
    template = "placeholder.html"
    return render(request, template)

def league(request):
    template = "placeholder.html"
    return render(request, template)

def scoring(request):
    template = "placeholder.html"
    return render(request, template)