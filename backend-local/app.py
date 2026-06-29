import socket
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

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
import json
import ollama

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    from rapidocr import RapidOCR

warnings.filterwarnings('ignore')

import re

# Removed legacy Turkish character normalization functions. Ollama handles language correction natively.

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
        # Force CPU for speech-to-text to avoid CUDA conflicts with Ollama
        self.device = "cpu"
        print(f"Using device: {self.device}")

        # OCR Engine Initialization
        print("Loading RapidOCR...")
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            from rapidocr import RapidOCR
        self.ocr_reader = RapidOCR()

        # Speech to text (Whisper-base)
        print("Loading Whisper-base model...")
        try:
            self.stt = pipeline("automatic-speech-recognition", model="openai/whisper-base", device=self.device)
        except Exception as e:
            print(f"Error loading Whisper model, falling back to CPU: {e}")
            self.stt = pipeline("automatic-speech-recognition", model="openai/whisper-base", device="cpu")

        print("Models loaded successfully.")
        self.chat_history = []
        self.last_scanned_text = None

    def extract_text(self, image_bytes):
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img_np = np.array(img)
            output = self.ocr_reader(img_np)
            if output and output.txts:
                return " ".join(output.txts).strip()
            return ""
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
                
            # Force Turkish language for transcription
            result = self.stt(
                {"raw": audio_data, "sampling_rate": 16000}, 
                generate_kwargs={"language": "turkish", "task": "transcribe"},
                return_timestamps=True
            )
            return result['text'].strip()
        except Exception as e:
            return f"Transcription error: {e}"

    def analyze_safety(self, scanned_text, allergies, medications):
        print(f"\n--- [BACKEND] ANALYZE SAFETY REQUEST ---")
        print(f"Allergies input: '{allergies}'")
        print(f"Medications input: '{medications}'")
        print(f"Scanned text: '{scanned_text}'")
        print(f"----------------------------------------\n")

        if not scanned_text:
            return {"safe": True, "explanation": "Okunacak metin bulunamadı."}
            
        clean_allergies = allergies.strip() if (allergies and allergies.strip()) else ""
        clean_medications = medications.strip() if (medications and medications.strip()) else ""
        
        # Eşleşme kontrolüne gerek yok: Eğer kullanıcının hiç alerjisi ve ilacı yoksa doğrudan güvenlidir
        if not clean_allergies and not clean_medications:
            return {
                "safe": True,
                "explanation": "Sağlık profilinizde tanımlı herhangi bir aktif alerjen veya ilaç bulunmamaktadır. Bu ürünü güvenle tüketebilirsiniz."
            }
            
        system_instructions = (
            "Sen VoxMed adında profesyonel bir Alerji ve Besin Öğeleri Kontrol Asistanısın. Görevin, sana beslenecek olan ham OCR çıktısını analiz etmek, metindeki alerjenleri, kullanılan ilaçlarla etkileşimleri ve besin değerlerini kullanıcının sağlığı için doğrulamaktır.\n\n"
            "Süreci şu 5 adıma göre yürüt:\n"
            "1. OCR ve Türkçe Karakter Restorasyonu: Sana gelen metin ham bir OCR çıktısı olduğu için bozuk karakterler, eksik harfler ve bitişik kelimeler içerebilir. Öncelikle bağlama göre bu hataları zihninde düzelt (örn: 'kvam artnci' -> 'kıvam arttırıcı', 'aroma veric (ilek)' -> 'aroma verici (çilek)', 'pancar șekeri' -> 'pancar şekeri', 'ya9' -> 'yağ'). Yanıtlarında ve analizinde her zaman bu kelimelerin düzeltilmiş, temiz Türkçe hallerini kullan. Eğer diğer dillerde de içerik varsa onları da içindekiler belirlemede kullanabilirsin. Çıktı yine Türkçe şekilde olsun.\n"
            "2. Alerjen Kontrolü: Düzeltilen içerik listesini, kullanıcının aktif alerjen listesiyle karşılaştır. Net eşleşmelerin yanı sıra, bu alerjenlerin tüm türevlerini ve gizli kaynaklarını da (örn: süt yerine süt tozu, peynir altı suyu, kazein; kakao yerine kakao kitlesi, kakao yağı; gluten yerine buğday unu, nişasta) titizlikle tespit et. ÇÖK ÖNEMLİ KURAL: YALNIZCA KULLANICININ AKTİF ALERJEN LİSTESİNDE YER ALAN MADDELER (veya türevleri) ÜRÜNDE VARSA ürünü tehlikeli ('safe': false) yapmalı ve uyarmalısın. Kullanıcının aktif alerjen listesinde yer almayan diğer genel alerjenler ürünün içinde olsa dahi ürünü KULLANICI İÇİN TAMAMEN GÜVENLİ (safe: true) kabul etmelisin. Kendiliğinden genel alerji uyarıları yapıp 'tüketmeyin' uyarısı yapma. Güvenliği sadece kullanıcının listesine göre doğrula.\n"
            "3. İlaç Etkileşimi Kontrolü: Düzeltilen içerik listesini, kullanıcının aktif ilaç listesiyle karşılaştır. İçerikteki maddelerin kullanıcının kullandığı ilaçlarla (örn: Warfarin ile kızılcık/ıspanak/yeşil çay gibi yüksek K vitamini veya etkileşimli maddeler; aspirin ile alkol; kolesterol ilaçları ile greyfurt vb.) bilinen klinik etkileşimlerini denetle. Eğer bir çakışma varsa kullanıcıyı açıkça uyar ve ürünü tehlikeli ('safe': false) olarak işaretle. Çakışma yoksa veya ilaç listesi boş ise bu adımı güvenli geç.\n"
            "4. Besin Değerleri ve Matematiksel Mantık Kontrolü: OCR metni içindeki enerji, besin öğelerini ve bileşen oranlarını (yüzdelerini) ayıkla. Gıda etiketlerindeki toplam bileşen yüzdesi matematiksel olarak %100'ü geçemez. Eğer OCR çıktısında mantıksız yüzdeler (örn: '%159', '%200') veya bozuk sayılar görürsen, bunu bir OCR okuma hatası (örn: noktayı/virgülü kaçırma, %1.5 veya %15'i yanlış okuma) olduğunu fark et. Yanıtında kullanıcıya bu matematiksel mantıksızlığı/hatayı açıklayıp olası gerçek değeri şeklinde mantık yürüterek belirt.\n"
            "5. Kesinlik ve Yanıt Kuralları:\n"
            "- Son derece kesin (precise), öz, analitik ve net ol.\n"
            "- Gereksiz nezaket cümleleri veya uzatılmış paragraflar kullanma, doğrudan bulguları listele.\n"
            "- Sadece sana verilen OCR metnine sadık kal, metinde olmayan besin değerlerini veya içerikleri kendinden uydurma (halüsinasyon görme).\n"
            "- Eğer OCR metni tamamen okunamaz veya çok kopuksa, kullanıcıyı kibarca uyar.\n"
            "- Kullanıcı eğer konu dışına sapmaya başlarsa, üründen alakasız sorular sorarsa soruları cevaplama ve kullanıcıyı görevin hakkında hatırlatarak uyar.\n\n"
            "Görevin, ürünün tüketiminin kullanıcı için güvenli olup olmadığını belirlemektir. Yanıtını mutlaka aşağıdaki JSON formatında ver:\n"
            "{\n"
            "  \"safe\": true veya false (güvenliyse true, tehlikeliyse false),\n"
            "  \"explanation\": \"Neden güvenli veya tehlikeli olduğuna dair net, kısa, Türkçe bir açıklama.\"\n"
            "}\n"
            "Not: Sadece belirtilen JSON formatında yanıt ver, başka hiçbir açıklama veya metin ekleme."
        )
        
        user_allergens = clean_allergies if clean_allergies else "Hiç yok (Boş)"
        user_medications = clean_medications if clean_medications else "Hiç yok (Boş)"
        user_prompt = (
            f"Kullanıcı Alerjileri: {user_allergens}\n"
            f"Kullanıcı İlaçları: {user_medications}\n"
            f"Taranan Ürün İçeriği: {scanned_text}"
        )
        
        try:
            response = ollama.chat(
                model='gemma4:e2b',
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response['message']['content'].strip()
            
            # Strip markdown code blocks if generated
            if content.startswith("```"):
                lines = content.splitlines()
                if len(lines) > 1 and (lines[0].startswith("```json") or lines[0].startswith("```")):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
                
            print(f"\n--- [BACKEND] LLM RAW OUTPUT ---")
            print(content)
            print(f"--------------------------------\n")
            
            result = json.loads(content)
            return {
                "safe": bool(result.get("safe", True)),
                "explanation": str(result.get("explanation", ""))
            }
        except Exception as e:
            print(f"Error in analyze_safety LLM call: {e}")
            return {
                "safe": True,
                "explanation": f"Analiz sırasında bir hata oluştu: {e}"
            }

    def chat(self, user_message, scanned_text, allergies, medications):
        if not user_message: 
            return ""
            
        # Clear history if product has changed
        if self.last_scanned_text != scanned_text:
            self.chat_history = []
            self.last_scanned_text = scanned_text
            
        chat_system = (
            "Sen VoxMed adında profesyonel bir Alerji ve Besin Öğeleri Kontrol Asistanısın. Görevin, taranan ürün içeriğini analiz etmek, kullanıcının sorularını yanıtlamak ve sağlık profilini korumaktır.\n\n"
            "Süreci şu 4 adıma göre yürüt:\n"
            "1. OCR ve Türkçe Karakter Restorasyonu: Sana gelen metin ham bir OCR çıktısı olduğu için bozuk karakterler, eksik harfler ve bitişik kelimeler içerebilir. Öncelikle bağlama göre bu hataları zihninde düzelt (örn: 'kvam artnci' -> 'kıvam arttırıcı', 'aroma veric (ilek)' -> 'aroma verici (çilek)', 'pancar șekeri' -> 'pancar şekeri', 'ya9' -> 'yağ'). Yanıtlarında ve analizinde her zaman bu kelimelerin düzeltilmiş, temiz Türkçe hallerini kullan. Eğer diğer dillerde de içerik varsa onları da içindekiler belirlemede kullanabilirsin. Çıktı yine Türkçe şekilde olsun.\n"
            "2. Alerjen Kontrolü: Düzeltilen içerik listesini, kullanıcının aktif alerjen listesiyle karşılaştır. Net eşleşmelerin yanı sıra, bu alerjenlerin tüm türevlerini ve gizli kaynaklarını da (örn: süt yerine süt tozu, peynir altı suyu, kazein; kakao yerine kakao kitlesi, kakao yağı; gluten yerine buğday unu, nişasta) titizlikle tespit et ve kullanıcıyı açıkça uyar.\n"
            "3. Besin Değerleri ve Matematiksel Mantık Kontrolü: OCR metni içindeki enerji, besin öğelerini ve bileşen oranlarını (yüzdelerini) ayıkla. Gıda etiketlerindeki toplam bileşen yüzdesi matematiksel olarak %100'ü geçemez. Eğer OCR çıktısında mantıksız yüzdeler (örn: '%159', '%200') veya bozuk sayılar görürsen, bunu bir OCR okuma hatası (örn: noktayı/virgülü kaçırma, %1.5 veya %15'i yanlış okuma) olduğunu fark et. Yanıtında kullanıcıya bu matematiksel mantıksızlığı/hatayı açıkla ve olası gerçek değeri şeklinde mantık yürüterek belirt.\n"
            "4. Kesinlik ve Yanıt Kuralları:\n"
            "- Son derece kesin (precise), öz, analitik ve net ol.\n"
            "- Gereksiz nezaket cümleleri veya uzatılmış paragraflar kullanma, doğrudan bulguları listele.\n"
            "- Sadece sana verilen OCR metnine sadık kal, metinde olmayan besin değerlerini veya içerikleri kendinden uydurma (halüsinasyon görme).\n"
            "- Eğer OCR metni tamamen okunamaz veya çok kopuksa, kullanıcıyı kibarca uyar.\n"
            "- Kullanıcı eğer konu dışına sapmaya başlarsa, üründen alakasız sorular sorarsa soruları cevaplama ve kullanıcıyı görevin hakkında hatırlatarak nazikçe uyar.\n\n"
            f"Kullanıcı Alerjileri: {allergies}\n"
            f"Kullanıcı İlaçları: {medications}\n"
            f"Taranan Ürün İçeriği: {scanned_text}\n"
        )
        
        chat_flow = [
            {"role": "system", "content": chat_system}
        ]
        
        # Append past clean history
        chat_flow.extend(self.chat_history[-6:])
        
        # Append the user's message
        chat_flow.append({"role": "user", "content": user_message})
        
        try:
            response = ollama.chat(
                model='gemma4:e2b',
                messages=chat_flow
            )
            response_text = response['message']['content'].strip()
            
            # Save only the CLEAN version to chat history
            self.chat_history.append({"role": "user", "content": user_message})
            self.chat_history.append({"role": "assistant", "content": response_text})
            
            return response_text
        except Exception as e:
            print(f"Error in chat LLM call: {e}")
            return f"Sohbet sırasında bir hata oluştu: {e}"

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
    app.run(host='0.0.0.0', port=7861, debug=False)
