import csv
import os.path

class CSVWriter:
    file_name: str
    file_exists: bool
    
    def __init__(self, file_name):
        self.file_name = file_name
        self.file_exists = os.path.isfile(file_name)
        if not self.file_exists:
            self.initialize()

    def initialize(self):
        with open(self.file_name, 'a', newline='') as file:
            self.writer = csv.writer(file)
            if not self.file_exists:
                self.writer.writerow(['Connection Summary'])

    def write(self, data):
        with open(self.file_name, 'a', newline='') as file:
            self.writer = csv.writer(file)
            self.writer.writerow(data)
