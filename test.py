import os
from google import genai
from google.genai import types

gemini_api_key = os.environ.get('GEMINI_API_KEY')

def GetResponse(query):
    client = genai.Client(
        api_key=gemini_api_key,
    )

    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=query),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        system_instruction="You are a farming expert. Ask the user necessary questions to gather data about their farming practices and provide recommendations to calculate their carbon emissions and optimize fertilizer use. keep response as small as possible. only provide necessary information. keep indian farmers in mind.", 
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=[],
            properties={
                "CarbonEmission": genai.types.Schema(
                    type=genai.types.Type.NUMBER,
                    description="Estimated carbon emissions in kg CO2-equivalent based on user inputs"
                ),
                "response": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Explanation of the carbon emission estimate and recommendations"
                ),
                "crop_details": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "cropName": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Name of the crop (e.g., wheat, rice, corn)"
                            ),
                            "area": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                                description="Area planted in acres or hectares"
                            ),
                            "unit": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                enum=["acres", "hectares"],
                                description="Unit of area measurement"
                            ),
                            "crop_yield": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                                description="Average yield per season in tons or kg per acre/hectare"
                            )
                        }
                    ),
                    description="List of crops grown by the farmer and their details"
                ),
                "farming_practices": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "tillage_method": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["conventional", "reduced", "no-till"],
                            description="Type of tillage used"
                        ),
                        "irrigation_type": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["flood", "drip", "sprinkler", "none"],
                            description="Irrigation method used"
                        ),
                        "irrigation_frequency": genai.types.Schema(
                            type=genai.types.Type.NUMBER,
                            description="Irrigation frequency in days per season (if applicable)"
                        ),
                        "fertilizer_usage": genai.types.Schema(
                            type=genai.types.Type.ARRAY,
                            items=genai.types.Schema(
                                type=genai.types.Type.OBJECT,
                                properties={
                                    "fertilizer_type": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="Type of fertilizer used (e.g., urea, NPK, compost)"
                                    ),
                                    "application_frequency": genai.types.Schema(
                                        type=genai.types.Type.NUMBER,
                                        description="Number of times fertilizer is applied per season"
                                    ),
                                    "amount": genai.types.Schema(
                                        type=genai.types.Type.NUMBER,
                                        description="Amount used in kg or liters per acre/hectare"
                                    ),
                                    "unit": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        enum=["kg", "liters"],
                                        description="Unit of fertilizer measurement"
                                    )
                                }
                            ),
                            description="Details of fertilizer usage"
                        )
                    },
                    description="Farming practices employed by the farmer"
                ),
                "machinery_usage": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "machinery_type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Type of machinery used (e.g., tractor, harvester)"
                            ),
                            "hours_per_season": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                                description="Number of hours machinery is used per season"
                            ),
                            "fuel_type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                enum=["diesel", "gasoline", "electric"],
                                description="Type of fuel used"
                            )
                        }
                    ),
                    description="Machinery usage details"
                ),
                "livestock_management": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "has_livestock": genai.types.Schema(
                            type=genai.types.Type.BOOLEAN,
                            description="Whether the farmer has livestock"
                        ),
                        "livestock_count": genai.types.Schema(
                            type=genai.types.Type.NUMBER,
                            description="Number of animals (if applicable)"
                        ),
                        "livestock_type": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            description="Type of livestock raised (e.g., cows, chickens)"
                        ),
                        "manure_management": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["compost", "spread", "stored", "none"],
                            description="How manure is managed"
                        )
                    },
                    description="Livestock and manure management details"
                ),
                "renewable_energy_usage": genai.types.Schema(
                    type=genai.types.Type.BOOLEAN,
                    description="Whether renewable energy sources like solar panels are used"
                ),
                "crop_residue_management": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    enum=["burned", "left on field", "composted", "removed"],
                    description="How crop residues or food waste are handled"
                ),
                "carbon_sequestration_practices": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "cover_crops": genai.types.Schema(
                            type=genai.types.Type.BOOLEAN,
                            description="Whether cover crops are used to improve soil health"
                        ),
                        "agroforestry": genai.types.Schema(
                            type=genai.types.Type.BOOLEAN,
                            description="Whether trees are integrated into farming practices"
                        ),
                        "biochar_usage": genai.types.Schema(
                            type=genai.types.Type.BOOLEAN,
                            description="Whether biochar is used for carbon sequestration"
                        )
                    },
                    description="Carbon sequestration practices used"
                ),
                "transportation_emissions": genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "distance_to_market": genai.types.Schema(
                            type=genai.types.Type.NUMBER,
                            description="Distance crops are transported after harvest in km or miles"
                        ),
                        "unit": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["km", "miles"],
                            description="Unit of distance"
                        ),
                        "transport_method": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["truck", "train", "ship"],
                            description="Mode of transportation"
                        )
                    },
                    description="Transportation details post-harvest"
                ),
                "fertilizer_recommendations": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "fertilizer_type": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Recommended fertilizer (e.g., urea, compost)"
                            ),
                            "amount": genai.types.Schema(
                                type=genai.types.Type.NUMBER,
                                description="Recommended amount in kg or liters per acre/hectare"
                            ),
                            "unit": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                enum=["kg", "liters"],
                                description="Unit of fertilizer"
                            ),
                            "best_time_to_apply": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Optimal season or growth stage for applying fertilizers"
                            ),
                            "reason": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Why this fertilizer is recommended"
                            )
                        }
                    ),
                    description="List of fertilizer recommendations (if requested)"
                ),
                "suggestions": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Additional suggestions to reduce carbon emissions"
                    ),
                    description="Suggestions to improve sustainability"
                )
            }
        )
    )
    response = ''
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        response += chunk.text
    return response
import json 
if __name__ == "__main__":
    for i in range(10):
        query = input("Enter query: ")
        response = GetResponse(query)
        try:
            # Parse the response as JSON if the API returns it as a string
            response_json = json.loads(response)
            print(response_json)
        except json.JSONDecodeError:
            print("response is not json format")
            print(response)