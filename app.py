import os
import logging
import json
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai.errors import APIError

# إعداد التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# الحصول على التوكن والمفتاح من متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN or GEMINI_API_KEY environment variable not set.")
    # لا نخرج هنا، بل نترك التطبيق يعمل لكي يتمكن Vercel من بنائه، لكنه سيفشل عند التشغيل الفعلي
    # هذا الإجراء ضروري لبيئات الاستضافة السحابية
    pass

# تهيئة عميل Gemini
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = "gemini-2.5-flash"
except Exception as e:
    logger.error(f"Error configuring Gemini client: {e}")
    pass

# 1. دالة لمعالجة أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يرسل رسالة ترحيب عند إصدار الأمر /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}! أنا بوت يعمل بتقنية Gemini AI. أرسل لي أي سؤال وسأجيبك.",
    )

# 2. دالة لمعالجة الرسائل النصية والرد عليها باستخدام Gemini
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يرد على رسالة المستخدم باستخدام نموذج Gemini."""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    # إرسال مؤشر الكتابة (typing)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # استدعاء Gemini API
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
        )
        
        # الرد على المستخدم
        await update.message.reply_text(response.text)

    except APIError as e:
        logger.error(f"Gemini API Error: {e}")
        await update.message.reply_text(
            "عذراً، حدث خطأ أثناء الاتصال بخدمة Gemini AI. يرجى المحاولة مرة أخرى لاحقاً."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        await update.message.reply_text(
            "عذراً، حدث خطأ غير متوقع. يرجى التحقق من سجلات البوت."
        )

# 3. إعداد تطبيق Telegram.ext
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 4. إعداد تطبيق Flask لاستقبال Webhooks
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """نقطة نهاية بسيطة للتحقق من حالة التطبيق."""
    return "Telegram Gemini Bot is running!", 200

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
async def webhook_handler():
    """نقطة نهاية Webhook لمعالجة تحديثات تليجرام."""
    if request.method == "POST":
        # قراءة البيانات المرسلة من تليجرام
        update = Update.de_json(request.get_json(force=True), application.bot)
        
        # معالجة التحديث
        await application.process_update(update)
        
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

# 5. دالة رئيسية للتشغيل المحلي (اختياري)
def main() -> None:
    """تشغيل البوت في وضع Polling للتشغيل المحلي."""
    logger.info("Starting bot in Polling mode for local testing...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # يمكن استخدام هذا الجزء للتشغيل المحلي فقط
    # main()
    # للتشغيل على Vercel، سيتم استدعاء التطبيق مباشرة
    pass
