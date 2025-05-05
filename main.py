# main.py
from fastapi import FastAPI, Request, UploadFile, File, HTTPException,Header
from typing import Annotated,Generator, TypeVar, List,AsyncGenerator
from fastapi.responses import RedirectResponse,StreamingResponse,JSONResponse
from fastapi.encoders import jsonable_encoder
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
from router_api import get_data_from_image, get_data_from_image_structured_output
from spotify_api import find_spotify
from spotify_api import transform_spotify_response,spotify
# chat improts
from aiohttp import ClientSession, TCPConnector, ClientTimeout
import asyncio
import json
# # Crear todas las tablas
# Base.metadata.create_all(bind=engine)
load_dotenv()
app = FastAPI()
app.include_router(spotify)
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
GEMMA_API_KEY_MARLON_3=os.getenv("GEMMA_API_KEY_MARLON_3")
OPEN_ROUTER_API_KEYS:List= [GEMMA_API_KEY_MARLON_3]

# Construcción mejorada de REDIRECT_URI con manejo adecuado de Vercel
# vercel_url = os.getenv("VERCEL_URL")

# if vercel_url:
    # Vercel URL no incluye https://, así que debemos agregarlo
REDIRECT_URI = f"http://localhost:8000/callback"
# else:
#     # Fallback para desarrollo local
#     REDIRECT_URI = "http://localhost:8000/callback"

# Configuración mejorada de ClientSession


@app.post("/get_tracks_array_chat")
async def Images_Spotifind_chat(
    files: Annotated[List[UploadFile], File()],
    spotify_token: str = Form(None)
):
    # Configurar el pool de conexiones
    connector = TCPConnector(
        limit=100,              # Máximo 100 conexiones simultáneas en total
        limit_per_host=20,      # Máximo 20 conexiones por servicio (Spotify/Cloudinary)
        enable_cleanup_closed=True,  # Limpiar conexiones cerradas automáticamente
        force_close=False       # Reutilizar conexiones siempre que sea posible
    )
    
    # Configurar timeout global para todas las operaciones HTTP
    timeout = ClientTimeout(total=30)  # 30 segundos máximo por operación
    
    async with ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": "MySpotifyApp/1.0"}
    ) as session:
        # 1. Subir imágenes a Cloudinary en paralelo
        upload_tasks = [upload_image(file) for file in files]
        cloudinary_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        # Filtrar solo resultados exitosos
        valid_images = [
            result for result in cloudinary_results
            if not isinstance(result, Exception)
        ]
        
        # 2. Procesamiento paralelo con control de concurrencia
        semaphore = asyncio.Semaphore(10)  # Máximo 10 imágenes procesadas concurrentemente
        
        async def process_image(image_result):
            async with semaphore:  # Controlar carga de procesamiento
                try:
                    # Rotación de API keys con seguridad para hilos
                    api_key = await asyncio.to_thread(
                        next, 
                        generador_ciclico(OPEN_ROUTER_API_KEYS)
                    )
                    
                    # Obtener datos de la imagen
                    model_response = await get_data_from_image(
                        session, 
                        image_result['url'], 
                        api_key
                    )
                    
                    # Procesar contenido de IA
                    content = model_response["choices"][0]["message"]["content"]
                    if content.strip() == "Null":
                        return []
                    
                    # Extraer JSON mejorado
                    tracks_data = extract_json_from_content(content)
                    if not tracks_data:
                        return []
                    
                    # 3. Búsqueda en Spotify con rate limiting
                    spotify_sem = asyncio.Semaphore(5)  # 5 solicitudes concurrentes a Spotify
                    
                    async def process_track(track):
                        async with spotify_sem:
                            try:
                                result = await find_spotify(
                                    session, 
                                    spotify_token, 
                                    track
                                )
                                return transform_spotify_response(result).model_dump()
                            except Exception as e:
                                print(f"Error en track {track}: {str(e)}")
                                return None
                    
                    # Procesar tracks en paralelo
                    track_tasks = [process_track(track) for track in tracks_data]
                    results = await asyncio.gather(*track_tasks)
                    
                    return [r for r in results if r is not None]
                    
                except Exception as e:
                    print(f"Error procesando imagen: {str(e)}")
                    return []
        
        # 4. Generar stream de resultados
        async def generate_stream():
            processing_tasks = [
                asyncio.create_task(process_image(img)) 
                for img in valid_images
            ]
            
            # Enviar resultados tan pronto estén disponibles
            for future in asyncio.as_completed(processing_tasks):
                try:
                    tracks = await future
                    for track in tracks:
                        yield f"data: {json.dumps(track)}\n\n"
                except Exception as e:
                    print(f"Error en stream: {str(e)}")
                    continue
            
            # Fin del stream
            yield "event: end\ndata: stream-completed\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
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
    print("sadas")
    print(REDIRECT_URI)
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
async def callback(code: str):
    print("entree")
    print(code)

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
        print(response.json())
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
    spotify_token: str = Form(None)

):
    dict_file = await upload_image(file)
    
    # Crear sesión manualmente (sin async with)
    session = aiohttp.ClientSession()
    try:
        key= next(generador_ciclico(OPEN_ROUTER_API_KEYS))
        print(key)
        model_response = await get_data_from_image(
            session,
            dict_file['url'], 
            key or GEMMA_API_KEY_CESAR
        )
        
        content = model_response["choices"][0]["message"]["content"]
        json_data = content.split("```json")[1].split("```")[0].strip()
        tracks_data = json.loads(json_data)
        # null_album = [song for song in tracks_data if "null" in song["album"]]
        # assign_album =[song["album"] for song in null_album]

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
                        jsonable= jsonable_encoder(dict_object)
                        yield f"data: {json.dumps(jsonable)}\n\n"
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
    print("imagenes cantida")
    print(len(cloudinary_results))
    
    # Crear una sesión HTTP compartida
    session = aiohttp.ClientSession()
    
    async def process_image(image_result):
        """Procesa una imagen individual y devuelve sus tracks"""
        try:
            # Obtener datos de la imagen usando OpenRouter
            api_key = next(generador_ciclico(OPEN_ROUTER_API_KEYS))
            model_response = await get_data_from_image(session, image_result['url'], api_key)
            
            # Extraer el JSON de la respuesta
            content = model_response["choices"][0]["message"]["content"]
            print("content",content)
            # Si la respuesta es simplemente "Null", retornar lista vacía
            if content.strip() == "Null":
                return []
                
            # Extraer JSON con manejo de errores mejorado
            try:
                # Intentar extraer JSON usando el formato estándar
                json_parts = content.split("```json")
                if len(json_parts) > 1:
                    json_text = json_parts[1].split("```")[0].strip()
                else:
                    # Intentar extraer JSON sin el markdown
                    json_text = content.split("[")[1].rsplit("]", 1)[0]
                    json_text = "[" + json_text + "]"
                    
                # Corregir valores Null sin comillas que causan el error JSON
                json_text = json_text.replace(': Null', ': null').replace(':Null', ':null')
                print("json_text",json_text)
                
                tracks_data = json.loads(json_text)
                print("cuantas canciones responde la IA de la imagen")
                print(len(tracks_data))
                
                # Buscar cada track en Spotify concurrentemente
                spotify_tasks = [
                    find_spotify(session, spotify_token, song)
                    for song in tracks_data
                ]
                
                # Usar asyncio.gather para mejor rendimiento
                spotify_results = await asyncio.gather(*spotify_tasks)
            
                # Transformar los resultados
                return [transform_spotify_response(result).model_dump() for result in spotify_results]
                
            except (json.JSONDecodeError, IndexError) as e:
                print(f"Error procesando JSON: {e}, contenido: {content[:200]}...")
                return []
                
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            return []

    async def generate_stream():
        """Genera el stream de eventos SSE"""
        try:
            # Procesar todas las imágenes concurrentemente
            # esto es un arreglo de tamano de la cantidad de fotos con arreglosd e canciones
            processing_tasks = [process_image(result) for result in cloudinary_results]
            print(" procesadas per foto")
            print(len(processing_tasks))

            # A medida que cada imagen se procesa, enviar sus tracks
            for future in asyncio.as_completed(processing_tasks):
                print("entrando")
                print(processing_tasks[0])
                print(processing_tasks[1])
                tracks = await future
                for track in tracks:
                    yield f"data: {json.dumps(track)}\n\n"
                    
            yield "event: end\ndata: stream-completed\n\n"
            
        finally:
            await session.close()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
#
@app.post("/get_vibe_from_image")
async def process_image_route(
    file: Annotated[UploadFile, File()],
    spotify_token: str = Form(None)

):
    dict_file = await upload_image(file)
    
    # Crear sesión manualmente (sin async with)
    session = aiohttp.ClientSession()
    try:
        key= next(generador_ciclico(OPEN_ROUTER_API_KEYS))
        print(key)
        model_response = await get_data_from_image_structured_output(
            session,
            dict_file['url'], 
            key or GEMMA_API_KEY_CESAR
        )
        
        content = model_response["choices"][0]["message"]["content"]

        json_data = json.loads(content)
        # print(json_data["data"])
        
        print(json_data["info"], "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAasdasdadasdasd")
        # json_data = content.split("```json")[1].split("```")[0].strip()
        # tracks_data = json.loads(json_data)
        # null_album = [song for song in tracks_data if "null" in song["album"]]
        # assign_album =[song["album"] for song in null_album]

        async def generate_results():
            try:
                tasks = [asyncio.create_task(
                            find_spotify(session, spotify_token, track)
                        )for track in json_data["data"]]

                    
                
                
                    

                  
                # for album in json_data['albums']:
                #     tasks.append(
                #         asyncio.create_task(
                #             find_spotify(session, spotify_token, album,type="album")
                #         )
                #     )
                # for artist in json_data['artists']:
                #     tasks.append(
                #         asyncio.create_task(
                #             find_spotify(session, spotify_token, artist,type="artist")
                #         )
                #     )
                print("tasks",tasks)
                
                for future in asyncio.as_completed(tasks):
                    try:
                        result = await future
                        print("resultsssssssssssssssssssssssssssssssssssss de tareas", result)
                        jsonable= jsonable_encoder(result)
                        yield f"data: {json.dumps(jsonable)}\n\n"                        
                        # simplified = await simplify_spotify_result(result)
                        # simplified_data = transform_spotify_response(result)
                        # print(simplified_data)
                        # dict_object= simplified_data.model_dump()
                        # jsonable= jsonable_encoder(dict_object)
                        # yield f"data: {json.dumps(jsonable)}\n\n"
                    except Exception as e:
                        
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                await session.close()  # Cerrar sesión cuando termine el generador
                
            yield "event: end\ndata: stream-completed\n\n"

        return StreamingResponse(generate_results(), media_type="text/event-stream")

    except json.JSONDecodeError:
        await session.close()
        raise HTTPException(400, "Formato de respuesta inválido")
    # except Exception as e:
    #     await session.close()
    #     print(e)
    #     raise HTTPException(500, f"Error interno: {str(e)}")




@app.post("/process_images")
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

@app.get("/debug-env")
async def debug_env():
    """Endpoint para depurar variables de entorno"""
    return {
        "vercel_url_raw": os.getenv("VERCEL_URL", "No disponible"),
        "vercel_env": os.getenv("VERCEL_ENV", "No disponible"),
        "redirect_uri_final": REDIRECT_URI,
        "all_env_vars": {k: v for k, v in os.environ.items() if not k.startswith("_")}
    }