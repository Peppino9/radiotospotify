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
# Söker efter en låt baserat på titel i Spotify
def search_spotify(query):
    try:
        results = get_spotify_client.search(q=query, type="track", limit=1)
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


# Söker efter en låt baserat på artist i Spotify
def search_spotify_artist(artist_name):
    try:
        results = get_spotify_client.search(q=f"artist:{artist_name}", type="artist", limit=1)
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
