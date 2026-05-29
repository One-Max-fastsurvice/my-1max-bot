import asyncio
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from ai_engine import get_ai_response, user_memory

# လူကြီးမင်း၏ Bot Token ကို ထည့်သွင်းပြီး
TOKEN = "8671029713:AAE3E5HrPdY1wQhR-Pas6-aaiAMZni45fNY"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ မိတ်ဆွေ။ 1Max AI Explainer မှ ကြိုဆိုပါတယ်။ လူကြီးမင်း သိရှိလိုသမျှကို မေးမြန်းနိုင်ပါတယ်။\n\n"
        "1Max Digital Market မှ အမြဲတမ်း အဆင်သင့်ရှိနေပါတယ်"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Typing Action ပြခြင်း
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    try:
        response_stream = get_ai_response(user_id, user_text)
        message = await update.message.reply_text("...") 
        full_response = ""
        counter = 0

        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                counter += 1
                
                # စာသား ၈ ကြိမ်ရတိုင်း တစ်ခါ Update လုပ်မယ်
                if counter % 8 == 0:
                    try:
                        await message.edit_text(full_response)
                    except:
                        pass
        
        # အချောသတ် စာသား
        await message.edit_text(full_response)
        user_memory[user_id].append({"role": "assistant", "content": full_response})

    except Exception as e:
        await update.message.reply_text(f"အမှားတစ်ခု ဖြစ်ပေါ်နေပါတယ် မိတ်ဆွေ။ ခဏနေမှ ပြန်ကြိုးစားပေးပါ။")
        print(f"Error: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("1Max AI Explainer is running...")
    app.run_polling()
  
