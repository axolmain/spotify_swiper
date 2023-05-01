from flask import Flask, render_template, request, redirect, session
from flask_session import Session
from flask_talisman import Talisman
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import CLIENT_ID, CLIENT_SECRET, APP_KEY, MONGODB_USER, MONGODB_PASS
import json
import pymongo
from pymongo import MongoClient
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = APP_KEY

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)
talisman = Talisman(app)

# Connect to MongoDB Atlas cluster
username = quote_plus(MONGODB_USER)
password = quote_plus(MONGODB_PASS)
MONGODB_URI = f"mongodb+srv://{username}:{password}@spotifyswiperfree.urhcq77.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGODB_URI)
db = client.spotifyswiperfree
collection = db.responses

# Set up Spotify authentication
# my_env_var =
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri="http://31.220.108.226:4200/redirect", scope="user-top-read")

@app.route('/')
def hello():
    return render_template('index.html')

@app.route("/login", methods=['POST'])
def login():
    # Redirect the user to the Spotify login page
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirected_name():
    # Get the authorization code from the Spotify redirect
    code = request.args.get('code')
    print("some code", code)

    # Exchange the code for an access token
    token_info = sp_oauth.get_access_token(code, check_cache=False)
    access_token = token_info['access_token']
    session['access_token'] = access_token

    # Create a new Spotipy client with the access token
    sp = spotipy.Spotify(auth=access_token)
    print("this is a code", code)
    print("sp thing", sp)

    # Get the user's ID from the Spotify API response
    user_id = sp.current_user()["id"]
    session['user_id'] = user_id
    print("user_id at start", user_id)

    return render_template('user.html', user_id=user_id, access_token=access_token)

@app.route('/give_data', methods=['POST'])
def give_data():
    access_token = session.get('access_token')
    user_id = session.get('user_id')

    print(user_id)

    if not access_token:
        return redirect('/')

    # Create a new Spotipy client with the access token
    sp = spotipy.Spotify(auth=access_token)


    # Get the user's top artists and tracks
    top_tracks_short = sp.current_user_top_tracks(time_range='short_term', limit=20)
    top_tracks_medium = sp.current_user_top_tracks(time_range='medium_term', limit=20)
    top_artists_short = sp.current_user_top_artists(time_range='short_term', limit=20)
    top_artists_medium = sp.current_user_top_artists(time_range='medium_term', limit=20)

    # Create a list of the top tracks, albums, and artists
    blist1 = [top_tracks_short['items'][song]['id'] for song in range(len(top_tracks_short['items']))]
    blist2 = [top_tracks_medium['items'][song]['id'] for song in range(len(top_tracks_medium['items']))]
    blist3 = [top_tracks_short['items'][song]['album']['id'] for song in range(len(top_tracks_short['items']))]
    blist4 = [top_tracks_medium['items'][song]['album']['id'] for song in range(len(top_tracks_medium['items']))]
    blist5 = [top_artists_short['items'][song]['id'] for song in range(len(top_artists_short['items']))]
    blist6 = [top_artists_medium['items'][song]['id'] for song in range(len(top_artists_medium['items']))]
    # all genres of the songs/albums put into a list
    blist7 = [top_tracks_short['items'][song]['album']['genres'] for song in range(len(top_tracks_short['items']))]
    audio_features_short = sp.audio_features(tracks=blist1)
    audio_features_medium = sp.audio_features(tracks=blist2)

    # Create a dictionary that contains all user information gathered here. Keys are "top_tracks_short", "top_tracks_medium", "top_artists_short", "top_artists_medium", "top_albums_short", and "top_albums_short". Values are the corresponding lists of tracks, artists, and albums except for the audio features, which is a list attached to each individual song.
    def extract_features(song_id):
        features = ["acousticness", "danceability", "energy", "speechiness", "tempo", "valence"]
        data = sp.audio_features(tracks=song_id)[0]
        user_features = {feature: data[feature] for feature in features}
        return user_features

    user_info = {
    "user_tracks_short": [
        {"song_id": track["id"], "audio_features": extract_features(track["id"])}
        for track in top_tracks_short["items"]
    ],
    "user_tracks_medium": [
        {"song_id": track["id"], "audio_features": extract_features(track["id"])}
        for track in top_tracks_medium["items"]
    ],
        "albums_short": [
            {"album_id": track["album"]["id"]}
            for track in top_tracks_short["items"]
        ],
        "albums_medium": [
            {"album_id": track["album"]["id"]}
            for track in top_tracks_medium["items"]
        ],
        "artists_short": [
            {"artist_id": artist["id"]}
            for artist in top_artists_short["items"]
        ],
        "artists_medium": [
            {"artist_id": artist["id"]}
            for artist in top_artists_medium["items"]
        ],
    }
    print("user_id almost end", user_id)

    # Save the user's information to a new MongoDB document
    if collection.find_one({"user_id": user_id}):
        collection.update_one({"user_id": user_id}, {"$set": {"user_info": user_info}})
    else:
        collection.insert_one({"user_id": user_id, "user_info": user_info})
    print("user_id at end", user_id)
    
    return render_template('display_data.html', user_info=user_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4200)