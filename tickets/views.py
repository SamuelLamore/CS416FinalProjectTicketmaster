from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
import requests
from datetime import datetime
from .models import FavoriteEvent
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
# Create your views here.

def ticketmaster_request(city_name, class_name):
    try:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "city": city_name,
            "classificationName": class_name,
            "apikey": "PECrBo7OkTkaSFuNNEfTjBAblJlSW7Z4",
            "sort": "date,asc"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return None


def getHighestResImage(card):
    maxHeight = 0
    curMax = 0
    for i, image in enumerate(card["images"]):
        if image["height"] > maxHeight:
            maxHeight = image["height"]
            curMax = i
    return card["images"][curMax]["url"]


def processCard(card, cardList, user, auth):
    if auth and FavoriteEvent.objects.filter(event_id=card["id"], user=user).exists():
        favorited = True
    else:
        favorited = False

    if "localTime" in card["dates"]["start"]:
        time_str = card["dates"]["start"]["localTime"]
        if "AM" in time_str or "PM" in time_str:
            time = datetime.strptime(time_str, "%I:%M %p")
        else:
            time = datetime.strptime(time_str, "%H:%M:%S")
        eventHour = time.strftime("%I:%M %p").lstrip("0")
    else:
        eventHour = "All Day"

    if "dateTime" in card["dates"]["start"]:
        eventDate = datetime.strptime(card["dates"]["start"]["dateTime"], "%Y-%m-%dT%H:%M:%SZ")
    else:
        eventDate = datetime.strptime(card["dates"]["start"]["localDate"], "%Y-%m-%d")
    cardInfo = {
        "eventImage": getHighestResImage(card),
        "eventName": card["name"],
        "eventDate": eventDate,
        "venueName": card["_embedded"]["venues"][0]["name"],
        "venueCity": card["_embedded"]["venues"][0]["city"]["name"],
        "venueState": card["_embedded"]["venues"][0]["state"]["name"],
        "venueAddress": card["_embedded"]["venues"][0]["address"]["line1"],
        "eventURL": card["url"],
        "eventHour": eventHour,
        "eventID": card["id"],
        "favorited": favorited
    }
    cardList.append(cardInfo)

def ticketmaster(request):
    # get city name and class name
    # handle case where theyre null
    # city_name = request.GET['city']?
    cardList = []
    renderCards = False
    cityEmpty = False
    classEmpty = False
    city_name = ""
    class_name = ""
    if request.method == "POST":
        city_name = request.POST["city"]
        class_name = request.POST["class"]
        if city_name == "":
            cityEmpty = True
        if class_name == "":
            classEmpty = True
        if cityEmpty is False and classEmpty is False:
            renderCards = True
            data = ticketmaster_request(city_name, class_name)
            if data is not None and "_embedded" in data:
                # print(data)
                for card in data["_embedded"]["events"]:
                    processCard(card, cardList, request.user, request.user.is_authenticated)

    context = {
        "renderCards": renderCards,
        "cityEmpty": cityEmpty,
        "classEmpty": classEmpty,
        "cityName": city_name,
        "className": class_name,
        "cards": cardList,
        "numCards": len(cardList),
    }
    return render(request, 'ticketmaster.html', context)




def ticketmaster_request_by_id(id):
    try:
        url = f"https://app.ticketmaster.com/discovery/v2/events/{id}.json"
        params = {
            "apikey": "PECrBo7OkTkaSFuNNEfTjBAblJlSW7Z4"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return None



def get_max_priority(user):
    return FavoriteEvent.objects.filter(user=user).order_by("-displayPriority").values_list("displayPriority", flat=True).first()


def recalculate_priorities(user):
    favorites = FavoriteEvent.objects.filter(user=user, displayOnProfile=True).order_by("displayPriority")
    for i, fav in enumerate(favorites):
        if fav.displayPriority != i+1:
            fav.displayPriority = i+1
            fav.save()

def add_or_remove_favorite(request, eventid):
    if FavoriteEvent.objects.filter(event_id=eventid, user=request.user).exists():
        FavoriteEvent.objects.filter(event_id=eventid, user=request.user).delete()
        action = "removed"
    else:
        max_priority = get_max_priority(request.user)
        if max_priority is None:
            max_priority = 0
        FavoriteEvent.objects.create(event_id=eventid, user=request.user, displayPriority=max_priority+1, displayOnProfile=True)
        action = "added"

    # ensure the priority values have no gaps
    recalculate_priorities(request.user)

    return JsonResponse({
        "id": eventid,
        "action": action,
    })


def register_view(request):
    user_form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if user_form.is_valid():
            user_form.save()
            return redirect('login')
    context = {'form': user_form}
    return render(request, 'register.html', context)


def login_view(request):
    user_form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        if user_form.is_valid():
            user = user_form.get_user()
            login(request, user)
            return redirect('ticketmaster')
    context = {'form': user_form}
    return render(request, 'login.html', context)


@login_required(login_url='login')
def logout_view(request):
    logout(request)
    return redirect('login')


def profile_view(request, user):
    if request.method == 'POST':
        if "type" in request.POST:
            obj = FavoriteEvent.objects.get(user=request.user, event_id=request.POST["event-id"])
            if obj is not None:
                if request.POST["type"] == "up":
                    swap_obj = FavoriteEvent.objects.get(user=request.user, displayPriority=obj.displayPriority-1)
                    if swap_obj is not None:
                        swap_obj.displayPriority = obj.displayPriority
                        swap_obj.save()
                    obj.displayPriority -= 1
                    obj.save()
                elif request.POST["type"] == "down":
                    swap_obj = FavoriteEvent.objects.get(user=request.user, displayPriority=obj.displayPriority+1)
                    if swap_obj is not None:
                        swap_obj.displayPriority = obj.displayPriority
                        swap_obj.save()
                    obj.displayPriority += 1
                    obj.save()
                elif request.POST["type"] == "delete":
                    obj.delete()
                elif request.POST["type"] == "display":
                    obj.displayOnProfile = not obj.displayOnProfile
                    obj.displayPriority = get_max_priority(request.user) + 1
                    obj.save()
                recalculate_priorities(request.user)
                messages.info(request, "edit")
            return redirect(request.path)
        else:
            return redirect(f"../{request.POST["user"]}")

    cardList = []
    maxPriority = 1
    userExists = User.objects.filter(username=user).exists()
    if userExists:
        profile_user = User.objects.get(username=user)
        # if user exists, we need to create their (public) favorited cards
        if request.user == profile_user:
            favorites = FavoriteEvent.objects.filter(user=profile_user)
        else:
            favorites = FavoriteEvent.objects.filter(user=profile_user, displayOnProfile=True)
        event_info = favorites.order_by("-displayOnProfile", "displayPriority").values_list("event_id", "displayPriority", "displayOnProfile")

        if event_info is not None and len(event_info) > 0:
            for event_id, priority, display in event_info:
                card = ticketmaster_request_by_id(event_id)
                if card is not None:
                    processCard(card, cardList, request.user, request.user.is_authenticated)
                    cardList[-1]["display"] = display
                    cardList[-1]["priority"] = priority
                    if display and priority > maxPriority:
                        maxPriority = priority

    context = {
        "userName": user,
        "userExists": userExists,
        "cards": cardList,
        "numCards": len(cardList),
        "maxPriority": maxPriority,
        "numDisplayed": maxPriority+1,
    }
    return render(request, 'profile.html', context)


def update_fav_priority(request, neg, eventid):
    if FavoriteEvent.objects.filter(event_id=eventid, user=request.user).exists():
        FavoriteEvent.objects.filter(event_id=eventid, user=request.user).delete()
    else:
        max_priority = get_max_priority(request.user)
        if max_priority is None:
            max_priority = 0
        FavoriteEvent.objects.create(event_id=eventid, user=request.user, displayPriority=max_priority+1, displayOnProfile=True)

    # ensure the priority values have no gaps
    favorites = FavoriteEvent.objects.filter(user=request.user, displayOnProfile=True).order_by("displayPriority")
    for i, fav in enumerate(favorites):
        if fav.displayPriority != i+1:
            fav.displayPriority = i+1
            fav.save()

    return JsonResponse({
        "id": eventid,
    })