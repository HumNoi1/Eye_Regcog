from huggingface_hub import HfApi, create_repo, upload_folder, login

login(token="")  # ใส่โทเคนของคุณ
repo_id = "HumNoi1/eye-detect-yolo"   # ชื่อรีโปที่ต้องการ
create_repo(repo_id, private=True, exist_ok=True)

# โฟลเดอร์ที่มีไฟล์โมเดล/weights/label.yaml/README.md
local_dir = "/home/humnoi1/Documents/GitHub/Eye_Regcog/backend/models"
upload_folder(
    repo_id=repo_id,
    folder_path=local_dir,
    path_in_repo=".",   # อัปทั้งโฟลเดอร์ขึ้น root
)
print("Uploaded!")
