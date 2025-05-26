import requests
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import json
load_dotenv()

fertilizerdata = pd.read_csv("datasets/Fertilizer Prediction.csv") 
weather_api_key = os.environ.get('WEATHER_API_KEY')
newsapi_api_key = os.environ.get('NEWSAPI_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')
govdata_api_key = os.environ.get('GOVDATA_API_KEY')
def getWeatherDetails(coords):
    lat, lon = coords[0], coords[1]
    weather_url = f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={lat},{lon}&aqi=no"

    response = requests.get(weather_url)
    data = response.json()

    if "error" in data:
        print(f"Error: {data['error']['message']}")
        return None

    weather = data["current"]["condition"]["text"]
    temp = data["current"]["temp_c"]  # Temperature in Celsius
    humidity = data["current"]["humidity"]
    wind_speed = data["current"]["wind_kph"]
    pressure = data["current"]["pressure_mb"]

    return [weather, temp, humidity, wind_speed, pressure]

def getAgroNews():
    newsapi_url = f"https://newsapi.org/v2/everything?q=agriculture&apiKey={newsapi_api_key}"
    response = requests.get(newsapi_url)
    data = response.json()
    return data["articles"][:20]

def getFertilizerRecommendation(model, nitrogen, phosphorus, potassium, temp, humidity, moisture, soil_type, crop):
    le_soil = LabelEncoder()
    fertilizerdata['Soil Type'] = le_soil.fit_transform(fertilizerdata['Soil Type'])
    le_crop = LabelEncoder()
    fertilizerdata['Crop Type'] = le_crop.fit_transform(fertilizerdata['Crop Type'])
    soil_enc = le_soil.transform([str(soil_type)])[0]
    crop_enc = le_crop.transform([crop])[0]
    user_input = [[temp,humidity,moisture,soil_enc,crop_enc,nitrogen,potassium,phosphorus]]
    prediction = model.predict(user_input)
    return prediction[0]

def getMarketPricesAllStates():
    states = ["Kerala", "Uttrakhand", "Uttar Pradesh", "Rajasthan", "Nagaland", "Gujarat", "Maharashtra", "Tripura", "Punjab", "Bihar", "Telangana", "Meghalaya"]
    final_list = []
    for state in states:
        state = state.replace(" ", "+")
        govdata_url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={govdata_api_key}&format=json&filters%5Bstate%5D={state}"
        response = requests.get(govdata_url)
        data = response.json()
        for entries in data["records"]:
            final_list.append(entries)

    return final_list



def GetResponse(query, conversation_history=None):
    print("Query:", query)
    if conversation_history is None:
            conversation_history = []

    # Convert conversation_history from dicts (if loaded from session) to types.Content
    if conversation_history and isinstance(conversation_history[0], dict):
        conversation_history = [
            types.Content(
                role=item["role"],
                parts=[types.Part.from_text(text=p["text"]) for p in item["parts"]]
            )
            for item in conversation_history
        ]

    # Append the new user query
    conversation_history.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)],
        )
    )
    try:
        client = genai.Client(api_key=gemini_api_key)
        model = "gemini-2.0-flash"

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            system_instruction="You are a farming expert. Ask the user necessary questions to gather data about their farming practices and provide recommendations to calculate their carbon emissions and optimize fertilizer use. Maintain context from previous messages.",
            response_mime_type="application/json",
            response_schema=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required = [
                    "CarbonEmission",
                    "response",
                    "crop_details",
                    "farming_practices",
                    "machinery_usage",
                    "livestock_management",
                    "renewable_energy_usage",
                    "crop_residue_management",
                    "carbon_sequestration_practices",
                    "transportation_emissions",
                    "fertilizer_recommendations",
                    "suggestions"
                ],
                properties={
                    "CarbonEmission": genai.types.Schema(type=genai.types.Type.NUMBER, description="Estimated carbon emissions in kg CO2-equivalent"),
                    "response": genai.types.Schema(type=genai.types.Type.STRING, description="Explanation and recommendations"),
                    "crop_details": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.OBJECT,
                            properties={
                                "cropName": genai.types.Schema(type=genai.types.Type.STRING),
                                "area": genai.types.Schema(type=genai.types.Type.NUMBER),
                                "unit": genai.types.Schema(type=genai.types.Type.STRING, enum=["acres", "hectares"]),
                                "crop_yield": genai.types.Schema(type=genai.types.Type.NUMBER),
                            }
                        )
                    ),
                    "farming_practices": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "tillage_method": genai.types.Schema(type=genai.types.Type.STRING, enum=["conventional", "reduced", "no-till"]),
                            "irrigation_type": genai.types.Schema(type=genai.types.Type.STRING, enum=["flood", "drip", "sprinkler", "none"]),
                            "irrigation_frequency": genai.types.Schema(type=genai.types.Type.NUMBER),
                            "fertilizer_usage": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                items=genai.types.Schema(
                                    type=genai.types.Type.OBJECT,
                                    properties={
                                        "fertilizer_type": genai.types.Schema(type=genai.types.Type.STRING),
                                        "application_frequency": genai.types.Schema(type=genai.types.Type.NUMBER),
                                        "amount": genai.types.Schema(type=genai.types.Type.NUMBER),
                                        "unit": genai.types.Schema(type=genai.types.Type.STRING, enum=["kg", "liters"]),
                                    }
                                )
                            ),
                        }
                    ),
                    "machinery_usage": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.OBJECT,
                            properties={
                                "machinery_type": genai.types.Schema(type=genai.types.Type.STRING),
                                "hours_per_season": genai.types.Schema(type=genai.types.Type.NUMBER),
                                "fuel_type": genai.types.Schema(type=genai.types.Type.STRING, enum=["diesel", "gasoline", "electric"]),
                            }
                        )
                    ),
                    "livestock_management": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "has_livestock": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                            "livestock_count": genai.types.Schema(type=genai.types.Type.NUMBER),
                            "livestock_type": genai.types.Schema(type=genai.types.Type.STRING),
                            "manure_management": genai.types.Schema(type=genai.types.Type.STRING, enum=["compost", "spread", "stored", "none"]),
                        }
                    ),
                    "renewable_energy_usage": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                    "crop_residue_management": genai.types.Schema(type=genai.types.Type.STRING, enum=["burned", "left on field", "composted", "removed"]),
                    "carbon_sequestration_practices": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "cover_crops": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                            "agroforestry": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                            "biochar_usage": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                        }
                    ),
                    "transportation_emissions": genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "distance_to_market": genai.types.Schema(type=genai.types.Type.NUMBER),
                            "unit": genai.types.Schema(type=genai.types.Type.STRING, enum=["km", "miles"]),
                            "transport_method": genai.types.Schema(type=genai.types.Type.STRING, enum=["truck", "train", "ship"]),
                        }
                    ),
                    "fertilizer_recommendations": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.OBJECT,
                            properties={
                                "fertilizer_type": genai.types.Schema(type=genai.types.Type.STRING),
                                "amount": genai.types.Schema(type=genai.types.Type.NUMBER),
                                "unit": genai.types.Schema(type=genai.types.Type.STRING, enum=["kg", "liters"]),
                                "best_time_to_apply": genai.types.Schema(type=genai.types.Type.STRING),
                                "reason": genai.types.Schema(type=genai.types.Type.STRING),
                            }
                        )
                    ),
                    "suggestions": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(type=genai.types.Type.STRING)
                    ),
                }
            )
        )
        response = ''
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=conversation_history,
            config=generate_content_config,
        ):
            response += chunk.text

        # Parse the response as JSON
        response_json = json.loads(response)

        # Append the bot's response to the conversation history
        conversation_history.append(
            types.Content(
                role="assistant",
                parts=[types.Part.from_text(text=response)],
            )
        )

        # Convert conversation_history to a JSON-serializable format
        serializable_history = [
            {
                "role": item.role,
                "parts": [{"text": part.text} for part in item.parts]
            }
            for item in conversation_history
        ]
        print("Response:", response_json)
        return response_json, serializable_history
    except json.JSONDecodeError:
        print("Error: JSONDecodeError")
        return {"response": response}, conversation_history
    except Exception as e:
        print(f"Error in GetResponse: {str(e)}")
        return {"error": f"Failed to get response: {str(e)}"}, conversation_history