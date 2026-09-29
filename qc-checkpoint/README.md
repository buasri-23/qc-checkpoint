# QC Checkpoint (React + FastAPI)

โครงสร้าง: `main.py` (API + เสิร์ฟหน้าเว็บ) · `static/index.html` (React) · `render.yaml` (Deploy) · `requirements.txt`

## รันในเครื่อง
```
pip install -r requirements.txt
uvicorn main:app --reload      # เปิด http://localhost:8000  (ใช้ SQLite ให้เอง)
```
เอกสาร API: http://localhost:8000/docs

## Deploy ฟรีบน Render (เว็บ + Postgres)
1. สร้าง repo บน GitHub แล้ว push โฟลเดอร์นี้ขึ้นไป
2. สมัคร https://render.com (ไม่ต้องใช้บัตร) → **New → Blueprint** → เลือก repo
3. กด **Apply** Render จะสร้างเว็บ `qc-checkpoint` และฐานข้อมูล `qc-db` ตาม `render.yaml`
4. รอ build เสร็จ แล้วเปิดลิงก์ `https://qc-checkpoint-xxxx.onrender.com`

## ข้อจำกัดของแผนฟรี
- เว็บหลับเมื่อไม่มีคนใช้ 15 นาที ตื่นขึ้นมาใช้เวลาราว 1 นาที
- ห้ามเก็บข้อมูลเป็นไฟล์ (SQLite) บน host ฟรี เพราะถูกล้างทุกครั้งที่รีสตาร์ต จึงใช้ Postgres ผ่าน `DATABASE_URL`
- Postgres ฟรีของ Render หมดอายุใน 30 วัน ถ้าจะใช้ต่อให้ย้าย `DATABASE_URL` ไปฐานข้อมูลฟรีเจ้าอื่น (เช่น Neon, Supabase) หรืออัปเกรด
- ยังไม่มีระบบล็อกอิน ใครมีลิงก์ก็เปลี่ยนสถานะได้
