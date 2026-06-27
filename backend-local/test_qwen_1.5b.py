import socket
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

import torch
import sys
from transformers import pipeline

sys.stdout.reconfigure(encoding='utf-8')

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

# Let's test Qwen2.5-1.5B-Instruct (3.1GB download, very smart)
model_name = "Qwen/Qwen2.5-1.5B-Instruct"

print(f"Loading {model_name}...")
llm = pipeline("text-generation", model=model_name, device=device)
print("Model loaded.")

# Test safety analysis
system_instructions = (
    "Sen VoxMed adında tıbbi ve gıda güvenliği yapay zeka asistanısın. "
    "Kullanıcının sağlık profilini (alerjiler, kullandığı ilaçlar) taranan ürünün içeriğiyle karşılaştır. "
    "Eğer herhangi bir çakışma varsa kesinlikle tüketilemez de. "
    "Yanıtını tam olarak şu formatta ver:\n"
    "SAFE: [YES veya NO]\n"
    "WARNING: [Eğer tüketilemez ise Türkçe kısa ve net bir uyarı yaz. Eğer güvenli ise Türkçe kısa bir içerik özeti yaz.]"
)

user_message = (
    f"Kullanıcı Sağlık Profili:\n"
    f"- Alerjiler: laktoz, fıstık\n"
    f"- İlaçlar: aspirin\n\n"
    f"Taranan Ürün İçeriği:\nSu, doğal kaynak suyu."
)

conversation = [
    {"role": "system", "content": system_instructions},
    {"role": "user", "content": user_message}
]

prompt = llm.tokenizer.apply_chat_template(
    conversation, tokenize=False, add_generation_prompt=True
)

outputs = llm(
    prompt, 
    max_new_tokens=150, 
    do_sample=True, 
    top_p=0.9, 
    temperature=0.3,
    repetition_penalty=1.1
)
print("--- SAFETY OUTPUT ---")
print(outputs[0]["generated_text"][len(prompt):].strip())
print("---------------------")

# Test chat
chat_system = (
    "Sen VoxMed adında tıbbi ve gıda güvenliği yapay zeka asistanısın. "
    "Sana kullanıcının alerjileri, ilaçları ve en son tarattığı ürünün içeriği XML etiketleri içerisinde verilecek. "
    "Kullanıcının Türkçe sorularını bu bilgilere dayanarak kısa ve net bir şekilde Türkçe cevapla. "
    "Sadece <taranan_urun_icerigi> etiketinin içindeki metinde o madde veya türevleri (örn. fıstık ezmesi, fıstıklı, yer fıstığı vb.) geçiyorsa olduğunu belirt, geçmiyorsa kesinlikle olmadığını söyle. "
    "Kullanıcı alerjileri veya ilaçları ürünün içeriğinde bulunmaz, onları karıştırma."
)

chat_user = (
    f"<kullanici_alerjileri>laktoz, fıstık</kullanici_alerjileri>\n"
    f"<kullanici_ilaclari>aspirin</kullanici_ilaclari>\n"
    f"<taranan_urun_icerigi>Su, fıstık ezmesi, doğal kaynak suyu</taranan_urun_icerigi>\n\n"
    f"Soru: bu üründe fıstık var mı?"
)

chat_conversation = [
    {"role": "system", "content": chat_system},
    {"role": "user", "content": chat_user}
]

chat_prompt = llm.tokenizer.apply_chat_template(
    chat_conversation, tokenize=False, add_generation_prompt=True
)

# Test 1: Greedy Decoding (do_sample=False)
chat_outputs_greedy = llm(
    chat_prompt,
    max_new_tokens=150,
    do_sample=False,
    repetition_penalty=1.1
)

print("--- CHAT OUTPUT (GREEDY) ---")
print(chat_outputs_greedy[0]["generated_text"][len(chat_prompt):].strip())
print("----------------------------")

# Test 2: Low Temp (do_sample=True, temp=0.1)
chat_outputs_low_temp = llm(
    chat_prompt,
    max_new_tokens=150,
    do_sample=True,
    temperature=0.1,
    repetition_penalty=1.1
)

print("--- CHAT OUTPUT (LOW TEMP 0.1) ---")
print(chat_outputs_low_temp[0]["generated_text"][len(chat_prompt):].strip())
print("----------------------------------")

