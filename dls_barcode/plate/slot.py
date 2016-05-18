EMPTY_SLOT_SYMBOL = "----EMPTY----"
NOT_FOUND_SLOT_SYMBOL = '-CANT-FIND-'


class Slot:
    """ Represents a single pin slot in a sample holder.
    """
    NO_RESULT = 0
    EMPTY = 1
    UNREADABLE = 2
    VALID = 3

    def __init__(self, number):
        self._number = number
        self._bounds = None
        self._barcode_position = None
        self._barcode = None
        self._empty = False

        self._total_frames = 0
        self._barcode_set_this_frame = False

    def new_frame(self):
        """ Call this at the start of a new frame before setting anything. """
        self._total_frames += 1
        self._barcode_set_this_frame = False

    def number(self):
        """ Get the slot number. """
        return self._number

    def bounds(self):
        """ Get the bounds ((x,y), radius) of the slot (as determined by the geometry). """
        return self._bounds

    def barcode_position(self):
        """ Get the position (x,y) of the center of the barcode (not exactly the same as the
        bounds center as predicted by the geometry. """
        return self._barcode_position

    def barcode_this_frame(self):
        """ True if the barcode has been set this frame. """
        return self._barcode_set_this_frame

    def set_bounds(self, bounds):
        self._bounds = bounds

    def set_barcode_position(self, coord):
        self._barcode_position = coord

    def set_barcode(self, barcode):
        self._barcode = barcode
        if barcode is not None:
            self._empty = False
            self._barcode_set_this_frame = True

    def set_empty(self):
        self._barcode = None
        self._empty = True

    def set_no_result(self):
        self._barcode = None
        self._empty = False

    def state(self):
        if self._empty:
            return Slot.EMPTY
        elif self._barcode and self._barcode.is_unreadable():
            return Slot.UNREADABLE
        elif self._barcode and self._barcode.is_valid():
            return Slot.VALID
        else:
            return Slot.NO_RESULT

    def contains_barcode(self):
        state = self.state()
        return state == Slot.UNREADABLE or state == Slot.VALID

    def barcode_data(self):
        """ Gets a string representation of the barcode data; returns an empty
        string if slot is empty
        """
        if self._empty:
            return EMPTY_SLOT_SYMBOL
        elif self._barcode is not None:
            return self._barcode.data()
        else:
            return NOT_FOUND_SLOT_SYMBOL