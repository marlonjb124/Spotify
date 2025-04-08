# main.py
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from typing import Annotated
from fastapi.responses import RedirectResponse,StreamingResponse,JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import 
from database import  get_db
from sqlalchemy.orm import Session
from schema import User as UserSchema
from fastapi import Depends
import httpx
import asyncio
import os
import aiohttp
import logging
import cloudinary
import cloudinary.uploader
from urllib.parse import urlencode
from database import engine, Base
from models import User as UserModel  # Importar todos los modelos

# # Crear todas las tablas
# Base.metadata.create_all(bind=engine)
load_dotenv()
app = FastAPI()
CLIENT_ID =  os.getenv("CLIENT_ID")
SPOTIFY_API_URL = "https://api.spotify.com/v1/search"
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GEMMA_API_KEY_CESAR=os.getenv("GEMMA_API_KEY_CESAR")
GEMMA_API_KEY_MARLON=os.getenv("GEMMA_API_KEY_MARLON")
# Configuración desde variables de entorno
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024 
def allowed_file(filename: str) -> bool:
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
@app.post("/upload")
async def process_image_route_upload(file: Annotated[UploadFile, File()]):
    # Validar archivo
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Formatos válidos: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    try:
        # Leer contenido del archivo
        file_content = await file.read()
        
        # Subir a Cloudinary
        upload_result = cloudinary.uploader.upload(
            file_content,
            folder="my-app",  # Opcional: organizar en carpetas
            resource_type="auto",  # Detecta automáticamente si es imagen/video
            unique_filename=True,  # Genera nombre único
            overwrite=False  # No sobrescribir archivos existentes
        )

        return             {
                "public_id": upload_result["public_id"],
                "url": upload_result["secure_url"],
                "format": upload_result["format"],
                "width": upload_result["width"],
                "height": upload_result["height"]
            }



        
    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo a Cloudinary: {str(e)}"
        )
    finally:
        await file.close()

# Crear directorio si no existe
# os.makedirs(PUBLIC_DIR, exist_ok=True)
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
async def process_image(session, image_url,key, spotify_token):
    try:
        # 1. Enviar imagen al modelo AI
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
              headers={
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json" # Optional. Site URL for rankings on openrouter.ai # Optional. Site title for rankings on openrouter.ai.
  },
            json={
    "model": "google/gemma-3-27b-it:free",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Necesito que me devuelvas una estructura json siempre igual que: {\"track\": \"track_name\", \"artist\": \"artist_name\"}"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": f"public/{image_url}"
            }
          }
        ]
      }
    ],
    
  }
        ) as response:
            ai_response = await response.json()
            if response.status != 200:
                raise Exception(f"Error en modelo {model_name}: {ai_response}")
        print(ai_response)
        # 2. Procesar respuesta del AI
        # track_info = extract_track_info(ai_response)  # Implementar esta función según el formato de respuesta
        
        # 3. Buscar en Spotify
        async with session.get(
            SPOTIFY_API_URL,
            headers={"Authorization": f"Bearer {spotify_token}"},
            params={
                "q": f"{ai_response['track']} {ai_response['artist']}",
                "type": "track",
                "limit": 1
            }
        ) as spotify_response:
            spotify_data = await spotify_response.json()
            if spotify_response.status != 200:
                raise Exception(f"Error en Spotify: {spotify_data}")
            
            # return format_response(spotify_data)  
            # Formatear según necesidades
            return spotify_data

    except Exception as e:
        logging.error(f"Error procesando imagen: {str(e)}")
        return {"error": str(e)}

async def image_processing_generator(images, spotify_token):
    async with aiohttp.ClientSession() as session:
        tasks = [process_image(session, img_data, spotify_token) 
                for img_data in images]
        
        # Procesar las tareas conforme se completan
        for future in asyncio.as_completed(tasks):
            result = await future
            yield f"data: {json.dumps(result)}\n\n"
async def find_spotify_user(token:str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        devices_url = "https://api.spotify.com/v1/me/"
        response = await client.get(devices_url, headers=headers)
        print(response.json())
        print(response.headers)
        return response.json()
    
def create_user(user:UserSchema,db:Session):
    
    db.add(UserModel(**user.model_dump()))
    db.commit()
    return user

@app.get("/login")
async def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-modify-playback-state user-read-playback-state"
        # "state": "1234567890"
    }
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)
@app.get("/callback")
async def callback(code: str,db:Session =Depends(get_db)):
    print("entree")

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
    return response.json()["access_token"]
    # user = UserSchema(username="user", token=response.json()["access_token"])
    # # tokens["user"]["access_token"] = response.json()["access_token"]
    # db_user=create_user(user,db)
    # print(db_user)
    # return db_user
    # response =RedirectResponse("http://localhost:3000/")
    # response.set_cookie("access_token", response.json()["access_token"])
    #return {"status": "¡Autenticación exitosa! Token almacenado en memoria."}
    # return response
    


    
@app.post("/get-track-info")
async def process_image_route(file: Annotated[UploadFile, File()]):
    dict_file = await process_image_route_upload(file)
    
    try:
        async with aiohttp.ClientSession() as session:
        # 1. Enviar imagen al modelo AI
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
        "Authorization": f"Bearer {GEMMA_API_KEY_MARLON}",
        "Content-Type": "application/json"
    },
                json={
        "model": "google/gemma-3-27b-it:free",
        "messages": [
        {
            "role": "user",
            "content": [
            {
                "type": "text",
                "text": "Necesito que me extraigas de la imagen los artistas,album,canciones y me lo devuelvas en una estructura json siempre igual que: {\"track\": \"track_name\", \"artist\": \"artist_name\", \"album\": \"album_name\}"
            },
            {
                "type": "image_url",
                "image_url": {
                "url": f"{dict_file['url']}"
                }
            }
            ]
        }
        ],
    
  }
        ) as response:
                ai_response = await response.json()
                if response.status != 200:
                    raise Exception(f"Error en modelo {model_name}: {ai_response}")
                print(ai_response)
                return ai_response
        # 2. Procesar respuesta del AI
        # track_info = extract_track_info(ai_response)  # Implementar esta función según el formato de respuesta
        
    #     # 3. Buscar en Spotify
    #         async with session.get(
    #             SPOTIFY_API_URL,
    #             headers={"Authorization": f"Bearer {spotify_token}"},
    #             params={
    #                 "q": f"{ai_response['track']} {ai_response['artist']}",
    #                 "type": "track",
    #                 "limit": 1
    #             }
    #         ) as spotify_response:
    #             spotify_data = await spotify_response.json()
    #             if spotify_response.status != 200:
    #                 raise Exception(f"Error en Spotify: {spotify_data}")
                
    #             # return format_response(spotify_data)  
    #             # Formatear según necesidades
    #             return spotify_data

    except Exception as e:
        logging.error(f"Error procesando imagen: {str(e)}")
        return {"error": str(e)} 
@app.put("/stop")
async def stop_song():
    # if not tokens.get("access_token"):
    #     raise HTTPException(status_code=401, detail="No autenticado. Ve a /login primero.")
    
    # headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
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
async def play_song(track_name: str,artist:str,):
    # if not tokens.get("access_token"):
    #     raise HTTPException(status_code=401, detail="No autenticado. Ve a /login primero.")
    
    headers = {"Authorization": "Bearer BQDGQVwuh5AaHl-zsn4k32Bj1noD6p65XFPriSrvK-f2OopBxcC5LzqXT3Wb9GcUTbmoWoQ9T6yHV2uG09pr1ldXvSmyWqif-4XTlao0knrZSxnAXAE2_Ub4k9dlFPYsxVroNEO7nKyg15UdADzgCYaSXVTBN2XdCC5ay_XvHQtp0d0vdnkLexZeuPsTp5dz1yJ8AqbYmJP2r2QXAiO79Zqhd-JWUMytKXC29libvzJK_9xr9Hc"}
    
    # Buscar la canción
    async with httpx.AsyncClient() as client:
        search_url = "https://api.spotify.com/v1/search"
        params = {"q": track_name +" "+ artist, "type": "track", "limit": 1}
        response = await client.get(search_url, headers=headers, params=params)
        print(response.json())
    if not response.json().get("tracks", {}).get("items"):
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    track_uri = response.json()["tracks"]["items"][0]["uri"]
    
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
    play_url = f"https://api.spotify.com/v1/me/player/play"
    data = {"uris": [track_uri],"position_ms":100
}
    
    async with httpx.AsyncClient() as client:
        response = await client.put(play_url, headers=headers, json=data)

    
    if response.status_code != 204:
        raise HTTPException(status_code=400, detail="Error al reproducir. ¿El dispositivo está activo?")
    
    return {"status": "¡Reproduciendo!", "track_uri": track_uri}






@app.post("/process-images")
async def process_images(images: list, spotify_token: str):
    """
    Endpoint principal que recibe:
    - images: Lista de diccionarios con {image_data: str, model: str}
    - spotify_token: Token de acceso para Spotify API
    """
    return StreamingResponse(
        image_processing_generator(images, spotify_token),
        media_type="text/event-stream"
    )

# def extract_track_info(ai_response):
#     # Implementar lógica específica para extraer información de cada modelo
#     # Ejemplo genérico:
#     return {
#         "title": ai_response.get("track"),
#         "artist": ai_response.get("artist")
#     }

def format_response(spotify_data):
    # Formatear la respuesta de Spotify
    if not spotify_data['tracks']['items']:
        return {"status": "No encontrado en Spotify"}
    
    track = spotify_data['tracks']['items'][0]
    return {
        "name": track['name'],
        "artist": track['artists'][0]['name'],
        "url": track['external_urls']['spotify'],
        "preview_url": track['preview_url']
    }
@app.get("/home")
async def home():
    return{"hi":"sda"}
    
    