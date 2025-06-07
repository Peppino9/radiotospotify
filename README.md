# Radio To Spotify
# Grupp 33

Detta projekt är en Flask-webbapplikation som låter användare hämta information om nuvarande låtar som spelas på Sveriges Radio, söka efter dem på Spotify och lägga till dem i sina spellistor.


## Funktioner

- Användare kan logga in med sitt Spotify-konto.
- Hämtar aktuell låt från Sveriges Radio via deras API.
- Söker efter låten på Spotify och visar en länk till den.
- Visar användarens Spotify-spellistor.
- Låter användaren lägga till låtar i en spellista.

## Krav för att projektet ska fungera

Innan du kör projektet behöver du ha följande installerat:

- Python 3.x**  
- pip3 (Python Package Installer)    
- Flask

## Installation

### 1. Klona projektet

```bash
git clone https://github.com/Peppino9/radiotospotify
cd radiotospotify
```

### 2. Skapa och aktivera en virtuell miljö 

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
``````

### 3. Installera beroenden
```bash
pip install -r requirements.txt
```


### 4. Miljövariabler

Byt ut `ClientID` och `ClientSecret` med de faktiska API-nycklarna från Spotify Developer Dashboard inne i **app.py**
```bash
SPOTIFY_CLIENT_ID = "ClientID"
SPOTIFY_CLIENT_SECRET = "ClientSecret"
```

### 5. Starta applikationen

Kör kommandot python app.py

Flask-servern startar och körs på `http://127.0.0.1:5000/`.

## Användning

1. Efter du har kört kommandot så öppna webbläsarenoch navigera fram till `http://127.0.0.1:5000/`.
2. Välj en av radiokanalerna för att se den aktuella låten som spelas.  
3. Logga in på Spotify för att visa dina spellistor.  
4. Lägg till låten i en av dina spellistor genom att välja en av dina spellistor och trycka på lägg till.

## API:er som används

- **Sveriges Radio API:** Hämtar den aktuella låten från valda radiokanaler.
- **Spotify API:** Autentisering, spellistor och låt-sökningar.

