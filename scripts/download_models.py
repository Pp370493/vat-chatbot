# scripts/download_models.py
import hashlib, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models", "multilingual-e5-small-q8")
MANIFEST = os.path.join(ROOT, "data", "embeddings", "multilingual-e5-small-q8", "manifest.json")
BASE_URL = "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/"

# ชื่อไฟล์ในเครื่อง -> path ในที่เก็บต้นทาง
FILES = {
    "model_quantized.onnx": "onnx/model_quantized.onnx",
    "tokenizer.json": "tokenizer.json",
    "config.json": "config.json",
    "tokenizer_config.json": "tokenizer_config.json",
    "special_tokens_map.json": "special_tokens_map.json",
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    expected = json.load(open(MANIFEST, encoding="utf-8"))["model_files_sha256"]
    os.makedirs(MODEL_DIR, exist_ok=True)
    for local, remote in FILES.items():
        dst = os.path.join(MODEL_DIR, local)
        if os.path.exists(dst) and sha256(dst) == expected[local]:
            print("ข้าม (ถูกต้องแล้ว):", local)
            continue
        print("กำลังดาวน์โหลด:", local)
        tmp = dst + ".part"
        urllib.request.urlretrieve(BASE_URL + remote, tmp)
        got = sha256(tmp)
        if got != expected[local]:
            os.remove(tmp)
            sys.exit(f"sha256 ไม่ตรง: {local}\n  คาด {expected[local]}\n  ได้ {got}")
        os.replace(tmp, dst)
    print("เสร็จ ไฟล์อยู่ที่", MODEL_DIR)

if __name__ == "__main__":
    main()
