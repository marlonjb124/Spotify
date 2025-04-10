# main.py
from fastapi import FastAPI, Request, UploadFile, File, HTTPException,Header
from typing import Annotated
from fastapi.responses import RedirectResponse,StreamingResponse,JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import 
from database import  get_db
from sqlalchemy.orm import Session
from fastapi import Depends, Form
import json
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
from router_api import get_data_from_image
from spotify_api import find_spotify
# # Crear todas las tablas
# Base.metadata.create_all(bind=engine)
load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes (¡cambiar en producción!)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc)
    allow_headers=["*"],  # Permite todos los headers
)
CLIENT_ID =  os.getenv("CLIENT_ID")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GEMMA_API_KEY_CESAR=os.getenv("GEMMA_API_KEY_CESAR")
GEMMA_API_KEY_MARLON=os.getenv("GEMMA_API_KEY_MARLON")
REDIRECT_URI = "http://localhost:8000/callback"
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
           
# @app.post("/upload")
async def upload_image(file: Annotated[UploadFile, File()]):
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

async def image_processing_generator(images, spotify_token):
    async with aiohttp.ClientSession() as session:
        tasks = [process_image_route(session, img_data, spotify_token) 
                for img_data in images]
        
        # Procesar las tareas conforme se completan
        for future in asyncio.as_completed(tasks):
            result = await future
            yield f"data: {json.dumps(result)}\n\n"


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
    

def simplify_spotify_result(raw_result):
    try:
        item = raw_result['tracks']['items'][0] if raw_result.get('tracks', {}).get('items') else None
        if not item:
            return {'error': 'No se encontraron resultados válidos'}

        track_info = {
            'track': {
                'name': item.get('name'),
                'external_url': item.get('external_urls', {}).get('spotify'),
                'images': [img['url'] for img in item.get('album', {}).get('images', [])],
            },
            'album': {
                'name': item.get('album', {}).get('name'),
                'external_url': item.get('album', {}).get('external_urls', {}).get('spotify'),
                'images': [img['url'] for img in item.get('album', {}).get('images', [])],
            },
            'artist': {
                'name': item.get('artists', [{}])[0].get('name'),
                'external_url': item.get('artists', [{}])[0].get('external_urls', {}).get('spotify'),
                # Nota: los artistas normalmente no traen imágenes aquí
                'images': []  # Si tienes otra fuente para imágenes de artistas, se puede agregar
            }
        }

        print('track_infoooooooooooooooooooooooooooooooooooooooooooo')
        print(track_info)
        return track_info
    except Exception as e:
        return {'error': str(e)}


@app.post("/get-track-info")
async def process_image_route(
    file: Annotated[UploadFile, File()],
    spotify_token: str = Form(None),
    model_api_key: str = None
):
    dict_file = await upload_image(file)
    
    # Crear sesión manualmente (sin async with)
    session = aiohttp.ClientSession()
    try:
        model_response = await get_data_from_image(
            session,
            dict_file['url'], 
            model_api_key or GEMMA_API_KEY_MARLON
        )
        
        content = model_response["choices"][0]["message"]["content"]
        json_data = content.split("```json")[1].split("```")[0].strip()
        tracks_data = json.loads(json_data)

        async def generate_results():
            try:
                tasks = [
                    asyncio.create_task(
                         find_spotify(session, spotify_token, song)
                       
                    ) for song in tracks_data
                ]
                
                for future in asyncio.as_completed(tasks):
                    try:
                        result = await future
                        # simplified = await simplify_spotify_result(result)
                        yield f"data: {json.dumps(result)}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                await session.close()  # Cerrar sesión cuando termine el generador
                
            yield "event: end\ndata: stream-completed\n\n"

        return StreamingResponse(generate_results(), media_type="text/event-stream")

    except json.JSONDecodeError:
        await session.close()
        raise HTTPException(400, "Formato de respuesta inválido")
    except Exception as e:
        await session.close()
        raise HTTPException(500, f"Error interno: {str(e)}")
            # aqui iria la limpieza de la respeusta del modelo para pasarle como parametro a find_spotify
            # spotify_response = await find_spotify(session, spotify_token, data)
            # return spotify_response
        # 2. Procesar respuesta del AI
        # track_info = extract_track_info(ai_response)  # Implementar esta función según el formato de respuesta
        
    #     # 3. Buscar en Spotify
    #         
    
    







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
    
    