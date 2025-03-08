from flask import Flask, render_template, request, session, redirect, url_for, request, jsonify
import requests
import xml.etree.ElementTree as ET
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = "secretdeluxe"

# Spotify API
SPOTIFY_CLIENT_ID = "Add_Client-ID"
SPOTIFY_CLIENT_SECRET = "Add_Client-Secret"

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
    return redirect(url_for("home"))

@app.route('/user-profile')
def user_profile():
    token_info = session.get("token_info")
    if not token_info:
        return jsonify({"authenticated": False})

    spotify = spotipy.Spotify(auth=token_info["access_token"])
    user_info = spotify.me()

    return jsonify({
        "authenticated": True,
        "name": user_info["display_name"],
        "image": user_info["images"][0]["url"] if user_info.get("images") else None
    })

# Söker efter en låt baserat på titel i Spotify
def search_spotify(query):
    try:
        results = spotify_client.search(q=query, type="track", limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return {
                "spotify_url": track["external_urls"]["spotify"],
                "song_name": track["name"],
                "artist_name": track["artists"][0]["name"]
            }
    except Exception as e:
        print(f"Fel vid Spotify-sökning: {e}")
    return None

# Söker efter en låt baserat på artist i Spotify
def search_spotify_artist(artist_name):
    try:
        results = spotify_client.search(q=f"artist:{artist_name}", type="artist", limit=1)
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            return artist["external_urls"]["spotify"]
    except Exception as e:
        print(f"Error searching Spotify for artist: {e}")
    return None

@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        # Standardkanal är P3 om inget val görs
        selected_channel_id = request.form.get("channel_id", "164")
        selected_channel_name = next((c["name"] for c in CHANNELS if c["id"] == selected_channel_id), "Okänd kanal")

        # Hämta låtdata från Sveriges Radios API
        response = requests.get(PLAYLIST_API_URL.format(channel_id=selected_channel_id))
        response.raise_for_status()
        root = ET.fromstring(response.content)

        # Nuvarande låt
        current_song = root.find(".//song")
        current_song_title = current_song.find("title").text if current_song is not None and current_song.find("title") is not None else "Ingen titel"
        current_song_artist = current_song.find("artist").text if current_song is not None and current_song.find("artist") is not None else "Ingen artist"
        current_spotify_result = search_spotify(f"{current_song_title} {current_song_artist}")
        current_song_start_time = current_song.find("starttimeutc").text if current_song is not None and current_song.find("starttimeutc") is not None else "Okänd tid"
        current_spotify_url = current_spotify_result["spotify_url"] if current_spotify_result else None
        current_artist_spotify_url = search_spotify_artist(current_song_artist)

        # Föregående låt
        previous_song = root.find(".//previoussong")
        previous_song_title = previous_song.find("title").text if previous_song is not None and previous_song.find("title") is not None else "Ingen föregående låt"
        previous_song_artist = previous_song.find("artist").text if previous_song is not None and previous_song.find("artist") is not None else "Ingen artist"
        previous_song_start_time = previous_song.find("starttimeutc").text if previous_song is not None and previous_song.find("starttimeutc") is not None else "Okänd tid"
        previous_spotify_result = search_spotify(f"{previous_song_title} {previous_song_artist}")
        previous_spotify_url = previous_spotify_result["spotify_url"] if previous_spotify_result else None
        previous_artist_spotify_url = search_spotify_artist(previous_song_artist)

        # Samla information om låtar och kanal
        song_info = {
            "current_song": {
                "title": current_song_title,
                "artist": current_song_artist,
                "spotify_url": current_spotify_url,
                "start_time": current_song_start_time,
                "artist_spotify_url": current_artist_spotify_url
                
            },
            "previous_song": {
                "title": previous_song_title,
                "artist": previous_song_artist,
                "spotify_url": previous_spotify_url,
                "start_time": previous_song_start_time,
                "artist_spotify_url": previous_artist_spotify_url
            },
            "channel": {
                "id": selected_channel_id,
                "name": selected_channel_name,
            }
        }

        return render_template('main.html', channels=CHANNELS, song_info=song_info, selected_channel_id=selected_channel_id)

    except requests.exceptions.RequestException as e:
        return f"<h1>Fel vid hämtning av data: {e}</h1>"

if __name__ == '__main__':
    app.run(debug=True)
