from flask import Flask, render_template, request
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# Sveriges Radios API
PLAYLIST_API_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid={channel_id}"

# Kanaler man kan välja mellan
CHANNELS = [
    {"id": "132", "name": "P1"},
    {"id": "163", "name": "P2"},
    {"id": "164", "name": "P3"},
    {"id": "2576", "name": "Din Gata"}
]

@app.route('/', methods=['GET', 'POST'])
def home():
    try:
        # Standardkanal är P3 om inget val görs
        selected_channel_id = request.form.get("channel_id", "164")
        selected_channel_name = next((c["name"] for c in CHANNELS if c["id"] == selected_channel_id), "Okänd kanal")

        # Hämta låtdata för vald kanal
        response = requests.get(PLAYLIST_API_URL.format(channel_id=selected_channel_id))
        response.raise_for_status()
        root = ET.fromstring(response.content)

        # Hämta låtdata
        current_song = root.find(".//song")
        previous_song = root.find(".//previoussong")

        song_info = {
            "current_song": {
                "title": current_song.find("title").text if current_song is not None and current_song.find("title") is not None else "Ingen titel",
                "artist": current_song.find("artist").text if current_song is not None and current_song.find("artist") is not None else "Ingen artist",
            },
            "previous_song": {
                "title": previous_song.find("title").text if previous_song is not None and previous_song.find("title") is not None else "Ingen föregående låt",
                "artist": previous_song.find("artist").text if previous_song is not None and previous_song.find("artist") is not None else "Ingen artist",
            },
            "channel": {
                "id": selected_channel_id,
                "name": selected_channel_name,
            }
        }

        # Rendera HTML
        return render_template('main.html', channels=CHANNELS, song_info=song_info, selected_channel_id=selected_channel_id)

    except requests.exceptions.RequestException as e:
        return f"<h1>Fel vid hämtning av data: {e}</h1>"

if __name__ == '__main__':
    app.run(debug=True)
