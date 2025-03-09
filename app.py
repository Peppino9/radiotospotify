from flask import Flask, render_template, request, session, redirect, url_for, request, jsonify
import requests
import xml.etree.ElementTree as ET
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = "secretdeluxe"

# Spotify API
SPOTIFY_CLIENT_ID = "Add_Client-ID"
SPOTIFY_CLIENT_ID = "c214a3e3850c4821899be00e77de846c" 

SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPE = "playlist-modify-public playlist-modify-private user-read-private user-top-read user-read-email"

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE
)

# Sveriges Radios API
PLAYLIST_API_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid={channel_id}"

# Kanaler man kan välja mellan
CHANNELS = [
    {"id": "132", "name": "P1"},
    {"id": "163", "name": "P2"},
    {"id": "164", "name": "P3"},
    {"id": "2576", "name": "Din Gata"}
]

@app.route('/')
def home():
    return render_template("main.html", channels=CHANNELS)

# Login
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url() + "&show_dialog=True"  #fresh login
    return redirect(auth_url)
# Log Out - clear session
@app.route('/logout')
def logout():
    session.clear() 
    try:
        os.remove(".cache")
    except FileNotFoundError:
        pass
    return redirect(url_for('home'))

@app.route('/callback')
def callback():
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    spotify = spotipy.Spotify(auth=token_info["access_token"])
    user_info = spotify.me()
    
    session["user"] = {
        "name": user_info["display_name"],
        "image": user_info["images"][0]["url"] if user_info.get("images") else None
    }
    return redirect(url_for("home"))

@app.route('/user-profile')
def user_profile():
    user = session.get("user", {})
    if not user:
        return jsonify({"authenticated": False})
    return jsonify({**user, "authenticated": True})

def get_spotify_client():
    token_info = session.get("token_info")
    if not token_info:
        return None

    if not session.get("user"):
        return None

    if sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            session["token_info"] = token_info
        except Exception as e:
            print(f"Error refreshing token: {e}")
            session.clear()
            return None

    return spotipy.Spotify(auth=token_info["access_token"])


#  Hämtar & visar användarens spellista
@app.route('/user-playlists')
def user_playlists():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify([])
    playlists = spotify.current_user_playlists()
    return jsonify(playlists["items"])

# Lägger till låt i användares spellistor
@app.route('/add-to-playlist', methods=['POST'])
def add_to_playlist():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.json
    track_uri = data.get("song_uri") 
    playlist_id = data.get("playlist_id")

    if not track_uri or not playlist_id:
        return jsonify({"error": "Missing song URI or playlist ID"}), 400

    try:
        spotify.playlist_add_items(playlist_id, [track_uri])
        return jsonify({"message": "Song added to playlist!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Hämtar spelad låt från Sveriges Radio
@app.route('/current-song/<channel_id>')
def current_song(channel_id):
    try:
        response = requests.get(PLAYLIST_API_URL.format(channel_id=channel_id))
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch song data"}), 500

        root = ET.fromstring(response.content)
        song_title = root.find(".//song/title")
        artist_name = root.find(".//song/artist")

        if song_title is None or artist_name is None:
            return jsonify({"error": "No song found"}), 404

        song_title = song_title.text if song_title.text else "Ingen titel"
        artist_name = artist_name.text if artist_name.text else "Ingen artist"

    except Exception as e:
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

    return jsonify({
        "title": song_title,
        "artist": artist_name
    })

if __name__ == '__main__':
    app.run(debug=True)
