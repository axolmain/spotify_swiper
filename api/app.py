# Run with python -m flask run
from flask import Flask, render_template, request, redirect
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheHandler
from config import CLIENT_ID, CLIENT_SECRET
import json
import pymongo
from pymongo import MongoClient
from urllib.parse import quote_plus

# Connect to MongoDB Atlas cluster
username = quote_plus("axolmain")
password = quote_plus("jxpxwWsZFP3vo5DT")
MONGODB_URI = f"mongodb+srv://{username}:{password}@spotifyswiperfree.urhcq77.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGODB_URI)
db = client.spotifyswiperfree
collection = db.responses

class MongoDBCacheHandler(CacheHandler):
    def __init__(self, db):
        self.db = db

    def get_cached_token(self):
        token = self.db.cacheHandler.find_one()
        return token if token else None

    def save_token_to_cache(self, token_info):
        self.db.cacheHandler.replace_one({}, token_info, upsert=True)


app = Flask(__name__)

# Set up Spotify authentication
# my_env_var =
# Set up Spotify authentication with custom cache handler
cache_handler = MongoDBCacheHandler(db)
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri="https://spotify-swiper-axolmain.vercel.app/redirect", scope="user-top-read", cache_handler=cache_handler)

# maybe setup as an auth header 

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

    # Exchange the code for an access token
    token_info = sp_oauth.get_access_token(code)
    access_token = token_info['access_token']

    # Create a new Spotipy client with the access token
    sp = spotipy.Spotify(auth=access_token)

    # Get the user's ID from the Spotify API response
    user_id = sp.current_user()["id"]

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

    # Save the user's information to a new MongoDB document
    collection.insert_one({"user_id": user_id, "user_info": user_info})

    # Return the top artists to the user
    return render_template('user.html', top_artists=blist1)