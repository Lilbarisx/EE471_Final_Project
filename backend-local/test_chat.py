import torch
import sys
from transformers import pipeline

sys.stdout.reconfigure(encoding='utf-8')

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

print("Loading model...")
llm = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-360M-Instruct", device=device)
print("Model loaded.")

allergies = "laktoz, fıstık"
medications = "aspirin"
scanned_text = "Su, doğal kaynak suyu"
user_message = "bu üründe fıstık var mı?"

system_instructions = (
    "Sen VoxMed adında tıbbi ve gıda güvenliği yapay zeka asistanısın. "
    "Kullanıcının alerjileri, ilaçları ve son tarattığı ürün bilgisi aşağıdadır. "
    "Kullanıcının Türkçe sorularını bu bilgilere dayanarak kısa ve net bir şekilde Türkçe cevapla. "
    "Asla kullanıcının sorusunu tekrar etme."
)

user_context = (
    f"Kullanıcı Alerjileri: {allergies}\n"
    f"Kullanıcı İlaçları: {medications}\n"
    f"Son Taranan Ürün İçeriği: {scanned_text}\n\n"
    f"Soru: {user_message}"
)

chat_flow = [
    {"role": "system", "content": system_instructions},
    {"role": "user", "content": user_context}
]

prompt = llm.tokenizer.apply_chat_template(
    chat_flow, tokenize=False, add_generation_prompt=True
)

outputs = llm(
    prompt, 
    max_new_tokens=150, 
    do_sample=True, 
    top_p=0.9, 
    temperature=0.3, # lower temperature for less hallucination
    repetition_penalty=1.2 # prevent loops
)
print("--- RAW GENERATED ---")
print(outputs[0]["generated_text"])
print("---------------------")
print("--- SLICED ---")
print(outputs[0]["generated_text"][len(prompt):].strip())
print("--------------")
