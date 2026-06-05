import pydicom

# Load the file
ds = pydicom.dcmread("../data/test/PATIENT_0002_1.dcm")

# Access the Modality tag
modality = ds.Modality

print(modality)

if modality == "CT":
    print("This is a CT Scan.")
elif modality in ["DX", "CR"]:
    print("This is a standard X-ray.")
else:
    print(f"This is a different type of scan: {modality}")