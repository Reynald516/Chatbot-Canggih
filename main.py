from fastapi import FastAPI, Request
import json
import requests
import os
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Bot, Update
from fastapi.responses import PlainTextResponse

# Inisialisasi FastAPI
app = FastAPI()

# Load .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load Whatsapp
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Load telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TELEGRAM_TOKEN)

# Inisialisasi client OpenAI
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY tidak ditemukan")
    return OpenAI(api_key=api_key)

client = get_openai_client()

# New: default system prompt 
DEFAULT_SYSTEM_PROMPT = (
    "Kamu adalah teman masa kecil. jawaban harus asik, santai,"
    "menyenangkan, dan lebih seperti imaginasi. Gunakan bahasa santai dan sehari hari tanpa baku atau kaku."
)

# Load data dari file json
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Load data dari file produk
with open("produk.json", "r", encoding="utf-8") as f:
    produk_data = json.load(f)

# Fungsi chatbot sederhana 
def get_response(message: str):
    message_lower = message.lower()
    for item in data:
        # Cek question
        if item["question"] in message_lower:
            return item["answer"]
        # Cek tags
        for tag in item["tags"]:
            if tag in message_lower:
                return item["answer"]
    return "maaf, saya tidak mengerti."

# Fungsi chatbot khusus produk
def get_response_produk(message: str):
    message_lower = message.lower()
    for item in produk_data:
        # Cek nama produk
        if item["name"].lower() in message_lower:
            return f"{item['name']} tersedia dengan harga Rp{item['price']:,}".replace(",", ".")
        # Cek tags
        for tag in item["tags"]:
            if tag in message_lower:
                return f"{item['name']} tersedia dengan harga Rp{item['price']}"
    return "maaf, saya tidak mengerti."

# Fungsi panggil OpenAI GPT
def get_response_gpt(message: str):
    try:
        # 1) Membuat messages: system prompt (profesional) + user message
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": message}
        ]

        # 2) Memanggil API OpenAI via client yang sudah di inisialisasikan
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200
        )

        # 3) Mengambil isi jawaan secara aman
        choice = response.choices[0]
        if hasattr(choice, "message"):
            return choice.message.content.strip()
        elif "text" in choice:
            return choice["text"].strip()
        else:
            return str(response)

    except Exception as e:
        import traceback
        print("Error GPT:", e)
        traceback.print_exc()
        return "Maaf, saya tidak bisa menghubungkan."

N8N_WEBHOOK_URL = "https://aldo1123.app.n8n.cloud/webhook/63c8f149-a500-4078-bae4-c14bc2d8588f"

def send_to_n8n(user_message: str, bot_response: str):
    payload = {
        "user_message": user_message,
        "bot_response": bot_response
    }
    try:
        r = requests.post(N8N_WEBHOOK_URL, json=payload)
        print("Status kirim ke N8N:", r.status_code)
        return r.status_code
    except Exception as e:
        print("Gagal kirim ke N8N:", e)
        return None
    
# Fungsi untuk mengambil data dari openweather
def get_weather(city: str):
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=id"

    try:
        r = requests.get(url)
        data = r.json()
        if r.status_code == 200:
            desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            return f"Cuaca di {city} sekarang: {desc}, suhu {temp}C (terasa {feels_like}C)."
        else:
            return f"Gagal ambil cuaca: {data.get('message', 'error tidak diketahui.')}"
    except Exception as e:
        return f"Error ambil cuaca: {e}"

# Fungsi inti untuk proses pesan
async def handle_chat(user_message: str):
    bot_response = get_response(user_message)

    # Cek apakah user meminta info produk
    if bot_response == "maaf, saya tidak mengerti.":
        bot_response = get_response_produk(user_message)

    # Cek apakah user meminta info cuaca
    if "cuaca" in user_message.lower():
        words = user_message.lower().split()
        if len(words) > 1:
            city = words[-1]
        else:
            city = "Jakarta"
        bot_response = get_weather(city)

    # Kalau JSON tidak punya jawaban, fallback ke GPT
    if bot_response == "maaf, saya tidak mengerti.":
        bot_response = get_response_gpt(user_message)

    # Kirim ke N8N
    send_to_n8n(user_message, bot_response)

    return bot_response
    
# Webhook Whatsapp verifikasi
@app.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(params["hub.challenge"])
    return {"error": "Token tidak valid"}

# Webhook Whatsapp Menerima pesan
@app.post("/webhook")
async def webhook_whatsapp(request: Request):
    data = await request.json()
    print("Data masuk dari whatsapp:", data)
    # Pastikan data valid
    if "entry" in data:
        for entry in data["entry"]:
            if "changes" in entry:
                for change in entry["changes"]:
                    if "value" in change and "messages" in change["value"]:
                        for message in change["value"]["messages"]:
                            sender = message["from"] # Nomor Pengirim
                            text = message.get("text", {}).get("body", "") # Isi Pesan
                            print(f"Pesan dari {sender}: {text}")
                            
                            # Jawaban dari chatbot
                            reply_text = await handle_chat(text)
                            
                            # Kirim balik ke Whatsapp
                            url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                            headers = {
                                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                                "Content-Type": "application/json"
                            }
                            payload = {
                                "messaging_product": "whatsapp",
                                "to": sender,
                                "text": {"body": reply_text}
                            }
                            requests.post(url, headers=headers, json=payload)
    return {"status": "ok"}
   

# Webhook Telegram
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    body = await request.json()
    update = Update.de_json(body, bot)
    
    if update.message:
        chat_id = update.message.chat.id
        message_text = update.message.text
        response = await handle_chat(message_text) 
        await bot.send_message(chat_id=chat_id, text=response)
    
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Chatbot API is running!"}

# Endpoint khusus frontend UI
@app.post("/chat")
async def chat_ui(request: Request):
    req_json = await request.json()
    user_message = req_json.get("message")

    if isinstance(user_message, dict):
        user_message = user_message.get("text", "")
    if not isinstance(user_message, str):
        user_message = str(user_message)

    response = await handle_chat(user_message)
    return {"reply": response}

# Endpoint untuk memanggil chatbot
@app.post("/")
async def chatbot(request: Request):
    req_json = await request.json()
    user_message = req_json.get("message")

    if isinstance(user_message, dict):
        user_message = user_message.get("text", "")
    if not isinstance(user_message, str):
        user_message = str(user_message)

    response = await handle_chat(user_message)
    return {"reply": response}

# 🔹 Ambil semua data
@app.get("/items")
def get_all_items():
    return data

# 🔹 Ambil semua produk
@app.get("/produk")
def get_all_produk():
    return produk_data

# Tambah healt endpoin
@app.get("/healt")
def healt():
    return {"ok":True}

# 🔹 Ambil data berdasarkan ID
@app.get("/items/{item_id}")
def get_item(item_id: int):
    for entry in data:
        if entry["id"] == item_id:
            return entry
    return {"message": "ID tidak ditemukan"}

# 🔹 Tambah data baru (ID otomatis)
@app.post("/items")
def add_item(entry: dict):
    new_id = max([d["id"] for d in data], default=0) + 1
    entry["id"] = new_id
    data.append(entry)
    save_data()
    return {"message": f"Data dengan id {new_id} berhasil ditambahkan"}

# 🔹 Update data berdasarkan ID
@app.put("/items/{item_id}")
def update_item(item_id: int, update_data: dict):
    for entry in data:
        if entry["id"] == item_id:
            entry.update(update_data)
            save_data()
            return {"message": f"Data dengan id {item_id} berhasil diupdate"}
    return {"message": "ID tidak ditemukan"}

# 🔹 Hapus data berdasarkan ID
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    global data
    data = [d for d in data if d["id"] != item_id]
    save_data()
    return {"message": f"Data dengan id {item_id} berhasil dihapus"}

# 🔹 Simpan perubahan ke data.json
def save_data():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)
