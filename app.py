from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests
import xml.etree.ElementTree as ET
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = "secretdeluxe"

SPOTIFY_CLIENT_ID = "ClientID"
SPOTIFY_CLIENT_SECRET = "ClientSecret"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPE = "playlist-modify-public playlist-modify-private user-read-private user-top-read user-read-email"

# Sveriges Radios API
PLAYLIST_API_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid={channel_id}"

# Kanaler man kan välja mellan
CHANNELS = [
    {"id": "132", "name": "P1"},
    {"id": "163", "name": "P2"},
    {"id": "164", "name": "P3"},
    {"id": "2576", "name": "Din Gata"},
]

def _make_spotify_oauth():
    user_id = session.get("user_id")
    cache_path = f".cache-{user_id}" if user_id else ".cache-temp"
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=cache_path
    )

@app.route('/')
def home():
    return render_template("main.html", channels=CHANNELS)

#Log in - skapa session
@app.route('/sessions', methods=['POST'])
def create_session():
    spotify_oauth = _make_spotify_oauth()
    auth_url = spotify_oauth.get_authorize_url() + "&show_dialog=True"
    return redirect(auth_url)

#Log Out - clear session
@app.route('/sessions', methods=['DELETE'])
def delete_session():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        try:
            os.remove(f".cache-{user_id}")
        except FileNotFoundError:
            pass
    try:
        os.remove(".cache-temp")
    except FileNotFoundError:
        pass
    return '', 204

@app.route('/callback')
def callback():
    if request.args.get("error"):
        return redirect(url_for("home"))
    code = request.args.get("code")
    if not code:
        return redirect(url_for("home"))

    temp_oauth = _make_spotify_oauth()
    token_info = temp_oauth.get_access_token(code)
    session["token_info"] = token_info

    spotify_client = spotipy.Spotify(auth=token_info["access_token"])
    user_info = spotify_client.me()
    user_id = user_info["id"]

    try:
        os.rename(".cache-temp", f".cache-{user_id}")
    except FileNotFoundError:
        pass

    session["user_id"] = user_id
    session["user"] = {
        "name": user_info.get("display_name"),
        "image": user_info.get("images")[0]["url"] if user_info.get("images") else None
    }

    return redirect(url_for("home"))

@app.route('/users/me')
def user_profile():
    user = session.get("user", {})
    if not user:
        return jsonify({"authenticated": False})
    return jsonify({**user, "authenticated": True})

def get_spotify_client():
    user_id = session.get("user_id")
    if not user_id:
        return None

    cache_path = f".cache-{user_id}"
    spotify_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=cache_path
    )

    token_info = spotify_oauth.get_cached_token()
    if not token_info:
        return None

    if spotify_oauth.is_token_expired(token_info):
        try:
            token_info = spotify_oauth.refresh_access_token(token_info["refresh_token"])
        except Exception:
            session.clear()
            return None

    return spotipy.Spotify(auth=token_info["access_token"])

#  Hämtar & visar användarens spellista
@app.route('/users/me/playlists')
def user_playlists():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify([])

    playlists = spotify.current_user_playlists()
    return jsonify(playlists["items"])

# Lägger till låt i användares spellistor
@app.route('/playlists/<playlist_id>/tracks', methods=['PATCH'])
def add_track_to_playlist(playlist_id):
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.json
    track_uri = data.get("song_uri")
    if not track_uri:
        return jsonify({"error": "Missing song URI"}), 400

    try:
        spotify.playlist_add_items(playlist_id, [track_uri])
        return jsonify({"message": "Song added to playlist!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sök efter låt på spotify
def search_spotify(query):
    spotify = get_spotify_client()
    if not spotify:
        return None

    result = spotify.search(q=query, type="track", limit=1)
    tracks = result.get("tracks", {}).get("items", [])
    if not tracks:
        return None

    song_uri = tracks[0]["uri"]
    song_url = f"https://open.spotify.com/track/{song_uri.split(':')[-1]}"
    return {"spotify_url": song_url}

# Hämtar spelad låt från Sveriges Radio
@app.route('/channels/<channel_id>/current-song')
def current_song(channel_id):
    try:
        response = requests.get(PLAYLIST_API_URL.format(channel_id=channel_id), timeout=5)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch song data"}), 500

        root = ET.fromstring(response.content)
        current_song = root.find(".//song")
        title = current_song.find("title").text if current_song is not None and current_song.find("title") is not None else "Ingen titel"
        artist = current_song.find("artist").text if current_song is not None and current_song.find("artist") is not None else "Ingen artist"

        spotify_result = search_spotify(f"{title} {artist}")
        spotify_url = spotify_result["spotify_url"] if spotify_result else None

    except Exception as e:
        return jsonify({"error": f"Error processing request: {e}"}), 500

    return jsonify({
        "title": title,
        "artist": artist,
        "song_url": spotify_url
    })

if __name__ == '__main__':
    app.run(debug=True)