from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import mysql.connector
import subprocess

# set this each month
ip = "156.253.5.152"


db_config = {
    'user': 'root',
    'password': 'aBc.123456',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'monitor_users_db',
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [" اطلاعات اتصال", " میزان مصرف"],
        [" آیدی عددی", " راهنما"],
        [" بازگشت"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=reply_markup)


async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    message = (
        f" آیدی عددی: {chat_id}\n"
    )

    await update.message.reply_text(message)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("help.mp4", "rb") as video_file:
        await update.message.reply_video(video=video_file, caption="راهنمای اتصال با استفاده از napsternetv")


async def connection_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password , port FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        id, password, port = result
        message = (
            f"اطلاعات اتصال:\n"
            f"آیپی سرور: {ip}\n"
            f"نام کاربری: {id}\n"
            f"رمز عبور: {password}\n"
            f"پورت: {port}"
        )
    else:
        message = "اطلاعاتی یافت نشد."

    await update.message.reply_text(message)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    if chat_id == 7858487903:
        cursor.execute(
            "SELECT id, download_volume, upload_volume FROM users")
        result = cursor.fetchall()
        message = ""
        for row in result:
            id, download, upload = row
            cmd = f'ps aux | awk -v u="{id}" \'$1 == u && $0 ~ ("sshd: " u)\' | wc -l'
            session_count = subprocess.check_output(cmd, shell=True, text=True).strip()

            message += (
                f"کاربر: {id}\n"
                f"تعداد اتصال: {session_count}\n"
                f"دانلود: {download}B\n"
                f"آپلود: {upload}B\n\n"
            )
    else:
        cursor.execute(
            "SELECT download_volume, upload_volume FROM users WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        if result:
            download, upload = result
            message = (
                f"مصرف شما:\n"
                f"دانلود: {download}B\n"
                f"آپلود: {upload}B"
            )
        else:
            message = "اطلاعاتی یافت نشد."

    cursor.close()
    conn.close()

    await update.message.reply_text(message)


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "اطلاعات اتصال":
        await connection_info(update, context)

    elif text == "میزان مصرف":
        await status(update, context)

    elif text == "آیدی عددی":
        await chatid(update, context)

    elif text == "راهنما":
        await help(update, context)

    else:
        msg = await update.message.reply_text("برگشتیم", reply_markup=ReplyKeyboardRemove())
        await msg.delete()


if __name__ == "__main__":
    BOT_TOKEN = "8423273599:AAFGa2YlPAhg6H97axaqq0DeBCl2jLNSfiw"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", chatid))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & (
        ~filters.COMMAND), handle_menu_selection))

    app.run_polling()
