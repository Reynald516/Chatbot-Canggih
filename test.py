import json
import csv

# Membaca data CSV
with open("produk.csv", mode="r", encoding="utf-8") as csv_file:
    reader = csv.reader(csv_file)
    print("Membaca file produk.csv :")
    for row in reader:
        print(row)

# Membaca data JSON
with open("data.json", mode="r", encoding="utf-8") as json_file:
    json_data = json.load(json_file)
    print("Membaca file data.json :")
    for item in json_data:
        print(f"ID : {item['id']}, Q : {item['question']}, A : {item['answer']}, T : {','.join(item['tags'])}")