import openai
from collections import deque

# OpenRouter Configuration (လူကြီးမင်း၏ Key ကို ထည့်သွင်းပြီး)
client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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", 
)

# User တစ်ဦးချင်းစီရဲ့ Memory ကို သိမ်းရန် (Max 5 messages)
user_memory = {}

def get_ai_response(user_id, user_input):
    if user_id not in user_memory:
        user_memory[user_id] = deque(maxlen=5)
    
    system_prompt = {
        "role": "system",
        "content": (
            "မင်းက 1Max Digital Market ရဲ့ တရားဝင် AI လက်ထောက် '1Max AI Explainer' ဖြစ်တယ်။ "
            "SMM ဝန်ဆောင်မှုတွေနဲ့ Telegram Bot အကြောင်းကို ကျွမ်းကျင်စွာ ဖြေကြားပေးပါ။ "
            "Customer တွေကို 'လူကြီးမင်း' သို့မဟုတ် 'မိတ်ဆွေ' လို့ သုံးနှုန်းပြီး ယဉ်ကျေးစွာ ပြောဆိုပါ။ "
            "စာကြောင်းတိုင်းရဲ့ အဆုံးမှာ '1Max Digital Market မှ အမြဲတမ်း အဆင်သင့်ရှိနေပါတယ်' လို့ ထည့်သွင်းပါ။"
        )
    }

    messages = [system_prompt]
    for msg in user_memory[user_id]:
        messages.append(msg)
    
    current_user_msg = {"role": "user", "content": user_input}
    messages.append(current_user_msg)

    response = client.chat.completions.create(
        model="google/gemini-pro-1.5",
        messages=messages,
        stream=True
    )

    user_memory[user_id].append(current_user_msg)
    return response
  
