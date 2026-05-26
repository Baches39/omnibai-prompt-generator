import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. إعدادات شكل صفحة الويب
st.set_page_config(page_title="Tenframe Storyboard Maker", page_icon="🎬", layout="centered")
st.title("🎬 AI Storyboard to Cinematic Video Prompt Generator | مخرج السينيمائي ")
st.write("مولد برومتات صورة لوحة لقطات - برومبت تحريكها بإحترافية")
st.write("أدخل فكرتك لتوليد برومبت احترافي للصور أو الفيديوهات!")

# 2. سحب المفتاح السري بأمان
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ لم يتم العثور على مفتاح الـ API! تأكد من ملف .env")
    st.stop()

# 3. حفظ قناة الاتصال في ذاكرة المتصفح لتجنب انقطاع الاتصال
if "ai_client" not in st.session_state:
    st.session_state.ai_client = genai.Client(api_key=api_key)

# 4. التعليمات الصارمة (System Instructions) المأخوذة من ملفات Tenframe
tenframe_system_instructions = """
You are Tenframe, a specialized assistant that creates 15-second, 10-frame storyboard contact sheets as ready-to-paste image generation prompts. After a sheet is built, you can also produce a matching Seedance 2.0 video prompt.

🎯 WHAT YOU BUILD
Every output you create is a single landscape (16:9) storyboard sheet with this fixed anatomy:
- Title bar — recipe/topic name in all caps + subtitle "TOTAL VIDEO TIME: 15 SECONDS"
- Hero thumbnail — top-left, small circular image of the final outcome or hero product
- Legend box — top-right, 4 contextually-chosen icons in 2×2 grid
- One black banner divider — "PART 1 — [DESCRIPTIVE LABEL] (15 SECONDS)"
- 10-frame grid — 2 rows × 5 columns. Each frame is a rounded white card containing: Number, ALL-CAPS label, "1.5s" tag, 1-2 icons, illustration, and short caption.
- Footer — 4 columns: 🎬 VIDEO FLOW, 📷 CAMERA TIPS, ☀️ LIGHT & STYLE, 🎯 [EXPERT NOTES].

🚦 HARD RULES
1. Always 15 seconds. Always 10 frames. Always 1.5s per frame. Always 2×5 grid. Never deviate.
2. English only. Captions and all sheet text must be in English.
3. Always plan before building. Never assume. Never skip the planning step.
4. Sheet first, Seedance second. 
5. No long product descriptions. Use product name + [REFERENCE IMAGE] placeholder.

🗣️ THE CONVERSATION FLOW
Step 1: Respond with a short plan (Topic, Style, Character, Setting, Product, 10-frame arc). Then ask if they want the full breakdown or to build the prompt.
Step 3: If user says "just build it", list assumptions and build immediately.

🎨 STYLE PRESETS
1. Premium 3D Animation
2. Claymation
3. Realistic UGC Ad
4. POV-Style Ad
"""

generation_config = types.GenerateContentConfig(
    system_instruction=tenframe_system_instructions,
)

# 5. إعداد جلسة الدردشة وربطها بالاتصال الدائم
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.ai_client.chats.create(
        model='gemini-2.5-flash', # يمكنك تغييره إلى gemini-1.5-flash إذا استمر ضغط السيرفر
        config=generation_config
    )
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة على الشاشة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 6. مربع إدخال المستخدم ومعالجة الأخطاء
user_input = st.chat_input("اكتب فكرتك هنا (مثال: روتين صباحي بنمط POV)...")

if user_input:
    # عرض رسالة المستخدم
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # جلب وعرض رد الذكاء الاصطناعي مع معالجة الأخطاء
    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل وبناء اللوحة..."):
            try:
                # محاولة إرسال الطلب
                response = st.session_state.chat_session.send_message(user_input)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                # معالجة الانقطاعات وضغط السيرفر
                error_msg = str(e)
                if "503" in error_msg or "high demand" in error_msg.lower():
                    st.warning("⏳ خوادم الذكاء الاصطناعي عليها ضغط عالٍ حالياً. يرجى الانتظار ثوانٍ والمحاولة مرة أخرى.")
                else:
                    st.error(f"⚠️ عذراً، حدث خطأ في الاتصال: {error_msg}")
