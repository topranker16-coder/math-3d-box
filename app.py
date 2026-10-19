import asyncio
import os
import tempfile
import time
import edge_tts
from google import genai
from google.genai import types
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="맞춤형 AI 팟캐스트 제작기", page_icon="🎙️", layout="wide"
)

st.title("🎙️ 잡담 없는 맞춤형 AI 팟캐스트 메이커 (100% 무료)")
st.markdown(
    "방송 대본을 입력하면 **Gemini**가 핵심 대화 스크립트로 각색하고, **MS"
    " Edge 무료 음성 엔진**이 남녀 대화 오디오로 즉시 변환해 드립니다."
)

# 사이드바 설정
with st.sidebar:
  st.header("🔑 API 설정")
  gemini_api_key = st.text_input("Gemini API Key (무료)", type="password")
  st.info(
      "💡 Gemini API 키 하나만 넣으면 끝납니다! 음성 생성(TTS)은 API 키가 전혀"
      " 필요 없는 MS Edge 무료 음성을 사용합니다."
  )

  st.markdown("---")
  st.markdown("### 🗣️ 한국어 성우 선택")
  male_voice = st.selectbox(
      "남성 성우 목소리",
      options=["ko-KR-InJoonNeural", "ko-KR-BongJinNeural"],
      index=0,
  )
  female_voice = st.selectbox(
      "여성 성우 목소리",
      options=["ko-KR-SunHiNeural", "ko-KR-JiMinNeural"],
      index=0,
  )

# 메인 입력 화면
col1, col2 = st.columns(2)

with col1:
  st.subheader("1. 원본 대본 또는 자료 입력")
  source_text = st.text_area(
      "팟캐스트로 만들고 싶은 방송 대본이나 텍스트를 입력하세요.",
      height=300,
      placeholder="여기에 대본을 붙여넣으세요...",
  )

with col2:
  st.subheader("2. 대본 각색 설정 (프롬프트 규칙)")
  system_instruction = st.text_area(
      "AI 각색 지시어 (System Prompt)",
      height=300,
      value=(
          "너는 전문 시사/학술 팟캐스트 작가다. 제공된 자료를 바탕으로 남녀"
          " 호스트가 주고받는 2인 팟캐스트 대본을 작성하라.\n\n[규칙]\n1."
          " 오프닝 멘트나 날씨 이야기 같은 무의미한 잡담, 농담, 감탄사는 절대"
          " 금지한다. 첫 마디부터 바로 본론의 핵심 논점으로 진입할 것.\n2. 남성"
          " 호스트(민준)는 질문과 구조적 허점을 찌르는 역할을 하고, 여성"
          " 호스트(서연)는 논리적 근거와 이론적 팩트를 바탕으로 명쾌하게 해설하는"
          " 역할을 맡는다.\n3. 반드시 모든 대사의 줄 시작을 [남성]: 또는 [여성]:"
          " 형태로 작성할 것."
      ),
  )


# 긴 문장을 안전하게 잘게 쪼개는 함수
def split_text_into_chunks(text, max_length=150):
  import re

  sentences = re.split(r"(?<=[.?!])\s+", text)
  chunks = []
  current_chunk = ""

  for sentence in sentences:
    if len(current_chunk) + len(sentence) <= max_length:
      current_chunk += " " + sentence
    else:
      if current_chunk:
        chunks.append(current_chunk.strip())
      current_chunk = sentence
  if current_chunk:
    chunks.append(current_chunk.strip())
  return chunks if chunks else [text]


# 동기 방식으로 Edge TTS 오디오를 생성하는 함수
def generate_audio_sync(script_text, male_v, female_v):
  audio_files = []
  lines = script_text.split("\n")

  for line in lines:
    line = line.strip()
    if not line:
      continue

    if line.startswith("[남성]") or line.startswith("남성:"):
      text = (
          line.replace("[남성]:", "")
          .replace("[남성]", "")
          .replace("남성:", "")
          .strip()
      )
      voice = male_v
    elif line.startswith("[여성]") or line.startswith("여성:"):
      text = (
          line.replace("[여성]:", "")
          .replace("[여성]", "")
          .replace("여성:", "")
          .strip()
      )
      voice = female_v
    else:
      continue

    if not text:
      continue

    text_chunks = split_text_into_chunks(text, max_length=120)

    for chunk in text_chunks:
      if not chunk:
        continue
      temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
      temp_file.close()

      communicate = edge_tts.Communicate(chunk, voice)
      import asyncio

      asyncio.run(communicate.save(temp_file.name))
      audio_files.append(temp_file.name)

  combined_audio = b""
  for fpath in audio_files:
    if os.path.exists(fpath):
      with open(fpath, "rb") as f:
        combined_audio += f.read()
      os.remove(fpath)

  return combined_audio


# 변환 실행 버튼
if st.button("🚀 팟캐스트 대본 생성 및 오디오 제작", type="primary"):
  if not gemini_api_key:
    st.error("Gemini API Key를 입력해주세요.")
    st.stop()
  if not source_text.strip():
    st.error("변환할 원본 텍스트를 입력해주세요.")
    st.stop()

  # 1단계: Gemini 대본 각색 (안정적인 gemini-2.5-flash 모델 및 자동 재시도 로직 적용)
  with st.spinner(
      "Gemini가 잡담을 배제하고 밀도 높은 대화 대본으로 각색 중입니다..."
  ):
    script_result = None
    client = genai.Client(api_key=gemini_api_key)

    for attempt in range(5):  # 최대 5회까지 자동 재시도
      try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"다음 텍스트를 바탕으로 대본을 만들어줘:\n\n{source_text}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=0.3
            ),
        )
        script_result = response.text
        break
      except Exception as e:
        if "503" in str(e) and attempt < 4:
          time.sleep(3)  # 503 발생 시 3초 대기 후 재시도
          continue
        else:
          st.error(f"Gemini API 오류 발생: {e}")
          st.stop()

  st.subheader("📝 각색된 대화 스크립트")
  st.markdown(script_result)

  # 2단계: Edge TTS 음성 생성
  st.subheader("🎧 음성(TTS) 생성 결과")
  with st.spinner(
      "MS Edge 무료 음성 엔진으로 대화 오디오를 렌더링 중입니다..."
  ):
    try:
      audio_bytes = generate_audio_sync(script_result, male_voice, female_voice)

      if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
        st.success("🎉 오디오 생성 완료! 플레이 버튼을 눌러 들어보세요.")
      else:
        st.warning(
            "대본에서 화자 패턴([남성]/[여성])을 찾지 못했습니다. 다시"
            " 시도해주세요."
        )

    except Exception as e:
      st.error(f"음성 생성 중 오류 발생: {e}")
