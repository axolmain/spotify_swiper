# Run with python -m flask run
from flask import Flask, render_template, request, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import CLIENT_ID, CLIENT_SECRET

app = Flask(__name__)

# Set up Spotify authentication
# my_env_var = 
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri="http://127.0.0.1:5000/redirect", scope="user-top-read")

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

    # Get the user's top artists
    top_artists = sp.current_user_top_artists()

    # Return the top artists to the user
    return render_template('user.html', top_artists=top_artists)

if __name__ == '__main__':
    app.run(debug=True)