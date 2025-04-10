# main.py
from fastapi import FastAPI, Request, UploadFile, File, HTTPException,Header
from typing import Annotated,Generator, TypeVar, List,AsyncGenerator
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
from spotify_api import transform_spotify_response
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
GEMMA_API_KEY_MARLON_2=os.getenv("GEMMA_API_KEY_MARLON_2")
GEMMA_API_KEY_CESAR_2=os.getenv("GEMMA_API_KEY_CESAR_2")
OPEN_ROUTER_API_KEYS:List= [GEMMA_API_KEY_CESAR,GEMMA_API_KEY_MARLON,GEMMA_API_KEY_MARLON_2,GEMMA_API_KEY_CESAR_2]
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
T = TypeVar('T')  # Tipo genérico

def generador_ciclico(lista: List[T]) -> Generator[T, None, None]:
    """Versión tipada del generador cíclico"""
    index = 0
    while True:
        yield lista[index]
        index = (index + 1) % len(lista)
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
        key= next(generador_ciclico(OPEN_ROUTER_API_KEYS))
        model_response = await get_data_from_image(
            session,
            dict_file['url'], 
            key or GEMMA_API_KEY_CESAR
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
                        simplified_data = transform_spotify_response(result)
                        print(simplified_data)
                        dict_object= simplified_data.model_dump()
                        print(type(dict_object))
                        yield f"data: {dict_object}\n\n"
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

  
@app.post("/get_tracks_array_mine")
async def Images_Spotifind_mine(
    files: Annotated[List[UploadFile], File()],
    spotify_token: str = Form(None)
):
    # Subir todas las imágenes a Cloudinary concurrentemente
    upload_tasks = [upload_image(file) for file in files]
    cloudinary_results = await asyncio.gather(*upload_tasks)
    
    # Crear una sesión HTTP compartida
    session = aiohttp.ClientSession()
    
    async def process_image(image_result):
        """Procesa una imagen individual y devuelve sus tracks"""
        try:
            # Obtener datos de la imagen usando OpenRouter
            api_key = next(generador_ciclico(OPEN_ROUTER_API_KEYS)) or GEMMA_API_KEY_CESAR
            model_response = await get_data_from_image(session, image_result['url'], api_key)
            
            # Extraer el JSON de la respuesta
            content = model_response["choices"][0]["message"]["content"]
            json_data = content.split("```json")[1].split("```")[0].strip()
            tracks_data = json.loads(json_data)
            
            # Buscar cada track en Spotify concurrentemente
            spotify_tasks = [
                find_spotify(session, spotify_token, song)
                for song in tracks_data
            ]
            
            spotify_results = await asyncio.gather(*spotify_tasks)
  
            
            # Transformar los resultados
            return [transform_spotify_response(result).model_dump() for result in spotify_results]
            
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            return []

    async def generate_stream():
        """Genera el stream de eventos SSE"""
        try:
            # Procesar todas las imágenes concurrentemente
            processing_tasks = [process_image(result) for result in cloudinary_results]
            
            # A medida que cada imagen se procesa, enviar sus tracks
            for future in asyncio.as_completed(processing_tasks):
                tracks = await future
                for track in tracks:
                    yield f"data: {json.dumps(track)}\n\n"
                    
            yield "event: end\ndata: stream-completed\n\n"
            
        finally:
            await session.close()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
# @app.post("/get_tracks_array")
# async def Images_Spotifind(
#     files: Annotated[List[UploadFile], File()],
#     spotify_token: str = Form(None)
# ):
#     # 1. Subir imágenes a Cloudinary
#     upload_tasks = [upload_image(file) for file in files]
#     cloudinary_results = await asyncio.gather(*upload_tasks)
    
#     # 2. Procesamiento concurrente
#     api_key_generator = generador_ciclico(OPEN_ROUTER_API_KEYS + [GEMMA_API_KEY_CESAR])
    
#     async with aiohttp.ClientSession() as session:
#         # 3. Crear tareas como corrutinas (no generadores)
#         processing_coros = [
#             process_single_image_tracks(
#                 session=session,
#                 image_url=result['url'],
#                 model_api_key=next(api_key_generator),
#                 spotify_token=spotify_token
#             ).__anext__()  # Convertimos el generador en corrutina
#             for result in cloudinary_results
#         ]
        
#         # 4. Crear tareas asyncio
#         processing_tasks = [asyncio.create_task(coro) for coro in processing_coros]
        
#         # 5. Generador de resultados
#         async def result_generator():
#             try:
#                 for future in asyncio.as_completed(processing_tasks):
#                     try:
#                         track_gen = await future
#                         async for track in track_gen:
#                             yield track
#                     except Exception as e:
#                         yield f"data: {json.dumps({'error': str(e)})}\n\n"
#             finally:
#                 yield "event: end\ndata: stream-completed\n\n"
        
#         return StreamingResponse(result_generator(), media_type="text/event-stream")

# async def process_single_image_tracks(
#     session: aiohttp.ClientSession,
#     image_url: str,
#     model_api_key: str,
#     spotify_token: str
# ) -> AsyncGenerator[str, None]:
#     """Versión modificada para trabajar con as_completed"""
#     try:
#         # 1. Obtener datos del modelo AI
#         model_response = await get_data_from_image(
#             session,
#             image_url,
#             model_api_key
#         )
        
#         # 2. Parsear respuesta
#         content = model_response["choices"][0]["message"]["content"]
#         json_data = content.split("```json")[1].split("```")[0].strip()
#         tracks_data = json.loads(json_data)
        
#         # 3. Buscar tracks en Spotify concurrentemente
#         spotify_tasks = [
#             asyncio.create_task(find_spotify(session, spotify_token, song))
#             for song in tracks_data
#         ]
        
#         # 4. Retornar generador de resultados
#         for future in asyncio.as_completed(spotify_tasks):
#             try:
#                 result = await future
#                 simplified = transform_spotify_response(result)
#                 yield f"data: {simplified.model_dump()}\n\n"
#             except Exception as e:
#                 yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
#     except Exception as e:
#         yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
#         # 2. Parsear respuesta
#         content = model_response["choices"][0]["message"]["content"]
#         json_data = content.split("```json")[1].split("```")[0].strip()
#         tracks_data = json.loads(json_data)
        
#         # 3. Buscar tracks en Spotify concurrentemente
#         spotify_tasks = [
#             asyncio.create_task(find_spotify(session, spotify_token, song))
#             for song in tracks_data
#         ]
        
#         # 4. Retornar generador de resultados
#         for future in asyncio.as_completed(spotify_tasks):
#             try:
#                 result = await future
#                 simplified = transform_spotify_response(result)
#                 yield f"data: {simplified.model_dump()}\n\n"
#             except Exception as e:
#                 yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
#     except Exception as e:
#         yield f"data: {json.dumps({'error': str(e)})}\n\n"






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
    
    