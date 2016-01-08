import time
import datetime

from dls_barcode import Record, Store

OUTPUT_FILE = '../../test-output/storetest.txt'
INPUT_FILE = './test-resources/store_input.txt'


bcs1 = ["barcode1", "", "barcode2", "", "", "", "barcode3", ""]
bcs2 = ["dsdfh", "", "", "", "hdghdgh", "aqeth", "jrysjsfj", ""]

rec1 = Record(plate_type="CPS_Puck", barcodes=bcs1, imagepath="C:\\temp\\image1.jpg")
rec2 = Record(plate_type="CPS_Puck", barcodes=bcs2, imagepath="C:\\temp\\image2.jpg")

store = Store(filepath=INPUT_FILE, records=[rec1, rec2])

store._to_file()


# READ

store2 = Store.from_file(INPUT_FILE)
print(store2.filepath)
for record in store2.Records:
    print record._formatted_date()
    print record.puck_type
    print record.imagepath
    print record.barcodes