import torch
import easyocr
import transformers
print("====================================")
print("Torch version:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA Device Name:", torch.cuda.get_device_name(0))
print("EasyOCR loaded successfully!")
print("Transformers loaded successfully!")
print("====================================")
