import os
import re
import asyncio
import traceback
import requests

from rubka.asynco import Robot


# ============================================================
# 🔐 تنظیمات
# ============================================================

RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")

GAPGPT_BASE_URL = "https://api.gapgpt.app/v1"
GAPGPT_MODEL = "gpt-4o-mini"

AI_TIMEOUT = 60


# ============================================================
# بررسی کلیدها
# ============================================================

if not RUBIKA_TOKEN:
    raise RuntimeError(
        "❌ RUBIKA_TOKEN تنظیم نشده است.\n"
        "مثال:\n"
        "export RUBIKA_TOKEN='توکن'"
    )

if not GAPGPT_API_KEY:
    raise RuntimeError(
        "❌ GAPGPT_API_KEY تنظیم نشده است.\n"
        "مثال:\n"
        "export GAPGPT_API_KEY='کلید'"
    )


# ============================================================
# 🤖 ربات
# ============================================================

bot = Robot(
    token=RUBIKA_TOKEN,
    platform="web",
    timeout=30,
    retries=3,
    retry_delay=1,
    parse_mode=None,
    show_log=True
)


# ============================================================
# 🌐 HTTP Session
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "Rubika-GapGPT-Bot/1.0",
    "Accept": "application/json"
})


# ============================================================
# 🧹 تمیز کردن متن
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text).strip()

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    return text


# ============================================================
# 🔗 پیدا کردن لینک
# ============================================================

def extract_urls(text):

    if not text:
        return []

    return re.findall(
        r"https?://[^\s<>\"]+",
        text
    )


# ============================================================
# 🤖 تشخیص گروه
# ============================================================

def is_group_message(message):

    # ------------------------------
    # روش اول: chat_type
    # ------------------------------

    chat_type = getattr(
        message,
        "chat_type",
        None
    )

    if chat_type:

        value = str(
            chat_type
        ).lower()

        if (
            "group" in value
            or "supergroup" in value
        ):
            return True

        if (
            "private" in value
            or "user" in value
        ):
            return False


    # ------------------------------
    # روش دوم: raw_data
    # ------------------------------

    raw_data = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw_data, dict):

        # بعضی نسخه‌های کتابخانه
        # اطلاعات چت را اینجا قرار می‌دهند.

        raw_string = str(
            raw_data
        ).lower()

        if (
            "supergroup" in raw_string
            or '"type": "group"' in raw_string
            or "'type': 'group'" in raw_string
        ):
            return True


    # ------------------------------
    # روش سوم: chat_id
    # ------------------------------

    chat_id = str(
        getattr(
            message,
            "chat_id",
            ""
        )
    ).lower()

    # بعضی ساختارها ID گروه را متفاوت
    # گزارش می‌کنند. اینجا فقط کمک‌کننده است.

    if chat_id.startswith("g_"):
        return True


    # ------------------------------
    # پیش‌فرض
    # ------------------------------

    return False


# ============================================================
# 🔁 شناسه Reply
# ============================================================

def get_reply_id(message):

    fields = [
        "reply_to_message_id",
        "reply_to_id",
        "reply_message_id"
    ]

    for field in fields:

        value = getattr(
            message,
            field,
            None
        )

        if value:
            return str(value)


    # بررسی raw_data

    raw_data = getattr(
        message,
        "raw_data",
        None
    )

    if isinstance(raw_data, dict):

        possible_keys = [
            "reply_to_message_id",
            "reply_to_id",
            "reply_message_id"
        ]

        for key in possible_keys:

            value = raw_data.get(key)

            if value:
                return str(value)


    return None


# ============================================================
# 🆔 شناسه پیام
# ============================================================

def get_message_id(message):

    fields = [
        "message_id",
        "id"
    ]

    for field in fields:

        value = getattr(
            message,
            field,
            None
        )

        if value:
            return str(value)

    return None


# ============================================================
# 🤖 تشخیص «ربات»
# ============================================================

def has_bot_prefix(text):

    text = clean_text(text)

    if not text:
        return False

    return (
        text == "ربات"
        or text.startswith("ربات ")
        or text.startswith("ربات:")
        or text.startswith("ربات:")
        or text.startswith("ربات،")
    )


# ============================================================
# حذف «ربات»
# ============================================================

def remove_bot_prefix(text):

    text = clean_text(text)

    prefixes = [
        "ربات ",
        "ربات:",
        "ربات،",
        "ربات"
    ]

    for prefix in prefixes:

        if text.startswith(prefix):

            return text[
                len(prefix):
            ].strip()

    return text


# ============================================================
# 🧠 درخواست به GapGPT
# ============================================================

def gapgpt_request(
    messages,
    temperature=0.7
):

    url = (
        GAPGPT_BASE_URL.rstrip("/")
        + "/chat/completions"
    )

    headers = {
        "Authorization":
            f"Bearer {GAPGPT_API_KEY}",

        "Content-Type":
            "application/json"
    }

    payload = {
        "model": GAPGPT_MODEL,
        "messages": messages,
        "temperature": temperature
    }

    response = session.post(
        url,
        headers=headers,
        json=payload,
        timeout=AI_TIMEOUT
    )

    print(
        "🌐 GapGPT:",
        response.status_code
    )

    if response.status_code != 200:

        raise RuntimeError(
            "GapGPT "
            + str(response.status_code)
            + ": "
            + response.text[:500]
        )

    data = response.json()

    choices = data.get(
        "choices",
        []
    )

    if not choices:

        raise RuntimeError(
            "❌ پاسخ GapGPT خالی است."
        )

    message_data = choices[0].get(
        "message",
        {}
    )

    content = message_data.get(
        "content",
        ""
    )

    return str(
        content
    ).strip()


async def ask_ai(
    messages,
    temperature=0.7
):

    return await asyncio.to_thread(
        gapgpt_request,
        messages,
        temperature
    )


# ============================================================
# 💬 چت هوشمند
# ============================================================

async def chat_ai(text):

    system_prompt = """
تو دستیار هوشمند یک ربات روبیکا هستی.

زبان اصلی فارسی است.

قوانین:
- طبیعی و کوتاه پاسخ بده.
- اگر جواب را نمی‌دانی، صادقانه بگو.
- اطلاعات ساختگی تولید نکن.
- نام کاربر را صدا نزن.
- درباره درخواست‌های نامشخص سؤال کوتاه بپرس.
"""

    return await ask_ai(
        [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": text
            }
        ],
        0.7
    )


# ============================================================
# 🎵 پیدا کردن اطلاعات آهنگ
# ============================================================

async def find_song(text):

    prompt = f"""
کاربر دنبال یک آهنگ است.

درخواست:
{text}

اگر اطلاعات کافی وجود دارد، این موارد را مشخص کن:

🎵 نام آهنگ
🎤 خواننده
💿 آلبوم
📅 سال انتشار
🎬 فیلم یا سریال مرتبط

اگر از اطلاعات مطمئن نیستی، حدس نزن.

پاسخ فارسی و خلاصه باشد.
"""

    return await ask_ai(
        [
            {
                "role": "system",
                "content":
                    "تو یک دستیار متخصص موسیقی هستی."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        0.3
    )


# ============================================================
# 🎵 تشخیص درخواست آهنگ
# ============================================================

def is_song_request(text):

    keywords = [
        "آهنگ",
        "اهنگ",
        "موزیک",
        "ترانه",
        "خواننده",
        "موسیقی"
    ]

    text = clean_text(
        text
    ).lower()

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# 🔗 تحلیل لینک
# ============================================================

async def analyze_link(url):

    prompt = f"""
این لینک را بررسی کن:

{url}

فقط بر اساس خود لینک بگو:

🔗 نوع لینک
📱 سرویس احتمالی
🎬 آیا احتمالاً لینک ویدیو است؟
🎵 آیا احتمالاً مرتبط با موسیقی است؟

اطلاعاتی که از URL قابل تشخیص نیست را قطعی اعلام نکن.
"""

    return await ask_ai(
        [
            {
                "role": "system",
                "content":
                    "تو تحلیلگر لینک هستی."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        0.2
    )


# ============================================================
# 📨 دریافت پیام
# ============================================================

@bot.on_message()
async def message_handler(
    bot,
    message
):

    try:

        # ====================================================
        # متن
        # ====================================================

        text = clean_text(
            getattr(
                message,
                "text",
                ""
            )
        )

        if not text:
            return


        # ====================================================
        # اطلاعات پیام
        # ====================================================

        chat_id = str(
            getattr(
                message,
                "chat_id",
                ""
            )
        )

        message_id = get_message_id(
            message
        )

        reply_id = get_reply_id(
            message
        )

        group = is_group_message(
            message
        )

        prefix = has_bot_prefix(
            text
        )


        # ====================================================
        # لاگ
        # ====================================================

        print()
        print("=" * 60)

        print(
            "📩 TEXT:",
            text
        )

        print(
            "💬 CHAT:",
            chat_id
        )

        print(
            "🆔 MESSAGE:",
            message_id
        )

        print(
            "👥 GROUP:",
            group
        )

        print(
            "↩️ REPLY:",
            reply_id
        )

        print(
            "🤖 PREFIX:",
            prefix
        )

        print("=" * 60)


        # ====================================================
        # 👥 گروه
        # ====================================================

        if group:

            # -----------------------------------------------
            # پیام عادی گروه
            # -----------------------------------------------

            if not prefix and not reply_id:

                print(
                    "⏭️ پیام عادی گروه → نادیده گرفته شد"
                )

                return


            # -----------------------------------------------
            # ربات + متن
            # -----------------------------------------------

            if prefix:

                command_text = remove_bot_prefix(
                    text
                )

            # -----------------------------------------------
            # Reply
            # -----------------------------------------------

            else:

                command_text = text


        # ====================================================
        # 💬 خصوصی
        # ====================================================

        else:

            command_text = text


        # ====================================================
        # پیام خالی
        # ====================================================

        if not command_text:

            await message.reply(
                "🤖 بله؟ چه کاری برات انجام بدم؟"
            )

            return


        # ====================================================
        # 🔗 لینک
        # ====================================================

        urls = extract_urls(
            command_text
        )

        if urls:

            url = urls[0]

            await message.reply(
                "🔗 لینک دریافت شد.\n"
                "🔎 دارم بررسیش می‌کنم..."
            )

            try:

                result = await analyze_link(
                    url
                )

                await message.reply(
                    "🔗 نتیجه بررسی:\n\n"
                    + result
                )

            except Exception as error:

                print(
                    "❌ LINK ERROR:",
                    repr(error)
                )

                await message.reply(
                    "⚠️ در بررسی لینک مشکلی پیش آمد."
                )

            return


        # ====================================================
        # 🎵 آهنگ
        # ====================================================

        if is_song_request(
            command_text
        ):

            await message.reply(
                "🎵 دارم اطلاعات آهنگ را بررسی می‌کنم..."
            )

            try:

                result = await find_song(
                    command_text
                )

                await message.reply(
                    "🎵 نتیجه:\n\n"
                    + result
                )

            except Exception as error:

                print(
                    "❌ SONG ERROR:",
                    repr(error)
                )

                await message.reply(
                    "⚠️ بررسی آهنگ با خطا مواجه شد."
                )

            return


        # ====================================================
        # 🧠 AI
        # ====================================================

        await message.reply(
            "🤖 در حال پردازش..."
        )

        try:

            result = await chat_ai(
                command_text
            )

            if not result:

                result = (
                    "⚠️ پاسخی دریافت نشد."
                )

            await message.reply(
                result
            )

        except Exception as error:

            print(
                "❌ AI ERROR:",
                repr(error)
            )

            await message.reply(
                "⚠️ اتصال به هوش مصنوعی با مشکل مواجه شد."
            )


    except Exception as error:

        print(
            "❌ MESSAGE ERROR:",
            repr(error)
        )

        traceback.print_exc()


# ============================================================
# 🚀 اجرا
# ============================================================

async def main():

    print()
    print("=" * 60)
    print("🤖 RUBIKA SMART BOT")
    print("=" * 60)
    print("🧠 GapGPT      : ON")
    print("🎵 Song        : ON")
    print("🔗 Link        : ON")
    print("👥 Group       : PREFIX / REPLY")
    print("💬 Private     : ON")
    print("👤 Username    : OFF")
    print("=" * 60)
    print("🚀 Connecting...")
    print()


    await bot.run()


# ============================================================
# ▶️ START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\n👋 Bot stopped."
        )

    except Exception as error:

        print(
            "\n❌ FATAL ERROR:",
            repr(error)
        )
