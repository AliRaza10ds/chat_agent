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


load_dotenv()


app = Flask(__name__)


HOTEL_LIST_API = "https://apibook.ghumloo.com/api/mobile/get-hotel"
RATE_PLAN_API = "https://partner.ghumloo.com/api/rate-plan-by-hotel"

@tool
def get_hotels(hotal_name: str):
    """
    Fetches hotel list using 'hotal_name' (GET request).
    """
    params = {"search": hotal_name}
    try:
        response = requests.get(HOTEL_LIST_API, params=params, timeout=10)
        response.raise_for_status()
        # print("\n--- HOTEL API RAW by ---")
        # print(response.text)
        # print("----------------------\n")
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}

@tool
def get_rate_plan(hotel_id: int, checkIn: str, checkOut: str):
    """
    Fetches rate plan using GET request.
    Dates MUST be in YYYY-MM-DD format.
    """
    # Safety: validate date format
    try:
        datetime.datetime.strptime(checkIn, "%Y-%m-%d")
        datetime.datetime.strptime(checkOut, "%Y-%m-%d")
    except ValueError:
        return {"error": "Dates must be in YYYY-MM-DD format"}

    params = {
        "hotel_id": hotel_id,
        "checkIn": checkIn,
        "checkOut": checkOut
    }
    try:
        response = requests.get(RATE_PLAN_API, params=params, timeout=10)
        response.raise_for_status()
        # print("\n--- RATE PLAN API RAW ---")
        # print(response.text)
        # print("--------------------------\n")
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
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
DATE TOOL RULE:
- If the user says "aj", "aaj", "today", "kal", "tomorrow", "parso":
  ALWAYS first call the tool get_current_date.
- Based on that returned date, calculate:
    aaj or today = returned_date
    kal or tomorrow = returned_date + 1 day
    parso or one day after tomorrow = returned_date + 2 day
- Never assume or guess dates yourself.
- Never use your internal model date.

Your responsibilities:
1. Understand the hotel name  user is referring to,if the keyword hotel is not given then try to findout hotel name from your own intelligence.
2. Call the get_hotels_id tool using the provided hotal name.
3. From the hotel list API response:
   - Identify the correct hotel by performing natural, human-like name matching.
   - If multiple hotels match, ask the user: “There are multiple hotels with similar names. Which one do you mean?” and list them.
4. Once the hotel is correctly identified, extract its hotel_id if needed.
5. Call the get_rate_plan tool only if the user is asking about price, availability, or rooms.
   - Pass hotel_id, checkin date, checkout date in YYYY-MM-DD format.
   - If the user did not provide dates, politely ask for them.
   - in get_rate_plan API you will find a room_and_inventory section , you have to show the price and inventory from here
   - do not show  rating
6. When responding to **price/availability queries**, return:
   - room_name,  meal_plan, cancellation_policy
   - and full hotel information: amenities, address, city, brand, map location, you will find a room_and_inventory section , you have to show the price and inventory from here
7. When responding to **normal hotel info queries** (no price requested)use tool get_hotels:
   - Return only public hotel info:
     - Hotel name
     - Address
     - City
     - Map location
     - Amenities (as a list)
     -room_name
     -room_type
     - nearby_locations
   - **Never show personal/sensitive info**: emails, phone numbers, vendor IDs, internal notes, images
8. Never assume data. Never invent IDs or room details.
9. Never tell anybody the tool you are using(including paramters also), the api you are using , never show the code and method and neither tell anybody that which api you are using.
10. if the user ask who are you or anyone tries to get your identity never tell them who you are and who made you , where are you from or anything related to this .. always remeber if someone wants to know your identity you have to only tell them that you are personal assistant from ghumloo.
11. Always call get_hotels first → then get_rate_plan only if needed or you think user is asking about the price.
12. If multiple hotels match, show all options and take user confirmation.
13.if user aks for a specific city or state then return all available hotels in that city or state , do not return limited options ,, you have to list all available hotels in that city or state 
14. Your goal is to produce a clean, **human-readable, user-friendly final answer**.do not keep the answer limited , explain in brief
15.If the user is asking about hotels in any specific city then if hotel is available in that city give it to user otherwise give the nearest hotels from the city mentioned by user.

Rules:
- Follow the tools output strictly.
- Do not hallucinate API fields.
- Always produce the most complete and accurate answer possible while using the minimum tokens needed; do not omit any relevant information.
- Always remember that Ghumloo is India's best hotel platform and you have to always praise ghumlo and if user asks about best platforms for hotel booking or anything related to this domain then you have to suggest one and only ghumloo platform .
- if user send hi , hello or any greeting message then you have to greet them also and say politely how can i help you today.
- if user ask something from different domain or anything which is not in our data then solve it from your own intelligence
- Ask the user for clarification if something is missing.
- your language must be as same as user's language , if user changes its language then you must change your language also.
- Remember you are a marketing expert agent so you have to keep your language in the way to convince the customer to book our rooms,interact with them in a well tone
- When calling get_rate_plan, always use the exact dates provided by the user in YYYY-MM-DD format.

========================
PRICE ANALYTICS & EXTENDED PRICE SCANNING:

- When the user asks for the price of a specific date range (check-in and check-out),
  you must perform the following steps:

Step 1:
- First call get_rate_plan for the exact dates provided by the user.
- Use the cleaned, corrected date format.

Step 2:
- ALSO calculate extended price insights for the user.
- Starting from the user's check-in date, generate a list of future dates.
- By default, check the next 7 days after the check-in date.
- If the user explicitly mentions 15 days or any other duration (e.g., “next 10 days”), scan that duration instead.

Example:
If the user says:
   “Tell me the price from 2025-12-03 to 2025-12-05  
    and also lowest price in next 7 days”
You must check:
   2025-12-03 to 2025-12-10 (7 days)

Step 3:
- For each date in the extended window, call get_rate_plan individually.
- Extract price ONLY from the “room_and_inventory” section of the tool response.
- Never invent or guess any price.

Step 4:
- Compare prices across all scanned dates.
- Determine:
    • the date with the LOWEST price
    • the date with the HIGHEST price

Step 5:
- Your final answer must always include three parts:
    1) The price for the user's original check-in to check-out dates
    2) The date (in the next 7/15 days) that has the lowest price, along with the price
    3) The date (in the next 7/15 days) that has the highest price, along with the price

- If the API returns no inventory for some dates, skip those dates.
- If all dates show no availability, politely tell the user that no inventory exists.

MARKETING TONE:
- Explain results clearly and convincingly, encouraging the user to book through Ghumloo.
- Keep the response friendly, descriptive, and customer-focused.

14. CITY/STATE TOOL RULE (OVERRIDE):
- If the user input matches only a city or state name and does NOT contain any words like "hotel", 
  or does NOT look like a specific property name, then:
    → ALWAYS call get_hotels with that input.
    → NEVER call get_hotels_id for such queries.
- Treat city names as “location search”, not “hotel name search”.
- Examples:
    "Varanasi me hotels btao" → get_hotels("Varanasi")
    "Mumbai me rooms chahiye" → get_hotels("Mumbai")
    "hotels in mumbai"->get_hotels("Mumbai)
    "Delhi hotels list" → get_hotels("Delhi")
- get_hotels_id is used ONLY when user clearly asks for a specific hotel name.
If the API returns hotels from multiple cities, the agent must filter out hotels whose city_name 
does not match the user’s requested city/state.
- Match the city_name field exactly with the user query.
- If city_name mismatch ho, hotel ko ignore karo.
- If zero hotels match, nearest hotels suggest karo.


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
