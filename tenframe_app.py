import streamlit as st
from google import genai
from google.genai import types

# 1. إعدادات شكل صفحة الويب
st.set_page_config(page_title="Tenframe Storyboard Maker", page_icon="🎬", layout="centered")
st.title("🎬 AI Storyboard to Cinematic Video Prompt Generator | مخرج السينيمائي ")
st.write("مولد برومتات صورة لوحة لقطات - برومبت تحريكها بإحترافية")
st.write("أدخل فكرتك لتوليد برومبت احترافي للصور أو الفيديوهات!")

# 2. سحب المفاتيح السرية من Streamlit Secrets
try:
    # جلب المفاتيح سواء كانت نصاً مفصولاً بفاصلة أو قائمة (List) جاهزة من إعدادات TOML
    keys_data = st.secrets["GEMINI_API_KEYS"]
    if isinstance(keys_data, list):
        api_keys = keys_data
    else:
        api_keys = [k.strip() for k in keys_data.split(",") if k.strip()]
except KeyError:
    st.error("⚠️ لم يتم العثور على المفاتيح! تأكد من إضافة GEMINI_API_KEYS في إعدادات st.secrets.")
    st.stop()

if not api_keys:
    st.error("⚠️ قائمة المفاتيح فارغة!")
    st.stop()

# 3. إعداد حالة المتصفح (Session State) للمفاتيح والرسائل
if "current_key_index" not in st.session_state:
    st.session_state.current_key_index = 0

if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. التعليمات الصارمة (System Instructions)
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

# 5. دالة لإنشاء أو إعادة بناء جلسة الدردشة
def create_chat_session(exclude_last_msg=False):
    """
    تُنشئ جلسة جديدة بالمفتاح النشط حالياً، وتسترجع سجل المحادثة.
    """
    current_api_key = api_keys[st.session_state.current_key_index]
    
    # التعديل الجوهري هنا: حفظ الـ Client في الـ session_state يمنع إغلاق القناة بشكل تلقائي بواسطة Python
    st.session_state.ai_client = genai.Client(api_key=current_api_key)
    
    history_contents = []
    msgs_to_include = st.session_state.messages[:-1] if exclude_last_msg else st.session_state.messages
    
    for msg in msgs_to_include:
        role = "user" if msg["role"] == "user" else "model"
        history_contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )
        
    return st.session_state.ai_client.chats.create(
        model='gemini-2.5-flash',
        config=generation_config,
        history=history_contents
    )

# تهيئة أول جلسة اتصال عند تشغيل التطبيق
if "chat_session" not in st.session_state:
    st.session_state.chat_session = create_chat_session()

# عرض الرسائل السابقة على الشاشة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 6. مربع إدخال المستخدم ومعالجة الأخطاء والتبديل التلقائي
user_input = st.chat_input("اكتب فكرتك هنا (مثال: روتين صباحي بنمط POV)...")

if user_input:
    # 1. عرض رسالة المستخدم وإضافتها للسجل
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. جلب وعرض رد الذكاء الاصطناعي مع التبديل الذكي للمفاتيح
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("جاري التحليل وبناء اللوحة..."):
            success = False
            attempts = 0
            max_attempts = len(api_keys)
            
            while not success and attempts < max_attempts:
                try:
                    response = st.session_state.chat_session.send_message(user_input)
                    message_placeholder.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    success = True
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # معالجة أخطاء تخطي الحصة اليومية للمفتاح (Quota أو Rate limit)
                    if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                        attempts += 1
                        if attempts < max_attempts:
                            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(api_keys)
                            st.toast(f"🔄 نفد رصيد المفتاح.. جاري التبديل للمفتاح رقم {st.session_state.current_key_index + 1}", icon="♻️")
                            st.session_state.chat_session = create_chat_session(exclude_last_msg=True)
                        else:
                            message_placeholder.error("⚠️ انتهت الحصة (Quota) في جميع المفاتيح المتاحة.")
                            break
                            
                    # معالجة أخطاء الضغط المؤقت على خوادم جوجل (503)
                    elif "503" in error_msg or "high demand" in error_msg:
                        message_placeholder.warning("⏳ خوادم الذكاء الاصطناعي عليها ضغط عالٍ حالياً. يرجى المحاولة بعد قليل.")
                        break
                        
                    # أي أخطاء أخرى غير متوقعة
                    else:
                        message_placeholder.error(f"⚠️ عذراً، حدث خطأ غير متوقع: {str(e)}")
                        break
