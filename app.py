import asyncio
import io
import os
import re
import edge_tts
import pdfplumber
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="🎙️ AI 소방 팟캐스트 & 오디오북 스튜디오",
    page_icon="🎧",
    layout="centered",
)


# 1. 텍스트 구어체 및 소방 단위 정제
def preprocess_text(raw_text):
  text = raw_text

  # 헤더/푸터 및 쪽 번호 제거
  text = re.sub(r'한국산업인력공단|청렴\s*한\s*세상|안전\s*한\s*세상', '', text)
  text = re.sub(r'-\s*\d+\s*-', '', text)
  text = re.sub(
      r'Page\s*\d+(\s*of\s*\d+)?', '', text, flags=re.IGNORECASE
  )
  text = re.sub(r'\\(\s*\d+\s*-\s*\d+\s*\\)', '', text)

  # 공고 및 법령 부칙 행정 문구 제거
  text = re.sub(r'\\[시행\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\\]', '', text)
  text = re.sub(r'\\[국립소방연구원공고[^\\]]*\]', '', text)
  text = re.sub(
      r'<\s*개정\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*>', '', text
  )
  text = re.sub(
      r'<\s*신설\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*>', '', text
  )

  # 문제 및 원문자 처리
  text = re.sub(r'【\s*문제\s*(\d+)\s*】', r'문제 \1번.', text)
  text = re.sub(r'\\((가|나|다|라|마|바|사|아)\\)', r'\1번, ', text)

  # 소방 기술 단위 및 원문자 한글화
  replacements = {
      'm³': '세제곱미터',
      'm3': '세제곱미터',
      '㎡': '제곱미터',
      'm2': '제곱미터',
      'kPa': '킬로파스칼',
      'MPa': '메가파스칼',
      'ℓ': '리터',
      'dB': '데시벨',
      '℃': '섭씨',
      '~': '에서 ',
      '①': '첫째, ',
      '②': '둘째, ',
      '③': '셋째, ',
      '④': '넷째, ',
      '⑤': '다섯째, ',
      '⑥': '여섯째, ',
      '⑦': '일곱째, ',
      '⑧': '여덟째, ',
      '⑨': '아홉째, ',
      '⑩': '열째, ',
  }
  for orig, rep in replacements.items():
    text = text.replace(orig, rep)

  # 문장 중간의 어색한 줄바꿈(\n) 잇기
  text = re.sub(r'(?<![\.\?!\:\n])\n(?![\n\d·①-⑩])', ' ', text)

  # 다중 공백 정리
  text = re.sub(r'[*\t#_]', ' ', text)
  text = re.sub(r'\s+', ' ', text).strip()
  return text


# 2. PDF 텍스트 추출
def extract_pdf_text(uploaded_file):
  full_text = []
  with pdfplumber.open(uploaded_file) as pdf:
    for page in pdf.pages:
      txt = page.extract_text()
      if txt:
        full_text.append(txt)
  return preprocess_text('\n\n'.join(full_text))


# 3. Smart 팟캐스트 대화 파싱 (2인 멀티 스피커 및 자동 교체)
def parse_podcast_dialogue(text, female_voice, male_voice):
  lines = [l.strip() for l in text.split('\n') if l.strip()]
  dialogue = []
  current_voice = female_voice

  female_pattern = (
      r'^\s*[\\[\\(]?\s*(진행자|MC|아나운서|질문|Q|User)\s*[\\]\\)]?\s*[:\.]?\s*'
  )
  male_pattern = (
      r'^\s*[\\[\\(]?\s*(전문가|소방기술사|답변|게스트|A|AI)\s*[\\]\\)]?\s*[:\.]?\s*'
  )

  # 대본 전체에 화자 태그([진행자], [전문가], Q:, A: 등)가 있는지 검사
  has_speaker_tags = any(
      re.search(female_pattern, l, re.IGNORECASE)
      or re.search(male_pattern, l, re.IGNORECASE)
      for l in lines
  )

  # 태그가 없으면 문단/줄 단위로 여성과 남성이 자동으로 교대
  if not has_speaker_tags:
    for idx, line in enumerate(lines):
      v = female_voice if idx % 2 == 0 else male_voice
      cleaned_line = preprocess_text(line)
      if cleaned_line:
        dialogue.append((v, cleaned_line))
    return dialogue

  # 태그가 있으면 지정된 화자에 맞게 목소리 전환 및 태그 제거
  for line in lines:
    if re.search(female_pattern, line, re.IGNORECASE):
      current_voice = female_voice
      content = re.sub(female_pattern, '', line, flags=re.IGNORECASE)
      content = preprocess_text(content)
      if content:
        dialogue.append((current_voice, content))
    elif re.search(male_pattern, line, re.IGNORECASE):
      current_voice = male_voice
      content = re.sub(male_pattern, '', line, flags=re.IGNORECASE)
      content = preprocess_text(content)
      if content:
        dialogue.append((current_voice, content))
    else:
      cleaned_content = preprocess_text(line)
      if cleaned_content:
        dialogue.append((current_voice, cleaned_content))

  return dialogue


# 4. Async edge-tts 병합 생성
async def generate_podcast_audio(dialogue, rate_str):
  combined_data = bytearray()

  for voice, chunk_text in dialogue:
    if not chunk_text.strip():
      continue
    communicate = edge_tts.Communicate(chunk_text, voice, rate=rate_str)
    async for chunk in communicate.stream():
      if chunk['type'] == 'audio':
        combined_data.extend(chunk['data'])

  return bytes(combined_data)


# --- Streamlit UI ---
st.title('🎙️ AI 소방 팟캐스트 & 오디오북 스튜디오')
st.caption(
    '1인 낭독 오디오북부터 [진행자]/[전문가] 2인 대화형 팟캐스트까지 자연스럽게'
    ' 생성합니다.'
)

tab1, tab2 = st.tabs(
    ['✍️ 대본 직접 입력 (팟캐스트 모드 지원)', '📄 PDF 파일 업로드']
)
script_text = ''

with tab1:
  st.info(
      '💡 **2인 팟캐스트 팁**: 문장 앞에 `[진행자]`, `[전문가]` (또는 `질문:`, `답변:`)를'
      ' 붙이시면 더 정확하게 대화가 구분됩니다. 태그가 없어도 문단별로 알아서'
      ' 번갈아가며 읽어 드립니다!'
  )
  user_input = st.text_area(
      '📋 팟캐스트/오디오북 대본:',
      height=280,
      placeholder=(
          '[진행자]: 안녕하세요! 오늘 알아볼 화재안전기준은 무엇인가요?\n[전문가]:'
          ' 네, 오늘은 소화기구의 핵심 설치기준인 20미터와 30미터 보행거리에'
          ' 대해 알아보겠습니다.'
      ),
  )
  if user_input.strip():
    script_text = user_input.strip()

with tab2:
  uploaded_file = st.file_uploader('📖 PDF 파일:', type=['pdf'])
  if uploaded_file and st.button('🔍 PDF 텍스트 추출'):
    st.session_state['pdf_text'] = extract_pdf_text(uploaded_file)
    st.success('PDF 텍스트 정제 완료!')

  if 'pdf_text' in st.session_state:
    script_text = st.session_state['pdf_text']
    with st.expander('🔍 추출된 대본 보기'):
      st.write(script_text[:1000] + '...')

st.write('---')
col1, col2 = st.columns(2)
with col1:
  mode = st.radio(
      '🎧 낭독 모드:',
      ['1인 단독 낭독', '2인 팟캐스트 대화 모드'],
      horizontal=True,
  )
with col2:
  speed = st.select_slider(
      '⚡ 낭독 속도:', options=['-10%', '-5%', '-3%', '0%', '+5%'], value='-3%'
  )

female_v = 'ko-KR-SunHiNeural'
male_v = 'ko-KR-InJoonNeural'

if st.button('🚀 팟캐스트 오디오 생성하기', type='primary'):
  if not script_text:
    st.warning('⚠️ 대본을 입력하거나 PDF를 업로드해 주세요!')
  else:
    with st.spinner('🎙️ AI 신경망 목소리로 팟캐스트 오디오를 생성 중입니다...'):
      if mode == '2인 팟캐스트 대화 모드':
        dialogue = parse_podcast_dialogue(script_text, female_v, male_v)
      else:
        dialogue = [(female_v, preprocess_text(script_text))]

      audio_bytes = asyncio.run(generate_podcast_audio(dialogue, speed))
      st.session_state['generated_audio'] = audio_bytes

if 'generated_audio' in st.session_state:
  st.success('🎉 팟캐스트 오디오북 생성 완료!')
  st.audio(st.session_state['generated_audio'], format='audio/mp3')
  st.download_button(
      label='📥 MP3 팟캐스트 다운로드',
      data=st.session_state['generated_audio'],
      file_name='소방시설관리사_팟캐스트.mp3',
      mime='audio/mp3',
  )
