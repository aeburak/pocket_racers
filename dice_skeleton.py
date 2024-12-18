import cv2
import numpy as np
import RPi.GPIO as GPIO
from threading import Thread
from queue import Queue
import time
from picamera.array import PiRGBArray
from picamera import PiCamera

class PiVideoStream:
    def __init__(self, resolution=(640, 480), framerate=32):
        # initialize the camera and stream
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
            format="bgr", use_video_port=True)
        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.stopped = False


    def start(self):
        # start the thread to read frames from the video stream
        Thread(target=self.update, args=()).start()
        return self
    

    def update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)
            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        # return the frame most recently read
        return self.frame


    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True


print("[INFO] sampling THREADED frames from `picamera` module...")
vs = PiVideoStream(resolution=(640,480)).start()
time.sleep(2.0)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

GPIO.setup(7, GPIO.OUT)
pi_pwm = GPIO.PWM(7, 50)
pi_pwm.start(0)

def output_result(dot_count):
    global pi_pwm
    duty_cycles = range(0, 97, 8)
    try:
        pi_pwm.ChangeDutyCycle(duty_cycles[dot_count])
    except:
        pi_pwm.ChangeDutyCycle(0)

bdp_white = cv2.SimpleBlobDetector_Params()
''' UPDATE THESE PARAMETERS FOR YOUR WHITE DIE BLOB DETECTION '''
bdp_white.filterByArea = False
bdp_white.filterByConvexity = False
bdp_white.filterByCircularity = True
bdp_white.filterByInertia = False
bdp_white.filterByColor = True
bdp_white.blobColor = 0
bdp_white.minCircularity = 0.5
bdp_white.maxCircularity = 1
detector_white = cv2.SimpleBlobDetector_create(bdp_white)

def white_dice(img):
    new_dims = (int(img.shape[1] * 0.4), int(img.shape[0] * 0.4))
    downscale = cv2.resize(img, new_dims)
    greyscale = cv2.cvtColor(downscale, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(greyscale,ksize=(3,3),sigmaX=0)
    threshold = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,85,80)
    #threshold = cv2.threshold(blur,127,255,cv2.THRESH_BINARY)
    #mask = cv2.inRange(blur, (135, 0, 0), (180, 255, 255))
    #threshold = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,55,50)
    erode1 = cv2.erode(threshold, np.ones((4,4), np.uint8), iterations=1)
    dilate1 = cv2.dilate(erode1, np.ones((4,4), np.uint8), iterations=1)
    dilate2 = cv2.dilate(dilate1, np.ones((4,4), np.uint8), iterations=1)
    erode2 = cv2.erode(dilate2, np.ones((4,4), np.uint8), iterations=1)
    points = detector_white.detect(erode2)
    cv2.imshow("Capture", erode2)
    return points

bdp_color = cv2.SimpleBlobDetector_Params()
''' UPDATE THESE PARAMETERS FOR YOUR COLORED DICE BLOB DETECTION '''
bdp_color.filterByColor = False

detector_color = cv2.SimpleBlobDetector_create(bdp_color)

def colored_dice(img):
    ''' YOUR FILTERS GO HERE '''
    return 0

frame_count = 0
try:
    while True:
        result = vs.read()
        frame_count += 1
        img = cv2.rotate(result, cv2.ROTATE_180)

        ''' PART 1 '''

        ''' GENERAL FILTERING '''

        ''' WHITE DIE '''
        points = white_dice(img)
        #print(points)

        ''' COLORED DICE '''
        # points = colored_dice(img)

        # Display the processed image with window title "Capture".
        # Test your filters by adding them directly to this while loop
        # (or creating a new function), then uncommenting the line below:
        
        #cv2.imshow("Capture", img)
 
        # Uncomment these two lines when getting checked off.

        if frame_count % 3 == 0:
             output_result(len(points))
             print(len(points))

        k = cv2.waitKey(3)
        if k == ord('q'):
            # If you press 'q' in the OpenCV window, the program will stop running.
            break
        elif k == ord('p'):
            # If you press 'p', the camera feed will be paused until you press
            # <Enter> in the terminal.
            input()
except KeyboardInterrupt:
    pass

# Clean-up: stop running the camera and close any OpenCV windows
cv2.destroyAllWindows()
vs.stop()
