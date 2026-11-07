from django.shortcuts import render


# Create your views here.
def home(request):
    return render(request, 'index.html')

def roster(request):
    template = 'roster.html'

    playerA = player.Player(1, "A", "ABC", "FG", "Healthy")
    playerB = player.Player(2, "B", "ABC", ["FG", "SF"], "Healthy")
    roster_list = {"PG": "Player A",
                   "SG": "Player B",
                   "SF": "Player C",
                   "PF": None,
                   "C": "Player D",
                   "G": "Player E",
                   "F": "Player F",
                   "UTIL": None,
                   "UTIL": None,
                   "UTIL": None,
                   "BN": "Player G"}
    return render(request, template, {"player_list": [playerA, playerB], "roster": roster_list})

def trade(request):
    template = "placeholder.html"
    return render(request, template)

def league(request):
    template = "placeholder.html"
    return render(request, template)

def scoring(request):
    template = "placeholder.html"
    return render(request, template)