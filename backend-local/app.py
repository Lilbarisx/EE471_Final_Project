from flask import Flask, request, jsonify
from transformers import pipeline
import torch
import warnings
import os
import io
import base64
import threading
from io import BytesIO
from PIL import Image
import numpy as np
import easyocr

warnings.filterwarnings('ignore')

app = Flask(__name__)

# Enable CORS manually for all endpoints
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

class VoxMedEngine:
    def __init__(self):
        print("Initializing VoxMedEngine...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # OCR Engine Initialization (supports Turkish, English, Croatian/Slovenian)
        print("Loading EasyOCR Reader...")
        self.ocr_reader = easyocr.Reader(['tr', 'en', 'hr'])

        # Speech to text (Whisper-tiny)
        print("Loading Whisper-tiny model...")
        try:
            self.stt = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device=self.device)
        except Exception as e:
            print(f"Error loading Whisper model, falling back to CPU: {e}")
            self.stt = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device="cpu")

        # Text Generation (SmolLM2-360M-Instruct)
        print("Loading SmolLM2-360M-Instruct model...")
        try:
            self.llm = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-360M-Instruct", device=self.device)
        except Exception as e:
            print(f"Error loading LLM model, falling back to CPU: {e}")
            self.llm = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-360M-Instruct", device="cpu")

        print("Models loaded successfully.")
        self.chat_history = []

    def extract_text(self, image_bytes):
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img_np = np.array(img)
            result = self.ocr_reader.readtext(img_np, detail=0)
            return " ".join(result).strip()
        except Exception as e:
            return f"OCR Error: {e}"

    def transcribe(self, audio_bytes):
        import soundfile as sf
        import numpy as np
        
        try:
            import librosa
            audio_data, samplerate = sf.read(io.BytesIO(audio_bytes))
            
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            if samplerate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=samplerate, target_sr=16000)
            
            rms = np.sqrt(np.mean(audio_data**2))
            if rms < 0.01:
                return "Sessizlik algılandı. Lütfen daha sesli konuşun."
                
            # Whisper handles language detection automatically when language is omitted
            result = self.stt(
                {"raw": audio_data, "sampling_rate": 16000}, 
                return_timestamps=True
            )
            return result['text'].strip()
        except Exception as e:
            return f"Transcription error: {e}"

    def analyze_safety(self, scanned_text, allergies, medications):
        if not scanned_text:
            return {"safe": True, "explanation": "Okunacak metin bulunamadı."}
            
        system_instructions = (
            "You are VoxMed, a medical and food safety AI assistant. "
            "Analyze the product ingredients text for conflicts with the user's health profile (allergies, existing medications). "
            "Do not suggest consumption if there is any mismatch. "
            "Return your assessment strictly in the following format:\n"
            "SAFE: [YES or NO]\n"
            "WARNING: [Provide a concise, clear warning in Turkish explaining any allergen conflicts or drug interactions. If safe, write a short Turkish summary of what the product is.]"
        )
        
        user_message = (
            f"User Health Profile:\n"
            f"- Allergies: {allergies}\n"
            f"- Current Medications: {medications}\n\n"
            f"Scanned ingredients text:\n{scanned_text}"
        )
        
        conversation = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_message}
        ]
        
        prompt = self.llm.tokenizer.apply_chat_template(
            conversation, tokenize=False, add_generation_prompt=True
        )
        
        outputs = self.llm(prompt, max_new_tokens=200, do_sample=True, top_p=0.9, temperature=0.3)
        response_text = outputs[0]["generated_text"][len(prompt):].strip()
        print(f"Raw LLM Response: {response_text}")
        
        safe_status = True
        if "SAFE: NO" in response_text or "SAFE: No" in response_text or "safe: no" in response_text.lower():
            safe_status = False
            
        warning_text = ""
        if "WARNING:" in response_text:
            warning_text = response_text.split("WARNING:")[1].strip()
        else:
            warning_text = response_text.replace("SAFE: YES", "").replace("SAFE: NO", "").replace("SAFE: Yes", "").replace("SAFE: No", "").strip()
            
        return {
            "safe": safe_status,
            "explanation": warning_text
        }

    def chat(self, user_message, scanned_text, allergies, medications):
        if not user_message: 
            return ""
            
        # We inject the scan context to help the chat model answer follow-up questions
        context_message = (
            f"SYSTEM CONTEXT:\n"
            f"User Allergies: {allergies}\n"
            f"User Medications: {medications}\n"
            f"Last Scanned Product ingredients: {scanned_text}\n"
            f"Please answer the user's follow-up questions in Turkish based on this context."
        )
        
        chat_flow = [
            {"role": "system", "content": context_message}
        ]
        
        # Append message history
        self.chat_history.append({"role": "user", "content": user_message})
        
        # Keep history compact for SmolLM2 context window
        recent_history = self.chat_history[-6:]
        chat_flow.extend(recent_history)
        
        prompt = self.llm.tokenizer.apply_chat_template(
            chat_flow, tokenize=False, add_generation_prompt=True
        )
        
        outputs = self.llm(prompt, max_new_tokens=150, do_sample=True, top_p=0.9, temperature=0.7)
        response_text = outputs[0]["generated_text"][len(prompt):].strip()
        self.chat_history.append({"role": "assistant", "content": response_text})
        return response_text

# Background Initialization State
engine = None
engine_error = None
loading_status = "Not started"

def load_engine_background():
    global engine, engine_error, loading_status
    loading_status = "Loading models..."
    try:
        engine = VoxMedEngine()
        loading_status = "Ready"
    except Exception as e:
        engine_error = str(e)
        loading_status = "Failed"
        print(f"Failed to load engine background: {e}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "engine_status": loading_status,
        "engine_error": engine_error
    })

@app.route('/ocr', methods=['POST'])
def ocr_endpoint():
    global engine
    if engine is None:
        return jsonify({"error": "VoxMed ML engine is loading. Please wait."}), 503
        
    if 'image' not in request.files and 'file' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    image_file = request.files.get('image') or request.files.get('file')
    extracted_text = engine.extract_text(image_file.read())
    return jsonify({"text": extracted_text})

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    global engine
    if engine is None:
        return jsonify({"error": "VoxMed ML engine is loading. Please wait."}), 503
        
    data = request.json or {}
    scanned_text = data.get('text', '')
    allergies = data.get('allergies', '')
    medications = data.get('medications', '')
    
    result = engine.analyze_safety(scanned_text, allergies, medications)
    return jsonify(result)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    global engine
    if engine is None:
        return jsonify({"error": "VoxMed ML engine is loading. Please wait."}), 503

    data = request.json or {}
    message = data.get('message', '')
    scanned_text = data.get('text', '')
    allergies = data.get('allergies', '')
    medications = data.get('medications', '')
    
    response = engine.chat(message, scanned_text, allergies, medications)
    return jsonify({"response": response})

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    global engine
    if engine is None:
        return jsonify({"error": "VoxMed ML engine is loading. Please wait."}), 503

    if 'audio' not in request.files:
        return jsonify({"error": "No audio file found"}), 400
        
    audio_file = request.files['audio']
    text = engine.transcribe(audio_file.read())
    return jsonify({"text": text})

if __name__ == '__main__':
    # Start loading models in the background so Flask starts instantly
    threading.Thread(target=load_engine_background, daemon=True).start()
    app.run(host='0.0.0.0', port=7860, debug=False)
