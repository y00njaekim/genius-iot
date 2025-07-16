# hardware_controller.py

import time
import numpy as np
import os


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
        print("✅ Mock hardware controller initialized.")

    def setup(self):
        print("🔧 Mock setup: No action needed as hardware is simulated.")
        pass

    def set_room_light(self, state):
        self._room_light_state = state
        status = "ON" if state else "OFF"
        print(f"💡 Mock Room Light -> {status}")

    def set_dimmable_light(self, brightness):
        self._dimmable_light_brightness = brightness
        print(f"💡 Mock Dimmable Light -> Brightness {brightness}%")

    def set_mood_lamp_color(self, r, g, b):
        self._mood_lamp_color = (r, g, b)
        print(f"🎨 Mock Mood Lamp -> Color ({r}, {g}, {b})")

    def read_doorbell(self):
        # In a real scenario, this would read a pin. We simulate it here.
        # A button in the web UI can toggle this state.
        return self._doorbell_pressed

    def get_distance(self):
        # Simulate the distance sensor with some noise
        base_distance = 80
        noise = np.random.uniform(-1.5, 1.5)
        return round(base_distance + noise, 1)

    def capture_image(self, output_path):
        # Return a placeholder image path.
        placeholder_path = os.path.join("assets", "placeholder.jpg")
        if os.path.exists(placeholder_path):
            # In a real app, this should copy the file to output_path
            print(f"📸 Mock Camera -> Using placeholder at {placeholder_path}")
            return placeholder_path
        else:
            print("Error: Placeholder image not found at assets/placeholder.jpg.")
            return None

    def cleanup(self):
        print("🧹 Mock cleanup: No action needed.")
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
        # --- 라즈베리파이 전용 라이브러리 임포트 ---
        # 이 컨트롤러는 라즈베리파이에서만 인스턴스화되어야 합니다.
        try:
            import RPi.GPIO as GPIO
            from picamera2 import Picamera2
        except (ImportError, RuntimeError) as e:
            print(f"Error: Could not import Raspberry Pi libraries. {e}")
            print("Please ensure this program is running on a Raspberry Pi and not in Mock mode.")
            raise

        self.GPIO = GPIO
        self.Picamera2 = Picamera2
        # -----------------------------------------

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
        print("✅ Raspberry Pi hardware controller initialized.")

    def setup(self):
        print("🔧 Raspberry Pi Setup: Configuring GPIO pins...")
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)

        # 거실 조명 & 밝기 조절 조명 (핀 공유)
        self.GPIO.setup(self.LED_PIN, self.GPIO.OUT)
        self.pwm_led = self.GPIO.PWM(self.LED_PIN, 500)  # 500 Hz 주파수
        self.pwm_led.start(0)  # 꺼진 상태에서 시작

        # RGB 무드 램프
        self.GPIO.setup([self.R_PIN, self.G_PIN, self.B_PIN], self.GPIO.OUT)
        self.pwm_r = self.GPIO.PWM(self.R_PIN, 100)
        self.pwm_g = self.GPIO.PWM(self.G_PIN, 100)
        self.pwm_b = self.GPIO.PWM(self.B_PIN, 100)
        self.pwm_r.start(0)
        self.pwm_g.start(0)
        self.pwm_b.start(0)

        # 초인종 버튼
        self.GPIO.setup(self.BTN_PIN, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)

        # 초음파 센서
        self.GPIO.setup(self.TRIG_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.ECHO_PIN, self.GPIO.IN)

        # 파이 카메라
        try:
            print("📷 Attempting to initialize camera...")
            self.picam2 = self.Picamera2()
            config = self.picam2.create_still_configuration()
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(1)  # Allow camera to warm up
            if self.picam2.started:
                print("✅ Camera started successfully.")
            else:
                print("⚠️ Camera failed to start, but no exception was raised. The button might not be displayed in the UI.")
                self.picam2 = None  # Explicitly set to None for UI checks
        except Exception as e:
            print(f"❌ Critical error during camera setup: {e}")
            print("    Please ensure the camera is connected and enabled correctly.")
            self.picam2 = None  # Explicitly set to None for UI checks

        print("✅ GPIO setup complete.")

    def set_room_light(self, state):
        # Set duty cycle to 100% or 0% for simple on/off
        brightness = 100 if state else 0
        self.pwm_led.ChangeDutyCycle(brightness)
        status = "ON" if state else "OFF"
        print(f"💡 Room Light -> {status}")

    def set_dimmable_light(self, brightness):
        self.pwm_led.ChangeDutyCycle(brightness)
        print(f"💡 Dimmable Light -> Brightness {brightness}%")

    def set_mood_lamp_color(self, r, g, b):
        # Convert 0-255 color values to 0-100 duty cycle
        self.pwm_r.ChangeDutyCycle(r / 255.0 * 100)
        self.pwm_g.ChangeDutyCycle(g / 255.0 * 100)
        self.pwm_b.ChangeDutyCycle(b / 255.0 * 100)
        print(f"🎨 Mood Lamp -> Color ({r}, {g}, {b})")

    def read_doorbell(self):
        # Button press pulls the GPIO pin to LOW due to PUD_UP
        return self.GPIO.input(self.BTN_PIN) == self.GPIO.LOW

    def get_distance(self):
        self.GPIO.output(self.TRIG_PIN, False)
        time.sleep(0.5)

        self.GPIO.output(self.TRIG_PIN, True)
        time.sleep(0.00001)
        self.GPIO.output(self.TRIG_PIN, False)

        while self.GPIO.input(self.ECHO_PIN) == 0:
            pulse_start = time.time()

        while self.GPIO.input(self.ECHO_PIN) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound (34300 cm/s) / 2
        return round(distance, 2)

    def capture_image(self, output_path):
        try:
            self.picam2.capture_file(output_path)
            print(f"📸 Camera -> Image saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Camera Error: Failed to capture image. Error: {e}")
            return None

    def cleanup(self):
        print("🧹 Cleaning up GPIO pins...")
        self.pwm_led.stop()
        self.pwm_r.stop()
        self.pwm_g.stop()
        self.pwm_b.stop()
        self.GPIO.cleanup()
        self.picam2.stop()
        print("✅ Cleanup complete.")
