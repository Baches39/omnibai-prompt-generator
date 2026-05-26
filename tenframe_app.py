import streamlit as st
from google import genai
from google.genai import types
from streamlit_local_storage import LocalStorage

# 1. إعدادات شكل صفحة الويب
st.set_page_config(page_title="Tenframe Storyboard Maker", page_icon="🎬", layout="centered")
st.title("🎬 AI Storyboard to Cinematic Video Prompt Generator | المخرج السينيمائي ")
st.write("مولد برومبتات صورة لوحة لقطات - برومبت تحريكها بإحترافية")
st.write("أدخل فكرتك لتوليد برومبت احترافي للصور أو الفيديوهات!")

# 2. إعداد أداة Local Storage للاتصال بمتصفح المستخدم
localS = LocalStorage()

# 3. سحب المفاتيح السرية من Streamlit Secrets
try:
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

# 4. إعداد حالة المتصفح (Session State) للمفاتيح
if "current_key_index" not in st.session_state:
    st.session_state.current_key_index = 0

# --- التعديل هنا: جلب المحادثة من المتصفح بدلاً من تصفيرها ---
if "messages" not in st.session_state:
    # نحاول جلب السجل المحفوظ باسم "chat_history" من متصفح المستخدم
    saved_messages = localS.getItem("chat_history")
    
    # إذا وجدنا رسائل محفوظة (ولم تكن فارغة أو None)، نضعها في الجلسة الحالية
    if saved_messages and isinstance(saved_messages, list):
        st.session_state.messages = saved_messages
    else:
        # إذا كان مستخدماً جديداً، نبدأ بقائمة فارغة
        st.session_state.messages = []

# 5. التعليمات الصارمة (System Instructions)
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
6. CRITICAL FINAL STEP: After the Footer, you MUST add a markdown code block (```) titled "COPY-PASTE PROMPTS". Inside this code block, write the raw image generation prompts for all 10 frames cleanly, separated by newlines, with NO tables and NO markdown formatting. Just pure text ready to be copied.

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

# 6. دالة لإنشاء أو إعادة بناء جلسة الدردشة
def create_chat_session(exclude_last_msg=False):
    current_api_key = api_keys[st.session_state.current_key_index]
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

# إضافة زر لاختياري لمسح المحادثة بالكامل من المتصفح
with st.sidebar:
    if st.button("🗑️ مسح المحادثة بالكامل", use_container_width=True):
        st.session_state.messages = []
        localS.deleteAll()
        st.session_state.chat_session = create_chat_session()
        st.rerun()

# عرض الرسائل السابقة على الشاشة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 7. مربع إدخال المستخدم ومعالجة الأخطاء
user_input = st.chat_input("اكتب فكرتك هنا (مثال: روتين صباحي بنمط POV)...")

if user_input:
    # 1. عرض رسالة المستخدم وإضافتها للسجل ثم حفظها في المتصفح
    st.session_state.messages.append({"role": "user", "content": user_input})
    localS.setItem("chat_history", st.session_state.messages) # حفظ
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. جلب وعرض رد الذكاء الاصطناعي مع التبديل الذكي
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
                    
                    # إضافة رد الذكاء الاصطناعي للسجل وحفظه في المتصفح
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    localS.setItem("chat_history", st.session_state.messages) # تحديث الحفظ
                    
                    success = True
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                        attempts += 1
                        if attempts < max_attempts:
                            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(api_keys)
                            st.toast(f"🔄 نفد رصيد المفتاح.. جاري التبديل للمفتاح رقم {st.session_state.current_key_index + 1}", icon="♻️")
                            st.session_state.chat_session = create_chat_session(exclude_last_msg=True)
                        else:
                            message_placeholder.error("⚠️ انتهت الحصة (Quota) في جميع المفاتيح المتاحة.")
                            break
                    elif "503" in error_msg or "high demand" in error_msg:
                        message_placeholder.warning("⏳ خوادم الذكاء الاصطناعي عليها ضغط عالٍ حالياً. يرجى المحاولة بعد قليل.")
                        break
                    else:
                        message_placeholder.error(f"⚠️ عذراً، حدث خطأ غير متوقع: {str(e)}")
                        break
