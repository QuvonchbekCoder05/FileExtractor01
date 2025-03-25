import asyncio
import logging
import os
import zipfile
import fitz  # PyMuPDF (PDFni o‘qish)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from docx import Document  # DOCX fayl yaratish uchun
from PIL import Image
from config import BOT_TOKEN, TEMP_DIR

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

processing_tasks = {}


# ✅ Fayllarni avtomatik tozalash
def cleanup_temp_files():
    for file in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, file)
        try:
            os.remove(file_path)
            logging.info(f"🗑️ Fayl o‘chirildi: {file_path}")
        except Exception as e:
            logging.error(f"❌ Faylni o‘chirishda xatolik: {file_path} - {str(e)}")


# ✅ Menyu tugmachalari (O‘zgartirilmagan!)
menu_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Rasm -> PDF"), KeyboardButton(text="📝 Rasm -> DOC")],
        [
            KeyboardButton(text="📄 DOC -> PDF"),
            KeyboardButton(text="📂 ZIP faylni ochish"),
        ],
        [
            KeyboardButton(text="📸 PDF -> Rasm"),
            KeyboardButton(text="📦 Faylni siqish"),
        ],
    ],
    resize_keyboard=True,
)


# ✅ /start komandasi
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "📂 Menga fayl yuboring va qanday formatga o‘zgartirishni tanlang.",
        reply_markup=menu_buttons,
    )


# ✅ Foydalanuvchi fayl yuborsa
@dp.message(F.document | F.photo)
async def handle_document(message: types.Message):
    file = None
    file_path = ""

    if message.document:
        file = await bot.get_file(message.document.file_id)
        file_path = os.path.join(TEMP_DIR, message.document.file_name)
    elif message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        file_path = os.path.join(TEMP_DIR, f"{message.photo[-1].file_id}.jpg")

    if file:
        await bot.download_file(file.file_path, file_path)

    await message.answer(
        "✅ Fayl qabul qilindi! Endi menyudan kerakli funksiyani tanlang.",
        reply_markup=menu_buttons,
    )


# ✅ Rasmni PDFga o‘girish
@dp.message(F.text == "📸 Rasm -> PDF")
async def image_to_pdf(message: types.Message):
    files = os.listdir(TEMP_DIR)
    image_files = [f for f in files if f.endswith(".jpg") or f.endswith(".png")]

    if not image_files:
        await message.answer("❌ Rasm yuklanmagan.")
        return

    image_paths = [os.path.join(TEMP_DIR, f) for f in image_files]
    pdf_path = os.path.join(TEMP_DIR, "converted.pdf")

    images = [Image.open(img_path).convert("RGB") for img_path in image_paths]
    images[0].save(pdf_path, save_all=True, append_images=images[1:])

    await message.answer("✅ Rasm PDFga o‘girildi!")
    await bot.send_document(message.chat.id, FSInputFile(pdf_path))

    cleanup_temp_files()


# ✅ PDFni Rasmga aylantirish
@dp.message(F.text == "📸 PDF -> Rasm")
async def pdf_to_image(message: types.Message):
    files = os.listdir(TEMP_DIR)
    pdf_files = [f for f in files if f.endswith(".pdf")]

    if not pdf_files:
        await message.answer("❌ PDF fayl yuklanmagan.")
        return

    file_path = os.path.join(TEMP_DIR, pdf_files[0])
    doc = fitz.open(file_path)
    processing_tasks[message.from_user.id] = True

    await message.answer(f"✅ PDF {len(doc)} ta rasmga o‘girilmoqda.")

    for i, page in enumerate(doc):
        if not processing_tasks.get(message.from_user.id, True):
            await message.answer("🚫 Jarayon to‘xtatildi.")
            break

        pix = page.get_pixmap()
        img_path = os.path.join(TEMP_DIR, f"pdf_page_{i}.jpg")
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(img_path, "JPEG")
        await bot.send_photo(message.chat.id, FSInputFile(img_path))

    doc.close()
    cleanup_temp_files()


# ✅ ZIP faylni ochish
@dp.message(F.text == "📂 ZIP faylni ochish")
async def unzip_file(message: types.Message):
    files = os.listdir(TEMP_DIR)
    zip_files = [f for f in files if f.endswith(".zip")]

    if not zip_files:
        await message.answer("❌ ZIP fayl yuklanmagan.")
        return

    file_path = os.path.join(TEMP_DIR, zip_files[0])
    unzip_dir = os.path.join(TEMP_DIR, "unzipped")
    os.makedirs(unzip_dir, exist_ok=True)

    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)

    for file_name in os.listdir(unzip_dir):
        await bot.send_document(
            message.chat.id, FSInputFile(os.path.join(unzip_dir, file_name))
        )

    cleanup_temp_files()


# ✅ Jarayonni To‘xtatish
@dp.message(F.text == "⏹️ Jarayonni To‘xtatish")
async def stop_processing(message: types.Message):
    user_id = message.from_user.id
    processing_tasks[user_id] = False
    await message.answer("🚫 Jarayon to‘xtatildi.")


# ✅ Always-on: Bot qayta ishga tushadi!
async def main():
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"🚀 Bot qayta ishga tushdi! Xatolik: {e}")


if __name__ == "__main__":
    asyncio.run(main())
