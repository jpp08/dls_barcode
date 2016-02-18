from pkg_resources import require;  require('numpy')
import cv2

import winsound
import time
import multiprocessing

from .image import CvImage
from dls_barcode.plate import Scanner

# TODO: Handle non-full pucks

Q_LIMIT = 1
SCANNED_TAG = "Already Scanned"
EXIT_KEY = 'q'

# Maximum frame rate to sample at (rate will be further limited by speed at which frames can be processed)
MAX_SAMPLE_RATE = 10.0
INTERVAL = 1.0 / MAX_SAMPLE_RATE


class ContinuousScan:
    """ Manages the continuous scanning mode which takes a live feed from an attached camera and
    periodically scans the images for plates and barcodes. Multiple partial images are combined
    together until enough barcodes are scanned to make a full plate.

    Two separate processes are spawned, one to handle capturing and displaying images from the camera,
    and the other to handle processing (scanning) of those images.
    """
    def __init__(self, result_queue):
        """ The task queue is used to store a queue of captured frames to be processed; the overlay
        queue stores Overlay objects which are drawn on to the image displayed to the user to highlight
        certain features; and the result queue is used to pass on the results of successful scans to
        the object that created the ContinuousScan.
        """
        self.task_queue = multiprocessing.Queue()
        self.overlay_queue = multiprocessing.Queue()
        self.result_queue = result_queue

    def stream_camera(self, camera_num):
        """ Spawn the processes that will continuously capture and process images from the camera.
        """
        capture_pool = multiprocessing.Pool(1, capture_worker, (camera_num, self.task_queue, self.overlay_queue,))
        scanner_pool = multiprocessing.Pool(1, scanner_worker, (self.task_queue, self.overlay_queue, self.result_queue,))


def capture_worker(camera_num, task_queue, overlay_queue):
    """ Function used as the main loop of a worker process. Continuously captures images from
    the camera and puts them on a queue to be processed. The images are displayed (as video)
    to the user with appropriate highlights (taken from the overlay queue) which indicate the
    position of scanned and unscanned barcodes.
    """
    # Initialize the camera
    cap = cv2.VideoCapture(camera_num)
    cap.set(3,1920)
    cap.set(4,1080)

    # Store the latest image overlay which highlights the puck
    latest_overlay = Overlay(None)
    last_time = time.time()

    while(True):
        # Capture the next frame from the camera
        _, frame = cap.read()

        # Add the frame to the task queue to be processed
        if task_queue.qsize() < Q_LIMIT and (time.time() - last_time >= INTERVAL):
            # Make a copy of image so the overlay doesn't overwrite it
            task_queue.put(frame.copy())
            last_time = time.time()

        # Get the latest overlay
        while not overlay_queue.empty():
            latest_overlay = overlay_queue.get(False)

        # Draw the overlay on the frame
        latest_overlay.draw_on_image(frame)

        # Display the frame on the screen
        small = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
        cv2.imshow('Barcode Scanner', small)

        # Exit scanning mode if the exit key is pressed
        if cv2.waitKey(1) & 0xFF == ord(EXIT_KEY):
            task_queue.put(None)
            break

    # Clean up camera and kill the worker threads
    cap.release()
    cv2.destroyAllWindows()


def scanner_worker(task_queue, overlay_queue, result_queue):
    """ Function used as the main loop of a worker process. Scan images for barcodes,
    combining partial scans until a full puck is reached.

    Keep the record of the last scan which was at least partially successful (aligned geometry
    and some barcodes scanned). For each new frame, we can attempt to merge the results with
    this previous plates so that we don't have to re-read any of the previously captured barcodes
    (because this is a relatively expensive operation).
    """
    last_plate = None
    last_full_plate = None
    frame_contains_barcodes = False

    while True:
        # Get next image from queue (terminate if a queue contains a 'None' sentinel)
        frame = task_queue.get(True)
        if frame is None:
            break

        timer = time.time()

        # Make grayscale version of image
        cv_image = CvImage(None, frame)
        gray_image = cv_image.to_grayscale().img

        # If we have an existing partial plate, merge the new plate with it and only try to read the
        # barcodes which haven't already been read. This significantly increases efficiency because
        # barcode read is expensive.
        if last_plate is None:
            plate = Scanner.ScanImage(gray_image)
        else:
            plate, frame_contains_barcodes = Scanner.ScanImageContinuous(gray_image, last_plate)

        # Scan must be correctly aligned to be useful
        if plate.scan_ok:
            # Plate mustn't have any barcodes that match the last successful scan
            last_plate = plate
            if last_full_plate and last_full_plate.has_slots_in_common(plate):
                if frame_contains_barcodes:
                    overlay_queue.put(Overlay(None, SCANNED_TAG))
            else:
                # If the plate has the required number of barcodes, store it
                if plate.is_full_valid():
                    Overlay(plate).draw_on_image(cv_image.img)
                    plate.crop_image(cv_image)
                    result_queue.put((plate, cv_image))
                    last_full_plate = plate

                if frame_contains_barcodes:
                    frequency = int(10000 * ((plate.num_slots -plate.num_valid_barcodes) / plate.num_slots)) + 37
                    winsound.Beep(frequency, 200) # frequency, duration
                    overlay_queue.put(Overlay(plate))

        #print("Scan Duration: {0:.3f} secs".format(time.time() - timer))


class Overlay:
    """ Represents an overlay that can be drawn on top of an image. Used to draw the outline of a plate
    on the continuous scanner camera image to highlight to the user which barcodes on th plate have
    already been scanned. Also writes status text messages. Has an specified lifetime so that the overlay
    will only be displayed for a short time.
    """
    def __init__(self, plate, text=None, lifetime=1):
        self._plate = plate
        self._text = text
        self._lifetime = lifetime
        self._start_time = time.time()

    def draw_on_image(self, image):
        """ Draw the plate highlight and status message to the image as well as a message that tells the
        user how to close the continuous scanning window.
        """
        cv_image = CvImage(filename=None, img=image)

        # If the overlay has not expired, draw on the plate highlight and/or the status message
        if (time.time() - self._start_time) < self._lifetime:
            if self._plate is not None:
                self._plate.draw_plate(cv_image, CvImage.BLUE)
                self._plate.draw_pins(cv_image)

            if self._text is not None:
                cv_image.draw_text(SCANNED_TAG, cv_image.center(), CvImage.GREEN, centered=True, scale=4, thickness=3)

        # Displays a message on the screen telling the user how to exit
        exit_msg = "Press '{}' to exit scanning mode".format(EXIT_KEY)
        cv_image.draw_text(exit_msg, (20, 50), CvImage.BLACK, centered=False, scale=1, thickness=2)
