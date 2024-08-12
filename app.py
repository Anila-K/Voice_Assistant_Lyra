from flask import Flask, request, jsonify, render_template
from flask_talisman import Talisman
from flask_socketio import SocketIO, emit
from  flask import g
import joblib
import spacy
import wikipedia
import pyttsx3
import vlc
import datetime
import pyjokes
import requests
import yt_dlp
import os
import  base64

app = Flask(__name__)

# Initialize the speech engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

# Load the intent pipeline
intent_pipeline = joblib.load('intent_pipeline.pkl')
nlp = spacy.load("en_core_web_sm")

# Global variables for media player
player = None
is_playing = False
is_paused = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.json
    command = data['command']

    # Process command with Lyra logic
    intent = classify_intent(command)
    response = handle_intent(intent, command)
    
    # Speak the response using the speech engine
    engine_talk(response)
    
    return jsonify({"intent": intent, "response": response})

@app.route('/start', methods=['POST'])
def start_intro():
    intro_message = "Hi, I'm your voice assistant Lyra. What can I do for you?"
    engine_talk(intro_message)
    return jsonify({"response": intro_message})

def classify_intent(command):
    intent = intent_pipeline.predict([command])[0]
    return intent

def handle_intent(intent, command):
    global is_playing, is_paused
    if intent == 'play_song':
        song = command.replace('play', '').strip()
        play_song(song)
        return f'Playing {song}'
    elif intent == 'pause_song':
        if is_playing:
            pause_song()
            return 'Pausing the song'
    elif intent == 'resume_song':
        if is_paused:
            resume_song()
            return 'Resuming the song'
    elif intent == 'stop_song':
        if is_playing or is_paused:
            stop_song()
            return 'Stopping the song'
    elif intent == 'restart_song':
        if is_playing or is_paused:
            stop_song()
        song = command.replace('restart', '').strip()
        play_song(song)
        return 'Playing the song from the beginning'
    elif intent == 'fetch_info':
        name = command.replace('who is', '').replace('what is', '').strip()
        return fetch_wikipedia_summary(name)
    elif intent == 'tell_joke':
        return pyjokes.get_joke()
    elif intent == 'time':
        return datetime.datetime.now().strftime('%I:%M %p')
    elif intent == 'get_weather':
        city = extract_city(command)
        if city:
            weather_info = weather(city)
            if weather_info == "City Not Found":
                return "City not found"
            else:
                return f'The current temperature in {city} is {weather_info} degrees Celsius'
        else:
            return "Sorry, I couldn't determine the city."
    elif intent == 'thank_you':
        return 'You are welcome'
    elif intent == 'shut_down':
        return 'Goodbye!'
    else:
        return 'I could not hear you properly'

def engine_talk(text):
    engine.say(text)
    engine.runAndWait()

def play_song(song):
    global player, is_playing, is_paused
    player = vlc.MediaPlayer()
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(f"ytsearch:{song}", download=False)
        video_url = info_dict['entries'][0]['url']
        player.set_mrl(video_url)
        player.play()
        is_playing = True
        is_paused = False

def pause_song():
    global is_playing, is_paused
    if player and is_playing:
        player.pause()
        is_playing = False
        is_paused = True

def resume_song():
    global is_playing, is_paused
    if player and is_paused:
        player.play()
        is_playing = True
        is_paused = False

def stop_song():
    global is_playing, is_paused
    if player:
        player.stop()
        is_playing = False
        is_paused = False

def fetch_wikipedia_summary(name):
    try:
        summary = wikipedia.summary(name, sentences=2)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:5])
        return f"The term is ambiguous. Did you mean one of the following? {options}"
    except wikipedia.exceptions.PageError:
        return "Sorry, I couldn't find any information on that topic."
    except Exception as e:
        return f"Sorry, an error occurred: {str(e)}"

def weather(city):
    api_key = "142ba3ad77c737d4d7023e7381b9b27a"
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + api_key + "&q=" + city
    response = requests.get(complete_url)
    x = response.json()
    if x["cod"] != "404":
        y = x["main"]
        current_temperature = y["temp"]
        current_temperature_celsius = current_temperature - 273.15
        return str(round(current_temperature_celsius, 2))
    else:
        return "City Not Found"

def extract_city(command):
    doc = nlp(command)
    for entity in doc.ents:
        if entity.label_ == 'GPE':
            return entity.text
    return None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
