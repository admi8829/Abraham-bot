import requests
import os
import uuid

CHAPA_AUTH = os.getenv("CHAPA_SECRET_KEY") # Vercel ላይ መኖር አለበት

def create_payment_url(user_id, amount, name):
    # ለእያንዳንዱ ክፍያ ልዩ መለያ (tx_ref) መፍጠር
    tx_ref = f"ticket-{user_id}-{uuid.uuid4().hex[:5]}"
    
    url = "https://api.chapa.co/v1/transaction/initialize"
    headers = {"Authorization": f"Bearer {CHAPA_AUTH}"}
    
    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": "student@smartx.com", # ለጊዜው ዝም ብሎ የተሞላ
        "first_name": name,
        "tx_ref": tx_ref,
        "callback_url": "https://abraham-bot.vercel.app/verify", # የ Vercel ሊንክህ
        "customization": {
            "title": "Smart-X Raffle",
            "description": "የዕጣ ትኬት መቁረጫ"
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    res_data = response.json()
    
    if res_data.get("status") == "success":
        return res_data['data']['checkout_url'], tx_ref
    return None, None
  
