import os
from TTS.api import TTS
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeVideoClip
from openai import OpenAI
import requests
import json
import re

from moviepy.config import change_settings

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})


OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


COMFYUI_OUTPUT = r"C:\Users\alexc\Documents\ComfyUI\output"
PREFIX = "python_development"

def clean_old_images():
    """Elimina imágenes anteriores con el prefijo definido."""
    for f in os.listdir(COMFYUI_OUTPUT):
        if f.startswith(PREFIX) and f.endswith(".png"):
            os.remove(os.path.join(COMFYUI_OUTPUT, f))
    print(f"🧹 Imágenes antiguas con prefijo '{PREFIX}' eliminadas.")

def generate_image_with_comfy(prompt: str, workflow_path="workflows\Image Generation (Default).json"):
    url = "http://127.0.0.1:8000/prompt"

    # Cargar workflow
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # Cambiar el prompt en el nodo CLIPTextEncode
    workflow["6"]["inputs"]["text"] = prompt


    # Enviar a ComfyUI
    resp = requests.post(url, json={"prompt": workflow})
    print("Mensaje enviado a ComfyUI: ", resp)

    resp_json = resp.json()
    print("ComfyUI response:", resp.json())

    # La imagen se guarda en ComfyUI/output/
    return resp_json["prompt_id"]


def get_images_for_prompt(images_folder, prompt_id):
    """
    Devuelve la lista de imágenes generadas para un prompt_id concreto.
    """
    images = sorted([
        os.path.join(images_folder, f)
        for f in os.listdir(images_folder)
        if f.endswith(".png") and prompt_id in f
    ])
    return images

import time, glob

def wait_for_new_images(expected=1, timeout=5):
    """Espera hasta que aparezcan las imágenes nuevas generadas con el prefijo."""
    start = time.time()
    while time.time() - start < timeout:
        new_imgs = [os.path.join(COMFYUI_OUTPUT, f) 
                    for f in os.listdir(COMFYUI_OUTPUT) 
                    if f.startswith(PREFIX) and f.endswith(".png")]
        if len(new_imgs) >= expected:
            return sorted(new_imgs)
        time.sleep(1)
    raise TimeoutError("⏳ No se generaron las imágenes a tiempo.")


def generate_script():
    # LM Studio corre un servidor local compatible con OpenAI
    client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not-needed")

    prompt = """
    Genera un guion breve (menos de 80 palabras) para un TikTok de 15 segundos.
    Debe:
    1. Empezar con un gancho que atrape la atención.
    2. Contar una curiosidad histórica interesante.
    3. Ser en español, estilo cercano y dinámico.
    No debe:
    1. Añadir exclamaciones ni emojis.
    2. Simplemente listar hechos; debe contar una historia.
    3. Solo el guion, sin instrucciones de producción.

    Devuélvelo **estrictamente en formato JSON**, con la clave "script". Ejemplo:
    {
        "script": "Aquí va el guion de la historia..."
    }
    No añadas nada más fuera del JSON.
    """


    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",  # o el modelo que tengas cargado en LM Studio
        messages=[
            {"role": "system", "content": "Eres un experto en historia y creación de guiones virales para TikTok."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=540
    )

    raw_text = response.choices[0].message.content.strip()

    data = extract_json_from_text(raw_text)

    if data and "script" in data:
        historia = data["script"]
    else:
        historia = raw_text.strip()  # fallback
    
    return historia

def extract_json_from_text(text):
    """
    Busca un diccionario JSON dentro de un texto y lo devuelve como dict.
    """
    # Buscar desde la primera '{' hasta el último '}'
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            print("❌ Error al parsear JSON, devolviendo None")
            return None
    else:
        print("❌ No se encontró JSON en el texto")
        return None

def generate_image_prompt_from_script(script):
    # LM Studio corre un servidor local compatible con OpenAI
    client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not-needed")

    prompt = f"""
    Toma el siguiente guion de historia breve y genera un prompt conciso
    para crear una sola imagen que ilustre la escena principal:

    "{script}"

    El prompt debe:
    1. Describir claramente los personajes, objetos y el escenario.
    2. Especificar época histórica o contexto temporal si aplica.
    3. Incluir estilo artístico y composición: por ejemplo, 'photorealistic', 'cinematic lighting', 'ultra detailed', '8k', 'digital painting'.
    4. Usar iluminación coherente, sombras y colores realistas.
    5. Ser en inglés para mejor compatibilidad con Absolute Reality v18.1.
    6. No incluir texto literal del guion ni instrucciones de producción.
    7. Ser breve, máximo 30 palabras.

    Devuélvelo estrictamente en formato JSON, con la clave "prompt", ejemplo:
    {{
        "prompt": "Aquí va el prompt optimizado para la imagen..."
    }}
    No añadas nada más fuera del JSON.
    """


    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",  # o el modelo que tengas cargado en LM Studio
        messages=[
            {"role": "system", "content": "Eres un experto en generación de prompts para imágenes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=560
    )

    raw_text = response.choices[0].message.content.strip()
    print("Raw prompt response:", raw_text)
    data = extract_json_from_text(raw_text)

    if data and "prompt" in data:
        prompt_imagen = data["prompt"]
    else:
        prompt_imagen = raw_text.strip()  # fallback
    
    return prompt_imagen



def text_to_speech(text, audio_path):
    # Usamos un modelo en español de Coqui TTS
    tts = TTS("tts_models/es/css10/vits",gpu=True)  # corre en tu 3090
    tts.tts_to_file(text=text, file_path=audio_path, )
    return audio_path


from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, vfx

def make_video(image_paths, audio_path, output_path, crossfade_duration=0.5):
    """
    Crea un video a partir de N imágenes con transiciones sencillas y audio.

    image_paths: lista de rutas de imágenes
    audio_path: ruta al archivo de audio
    output_path: ruta del video final
    video_duration: duración total del video en segundos
    crossfade_duration: duración del fundido cruzado entre imágenes
    zoom_factor: factor de zoom ligero (Ken Burns)
    """
    num_images = len(image_paths)
    if num_images == 0:
        raise ValueError("No hay imágenes para generar el video.")

    # Cargar audio
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # Duración proporcional de cada imagen
    img_duration = audio_duration / num_images

    # Crear clips
    clips = [ImageClip(img).set_duration(img_duration) for img in image_paths]

    # Aplicar crossfade automático
    for i in range(1, len(clips)):
        clips[i] = clips[i].crossfadein(crossfade_duration)

    # Concatenar clips
    final_clip = concatenate_videoclips(clips, method="compose", padding=-crossfade_duration)

    # Añadir audio
    audio = AudioFileClip(audio_path)
    final_clip = final_clip.set_audio(audio).set_duration(audio_duration)

    # Guardar video
    final_clip.write_videofile(output_path, fps=24)

    return output_path

from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip
import math

def make_video_with_subs(image_paths, audio_path, output_path, subtitles_text, crossfade_duration=0.5):
    """
    Crea un video con imágenes, audio y subtítulos estilo TikTok.
    
    image_paths: lista de imágenes
    audio_path: archivo de audio
    output_path: salida del video
    subtitles_text: string largo con el guion a mostrar
    """
    if not image_paths:
        raise ValueError("No hay imágenes para generar el video.")

    # Cargar audio
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # Dividir subtítulos en frases
    phrases = subtitles_text.split(". ")
    num_phrases = len(phrases)

    # Duración de cada frase
    phrase_duration = audio_duration / num_phrases

    # Crear clips de imágenes
    img_duration = audio_duration / len(image_paths)
    clips = [ImageClip(img).set_duration(img_duration) for img in image_paths]

    # Crossfade simple
    for i in range(1, len(clips)):
        clips[i] = clips[i].crossfadein(crossfade_duration)

    video = concatenate_videoclips(clips, method="compose", padding=-crossfade_duration)

    # Subtítulos
    subtitle_clips = []
    for i, phrase in enumerate(phrases):
        txt = TextClip(
            phrase,
            fontsize=60,
            font="Arial-Bold",
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(video.w - 100, None),  # ancho con márgenes
        )
        txt = txt.set_position(("center", "bottom")).set_duration(phrase_duration).set_start(i * phrase_duration)
        subtitle_clips.append(txt)

    # Combinar video + subtítulos
    final = CompositeVideoClip([video] + subtitle_clips)
    final = final.set_audio(audio).set_duration(audio_duration)

    # Guardar
        # Save video with explicit codec settings
    final.write_videofile(
        output_path,
        fps=24,
        codec='libx264',  # Explicitly set video codec
        audio_codec='aac',  # Explicitly set audio codec
        preset='medium',   # Encoding preset (options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        bitrate='2000k'    # Video bitrate
    )

    return output_path

import subprocess
def merge_video_audio(video_path: str, audio_path: str, output_path: str = None) -> str:
    """
    Une un video mp4 con un archivo de audio wav y genera un nuevo mp4 con audio embebido.

    Args:
        video_path (str): Ruta del archivo mp4.
        audio_path (str): Ruta del archivo wav.
        output_path (str, optional): Ruta del archivo de salida. Si no se proporciona, 
                                     genera "video_con_audio.mp4" en la misma carpeta.

    Returns:
        str: Ruta del archivo generado.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"No se encontró el audio: {audio_path}")

    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_con_audio.mp4"

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",   # Mantener video
        "-c:a", "aac",    # Convertir audio a AAC
        "-strict", "experimental",
        output_path
    ]

    subprocess.run(cmd, check=True)
    return output_path



if __name__ == "__main__":
    print("🤖 Generando guion...")
    script = generate_script()
    print(f"📝 Guion generado: {script}")

    audio_file = os.path.join(OUTPUT_DIR, "audio.wav")
    video_file = os.path.join(OUTPUT_DIR, "video.mp4")

    clean_old_images()

    print("🎬 Generando audio...")
    text_to_speech(script, audio_file)

    print("Generando prompt para imagen...")
    prompt = generate_image_prompt_from_script(script)
    print(f"🖼️ Prompt para imagen: {prompt}")
    print("🎥 Creando video...")
    prompt_id = generate_image_with_comfy(prompt)

    images = wait_for_new_images(expected=3)  # espera 3 imágenes nuevas

    final_video = make_video_with_subs(images, audio_file, video_file, script)

    output_file = merge_video_audio("outputs/video.mp4", "outputs/audio.wav")


    print(f"✅ Video generado: {output_file}")
