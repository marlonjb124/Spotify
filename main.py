# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from database import  get_db
from sqlalchemy.orm import Session
from schema import User as UserSchema
from fastapi import Depends
import httpx
import os
from urllib.parse import urlencode
from database import engine, Base
from models import User  # Importar todos los modelos

# Crear todas las tablas
Base.metadata.create_all(bind=engine)
load_dotenv()
app = FastAPI()
CLIENT_ID =  os.getenv("CLIENT_ID")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# Configuración desde variables de entorno

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes (¡cambiar en producción!)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc)
    allow_headers=["*"],  # Permite todos los headers
)
# Configuración
REDIRECT_URI = "http://localhost:8000/callback"

# Almacenamiento temporal (solo para pruebas)
tokens = {}
async def find_spotify_user(token:str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        devices_url = "https://api.spotify.com/v1/me/"
        response = await client.get(devices_url, headers=headers)
        print(response.json())
        print(response.headers)
        return response.json()
    
def create_user(user:UserSchema,db:Session =Depends(get_db)):
    
    db.add(UserModel(**user.dict()))
    db.commit()
    return user

@app.get("/login")
async def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-modify-playback-state user-read-playback-state",
        "state": "1234567890"
    }
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)
@app.get("/callback")
async def callback(code: str,state:str):


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
    user = UserSchema()    
    tokens["user"]["access_token"] = response.json()["access_token"]
    create_user(UserSchema(username="user", token=response.json()["access_token"]))
    response =RedirectResponse("http://localhost:3000/")
    response.set_cookie("access_token", response.json()["access_token"])
    #return {"status": "¡Autenticación exitosa! Token almacenado en memoria."}
    return response
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
    
    