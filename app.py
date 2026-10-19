import os
import tempfile
import time
from gtts import gTTS
from google import genai
from google.genai import types
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="맞춤형 AI 팟캐스트 제작기", page_icon="🎙️", layout="wide"
)

st.title("🎙️ 잡담 없는 맞춤형 AI 팟캐스트 메이커 (100% 무료)")
st.markdown(
    "방송 대본을 입력하면 **Gemini**가 핵심 대화 스크립트로 각색하고, **Google TTS"
    " 엔진**이 남녀 대화 오디오로 즉시 변환해 드립니다."
)

# 사이드바 설정
with st.sidebar:
  st.header("🔑 API 설정")
  gemini_api_key = st.text_input("Gemini API Key (무료)", type="password")
  st.info(
      "💡 Gemini API 키 하나만 넣으면 끝납니다! 음성 생성(TTS)은 완전 무료인 Google"
      " TTS를 사용합니다."
  )

  st.markdown("---")
  st.markdown("### 🗣️ 한국어 억양/속도 설정")
  male_tld = st.selectbox(
      "남성 호스트 억양",
      options=["co.kr (한국)", "ca (캐나다/안정적)"],
      index=0,
  )
  female_tld = st.selectbox(
      "여성 호스트 억양", options=["co.kr (한국)", "com (미국/안정적)"], index=0
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


# gTTS 기반 100% 안정적인 오디오 생성 함수
def generate_audio_gtts(script_text, male_tld_val, female_tld_val):
  audio_files = []
  lines = script_text.split("\n")

  male_tld_code = "co.kr" if "co.kr" in male_tld_val else "ca"
  female_tld_code = "co.kr" if "co.kr" in female_tld_val else "com"

  for line in lines:
    line = line.strip()
    if not line:
      continue

    # 화자 판별
    if line.startswith("[남성]") or line.startswith("남성:"):
      text = (
          line.replace("[남성]:", "")
          .replace("[남성]", "")
          .replace("남성:", "")
          .strip()
      )
      tld = male_tld_code
    elif line.startswith("[여성]") or line.startswith("여성:"):
      text = (
          line.replace("[여성]:", "")
          .replace("[여성]", "")
          .replace("여성:", "")
          .strip()
      )
      tld = female_tld_code
    else:
      continue

    if not text:
      continue

    # gTTS 음성 파일 생성
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()

    tts = gTTS(text=text, lang="ko", tld=tld, slow=False)
    tts.save(temp_file.name)
    audio_files.append(temp_file.name)

  # 생성된 음성 파일들 결합
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

  # 1단계: Gemini 대본 각색
  with st.spinner(
      "Gemini가 잡담을 배제하고 밀도 높은 대화 대본으로 각색 중입니다..."
  ):
    script_result = None
    client = genai.Client(api_key=gemini_api_key)

    for attempt in range(5):
      try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"다음 텍스트를 바탕으로 대본을 만들어줘:\n\n{source_text}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=0.3
            ),
        )
        script_result = response.text
        break
      except Exception as e:
        if "503" in str(e) and attempt < 4:
          time.sleep(3)
          continue
        else:
          st.error(f"Gemini API 오류 발생: {e}")
          st.stop()

  st.subheader("📝 각색된 대화 스크립트")
  st.markdown(script_result)

  # 2단계: gTTS 음성 생성
  st.subheader("🎧 음성(TTS) 생성 결과")
  with st.spinner("Google 음성 엔진으로 대화 오디오를 생성 중입니다..."):
    try:
      audio_bytes = generate_audio_gtts(script_result, male_tld, female_tld)

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
