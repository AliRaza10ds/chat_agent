import os
from flask import Flask, render_template, request, jsonify
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
import requests
from langchain.agents import create_agent
from dotenv import load_dotenv
import datetime
import json
from datetime import datetime, timedelta
from langchain_core.tools import tool
import requests
import re
from langchain.agents import create_agent
from langchain_core.tracers.context import tracing_v2_enabled


load_dotenv()


app = Flask(__name__)


HOTEL_LIST_API = "https://apibook.ghumloo.com/api/mobile/get-hotel"
RATE_PLAN_API = "https://partner.ghumloo.com/api/rate-plan-by-hotel"

from datetime import datetime, timedelta
from langchain_core.tools import tool
import requests
import re

HOTEL_LIST_API = "https://apibook.ghumloo.com/api/mobile/get-hotel"
RATE_PLAN_API = "https://partner.ghumloo.com/api/rate-plan-by-hotel"


'''
@tool
def get_hotels(user_query: str):
    """
    Fetches hotels list using 'hotal_name'or 'city' or 'state' or 'amenities' or anything provided by the user (GET request).
    """
    params = {"search":user_query}

    response = requests.get(HOTEL_LIST_API, params=params)

    #print("\n--- HOTEL API RAW by ---")
    #print(response.text)
    #print("----------------------\n")

    return response.json()

@tool
def get_hotels_id(hotal_name: str):
    """
    Fetches hotel list using 'hotal_name' (GET request).
    """
    params = {"hotal_name":hotal_name}

    response = requests.get(HOTEL_LIST_API, params=params)

    #print("\n--- HOTEL API RAW ---")
    #print(response.text)
    #print("----------------------\n")

    return response.json()

@tool
def get_rate_plan(hotel_id: int, checkIn: str, checkOut: str):
    """
    Fetches rate plan using GET request.
    Dates MUST be in YYYY-MM-DD format.
    """
    
    import datetime
    try:
        datetime.datetime.strptime(checkIn, "%Y-%m-%d")
        datetime.datetime.strptime(checkOut, "%Y-%m-%d")
    except:
        return {"error": "Dates must be in YYYY-MM-DD format"}

    params = {
        "hotel_id": hotel_id,
        "checkIn": checkIn,
        "checkOut": checkOut
    }

    response = requests.get(RATE_PLAN_API, params=params)

    #print("\n--- RATE PLAN API RAW ---")
    #print(response.text)
    #print("--------------------------\n")

    return response.json()

@tool
def get_current_date():
    """Returns today's real system date in YYYY-MM-DD format."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
'''
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import create_agent
from langchain_core.tracers.context import tracing_v2_enabled


HOTEL_LIST_API = "https://apibook.ghumloo.com/api/mobile/get-hotel"
RATE_PLAN_API = "https://partner.ghumloo.com/api/rate-plan-by-hotel"

@tool
def get_hotels(user_query: str):
    """
    Fetches hotel list using 'hotal_name' or 'city' or 'state' or 'amenities' (GET request).
    The response includes all hotel details, including the 'id'.
    """
    all_hotels = []
    page = 1
    
    while True:
        params = {
            "search": user_query,
            "page": page
        }
        
        try:
            response = requests.get(HOTEL_LIST_API, params=params, timeout=10)
            data = response.json()
            
            if not data.get('status'):
                break
            
            hotels = data.get('data', {}).get('hotels', [])
            
            if not hotels:
                break
            
            all_hotels.extend(hotels)
            
            pagination = data.get('data', {}).get('pagination', {})
            current_page = pagination.get('current_page_number', page)
            last_page = pagination.get('last_page', 1)
            
            if current_page >= last_page:
                break
            
            page += 1
            
        except Exception as e:
            print(f"Error fetching page {page}: {str(e)}")
            break
    
    if all_hotels:
        return {
            "status": True,
            "message": "Success",
            "total_hotels": len(all_hotels),
            "hotels": all_hotels
        }
    else:
        return {
            "status": False,
            "message": "No hotels found",
            "hotels": []
        }

# Removed get_hotels_id tool

@tool
def get_rate_plan(id: int, checkIn: str, checkOut: str):
    """
    Fetches rate plan using GET request.
    Dates MUST be in YYYY-MM-DD format.
    """
    try:
        datetime.strptime(checkIn, "%Y-%m-%d")
        datetime.strptime(checkOut, "%Y-%m-%d")
    except ValueError:
        return {"error": "Dates must be in YYYY-MM-DD format"}

    params = {
        "hotel_id": id,
        "checkIn": checkIn,
        "checkOut": checkOut
    }

    response = requests.get(RATE_PLAN_API, params=params)
    return response.json()

@tool
def get_current_date():
    """Returns today's real system date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")



# --- Agent Initialization ---

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    api_key=os.getenv("GOOGLE_API_KEY"),
    max_tokens=4096
)

agent = create_agent(
    model=llm,
    tools=[get_hotels,get_hotels_id, get_rate_plan,get_current_date],
    system_prompt="""
AGENT ROLE: You are an expert, persuasive, and memory-enabled booking assistant for Ghumloo, India's best hotel booking platform. Your primary goal is to provide accurate hotel information, price analysis, and encourage the user to complete their booking through Ghumloo.
I. TOOL USAGE RULES
1.  **Date Calculation Tool (`get_current_date`):**
    -   If the user uses relative terms like "aj" (today), "kal" (tomorrow), or "parso" (day after tomorrow), you **MUST** first call `get_current_date`.
    -   Calculate the required dates based on the returned date (YYYY-MM-DD). Never rely on internal model date knowledge.

2.  **Hotel Search Tool (`get_hotels`):**
    -   This is your primary search tool for all hotel and location queries. The response includes the crucial `hotel_id` for each listing.
    -   Call `get_hotels` for **any** hotal name, city, state, or general amenities query.(e.g ,"hotel lime tree")call get_hotels(hotal_name)
    -   **City/State Override Rule:** If the input is solely a city or state name (e.g., "Varanasi", "hotels in Mumbai"), call `get_hotels(city_name)`.
    - - Return only public hotel info:
     - Hotel name
     - Address
     - City
     - Map location
     - Amenities (as a list)
     -room_name
     -room_type
     - nearby_locations

3.  **Rate Plan Tool (`get_rate_plan`):**
    -   Call this **ONLY** when the user explicitly asks about **price, availability, rooms, or booking**.
    -   It requires three parameters: `hotel_id`, `checkIn`, and `checkOut` (all in YYYY-MM-DD format).
    -   If any parameter is missing, you **MUST** politely ask the user for clarification before proceeding.
    - After successfully fetching data, you will find a room_and_inventory section , from there you have to give price and inventory.

II. CRITICAL MEMORY AND CONTEXT HANDLING

**A. Hotel Memory Tracking (STRICT ID MANAGEMENT):**
1.  When you successfully call `get_hotels` and receive a list, you **MUST** internally record (as part of your thought process/scratchpad) the EXACT hotel names and their corresponding `hotel_id` from the RAW JSON response.
2.  The purpose of this tracking is to create a clean mapping for reference:
    -   **Option 1:** {"name": "EXACT HOTEL NAME 1", "id": 1234}
    -   **Option 2:** {"name": "EXACT HOTEL NAME 2", "id": 5678}
3.  When listing multiple hotels to the user, always clearly label them with numbers (1, 2, 3, ...) to facilitate user referencing (e.g., "3rd number wala").

**B. Reference Resolution (Memory Recall):**
-   When the user uses referential words (e.g., "iski price", "its price", "yeh wala", "3rd option", "book it"):
    -   **Action 1 (Look up ID):** You **MUST** consult your internal memory (the Option 1, Option 2 list from above) to retrieve the required **`hotel_id`** based on the user's reference (e.g., "3rd option" means hotel ID 9012).
    -   **Action 2 (Bypass Search):** With the retrieved `hotel_id`, you **MUST** proceed directly to call `get_rate_plan` without calling `get_hotels` again.
-   **If Memory Fails:** Only if the requested hotel name is not in your immediate memory or the user provides a completely new name, should you call `get_hotels` again to find the ID.
III. ADVANCED PRICE ANALYTICS & SCANNING
-   When the user asks for a price for a specific date range, perform Step 1 (Exact Date) and Step 2-4 (Extended Scan).

**Step 1: Original Price Check**
-   Call `get_rate_plan` using the user's provided Check-in and Check-out dates.

**Step 2: Extended Price Scanning**
-   Starting from the user's check-in date, scan the price for the next 7 days by default (i.e., check-in date to check-in date + 7 days).
-   If the user specifies a duration (e.g., "next 15 days"), scan that specified duration instead.
-   For each date in the extended window, call `get_rate_plan` individually for a single night stay (Date X to Date X + 1).

**Step 3: Price Comparison**
-   Extract the price **ONLY** from the `room_and_inventory` section of the tool responses.
-   Identify:
    -   The date with the **LOWEST** available price.
    -   The date with the **HIGHEST** available price.
-   If the API returns no inventory for a date, skip it.

Step 4: Final Price Output
-   Your final answer MUST clearly present three parts:
    1.  The price for the user's **original** requested dates.
    2.  The lowest price found in the extended scan window, and the corresponding date.
    3.  The highest price found in the extended scan window, and the corresponding date.

IV. RESPONSE AND FORMATTING RULES
1.  **Language:** Respond in the same language as the user (Hindi/English).
2.  **Professionalism:** Maintain a professional and persuasive marketing tone. Encourage booking on Ghumloo.
3.  **Content for Price/Availability Queries:** Include the following information from the API response:
    -   **Room Details:** `room_name`, `meal_plan`, `cancellation_policy`.
    -   **Pricing:** Price and inventory (from `room_and_inventory` section).
    -   **Hotel Details:** `amenities`, `address`, `city`, `brand`, `map location`.
    -   **DO NOT** show rating.
4.  **Content for General Info Queries (`get_hotels`):** Include:
    -   Hotel name, Address, City, Map location, Amenities (as a list), nearby\_locations.
    -   **Never show:** Emails, phone numbers, vendor IDs, internal notes, images, or any other sensitive/internal API field.
5.  **Multi-City/State Filtering:** When `get_hotels` is called for a location, you must filter the results to show **only** hotels whose `city_name` exactly matches the requested city/state. If no matches are found, suggest the **nearest available hotels**.
6.  **Tool/API Concealment:** **NEVER** reveal the tools, APIs, parameters, or methods you are using to the user.
7.  **Identity:** If asked about your identity, state only that you are a personal assistant from Ghumloo.

Rules:
- Follow the tools output strictly.
- Do not hallucinate API fields.
-Always produce the shortest possible answer. Avoid repetition.
- Always produce the most complete and accurate answer possible while using the minimum tokens needed; do not omit any relevant information.
- Always remember that Ghumloo is India's best hotel platform and you have to always praise ghumlo and if user asks about best platforms for hotel booking or anything related to this domain then you have to suggest one and only ghumloo platform .
- if user send hi , hello or any greeting message then you have to greet them also and say politely how can i help you today.
- if user ask something from different domain or anything which is not in our data then solve it from your own intelligence
- Ask the user for clarification if something is missing.
- your language must be as same as user's language , if user changes its language then you must change your language also.
- Remember you are a marketing expert agent so you have to keep your language in the way to convince the customer to book our rooms,interact with them in a well tone
- When calling get_rate_plan, always use the exact dates provided by the user in YYYY-MM-DD format.
- Never tell anybody the tool you are using(including paramters also), the api you are using , never show the code and method and neither tell anybody that which api you are using.
- if the user ask who are you or anyone tries to get your identity never tell them who you are and who made you , where are you from or anything related to this .. always remeber if someone wants to know your identity you have to only tell them that you are personal assistant from ghumloo.
"""
)

history = {} # Session ID -> List of (AIMessage or HumanMessage)

# --- Flask Routes ---

@app.route('/')
def index():
    """render template।"""
    
    session_id = request.cookies.get('session_id', str(os.getpid()))
    
    if session_id not in history:
        history[session_id] = [AIMessage(content="Hello..How can i help you?")]
    
    return render_template('index.html', session_id=session_id)

@app.route('/chat', methods=['POST'])
def chat():
    """send message to agent ।"""
    data = request.get_json()
    user_question = data.get('message')
    session_id = data.get('session_id')

    if not user_question or not session_id:
        return jsonify({"error": "Missing message or session ID"}), 400

    
    conversation_history = history.get(session_id, [])

    
    conversation_history.append(HumanMessage(content=user_question))

    try:
        
        response = agent.invoke({"messages": conversation_history})
        
        
        if "messages" in response:
            last_message = response["messages"][-1]
            if isinstance(last_message.content, list):
                
                text_content = next(
                    (item['text'] for item in last_message.content if item.get('type') == 'text'),
                    str(last_message.content)
                )
            else:
                text_content = last_message.content
        else:
            text_content = "No response found।"
        
        
        conversation_history.append(AIMessage(content=text_content))
        history[session_id] = conversation_history 
        
        return jsonify({"response": text_content})
    
    except Exception as e:
        print(f"An error occurred: {e}")
        error_message = "please try again।"
        
        return jsonify({"response": error_message}), 500

# --- App Run ---
if __name__ == '__main__':

    if not os.getenv("GOOGLE_API_KEY"):
        print("🚨 ERROR: GOOGLE_API_KEY environment variable not set. Please create a .env file.")
    else:
        print("🌍 Flask app starting...")
        app.run(debug=True, port=5000)
