# hardware_controller.py

import time
import numpy as np
import os

# --- 이 섹션은 라즈베리파이에서 사용됩니다 ---
# 라즈베리파이에 배포할 때 아래 줄의 주석을 해제하세요.
# import RPi.GPIO as GPIO
# from picamera2 import Picamera2, Preview
# ---------------------------------------------------------


class BaseController:
    """
    모든 하드웨어 컨트롤러의 인터페이스를 정의하는 기본 클래스입니다.
    이를 통해 목(Mock) 컨트롤러와 실제 컨트롤러가 동일한 메서드를 갖도록 보장합니다.
    """

    def setup(self):
        raise NotImplementedError

    def set_room_light(self, state):
        raise NotImplementedError

    def set_dimmable_light(self, brightness):
        raise NotImplementedError

    def set_mood_lamp_color(self, r, g, b):
        raise NotImplementedError

    def read_doorbell(self):
        raise NotImplementedError

    def get_distance(self):
        raise NotImplementedError

    def capture_image(self, output_path):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError


class MockController(BaseController):
    """
    하드웨어 구성 요소를 시뮬레이션하는 목(Mock) 하드웨어 컨트롤러입니다.
    실제 하드웨어 없이 모든 컴퓨터에서 실행됩니다.
    개발 및 테스트에 적합합니다.
    """

    def __init__(self):
        self._room_light_state = False
        self._dimmable_light_brightness = 100
        self._mood_lamp_color = (255, 255, 255)
        self._doorbell_pressed = False
        print("✅ Mock 하드웨어 컨트롤러가 초기화되었습니다.")

    def setup(self):
        print("🔧 Mock 설정: 하드웨어가 시뮬레이션되므로 별도 작업 없음.")
        pass

    def set_room_light(self, state):
        self._room_light_state = state
        status = "ON" if state else "OFF"
        print(f"💡 Mock 거실 조명 -> {status}")

    def set_dimmable_light(self, brightness):
        self._dimmable_light_brightness = brightness
        print(f"💡 Mock 밝기 조절 조명 -> 밝기 {brightness}%")

    def set_mood_lamp_color(self, r, g, b):
        self._mood_lamp_color = (r, g, b)
        print(f"🎨 Mock 무드 램프 -> 색상 ({r}, {g}, {b})")

    def read_doorbell(self):
        # 실제 시나리오에서는 핀을 읽지만, 여기서는 시뮬레이션합니다.
        # 웹 UI의 버튼으로 이 상태를 토글할 수 있습니다.
        return self._doorbell_pressed

    def get_distance(self):
        # 약간의 노이즈를 포함하여 거리 센서를 시뮬레이션합니다.
        base_distance = 80
        noise = np.random.uniform(-1.5, 1.5)
        return round(base_distance + noise, 1)

    def capture_image(self, output_path):
        # 플레이스홀더 이미지 경로를 반환합니다.
        placeholder_path = os.path.join("assets", "placeholder.jpg")
        if os.path.exists(placeholder_path):
            # 실제 앱에서는 이 파일을 output_path로 복사해야 합니다.
            print(f"📸 Mock 카메라 -> {placeholder_path}의 플레이스홀더 사용")
            return placeholder_path
        else:
            print("오류: assets/placeholder.jpg 에서 플레이스홀더 이미지를 찾을 수 없습니다.")
            return None

    def cleanup(self):
        print("🧹 Mock 정리: 별도 작업 없음.")
        pass


class RaspberryPiController(BaseController):
    """
    라즈베리파이를 위한 실제 하드웨어 컨트롤러입니다.
    RPi.GPIO와 picamera2를 사용하여 실제 하드웨어를 제어합니다.

    참고: 이 코드는 제공된 마크다운 문서를 기반으로 하며,
    다음과 같은 핀 연결을 가정합니다:
    - 거실 조명 (LED): GPIO 12 (물리적 핀 32)
    - 밝기 조절 조명 (PWM LED): 예제를 위해 GPIO 12 공유
    - RGB LED: Red=GPIO 18, Green=GPIO 23, Blue=GPIO 24
    - 초인종 (Push Button): GPIO 25
    - 초음파 센서: Trig=GPIO 22, Echo=GPIO 27
    """

    def __init__(self):
        # 제공된 문서 기반 GPIO 핀 매핑 (BCM 모드 기준)
        self.LED_PIN = 12  # 거실 조명 (물리적 핀 32)
        self.BTN_PIN = 25  # 초인종 버튼 (물리적 핀 22)
        self.TRIG_PIN = 22  # 초음파 Trig (물리적 핀 15)
        self.ECHO_PIN = 27  # 초음파 Echo (물리적 핀 13)

        self.R_PIN = 18  # RGB Red (물리적 핀 12)
        self.G_PIN = 23  # RGB Green (물리적 핀 16)
        self.B_PIN = 24  # RGB Blue (물리적 핀 18)

        self.pwm_led = None
        self.pwm_r = None
        self.pwm_g = None
        self.pwm_b = None

        self.picam2 = None
        print("✅ 라즈베리파이 하드웨어 컨트롤러가 초기화되었습니다.")

    def setup(self):
        print("🔧 라즈베리파이 설정: GPIO 핀 구성 중...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # 거실 조명 & 밝기 조절 조명 (핀 공유)
        GPIO.setup(self.LED_PIN, GPIO.OUT)
        self.pwm_led = GPIO.PWM(self.LED_PIN, 500)  # 500 Hz 주파수
        self.pwm_led.start(0)  # 꺼진 상태에서 시작

        # RGB 무드 램프
        GPIO.setup([self.R_PIN, self.G_PIN, self.B_PIN], GPIO.OUT)
        self.pwm_r = GPIO.PWM(self.R_PIN, 100)
        self.pwm_g = GPIO.PWM(self.G_PIN, 100)
        self.pwm_b = GPIO.PWM(self.B_PIN, 100)
        self.pwm_r.start(0)
        self.pwm_g.start(0)
        self.pwm_b.start(0)

        # 초인종 버튼
        GPIO.setup(self.BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # 초음파 센서
        GPIO.setup(self.TRIG_PIN, GPIO.OUT)
        GPIO.setup(self.ECHO_PIN, GPIO.IN)

        # 파이 카메라
        self.picam2 = Picamera2()
        config = self.picam2.create_still_configuration()
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1)  # 카메라 예열 시간
        print("✅ GPIO 및 카메라 설정 완료.")

    def set_room_light(self, state):
        # 단순 켜고 끄기를 위해 듀티 사이클을 100% 또는 0%로 설정
        brightness = 100 if state else 0
        self.pwm_led.ChangeDutyCycle(brightness)
        status = "ON" if state else "OFF"
        print(f"💡 거실 조명 -> {status}")

    def set_dimmable_light(self, brightness):
        self.pwm_led.ChangeDutyCycle(brightness)
        print(f"💡 밝기 조절 조명 -> 밝기 {brightness}%")

    def set_mood_lamp_color(self, r, g, b):
        # 0-255 색상 값을 0-100 듀티 사이클로 변환
        self.pwm_r.ChangeDutyCycle(r / 255.0 * 100)
        self.pwm_g.ChangeDutyCycle(g / 255.0 * 100)
        self.pwm_b.ChangeDutyCycle(b / 255.0 * 100)
        print(f"🎨 무드 램프 -> 색상 ({r}, {g}, {b})")

    def read_doorbell(self):
        # PUD_UP 설정으로 인해 버튼이 눌리면 GPIO 핀이 LOW 상태가 됨
        return GPIO.input(self.BTN_PIN) == GPIO.LOW

    def get_distance(self):
        GPIO.output(self.TRIG_PIN, False)
        time.sleep(0.5)

        GPIO.output(self.TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG_PIN, False)

        while GPIO.input(self.ECHO_PIN) == 0:
            pulse_start = time.time()

        while GPIO.input(self.ECHO_PIN) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # 음속 (34300 cm/s) / 2
        return round(distance, 2)

    def capture_image(self, output_path):
        self.picam2.capture_file(output_path)
        print(f"📸 카메라 -> 이미지가 {output_path}에 저장됨")
        return output_path

    def cleanup(self):
        print("🧹 GPIO 핀 정리 중...")
        self.pwm_led.stop()
        self.pwm_r.stop()
        self.pwm_g.stop()
        self.pwm_b.stop()
        GPIO.cleanup()
        self.picam2.stop()
        print("✅ 정리 완료.")
