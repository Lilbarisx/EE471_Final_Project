import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    from rapidocr import RapidOCR
import ollama

# 1. DOSYA KONTROLÜ VE OCR AŞAMASI
image_path = r"C:\Users\brstp\Desktop\EE471\Final_Project\backend-local\images\golfkeci.jpg"

if not os.path.exists(image_path):
    print(f"Hata: '{image_path}' konumunda görsel bulunamadı! Lütfen yolu kontrol et.")
    exit()

print("Görsel taranıyor (RapidOCR)...")
engine = RapidOCR()
output = engine(image_path)

if output and output.txts:
    icindekiler_metni = " ".join(output.txts).strip()
else:
    icindekiler_metni = ""

print("\n--- Ayıklanan Etiket Metni ---")
print(icindekiler_metni)
print("------------------------------\n")

# 2. CHATBOX VE BELLEK (MEMORY) KURULUMU
user_allergens = ["süt", "kakao", "gluten", "brokoli"]

system_prompt = f"""
Sen bir Alerji ve Besin Öğeleri Kontrol Asistanısın. Görevin, sana beslenecek olan ham OCR (Optik Karakter Tanıma) çıktısını analiz etmek, metindeki alerjenleri ve besin değerlerini kullanıcının sağlığı için doğrulamaktır.

Süreci şu 4 adıma göre yürüt:

1. OCR ve Türkçe Karakter Restorasyonu: Sana gelen metin ham bir OCR çıktısı olduğu için bozuk karakterler, eksik harfler ve bitişik kelimeler içerebilir. Öncelikle bağlama göre bu hataları zihninde düzelt (örn: 'kvam artnci' -> 'kıvam arttırıcı', 'aroma veric (ilek)' -> 'aroma verici (çilek)', 'pancar șekeri' -> 'pancar şekeri', 'ya9' -> 'yağ'). Yanıtlarında ve analizinde her zaman bu kelimelerin düzeltilmiş, temiz Türkçe hallerini kullan.

2. Alerjen Kontrolü: Düzeltilen içerik listesini, kullanıcının aktif alerjen listesiyle ({', '.join(user_allergens)}) karşılaştır. Net eşleşmelerin yanı sıra, bu alerjenlerin tüm türevlerini ve gizli kaynaklarını da (örn: süt yerine süt tozu, peynir altı suyu, kazein; kakao yerine kakao kitlesi, kakao yağı; gluten yerine buğday unu, nişasta) titizlikle tespit et ve kullanıcıyı açıkça uyar.

3. Besin Değerleri ve Matematiksel Mantık Kontrolü: OCR metni içindeki enerji, besin öğelerini ve bileşen oranlarını (yüzdelerini) ayıkla. Gıda etiketlerindeki toplam bileşen yüzdesi matematiksel olarak %100'ü geçemez. Eğer OCR çıktısında mantıksız yüzdeler (örn: '%159', '%200') veya bozuk sayılar görürsen, bunu körü körüne kabullenme. Bunun bir OCR okuma hatası (örn: noktayı/virgülü kaçırma, %1.5 veya %15'i yanlış okuma) olduğunu fark et. Yanıtında kullanıcıya bu matematiksel mantıksızlığı/hatayı açıkla ve olası gerçek değeri (örn: 'Metinde %159 görünse de bu muhtemelen bir OCR hatasıdır ve aslı %15 veya %1.5 olabilir') şeklinde mantık yürüterek belirt.

4. Kesinlik ve Yanıt Kuralları:
- Son derece kesin (precise), öz, analitik ve net ol.
- Gereksiz nezaket cümleleri veya uzatılmış paragraflar kullanma, doğrudan bulguları listele.
- Sadece sana verilen OCR metnine sadık kal, metinde olmayan besin değerlerini veya içerikleri kendinden uydurma (halüsinasyon görme).
- Eğer OCR metni tamamen okunamaz veya çok kopuksa, kullanıcıyı kibarca uyar.
"""

# Sohbet geçmişini tutacağımız hafıza listesi
messages = [
    {'role': 'system', 'content': system_prompt}
]

# İlk analizi tetiklemek için otomatik ilk promptu gönderiyoruz
ilk_istek = f"Ürün İçindekiler Kısmı: {icindekiler_metni}\n\nBu üründe alerjenlerim var mı? Genel bir analiz yap."
messages.append({'role': 'user', 'content': ilk_istek})

print("Asistan analiz ediyor...")
response = ollama.chat(model='gemma4:e2b', messages=messages)
asistan_cevabi = response['message']['content']

print(f"\n[Asistan]: {asistan_cevabi}\n")
messages.append({'role': 'assistant', 'content': asistan_cevabi})

# 3. KESİNTİSİZ SOHBET DÖNGÜSÜ (CHATBOX)
print("="*50)
print("Ürün hakkında chatbox açıldı. Sorularını sorabilirsin (Çıkış için 'exit' yaz).")
print("="*50)

while True:
    user_input = input("\nSiz >>> ")
    
    if user_input.lower() in ['exit', 'quit', 'çıkış']:
        print("Sohbet sonlandırıldı.")
        break
        
    if not user_input.strip():
        continue
        
    # Kullanıcının sorusunu geçmişe ekle
    messages.append({'role': 'user', 'content': user_input})
    
    # Modeli GPU'da tetikle
    response = ollama.chat(model='gemma4:e2b', messages=messages)
    asistan_cevabi = response['message']['content']
    
    # Asistanın cevabını ekrana bas ve hafızaya kaydet
    print(f"\n[Asistan]: {asistan_cevabi}")
    messages.append({'role': 'assistant', 'content': asistan_cevabi})