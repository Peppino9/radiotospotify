from flask import Flask, render_template, request
import requests
import xml.etree.ElementTree as ET
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# Spotify API

# Skapa Spotify-klient
spotify_auth = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
spotify_client = spotipy.Spotify(auth_manager=spotify_auth)

# Sveriges Radios API
PLAYLIST_API_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid={channel_id}"

# Kanaler man kan välja mellan
CHANNELS = [
    {"id": "132", "name": "P1"},
    {"id": "163", "name": "P2"},
    {"id": "164", "name": "P3"},
    {"id": "2576", "name": "Din Gata"}
]

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
        current_spotify_url = current_spotify_result["spotify_url"] if current_spotify_result else None

        # Föregående låt
        previous_song = root.find(".//previoussong")
        previous_song_title = previous_song.find("title").text if previous_song is not None and previous_song.find("title") is not None else "Ingen föregående låt"
        previous_song_artist = previous_song.find("artist").text if previous_song is not None and previous_song.find("artist") is not None else "Ingen artist"
        previous_spotify_result = search_spotify(f"{previous_song_title} {previous_song_artist}")
        previous_spotify_url = previous_spotify_result["spotify_url"] if previous_spotify_result else None

        # Samla information om låtar och kanal
        song_info = {
            "current_song": {
                "title": current_song_title,
                "artist": current_song_artist,
                "spotify_url": current_spotify_url
            },
            "previous_song": {
                "title": previous_song_title,
                "artist": previous_song_artist,
                "spotify_url": previous_spotify_url
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
