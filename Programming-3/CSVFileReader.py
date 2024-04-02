import csv
import os

def read_csv_data(file_path):
    dependencies = []
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Assuming every row has exactly two elements: file and its dependency
            if len(row) >=1 :  # To ensure the row has two elements
                dependencies.append((row[0].strip()))
            else:  # For rows that might not have a dependency or are formatted differently
                dependencies.append((row[0].strip(), None))
    return dependencies

# File path to the CSV file
#file_path = os.getcwd() + "/www/test_dependency/dependency.csv"
file_path = "/Users/sumanthreddy/Assigments/Semester-2/Computer Networks/Assignment PDF'S/CSDS425-Computer-Networks-1/Programming-3/www/test_dependency/dependency.csv"

# Reading the CSV data
dependencies = read_csv_data(file_path)

# Printing the dependencies to verify
uri="/"
for i in dependencies:
    print(uri+i)
