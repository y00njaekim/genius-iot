# 🏠_Home_Dashboard.py

import streamlit as st
import time
from hardware_controller import MockController, RaspberryPiController
import platform
import os

# --- 페이지 설정 ---
st.set_page_config(page_title="스마트 홈 대시보드", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")


# --- 하드웨어 초기화 ---
# 이 부분이 핵심입니다: 라즈베리파이에서 실행 중인지 확인합니다.
# 맞으면 RaspberryPiController를, 아니면 MockController를 사용합니다.
def get_controller():
    # 파이에서 실행 중인지 확인하는 간단한 방법은 플랫폼을 확인하는 것입니다.
    is_pi = platform.machine().startswith("arm") or platform.machine().startswith("aarch64")

    # 테스트용: 아래와 같이 컨트롤러를 강제로 지정할 수 있습니다.
    # return MockController()

    if is_pi:
        try:
            # 이 import는 RPi.GPIO 라이브러리가 설치된 파이에서만 성공합니다.
            import RPi.GPIO
            from picamera2 import Picamera2

            return RaspberryPiController()
        except (ImportError, RuntimeError):
            st.warning("라즈베리파이 하드웨어를 초기화할 수 없습니다. Mock 컨트롤러로 대체합니다.")
            return MockController()
    else:
        return MockController()


# 컨트롤러를 초기화하고 세션 상태에 저장하여 매 상호작용마다
# 다시 초기화되는 것을 방지합니다.
if "hw_controller" not in st.session_state:
    st.session_state.hw_controller = get_controller()
    st.session_state.hw_controller.setup()

# 컨트롤러를 위한 짧은 별칭 생성
hw = st.session_state.hw_controller


# --- 헬퍼 함수 ---
def hex_to_rgb(hex_color):
    """헥스(hex) 색상 문자열을 (R, G, B) 튜플로 변환합니다."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


# --- UI 레이아웃 ---

# 헤더
st.title("🏠 스마트 홈 대시보드")
st.markdown("연결된 홈 디바이스를 제어하고 모니터링하세요.")

# --- 디바이스 제어 ---
col1, col2 = st.columns(2)

# --- 컬럼 1: 조명 제어 ---
with col1:
    st.header("💡 조명")

    # 거실 조명 (단일 LED로 표현)
    with st.container(border=True):
        st.subheader("거실 조명")
        # 'room_light_toggle' 키는 위젯의 상태를 저장합니다.
        is_on = st.toggle("켜기/끄기", key="room_light_toggle")
        hw.set_room_light(is_on)
        if isinstance(hw, MockController):
            st.info("이 기능은 GPIO 핀으로 제어되는 단일 LED에 해당합니다.")

    # 밝기 조절 조명 (PWM 제어 LED로 표현)
    with st.container(border=True):
        st.subheader("침실 조명 밝기")
        brightness = st.slider("밝기", min_value=0, max_value=100, value=100, step=1, key="dimmable_light_slider")
        hw.set_dimmable_light(brightness)
        if isinstance(hw, MockController):
            st.info("이 기능은 PWM(펄스 폭 변조)을 사용하여 LED 밝기를 제어합니다.")

    # 무드 램프 (RGB LED로 표현)
    with st.container(border=True):
        st.subheader("RGB 무드 램프")
        color = st.color_picker("색상 선택", "#FFFFFF", key="mood_lamp_picker")
        r, g, b = hex_to_rgb(color)
        hw.set_mood_lamp_color(r, g, b)
        if isinstance(hw, MockController):
            st.info("이 기능은 3개의 PWM 신호로 RGB LED의 각 채널(Red, Green, Blue)을 제어합니다.")


# --- 컬럼 2: 센서 & 보안 ---
with col2:
    st.header("🔬 센서 & 보안")

    # 초인종 (푸시 버튼으로 표현)
    with st.container(border=True):
        st.subheader("초인종")
        if isinstance(hw, MockController):
            st.info("Mock 모드에서는 아래 버튼을 눌러 초인종 작동을 시뮬레이션할 수 있습니다.")
            if st.button("초인종 누르기 시뮬레이션"):
                # MockController의 내부 상태를 직접 토글
                hw._doorbell_pressed = not hw._doorbell_pressed
                st.rerun()  # 화면을 새로고침하여 상태 업데이트

        if hw.read_doorbell():
            st.success("🔔 **딩동!** 누군가 문 앞에 있습니다!")
        else:
            st.write("문 앞에 아무도 없습니다.")

    # 존재 감지 센서 (초음파 센서로 표현)
    with st.container(border=True):
        st.subheader("차고 감지 센서")
        distance = hw.get_distance()

        # 객체 감지를 위한 임계값 정의
        detection_threshold = 20.0  # cm 단위

        if distance <= detection_threshold:
            st.warning(f"**물체 감지!** 거리: **{distance:.1f} cm**")
        else:
            st.info(f"이상 없음. 거리: **{distance:.1f} cm**")

        # 0.0 ~ 1.0 범위로 값을 정규화하기 위해 100으로 나눕니다.
        progress_value = max(0, 100 - (distance / 3)) / 100.0
        st.progress(progress_value)  # 시각적 프로그레스 바
        if isinstance(hw, MockController):
            st.info("이 기능은 초음파 센서를 사용하여 거리를 측정합니다.")

    # 보안 카메라 (파이 카메라로 표현)
    with st.container(border=True):
        st.subheader("보안 카메라")

        if st.button("스냅샷 찍기 📸"):
            with st.spinner("이미지 캡처 중..."):
                # 이미지 경로 정의
                image_path = "snapshot.jpg"

                # 컨트롤러를 사용하여 이미지 캡처
                captured_path = hw.capture_image(image_path)

                if captured_path and os.path.exists(captured_path):
                    st.image(captured_path, caption="실시간 스냅샷", use_column_width=True)
                else:
                    st.error("이미지를 캡처하지 못했습니다.")
        if isinstance(hw, MockController):
            st.info("이 기능은 파이 카메라 모듈을 사용하여 실시간 이미지를 캡처합니다.")

# --- Footer / 정리 ---
st.sidebar.info("앱 종료 시 GPIO 리소스를 정리하려고 시도합니다.")
