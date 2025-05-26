
from django.contrib import admin
from django.urls import path, include
from dashboard.views import *

urlpatterns = [
    path("", home_page, name ="admin"),
    path('tools/crop_recommendation', croprec),
    path('tools/fertilizer_recommendation', fertrec),
    path('forum/', forum),
    path('prices/', crop_prices_page),
    path('news/', news_page),
    path('help/', help_page,  name="help_page"),
    path('profile/', profile_page),
    path('404/', e404_page),
    path('layout_dashboard/', layout_dashboard),
    path('logout/', logout_view),
    path('list_product/', list_page),
    path('check_products/', check_my_listings),
    path('delete_listing/<int:id>/', delete_listing),
    path('chatbot-api/', chatbot_api, name='chatbot_api'),
    path('generate_yaml/', generate_yaml, name='generate_yaml'),
    path('download_yaml/', download_yaml, name='download_yaml'),
    path('satellite/', satellite),
    path('inventory/', inventory),
]


