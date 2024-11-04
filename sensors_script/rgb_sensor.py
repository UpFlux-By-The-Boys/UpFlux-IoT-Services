"""
module for reading color RGB values using TCS3200 Color Sensor and activating a buzzer based on specific RGB values. DETECT WHITE
"""
import RPi.GPIO as GPIO
import time
import logging
import json

LOG_FILE = '/var/log/upflux/upflux-sensors.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

S0_PIN = 18
S1_PIN = 15
OE_PIN = 14
OUT_PIN = 22
S2_PIN = 17
S3_PIN = 27
BUZZER_PIN = 7

NUM_CYCLES = 10 
RED_THRESHOLD = 200
GREEN_THRESHOLD = 200
BLUE_THRESHOLD = 200
 
FREQ_MIN = {'red': 500, 'green': 500, 'blue': 500}
FREQ_MAX = {'red': 2000, 'green': 2000, 'blue': 2000}  

class ColorSensor:
    def __init__(self):
        self.pwm = None
        self.setup_gpio()
        
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(OUT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(S0_PIN, GPIO.OUT)
        GPIO.setup(S1_PIN, GPIO.OUT)
        GPIO.setup(S2_PIN, GPIO.OUT)
        GPIO.setup(S3_PIN, GPIO.OUT)
        GPIO.setup(OE_PIN, GPIO.OUT)
        
        GPIO.output(OE_PIN, GPIO.LOW)
        GPIO.output(S0_PIN, GPIO.HIGH)
        GPIO.output(S1_PIN, GPIO.LOW)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

        global pwm
        pwm = GPIO.PWM(BUZZER_PIN, 1000) 
        
    def buzzer_condition(self, red_value, green_value, blue_value):
        return  red_value < RED_THRESHOLD or green_value < GREEN_THRESHOLD or blue_value < BLUE_THRESHOLD

    def activate_buzzer(self):
        pwm.start(50)  
        time.sleep(1)  
        pwm.stop()
    
    def map_frequency_to_rgb(self, freq, color):
        """
        maps the frequency measured by sensor to an a RGB value(0 - 255).
        frequency is constrained between max and min rounds
        """
        freq_min = FREQ_MIN[color]
        freq_max = FREQ_MAX[color]
        freq = max(freq_min, min(freq, freq_max))
        rgb_value = int((freq - freq_min) / (freq_max - freq_min) * 255)
        return rgb_value
    
    def measure_color_frequency(self, color):
        """
        measure the frequency for a color by configuring the sensor's filter
        and counting the number of pulses within a time frame  
        """
        if color == 'red':
            GPIO.output(S2_PIN, GPIO.LOW)
            GPIO.output(S3_PIN, GPIO.LOW)
        elif color == 'blue':
            GPIO.output(S2_PIN, GPIO.LOW)
            GPIO.output(S3_PIN, GPIO.HIGH)
        elif color == 'green':
            GPIO.output(S2_PIN, GPIO.HIGH)
            GPIO.output(S3_PIN, GPIO.HIGH)

        time.sleep(0.3)  
        start = time.time()
        for _ in range(NUM_CYCLES):
            GPIO.wait_for_edge(OUT_PIN, GPIO.FALLING)
        duration = time.time() - start
        frequency = NUM_CYCLES / duration
        return frequency

    def loop(self):
        while True:
            try:
                red_freq = self.measure_color_frequency('red')
                red_value = self.map_frequency_to_rgb(red_freq, 'red')
                #print(f"Red frequency: {red_freq} Hz -> RGB value: {red_value}")

                blue_freq = self.measure_color_frequency('blue')
                blue_value = self.map_frequency_to_rgb(blue_freq, 'blue')
                #print(f"Blue frequency: {blue_freq} Hz -> RGB value: {blue_value}")

                green_freq = self.measure_color_frequency('green')
                green_value = self.map_frequency_to_rgb(green_freq, 'green')
                #print(f"Green frequency: {green_freq} Hz -> RGB value: {green_value}")

                #print(f"RGB Values -> {red_value}, {green_value}, {blue_value}")
                
                # Create a dictionary with the RGB values
                sensor_data = {
                    "red_value": red_value,
                    "green_value": green_value,
                    "blue_value": blue_value
                }

                # Output the JSON-formatted sensor data
                print(json.dumps(sensor_data), flush=True)

                # Log the sensor data if needed
                logging.info(f"RGB Values -> R: {red_value}, G: {green_value}, B: {blue_value}")

                if self.buzzer_condition(red_value, green_value, blue_value):
                    #print("Buzzer activated")
                    logging.error(
                        f"buzzer activated due to Invalid Color"
                        f"(R > {RED_THRESHOLD}, G < {GREEN_THRESHOLD}, B < {BLUE_THRESHOLD})"
                    )
                    self.activate_buzzer()
                else:
                    logging.info("Valid color detected")
                    
                time.sleep(2)

            except Exception as e:
                logging.error(f"error occurred: {e}", exc_info=True)
                time.sleep(1)

    def cleanup(self):
        GPIO.cleanup()
        logging.info("RGB sensor shutdown")


def main():
    sensor = ColorSensor()
    try:
        sensor.loop()
    except KeyboardInterrupt:
        logging.info("Program interrupted")
    finally:
        sensor.cleanup()

if __name__ == '__main__':
    main()
