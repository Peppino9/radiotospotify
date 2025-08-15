from flask import Flask, render_template, request, redirect, jsonify, url_for
import requests
import xml.etree.ElementTree as ET
import spotipy
from spotipy.oauth2 import SpotifyOAuth

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

def make_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=None
    )

def spotify_from_request():
    # Spotify client från Authorization, access token header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, ("Missing or invalid Authorization header", 401)
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None, ("Missing access token", 401)
    sp = spotipy.Spotify(auth=token)
    try:
        sp.current_user()
    except spotipy.exceptions.SpotifyException:
        return None, ("Invalid or expired token", 401)
    return sp, None

@app.route("/")
def home():
    return render_template("main.html", channels=CHANNELS)

@app.route("/oauth/spotify/authorize")
def oauth_authorize():
    url = make_oauth().get_authorize_url() + "&show_dialog=True"
    return redirect(url, code=302)

@app.route("/callback")
def oauth_callback():
    error = request.args.get("error")
    if error:
        return redirect("/")
    
    code = request.args.get("code")
    if not code:
        return redirect("/")

    oauth = make_oauth()
    token_info = oauth.get_access_token(code, check_cache=False, as_dict=True)

    access_token = token_info.get("access_token", "")
    refresh_token = token_info.get("refresh_token", "")
    expires_in = int(token_info.get("expires_in", 0))

    sp = spotipy.Spotify(auth=access_token)
    me = sp.me()

    return redirect(
        url_for(
            "home",
            spotify_access_token=access_token,
            spotify_refresh_token=refresh_token,
            spotify_expires_at=expires_in,
            spotify_user=me.get("id")
        )
    )



@app.route("/oauth/spotify/refresh", methods=["POST"])
def oauth_refresh():
    data = request.get_json(force=True, silent=True) or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "refresh_token is required"}), 400
    try:
        token_info = make_oauth().refresh_access_token(refresh_token)
        return jsonify({
            "access_token": token_info.get("access_token"),
            "expires_in": token_info.get("expires_in"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/users/me", methods=["GET"])
def users_me():
    sp, err = spotify_from_request()
    if err:
        msg, code = err
        return jsonify({"error": msg}), code

    me = sp.me()
    return jsonify({
        "name": me.get("display_name"),
        "image": (me.get("images") or [{}])[0].get("url"),
        "id": me.get("id"),
        "authenticated": True
    })


# Hämtar & visar användarens spellista
@app.route("/users/me/playlists", methods=["GET"])
def users_playlists():
    sp, err = spotify_from_request()
    if err:
        msg, code = err
        return jsonify([]), code
    playlists = sp.current_user_playlists()
    return jsonify(playlists.get("items", []))

# Lägg till låt i använderens spellistor
@app.route("/playlists/<playlist_id>/tracks", methods=["PATCH"])
def add_track(playlist_id):
    sp, err = spotify_from_request()
    if err:
        msg, code = err
        return jsonify({"error": msg}), code
    data = request.get_json(force=True, silent=True) or {}
    track_uri = data.get("song_uri")
    if not track_uri:
        return jsonify({"error": "Missing song_uri"}), 400
    try:
        sp.playlist_add_items(playlist_id, [track_uri])
        return jsonify({"message": "Song added to playlist!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sök efter låt på spotify
def search_spotify(sp, query):
    try:
        result = sp.search(q=query, type="track", limit=1)
        items = result.get("tracks", {}).get("items", [])
        if not items:
            return None
        uri = items[0]["uri"]
        return f"https://open.spotify.com/track/{uri.split(':')[-1]}"
    except Exception:
        return None

# Hämtar spelad låt från Sveriges Radio
@app.route("/channels/<channel_id>/current-song", methods=["GET"])
def current_song(channel_id):
    try:
        r = requests.get(PLAYLIST_API_URL.format(channel_id=channel_id), timeout=5)
        if r.status_code != 200:
            return jsonify({"error": "Failed to fetch song data"}), 502

        root = ET.fromstring(r.content)
        song = root.find(".//song")
        title = song.find("title").text if song is not None and song.find("title") is not None else "Ingen titel"
        artist = song.find("artist").text if song is not None and song.find("artist") is not None else "Ingen artist"

        sp, err = spotify_from_request()
        spotify_url = None
        if not err:
            spotify_url = search_spotify(sp, f"{title} {artist}")

        return jsonify({"title": title, "artist": artist, "song_url": spotify_url})
    except Exception as e:
        return jsonify({"error": f"Error processing request: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)