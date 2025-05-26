import datetime
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.db import transaction
from .models import User, Produce
from django.http import JsonResponse

from .forms import CropRecommendationForm, FertilizerPredictionForm, UserInputForm, CropProduceListForm
import pickle
import numpy as np
from django.template.defaulttags import register
from .functions import getWeatherDetails, getAgroNews, getFertilizerRecommendation, getMarketPricesAllStates, GetResponse
import base64
import os
import json 
from google import genai
from google.genai import types
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load models once at startup with error handling
try:
    cropRecommendationModel = pickle.load(open('model_code/CropRecommend.pkl', 'rb'))
    fertilizerRecommendModel = pickle.load(open('model_code/Fertilizer.pkl', 'rb'))
except Exception as e:
    logger.error(f"Failed to load models: {str(e)}")
    cropRecommendationModel = None
    fertilizerRecommendModel = None

@register.filter
def get_range(value):
    return range(value)

@register.filter
def index(indexable, i):
    return indexable[i]

def getDetailsFromUID(id):
    cache_key = f'user_{id}'
    user = cache.get(cache_key)
    if not user:
        try:
            user = User.objects.get(id=id)
            cache.set(cache_key, user, timeout=300)  # Cache for 5 minutes
        except User.DoesNotExist:
            logger.error(f"User with id {id} not found")
            raise
    return user

def e404_page(request):
    error_message = request.session.get("error_message", "An error occurred")
    return render(request, "dash/404.html", {"errormsg": error_message})

def home_page(request):
    try:
        id = request.session.get("member_logged_id")
        if not id:
            raise ValueError("User not logged in")

        userlogged = getDetailsFromUID(id)
        
        my_products = Produce.objects.filter(farmerid=userlogged.id)
        public_products = Produce.objects.all()
        
        # Cache expensive operations
        weather_cache_key = f'weather_{userlogged.coords}'
        details = cache.get(weather_cache_key)
        if not details:
            details = getWeatherDetails(userlogged.coords)
            cache.set(weather_cache_key, details, timeout=3600)  # Cache for 1 hour

        news_cache_key = 'agro_news'
        news = cache.get(news_cache_key)
        if not news:
            news = getAgroNews()
            cache.set(news_cache_key, news, timeout=86400)  # Cache for 24 hours

        context = {
            "user": userlogged,
            "produces": my_products,
            "produces_count": my_products.count(),
            "public_produces_count": public_products.count(),
            "last_listing": my_products.last() if my_products.exists() else "",
            'news': news[:3],
            'weather': details,
        }
        return render(request, 'dash/home.html', context)
    except Exception as e:
        logger.error(f"Home page error: {str(e)}")
        request.session["error_message"] = "An unexpected error occurred"
        return redirect('/admin/404/')

def forum(request):
    try:
        id = request.session.get("member_logged_id")
        if not id:
            raise ValueError("User not logged in")
        return render(request, 'dash/forum.html')
    except Exception as e:
        logger.error(f"Forum error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def croprec(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        form = CropRecommendationForm(request.POST if request.method == 'POST' else None)
        
        if request.method == 'POST' and form.is_valid():
            weatherd = getWeatherDetails(userlogged.coords)
            try:
                data = np.array([[
                    form.cleaned_data['nitrogen'],
                    form.cleaned_data['phosphorus'],
                    form.cleaned_data['potassium'],
                    weatherd[1],  # temp
                    weatherd[2],  # humidity
                    form.cleaned_data['PH'],
                    form.cleaned_data['rainfall']
                ]])
                prediction = cropRecommendationModel.predict(data)
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'prediction': prediction[0]
                }
            except Exception as e:
                logger.error(f"Crop recommendation prediction error: {str(e)}")
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'error': "Prediction failed"
                }
        else:
            context = {
                "form": form,
                'userid': userlogged.id,
                'user': userlogged,
            }
        return render(request, 'dash/tools/crop_rec.html', context)
    except Exception as e:
        logger.error(f"Crop recommendation error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def news_page(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        news_cache_key = 'agro_news'
        news = cache.get(news_cache_key)
        if not news:
            news = getAgroNews()
            cache.set(news_cache_key, news, timeout=86400)
            
        context = {
            'news': news,
            'user': userlogged,
            'userid': userlogged.id,
        }
        return render(request, 'dash/news.html', context)
    except Exception as e:
        logger.error(f"News page error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def fertrec(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        form = FertilizerPredictionForm(request.POST if request.method == 'POST' else None)
        
        if request.method == 'POST' and form.is_valid():
            weatherd = getWeatherDetails(userlogged.coords)
            try:
                prediction = getFertilizerRecommendation(
                    fertilizerRecommendModel,
                    form.cleaned_data['nitrogen'],
                    form.cleaned_data['phosphorus'],
                    form.cleaned_data['potassium'],
                    weatherd[1],  # temp
                    weatherd[2],  # humidity
                    form.cleaned_data['moisture'],
                    form.cleaned_data['soil_type'],
                    form.cleaned_data['crop']
                )
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'prediction': prediction
                }
            except Exception as e:
                logger.error(f"Fertilizer recommendation error: {str(e)}")
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'error': "Prediction failed"
                }
        else:
            context = {
                "form": form,
                "user": userlogged,
                'userid': userlogged.id,
            }
        return render(request, 'dash/tools/fert_rec.html', context)
    except Exception as e:
        logger.error(f"Fertilizer recommendation error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def crop_prices_page(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        prices_cache_key = f'prices_{logged_id}'
        latest_prices = cache.get(prices_cache_key)
        if not latest_prices:
            latest_prices = getMarketPricesAllStates()
            cache.set(prices_cache_key, latest_prices, timeout=3600)
            
        context = {
            "userid": userlogged.id,
            "user": userlogged,
            "date": datetime.datetime.now(),
            "prices": latest_prices
        }
        return render(request, 'dash/check_prices.html', context)
    except Exception as e:
        logger.error(f"Crop prices error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def profile_page(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        context = {
            "userid": userlogged.id,
            "user": userlogged,
        }
        return render(request, 'dash/profile.html', context)
    except Exception as e:
        logger.error(f"Profile page error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def logout_view(request):
    try:
        if 'member_logged_id' in request.session:
            del request.session["member_logged_id"]
            return redirect('/')
        else:
            raise ValueError("Not logged in")
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        request.session["error_message"] = "You are not logged in yet."
        return redirect('/admin/404/')

def list_page(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        
        form = CropProduceListForm(request.POST if request.method == 'POST' else None)
        
        if request.method == 'POST' and form.is_valid():
            try:
                Produce.objects.create(
                    **form.cleaned_data,
                    farmerid=int(userlogged.id),
                    unit="quintals"
                )
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'success': "Your produce has been listed."
                }
            except Exception as e:
                logger.error(f"Listing creation error: {str(e)}")
                context = {
                    'form': form,
                    'user': userlogged,
                    'userid': userlogged.id,
                    'error': "Failed to list produce"
                }
        else:
            context = {
                "form": form,
                'userid': userlogged.id,
                'user': userlogged,
            }
        return render(request, "dash/market/list_produce.html", context)
    except Exception as e:
        logger.error(f"List page error: {str(e)}")
        request.session["error_message"] = "Please login to continue"
        return redirect('/admin/404/')

def check_my_listings(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        produces = Produce.objects.filter(farmerid=userlogged.id)
        
        context = {
            'user': userlogged,
            'produces': produces
        }
        return render(request, "dash/market/check_produces.html", context)
    except Exception as e:
        logger.error(f"Check listings error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def delete_listing(request, id):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")
            
        userlogged = getDetailsFromUID(logged_id)
        listing = Produce.objects.get(id=id, farmerid=userlogged.id)
        listing.delete()
        return redirect('/admin/check_products')
    except Exception as e:
        logger.error(f"Delete listing error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect('/admin/404/')

def layout_dashboard(request):
    return render(request, 'dash/layout_dashboard.html')

# API Endpoint for React Chatbot
def chatbot_api(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            return JsonResponse({"error": "User not logged in"}, status=401)

        query = request.POST.get("query", "").strip()
        if not query:
            return JsonResponse({"error": "Query cannot be empty"}, status=400)

        # Retrieve histories from session
        chat_history = request.session.get("chatlog", {"queries": [], "responses": []})
        conversation_history = request.session.get("conversation_history", [])

        # Get response from the AI
        response, updated_conversation_history = GetResponse(query, conversation_history)

        if isinstance(response, dict) and "error" in response:
            return JsonResponse({"error": response["error"]}, status=500)

        # Calculate carbon_percentage (max 100 kg CO₂e for demo)
        carbon_emission = response.get("CarbonEmission", 0)
        max_emission = 100  # Adjust this based on your app’s scale
        carbon_percentage = min(100, (carbon_emission / max_emission) * 100) if carbon_emission > 0 else 0

        # Update chat history for display
        chat_history["queries"].append(query)
        chat_history["responses"].append(response if isinstance(response, str) else json.dumps(response))
        request.session["chatlog"] = chat_history
        request.session["conversation_history"] = updated_conversation_history

        # Prepare JSON response for React
        response_data = {
            "response": response.get("response", "N/A") if isinstance(response, dict) else response,
            "CarbonEmission": carbon_emission,
            "carbon_percentage": carbon_percentage,
            "fertilizer_recommendations": response.get("fertilizer_recommendations", []),
            "farming_practices": response.get("farming_practices", {}),
            "crop_details": response.get("crop_details", []),
            "suggestions": response.get("suggestions", []),
            "crop_residue_management": response.get("crop_residue_management", "none")
        }
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Chatbot API error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

# Layout View for Rendering HTML with Iframe
def help_page(request):
    try:
        logged_id = request.session.get("member_logged_id")
        if not logged_id:
            raise ValueError("User not logged in")

        userlogged = getDetailsFromUID(logged_id)

        # For GET requests, render the page with the iframe
        context = {
            "userid": userlogged.id,
            "user": userlogged,
            "latest_response": request.session.get("latest_response", {}),
            "chatlog": request.session.get("chatlog", {"queries": [], "responses": []}),
        }
        return render(request, "dash/help.html", context)

    except Exception as e:
        logger.error(f"Help page error: {str(e)}")
        request.session["error_message"] = "Please Login to Continue"
        return redirect("/admin/404/")

import yaml
def generate_yaml(request):
    if request.method == "POST":
        headland_width = float(request.POST.get("headland_width"))
        bed_width = float(request.POST.get("bed_width"))
        plants_count = int(request.POST.get("plants_count"))
        plant_distance = float(request.POST.get("plant_distance"))
        output_format = request.POST.get("output_format")

        # Dynamically collect all bed data
        beds = {}
        bed_id = 1
        while f"plant_type_{bed_id}" in request.POST:
            plant_type = request.POST.get(f"plant_type_{bed_id}")
            if plant_type:
                beds[f"bed{bed_id}"] = {
                    "plant_type": plant_type,
                    "plant_height": float(request.POST.get(f"plant_height_{bed_id}")),
                    "rows_count": int(request.POST.get(f"rows_count_{bed_id}")),
                    "row_distance": float(request.POST.get(f"row_distance_{bed_id}")),
                    "beds_count": int(request.POST.get(f"beds_count_{bed_id}"))
                }
            bed_id += 1

        # Build YAML structure
        yaml_data = {
            "output_enabled": [],
            "output": {},
            "field": {
                "headland_width": headland_width,
                "bed_width": bed_width,
                "plants_count": plants_count,
                "plant_distance": plant_distance,
                "beds": beds
            }
        }

        # Add noise if any field is provided
        noise = {}
        if request.POST.get("noise_position"):
            noise["position"] = float(request.POST.get("noise_position"))
        if request.POST.get("noise_tilt"):
            noise["tilt"] = float(request.POST.get("noise_tilt"))
        if request.POST.get("noise_scale"):
            noise["scale"] = float(request.POST.get("noise_scale"))
        if request.POST.get("noise_missing"):
            noise["missing"] = float(request.POST.get("noise_missing"))
        if noise:
            yaml_data["field"]["noise"] = noise

        # Add stones if any field is provided
        stones = {}
        if request.POST.get("stones_density"):
            stones["density"] = float(request.POST.get("stones_density"))
        if request.POST.get("stones_noise_scale"):
            stones["noise_scale"] = float(request.POST.get("stones_noise_scale"))
        if stones:
            yaml_data["field"]["stones"] = stones

        # Set output based on selection
        if output_format in ["blender", "both"]:
            yaml_data["output_enabled"].append("blender")
            yaml_data["output"]["blender"] = {
                "type": "blender_file",
                "filename": "cropcraft_test3.blend"
            }
        if output_format in ["gazebo", "both"]:
            yaml_data["output_enabled"].append("gazebo")
            yaml_data["output"]["gazebo"] = {
                "type": "gazebo_model",
                "name": "cropcraft_test3",
                "author": "Farm Saathi User"
            }

        # Convert to YAML string
        yaml_content = yaml.dump(yaml_data, default_flow_style=False)
        request.session["yaml_content"] = yaml_content
        return render(request, "dash/generate_yaml.html", {"yaml_content": yaml_content})
    return render(request, "dash/generate_yaml.html")

from django.http import HttpResponse
def download_yaml(request):
    yaml_content = request.session.get("yaml_content", "")
    response = HttpResponse(yaml_content, content_type="application/x-yaml")
    response["Content-Disposition"] = 'attachment; filename="cropcraft_config.yaml"'
    return response

def satellite(request):
    return render(request, "dash/satellite.html")

def inventory(request):
    return render(request, "dash/inventory.html")
