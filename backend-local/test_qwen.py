import torch
import sys
from transformers import pipeline

sys.stdout.reconfigure(encoding='utf-8')

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

# Let's test Qwen2.5-0.5B-Instruct first (extremely lightweight, ~950MB download)
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

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
    "Kullanıcının alerjileri, ilaçları ve son tarattığı ürün bilgisi aşağıdadır. "
    "Kullanıcının Türkçe sorularını bu bilgilere dayanarak kısa ve net bir şekilde Türkçe cevapla. "
    "Asla kullanıcının sorusunu veya istemi tekrar etme."
)

chat_user = (
    f"Kullanıcı Alerjileri: {allergies}\n"
    f"Kullanıcı İlaçları: {medications}\n"
    f"Son Taranan Ürün İçeriği: {scanned_text}\n\n"
    f"Soru: bu üründe fıstık var mı?"
) if 'allergies' in globals() else (
    f"Kullanıcı Alerjileri: laktoz, fıstık\n"
    f"Kullanıcı İlaçları: aspirin\n"
    f"Son Taranan Ürün İçeriği: Su, doğal kaynak suyu\n\n"
    f"Soru: bu üründe fıstık var mı?"
)

chat_conversation = [
    {"role": "system", "content": chat_system},
    {"role": "user", "content": chat_user}
]

chat_prompt = llm.tokenizer.apply_chat_template(
    chat_conversation, tokenize=False, add_generation_prompt=True
)

chat_outputs = llm(
    chat_prompt,
    max_new_tokens=150,
    do_sample=True,
    top_p=0.9,
    temperature=0.4,
    repetition_penalty=1.1
)

print("--- CHAT OUTPUT ---")
print(chat_outputs[0]["generated_text"][len(chat_prompt):].strip())
print("-------------------")
