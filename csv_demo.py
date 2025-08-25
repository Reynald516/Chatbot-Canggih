import csv

# List data
data = [
    ["id", "nama", "kategori", "harga"],
    [1, "kopi", "minuman", "5000"],
    [2, "teh", "minuman", "3000"],
    [3, "nasi goreng", "makanan", "10000"]
]

# Menulis data CSV
with open("produk.csv", mode="w", newline="")as file:
    writer = csv.writer(file)
    writer.writerows(data)
print("File produk.csv Berhasil dibuat.")

# Membaca data CSV
with open("produk.csv", mode="r") as file:
    reader = csv.reader(file)
    print("Membaca produk.csv:")
    for row in reader:
        print(row)