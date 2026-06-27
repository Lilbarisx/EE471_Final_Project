import torch
import sys
from transformers import pipeline

# Set standard output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

print("Loading model...")
llm = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-360M-Instruct", device=device)
print("Model loaded.")

# Let's test the safety analysis
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
    f"- Allergies: laktoz, fıstık\n"
    f"- Current Medications: aspirin\n\n"
    f"Scanned ingredients text:\nSu, doğal kaynak suyu."
)

conversation = [
    {"role": "system", "content": system_instructions},
    {"role": "user", "content": user_message}
]

prompt = llm.tokenizer.apply_chat_template(
    conversation, tokenize=False, add_generation_prompt=True
)

outputs = llm(prompt, max_new_tokens=200, do_sample=True, top_p=0.9, temperature=0.3)
print("--- RAW OUTPUT ---")
print(outputs[0]["generated_text"])
print("------------------")

print("--- SLICED OUTPUT ---")
print(outputs[0]["generated_text"][len(prompt):].strip())
print("---------------------")
