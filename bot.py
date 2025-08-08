from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import mysql.connector
import subprocess
import re

ip = ""
port = "6040"

db_config = {
    'user': 'root',
    'password': 'aBc.123456',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'monitor_users_db',
}


async def reset_configures(context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_password"):
        context.user_data.pop("awaiting_password", None)
    if context.user_data.get("awaiting_remove_ips"):
        context.user_data.pop("awaiting_remove_ips", None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reset_configures(context)

    keyboard = [
        [" اطلاعات اتصال"],
        [" آیدی عددی", " راهنما"],
        ["تغییر رمز عبور", "لیست آیپی ها"],
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
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result:
        with open("help.mp4", "rb") as video_file:
            await update.message.reply_video(video=video_file, caption="راهنمای اتصال با استفاده از napsternetv")
    else:
        message = "اطلاعاتی یافت نشد"
        await update.message.reply_text(message)

    cursor.close()
    conn.close()


async def change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result:
        id = result[0]
        if not context.user_data.get("awaiting_password"):
            await update.message.reply_text("لطفاً رمز عبور جدید خود را وارد کنید")
            context.user_data["awaiting_password"] = True
            cursor.close()
            conn.close()
            return

        new_password = update.message.text.strip()
        contains_persian = bool(re.search(r'[\u0600-\u06FF]', new_password))
        if not new_password or contains_persian:
            await update.message.reply_text("رمز عبور معتبر نیست. لطفاً فقط از حروف لاتین و اعداد استفاده کنید")
            return
        try:
            command = f'echo "{id}:{new_password}" | /usr/sbin/chpasswd'
            subprocess.run(command, shell=True, check=True)
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s", (new_password, id,))
            conn.commit()
            await update.message.reply_text("رمز عبور با موفقیت تغییر کرد")

        except subprocess.CalledProcessError:
            await update.message.reply_text("خطا در تغییر رمز عبور")
    else:
        message = "اطلاعاتی یافت نشد"
        await update.message.reply_text(message)

    context.user_data.pop("awaiting_password", None)
    cursor.close()
    conn.close()


async def connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result:
        id= result[0]
        cmd = cmd = f"ps aux | awk -v u='{id}' '$1 == \"{id}\" && $0 ~ (\"sshd: \" u) {{ print $2 }}'"
        pids = subprocess.check_output(
            cmd, shell=True, text=True).strip().split()

        if not pids:
            context.user_data.pop("awaiting_remove_ips", None)
            await update.message.reply_text("درحال حاضر هیچ اتصالی ندارید")
            return
        ips = []
        for pid in pids:
            cmd = f"ss -tunp | grep 'pid={pid}' |grep {port} | awk '{{print $6}}' | cut -d':' -f1"
            ip = subprocess.check_output(cmd, shell=True, text=True).strip()
            if ip not in ips:
                ips.append(ip)

        context.user_data["pids"] = pids
        context.user_data["ips"] = ips
        context.user_data["id"] = id

        keyboard = [
            [InlineKeyboardButton(ip, callback_data=f"ip:{ip}")]
            for ip in ips
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اتصال کدام آیپی قطع شود؟", reply_markup=reply_markup)

    else:
        context.user_data.pop("awaiting_remove_ips", None)
        message = "اطلاعاتی یافت نشد"
        await update.message.reply_text(message)

    cursor.close()
    conn.close()


async def handle_ip_click(update, context):
    pids = context.user_data.pop("pids", None)
    ips = context.user_data.pop("ips", None)
    id = context.user_data.pop("id", None)

    query = update.callback_query
    await query.answer()

    data = query.data
    selected_ip = data.split("ip:")[1]
    try:
        blocked_file = "/root/monitor_users/blocked_users_ips.txt"
        with open(blocked_file, "a") as f:
            f.write(f"{id}:{selected_ip}\n")
            f.close()
        sed_cmd = f"sed -i '/^{id}:{selected_ip}$/d' '{blocked_file}'"
        subprocess.run(
            f"echo \"{sed_cmd}\" | at now + 5 minute", shell=True, check=True)

        indices = [i for i, ip in enumerate(ips) if ip == selected_ip]
        for index in indices:
            pid = pids[index]
            subprocess.run(["kill", "-9", pid])
        await query.edit_message_text(
            f"آیپی {selected_ip} با موفقیت حذف شد",
            reply_markup=None
        )

    except:
        await query.edit_message_text(
            f"پوزش! نتونستیم حذفش کنیم",
            reply_markup=None
        )


async def connection_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result:
        id, password = result
        message = (
            f"اطلاعات اتصال:\n"
            f"آیپی سرور: {ip}\n"
            f"نام کاربری: {id}\n"
            f"رمز عبور: {password}\n"
            f"پورت: {port}\n"
        )
        if chat_id == 7858487903:
            cursor.execute(
                "SELECT id FROM users")
            result = cursor.fetchall()
            for row in result:
                user_id = row[0]
                cmd = f'ps aux | awk -v u="{user_id}" \'$1 == u && $0 ~ ("sshd: " u)\' | wc -l'
                session_count = subprocess.check_output(
                    cmd, shell=True, text=True).strip()
                message += (
                    f"--------------------------------------\n"
                    f"کاربر: {user_id}\n"
                    f"تعداد اتصال: {session_count}\n"
                )

        else:
            cmd = f'ps aux | awk -v u="{id}" \'$1 == u && $0 ~ ("sshd: " u)\' | wc -l'
            session_count = subprocess.check_output(
                cmd, shell=True, text=True).strip()
            message += (
                f"تعداد اتصال: {session_count}\n"
            )
    else:
        message = "اطلاعاتی یافت نشد"
    cursor.close()
    conn.close()

    await update.message.reply_text(message)


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    commands = ["اطلاعات اتصال", "آیدی عددی", "راهنما",
                "تغییر رمز عبور", "لیست آیپی ها", "بازگشت"]

    if text in commands:
        await reset_configures(context)
        if text == "اطلاعات اتصال":
            await connection_info(update, context)

        elif text == "آیدی عددی":
            await chatid(update, context)

        elif text == "راهنما":
            await help(update, context)

        elif text == "تغییر رمز عبور":
            await change_password(update, context)

        elif text == "لیست آیپی ها":
            await connections(update, context)

        else:
            msg = await update.message.reply_text("برگشتیم", reply_markup=ReplyKeyboardRemove())
            await msg.delete()

    elif context.user_data.get("awaiting_password"):
        await change_password(update, context)
        return

    elif context.user_data.get("awaiting_remove_ips"):
        await connections(update, context)
        return


if __name__ == "__main__":
    BOT_TOKEN = "8423273599:AAFGa2YlPAhg6H97axaqq0DeBCl2jLNSfiw"

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_ip_click, pattern=r"^ip:"))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", chatid))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(MessageHandler(filters.TEXT & (
        ~filters.COMMAND), handle_menu_selection))

    app.run_polling()