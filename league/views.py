from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from engine import player
from nba.models import Player, Injury
from league.models import PlayerList, DummyManager
from trade_analyzer.fiveStarMap import evaluate_trade_differential
from .trade_stats import CATEGORY_LABELS, NotEnoughGames, side_baseline, build_results

MAX_PLAYERS_PER_SIDE = 4  # change to 5 if the group decides to

# Create your views here.
def home(request):
    return render(request, 'index.html')

def roster_select(request):
    context = {"manager_list": list(DummyManager.objects.all()) }
    return render(request, "roster_select.html", context)

def roster(request, m_id):
    template = 'roster.html'
    pl = list(PlayerList.objects.all())
    manager = get_object_or_404(DummyManager, pk=m_id)

    playerA = player.Player(1, "A", "ABC", "FG", False)
    playerB = player.Player(2, "B", "ABC", ["FG", "SF"], False)

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
    return render(request, template, {"player_list": [playerA, playerB], "roster": roster_list, "db_pl": pl, "manager": manager})

def update_player(request, p_id):
    p = PlayerList.objects.get_player_by_id(p_id)
    if request.method == "POST":
        post = request.POST
        print(post)
        m_id = int(post.get("form_manager"))
        manager = get_object_or_404(DummyManager, pk=m_id)
        if post.get("action") == "remove":
            if p.manager.id == manager.id:
                p.toggle_status()
            else:
                print("Cannot remove another manager's player")
        else:
            p.add_to_roster(manager=manager)
    
    return redirect("roster", m_id=m_id) # TODO Change so that it does not trigger a full page refresh


def league(request):
    template = "placeholder.html"
    return render(request, template)

def scoring(request):
    template = "placeholder.html"
    return render(request, template)


def trade(request):
    """Trade evaluator page: pick players on each side, then show the star ratings."""
    context = {
        "players": Player.objects.filter(is_active=True).order_by("full_name"),
        "categories": CATEGORY_LABELS,
        "slots": range(MAX_PLAYERS_PER_SIDE),
        # Form defaults for a first visit (nothing picked yet).
        "give_slots": [""] * MAX_PLAYERS_PER_SIDE,
        "get_slots": [""] * MAX_PLAYERS_PER_SIDE,
        "selected_cats": list(CATEGORY_LABELS),
        "season_mode": "both",
        "last_n": "",
    }

    if request.method == "POST":
        # Read the form. Empty dropdowns come in as "", so skip them.
        give_ids = [x for x in request.POST.getlist("give") if x]
        get_ids = [x for x in request.POST.getlist("get") if x]
        cats = [c for c in request.POST.getlist("categories") if c in CATEGORY_LABELS]
        cats = cats or list(CATEGORY_LABELS)  # no boxes checked means use all
        season_mode = request.POST.get("season_mode", "both")
        last_n = int(request.POST.get("last_n") or 0) or None

                # Remember what the user picked so the form keeps it after submitting.
        context.update({
            "give_slots": request.POST.getlist("give"),
            "get_slots": request.POST.getlist("get"),
            "selected_cats": cats,
            "season_mode": season_mode,
            "last_n": request.POST.get("last_n", ""),
        })

        if not give_ids or not get_ids:
            context["error"] = "Pick at least one player on each side."
        elif set(give_ids) & set(get_ids):
            context["error"] = "The same player can't be on both sides."
        else:
            give = list(Player.objects.filter(id__in=give_ids))
            get = list(Player.objects.filter(id__in=get_ids))
            try:
                # "You get" goes first, so a positive difference means the user gains.
                result = evaluate_trade_differential(
                    side_baseline(get, season_mode, last_n, cats),
                    side_baseline(give, season_mode, last_n, cats),
                )
            except NotEnoughGames as e:
                context["error"] = str(e)
            else:
                context.update(build_results(result, cats))
                context["give_names"] = [p.full_name for p in give]
                context["get_names"] = [p.full_name for p in get]
                # Show an injury note for anyone not fully available.
                context["injuries"] = (Injury.objects
                                       .filter(player__in=give + get)
                                       .exclude(status=Injury.Status.AVAILABLE))

    return render(request, "trade.html", context)