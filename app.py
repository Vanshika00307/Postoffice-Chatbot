# Import the necessary libraries
from flask import Flask, request, jsonify, render_template, session
import json
import os
import requests
from requests.exceptions import RequestException
import time
import random

# Initialize the Flask application
app = Flask(__name__)
# IMPORTANT: This must be a unique, random string.
app.secret_key = 'a_very_secret_key_that_is_hard_to_guess'

# Define the path to your data file
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data.json')

# Cache for storing API responses to avoid repeated calls
PINCODE_CACHE = {}
CACHE_EXPIRY = 3600  # 1 hour in seconds

def load_data():
    """Loads the FAQ data from the data.json file with error handling."""
    try:
        # Explicitly open the file with UTF-8 encoding
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data.json: {e}")
        return []

def fetch_pincode_data(pincode):
    """Fetches pincode data from API with proper error handling and caching."""
    url = f"https://api.postalpincode.in/pincode/{pincode}"
    
    # Check cache first
    cached_data = PINCODE_CACHE.get(pincode)
    if cached_data and (time.time() - cached_data['timestamp']) < CACHE_EXPIRY:
        return cached_data['data']
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate API response structure
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Invalid API response format")
        
        # Cache the successful response
        PINCODE_CACHE[pincode] = {
            'data': data,
            'timestamp': time.time()
        }
        
        return data
        
    except RequestException as e:
        print(f"API request failed for pincode {pincode}: {str(e)}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        print(f"Data parsing error for pincode {pincode}: {str(e)}")
        return None

def fetch_pincode_from_location(latitude, longitude):
    """Uses Nominatim API to get a pincode from coordinates."""
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract the pincode from the response
        if 'address' in data and 'postcode' in data['address']:
            return data['address']['postcode']
        return None
    except RequestException as e:
        print(f"Nominatim API request failed: {str(e)}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing Nominatim response: {str(e)}")
        return None

@app.route('/')
def home():
    """Renders the main HTML page for the chatbot."""
    return render_template('index.html')

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Main endpoint for chatbot communication, handling intents and API calls."""
    request_data = request.json
    user_message = request_data.get('message', '').strip().lower()
    latitude = request_data.get('latitude')
    longitude = request_data.get('longitude')
    current_state = session.get('chatbot_state', None)
    
    # --- RESET CONVERSATION LOGIC ---
    if user_message == 'reset':
        session.pop('chatbot_state', None)  # Clear any existing state
        
        # In a real app, 'data' would be loaded from your JSON file.
        # data = load_data()

        initial_entry = None
        # Find the entry with the 'hi' keyword
        for entry in data:
            if 'hi' in entry['keywords']:
                initial_entry = entry
                break  # Stop searching once we find it

        if initial_entry:
            # FIX: Correctly handle the answer object from JSON
            answer_data = initial_entry.get('answer', {})
            if isinstance(answer_data, dict) and answer_data.get('randomize', False):
                # Pick a random string from the 'options' list within the 'answer' object
                answer = random.choice(answer_data.get('options', ["Hello! Welcome to India Post Assistant."]))
            else:
                # Fallback if the structure is not as expected
                answer = "Hello! Welcome to India Post Assistant."

            # FIX: Extract the options for the buttons correctly
            options = []
            for opt in initial_entry.get('options', []):
                if isinstance(opt, dict) and "text" in opt:
                    options.append(opt["text"])
                elif isinstance(opt, str):
                    options.append(opt)
            
            return jsonify({
                "response": answer,
                "options": options
            })
        else:
            # Fallback if the 'hi' keyword is not found in the data
            return jsonify({
                "response": "Hello! Welcome to India Post Assistant.",
                "options": ["Track & Trace", "Find Post Office", "Banking Services"]
            })
    
    # ... rest of your chatbot logic would go here


    
    # --- LOCATION-BASED SEARCH IMPLEMENTATION ---
    if latitude is not None and longitude is not None:
        pincode = fetch_pincode_from_location(latitude, longitude)
        if pincode:
            api_data = fetch_pincode_data(pincode)
            if api_data and api_data[0]['Status'] == 'Success':
                post_offices = api_data[0]['PostOffice']
                if post_offices:
                    options = [{
                        "text": f"{po.get('Name', 'N/A')} ({po.get('BranchType', 'Office')})",
                        "value": f"post_office_{po.get('Name', '').replace(' ', '_')}"
                    } for po in post_offices[:5]]
                    response_msg = f"Found {len(post_offices)} post offices for your location (pincode {pincode}):"
                    if len(post_offices) > 5:
                        response_msg += f" (showing 5 of {len(post_offices)})"
                    return jsonify({"response": response_msg, "options": options})
                else:
                    return jsonify({"response": f"No post offices found for your location (pincode {pincode}).", "options": []})
            else:
                return jsonify({"response": "Sorry, I could not find post offices near your location.", "options": []})
        else:
            return jsonify({"response": "I could not determine the pincode for your location.", "options": []})
    
    # --- PINCODE SEARCH IMPLEMENTATION ---
    if current_state == 'awaiting_pincode':
        if user_message.isdigit() and len(user_message) == 6:
            pincode = user_message
            api_data = fetch_pincode_data(pincode)
            
            if api_data is None:
                return jsonify({
                    "response": "Sorry, we couldn't fetch pincode information at this time. Please enter a valid 6-digit number to try again."
                })
            
            session.pop('chatbot_state', None)
            
            if api_data[0]['Status'] == 'Success':
                post_offices = api_data[0]['PostOffice']
                if post_offices:
                    options = [{
                        "text": f"{po.get('Name', 'N/A')} ({po.get('BranchType', 'Office')})",
                        "value": f"post_office_{po.get('Name', '').replace(' ', '_')}"
                    } for po in post_offices[:5]]
                    
                    response_msg = f"Found {len(post_offices)} post offices for {pincode}. Main offices:"
                    if len(post_offices) > 5:
                        response_msg += f" (showing 5 of {len(post_offices)})"
                    
                    return jsonify({
                        "response": response_msg,
                        "options": options,
                        "full_data": post_offices
                    })
                else:
                    return jsonify({
                        "response": f"No post offices found for pincode {pincode}. Please enter another 6-digit number to try again.",
                        "options": []
                    })
            else:
                return jsonify({
                    "response": f"Error: {api_data[0].get('Message', 'Pincode not found')}. Please enter a valid 6-digit number to try again.",
                    "options": []
                })
        else:
            return jsonify({
                "response": "That doesn't look like a valid Pincode. Please enter a 6-digit number.",
                "options": []
            })
    
    # Set the state if the user chooses to search by pincode
    if user_message == 'find_by_pincode':
        session['chatbot_state'] = 'awaiting_pincode'
        return jsonify({
            "response": "Please enter the 6-digit pincode to search for post offices:",
            "options": []
        })

    if user_message == 'find_office_by_location':
        return jsonify({"response": "Please share your location to find nearby post offices."})
    
    # Fallback to keyword-based responses from the data.json file
    data = load_data()
    for entry in data:
        keywords = [k.lower() for k in entry['keywords']]
        if any(keyword in user_message for keyword in keywords):
            answers = entry.get('answer')
            if isinstance(answers, dict) and 'options' in answers:
                answer = random.choice(answers['options'])
            else:
                answer = answers
            response_data = {"response": answer}
            if 'options' in entry:
                response_data['options'] = entry['options']
            return jsonify(response_data)
    
    # Generic fallback if no intent is matched
    return jsonify({
        "response": "I'm not sure I understand. How can I help you?",
        "options": [
           
            {"text": "Go back", "value": "reset"}
        ]
    })
if __name__ == '__main__':
    app.run(debug=True)
