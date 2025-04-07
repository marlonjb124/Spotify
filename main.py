# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import os
from urllib.parse import urlencode

app = FastAPI()

# Configuración desde variables de entorno
CLIENT_ID =  'b592b4bfc0394c5aaaf2fc453ba9a462'

CLIENT_SECRET = '5471d9bd1bd1430aa096100afc2e75bb'

# Configuración
REDIRECT_URI = "http://localhost:8000/callback"

# Almacenamiento temporal (solo para pruebas)
tokens = {"access_token":"BQCENXwu0ut4-UToERq2zyAZJy96R4dFmkhHASS2oZHleUcvIQeS06kNgXkF-ul6V5p_kzl8RR7xwXHHPwBMNj6Hhry2MGh-XlvLilnaClmS40i3lTaosUUXbnA4g6A2XN3LbAMYhVn4E82-YhRPAzuohEiCWH7kgb7P6y67TtpskaHagbza5X5RxDr00KdEPeHa_BpodrnpJ9OGeyl3xHF3DIUgcDJy44OfPvXNY40O18lMmqw"}

@app.get("/login")
async def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-modify-playback-state user-read-playback-state",
    }
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(code: str):


    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Error de autenticación")
    print(response.json()["access_token"])
    tokens["access_token"] = response.json()["access_token"]
    return {"status": "¡Autenticación exitosa! Token almacenado en memoria."}
@app.put("/stop")
async def stop_song(track_name: str,artist:str):
    if not tokens.get("access_token"):
        raise HTTPException(status_code=401, detail="No autenticado. Ve a /login primero.")
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # Buscar la canción
    # async with httpx.AsyncClient() as client:
    #     search_url = "https://api.spotify.com/v1/search"
    #     params = {"q": track_name +" "+ artist, "type": "track", "limit": 1}
    #     response = await client.get(search_url, headers=headers, params=params)
    
    # if not response.json().get("tracks", {}).get("items"):
    #     raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    # track_uri = response.json()["tracks"]["items"][0]["uri"]
    
    # Obtener dispositivo activo
    # async with httpx.AsyncClient() as client:
    #     devices_url = "https://api.spotify.com/v1/me/player/devices"
    #     response = await client.get(devices_url, headers=headers)
    #     print(response.json())
    #     print(response.headers)
    
    # devices = response.json().get("devices", [])

    # if not devices:
    #     raise HTTPException(status_code=400, detail="Activa un dispositivo en Spotify primero (ej: app móvil o web).")
    
    # device_id = devices[0]["id"]
    
    # Reproducir
    play_url = f"https://api.spotify.com/v1/me/player/pause?device_id=01f57fb8045a8e484c44192a94e8527ed811a87d"


    
    async with httpx.AsyncClient() as client:
        response = await client.put(play_url, headers=headers)
        # print(response.json())
    
    if response.status_code != 204:
        raise HTTPException(status_code=400, detail="Error al pausar. ¿El dispositivo está activo?")
    
    return {"status": "¡Reproduciendo!", "track_uri": track_uri}
@app.put("/play")
async def play_song(track_name: str,artist:str):
    if not tokens.get("access_token"):
        raise HTTPException(status_code=401, detail="No autenticado. Ve a /login primero.")
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # Buscar la canción
    async with httpx.AsyncClient() as client:
        search_url = "https://api.spotify.com/v1/search"
        params = {"q": track_name +" "+ artist, "type": "track", "limit": 1}
        response = await client.get(search_url, headers=headers, params=params)
    
    if not response.json().get("tracks", {}).get("items"):
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    track_uri = response.json()["tracks"]["items"][0]["uri"]
    
    # Obtener dispositivo activo
    async with httpx.AsyncClient() as client:
        devices_url = "https://api.spotify.com/v1/me/player/devices"
        response = await client.get(devices_url, headers=headers)
        print(response.json())
        print(response.headers)
    
    devices = response.json().get("devices", [])

    if not devices:
        raise HTTPException(status_code=400, detail="Activa un dispositivo en Spotify primero (ej: app móvil o web).")
    
    device_id = devices[0]["id"]
    
    # Reproducir
    play_url = f"https://api.spotify.com/v1/me/player/play?device_id=01f57fb8045a8e484c44192a94e8527ed811a87d"
    data = {"uris": [track_uri],"position_ms":100
}
    
    async with httpx.AsyncClient() as client:
        response = await client.put(play_url, headers=headers, json=data)
        # print(response.json())
    
    if response.status_code != 204:
        raise HTTPException(status_code=400, detail="Error al reproducir. ¿El dispositivo está activo?")
    
    return {"status": "¡Reproduciendo!", "track_uri": track_uri}
# from fastapi import FastAPI
# # from fastapi.encoders import jsonable_encoder
# import requests
# app = FastAPI()
# CLIENT_ID =  'b592b4bfc0394c5aaaf2fc453ba9a462'

# CLIENT_SECRET = '5471d9bd1bd1430aa096100afc2e75bb'

# # Obtener token
# auth_url = 'https://accounts.spotify.com/api/token'
# @app.post("/spotify")
# async def buscar(q:str|None = None):
#     auth_response = requests.post(auth_url, {
#         'grant_type': 'client_credentials',
#         'client_id': CLIENT_ID,
#         'client_secret': CLIENT_SECRET,
#     })

#     access_token = auth_response.json().get('access_token')

#     headers = {
#         'Authorization': f'Bearer {access_token}'
#     }

#     search_url = 'https://api.spotify.com/v1/search'
#     params = {
#         'q': 'track:Thriller artist:Michael Jackson',
#         'type': 'track',
#         'limit': 1
#     }

#     response = requests.get(search_url, headers=headers, params=params)
#     data = response.json()
#     track_uri = data["tracks"]["items"][0]["uri"]
#     devices_url = "https://api.spotify.com/v1/me/player/devices"
#     response = requests.get(devices_url, headers=headers)
#     devices = response.json()["devices"]

#     if not devices:
#         print("¡Activa un dispositivo en Spotify (web/app) primero!")
#         exit()

#     device_id = devices[0]["id"]  # Tomamos el primer dispositivo activo
#     play_url = f"https://api.spotify.com/v1/me/player/play?device_id={device_id}"
#     body = {
#         "uris": [track_uri]  # Envía el URI como lista
#     }

#     response = requests.put(play_url, headers=headers, json=body)

#     if response.status_code == 204:
#         print("✅ Canción reproduciéndose en Spotify!")
#     else:
#         print("Error:", response.json())
    # print(data)
    # return data

    # Extraer datos del primer resultado
    # if data['albums']['items']:
    #     album = data['albums']['items'][0]
    #     print(album.items())
    #     print(f"ID: {album['id']}")
    #     print(f"Nombre: {album['name']}")
    #     print(f"Artista: {album['artists'][0]['name']}")
    #     print(f"Fecha de lanzamiento: {album['release_date']}")
    #     return album
    # else:
    #     print("No se encontraron resultados.")
@app.get("/home")
async def home():
    return{"hi":"sda"}
    
    