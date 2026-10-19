import os
import requests
import streamlit as st
from google import genai
from google.genai import types

# 페이지 설정
st.set_page_config(
    page_title="맞춤형 AI 팟캐스트 제작기", page_icon="🎙️", layout="wide"
)

st.title("🎙️ 잡담 없는 맞춤형 AI 팟캐스트 메이커")
st.markdown(
    "방송 대본이나 학습 노트를 입력하면 **잡담을 배제**하고 핵심만 짚어주는 남녀"
    " 2인 대화 스크립트로 각색한 뒤, 고품질 음성(TTS)으로 변환합니다."
)

# 사이드바 설정 (API 키 입력)
with st.sidebar:
  st.header("🔑 API 설정")
  gemini_api_key = st.text_input("Gemini API Key", type="password")
  eleven_api_key = st.text_input("ElevenLabs API Key", type="password")

  st.markdown("---")
  st.markdown("### 🗣️ ElevenLabs 목소리 ID 설정")
  # 주석을 괄호 밖으로 완전히 분리하여 문법 오류 해결
  male_voice_id = st.text_input(
      "남성 호스트 Voice ID (예: Adam)", value="pNInz6obpgDQGcFmaJgB"
  )
  female_voice_id = st.text_input(
      "여성 호스트 Voice ID (예: Rachel)", value="21m00Tcm4TlvDq8ikWAM"
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
          "너는 전문 시사/학술 팟캐스트 작가다. 제공된 자료를 바탕으로 남녀 호스트가"
          " 주고받는 2인 팟캐스트 대본을 작성하라.\n\n[규칙]\n1. 오프닝 멘트나 날씨"
          " 이야기 같은 무의미한 잡담, 농담, 감탄사는 절대 금지한다. 첫 마디부터 바로"
          " 본론의 핵심 논점으로 진입할 것.\n2. 남성 호스트(민준)는 질문과 구조적 허점을"
          " 찌르는 역할을 하고, 여성 호스트(서연)는 논리적 근거와 이론적 팩트를 바탕으로"
          " 명쾌하게 해설하는 역할을 맡는다.\n3. 대화의 호흡은 빠르게 가져가며, 반드시"
          " 제공된 텍스트/팩트에만 기반할 것.\n4. 출력 형식은 반드시 아래와 같이 지정된"
          " 화자 이름으로 시작할 것:\n[남성]: ...\n[여성]: ..."
      ),
  )

# 변환 실행 버튼
if st.button("🚀 팟캐스트 대본 생성 및 오디오 제작", type="primary"):
  if not gemini_api_key:
    st.error("Gemini API Key를 입력해주세요.")
    st.stop()
  if not source_text.strip():
    st.error("변환할 원본 텍스트를 입력해주세요.")
    st.stop()

  # 1단계: Gemini를 이용해 잡담 없는 대본 각색
  with st.spinner(
      "Gemini가 잡담을 배제하고 밀도 높은 대화 대본으로 각색 중입니다..."
  ):
    try:
      client = genai.Client(api_key=gemini_api_key)
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=f"다음 텍스트를 바탕으로 대본을 만들어줘:\n\n{source_text}",
          config=types.GenerateContentConfig(
              system_instruction=system_instruction, temperature=0.3
          ),
      )
      script_result = response.text
    except Exception as e:
      st.error(f"Gemini API 오류 발생: {e}")
      st.stop()

  st.subheader("📝 각색된 대화 스크립트")
  st.markdown(script_result)

  # 2단계: ElevenLabs 연동 (선택 사항)
  if eleven_api_key:
    st.subheader("🎧 음성(TTS) 생성 결과")
    with st.spinner(
        "ElevenLabs를 통해 남녀 대화 오디오를 렌더링 중입니다..."
    ):
      try:
        # 간단한 파싱 예시 ([남성]: / [여성]: 턴을 나누어 처리)
        lines = script_result.split("\n")
        audio_segments = []

        for line in lines:
          if line.startswith("[남성]"):
            text_to_speak = line.replace("[남성]:", "").strip()
            voice_id = male_voice_id
          elif line.startswith("[여성]"):
            text_to_speak = line.replace("[여성]:", "").strip()
            voice_id = female_voice_id
          else:
            continue

          if not text_to_speak:
            continue

          # ElevenLabs API 호출
          url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
          headers = {
              "Accept": "audio/mpeg",
              "Content-Type": "application/json",
              "xi-api-key": eleven_api_key,
          }
          data = {
              "text": text_to_speak,
              "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
          }

          res = requests.post(url, json=data, headers=headers)
          if res.status_code == 200:
            audio_segments.append(res.content)
          else:
            st.warning(
                f"음성 생성 실패 일부 구간 생략 (Status: {res.status_code})"
            )

        # 오디오 세그먼트 합치기 (바이트 단위 결합)
        if audio_segments:
          full_audio_bytes = b"".join(audio_segments)
          st.audio(full_audio_bytes, format="audio/mp3")
          st.success("오디오 생성 완료! 플레이 버튼을 눌러 들어보세요.")
        else:
          st.warning(
              "대본에서 화자 패턴([남성]/[여성])을 찾지 못해 음성을 생성하지"
              " 못했습니다."
          )

      except Exception as e:
        st.error(f"ElevenLabs API 연동 중 오류 발생: {e}")
  else:
    st.info(
        "💡 ElevenLabs API 키를 입력하시면 음성(TTS) 오디오 파일까지 자동으로"
        " 생성하실 수 있습니다."
    )
