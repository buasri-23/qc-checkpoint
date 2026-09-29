"""QC Checkpoint API (FastAPI) — เสิร์ฟทั้ง API และหน้าเว็บ React ในบริการเดียว
DATABASE_URL ไม่ตั้ง  -> ใช้ SQLite (qc.db) สำหรับพัฒนา
DATABASE_URL ตั้งค่า  -> ใช้ PostgreSQL (แนะนำสำหรับ host ฟรี เพราะดิสก์ถูกล้างเมื่อรีสตาร์ต)
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

url = os.getenv("DATABASE_URL", "sqlite:///qc.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
engine = sa.create_engine(url, pool_pre_ping=True)
meta = sa.MetaData()
issues = sa.Table(
    "issues", meta,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("checkpoint", sa.String(100)),
    sa.Column("expected", sa.String(100)),
    sa.Column("scanned", sa.String(100)),
    sa.Column("note", sa.Text),
    sa.Column("photo", sa.String(255)),
    sa.Column("status", sa.String(20)),
    sa.Column("fix_note", sa.Text),
    sa.Column("created", sa.String(40)),
    sa.Column("log", sa.Text),
)
meta.create_all(engine)

# action -> (สถานะก่อนหน้า, สถานะใหม่, ผู้ดำเนินการ, ข้อความใน log)
FLOW = {
    "ack": ("found", "ack", "หัวหน้าไลน์ QC", "ตรวจเช็คข้อมูลใน BackOffice → รับทราบปัญหากำลังแก้ไข"),
    "record": ("ack", "recorded", "หัวหน้าไลน์ QC", "แก้ไขชิ้นงานและบันทึกข้อมูล: {note}"),
    "fix": ("recorded", "fixed", "Backoffice", "Update สถานะชิ้นงาน → แก้ไขเสร็จสิ้น"),
    "resume": ("fixed", "resumed", "Application", "ปรับสถานะให้ทำงานขั้นตอนต่อไปได้ → เจ้าหน้าที่ตรวจชิ้นงานต่อ"),
}

app = FastAPI(title="QC Checkpoint API")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def out(r) -> dict:
    return {
        "id": r.id, "checkpoint": r.checkpoint, "expected": r.expected,
        "scanned": r.scanned, "note": r.note or "", "photo": r.photo or "",
        "status": r.status, "fixNote": r.fix_note or "", "created": r.created,
        "log": json.loads(r.log),
    }


class NewIssue(BaseModel):
    checkpoint: str
    expected: str
    scanned: str
    note: str = ""
    photo: str = ""


class Action(BaseModel):
    fix_note: Optional[str] = None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/issues")
def list_issues():
    with engine.connect() as c:
        rows = c.execute(sa.select(issues).order_by(issues.c.id.desc())).all()
    return [out(r) for r in rows]


@app.post("/api/issues", status_code=201)
def create_issue(b: NewIssue):
    cp, exp, sc = b.checkpoint.strip(), b.expected.strip(), b.scanned.strip()
    if not (cp and exp and sc):
        raise HTTPException(422, "กรอก Checkpoint, ID ที่ถูกต้อง และ ID ที่ตรวจพบให้ครบ")
    if exp == sc:
        raise HTTPException(400, "ID ถูกต้อง ไม่ต้องสร้างรายการปัญหา")
    ts = now()
    log = [
        {"ts": ts, "who": "Application", "text": f"ตรวจพบ ID ไม่ถูกต้อง ({sc} ≠ {exp}) → ตรวจพบปัญหา"},
        {"ts": ts, "who": "Application", "text": "ส่งข้อมูลชิ้นงานมีปัญหาไป Backoffice"},
        {"ts": ts, "who": "Backoffice", "text": "แสดงผลรายการ และแจ้งเตือนหัวหน้าไลน์ QC"},
    ]
    with engine.begin() as c:
        res = c.execute(issues.insert().values(
            checkpoint=cp, expected=exp, scanned=sc, note=b.note, photo=b.photo,
            status="found", fix_note="", created=ts, log=json.dumps(log, ensure_ascii=False)))
        return {"id": res.inserted_primary_key[0]}


@app.post("/api/issues/{issue_id}/{action}")
def transition(issue_id: int, action: str, b: Action):
    if action not in FLOW:
        raise HTTPException(404, "ไม่รู้จัก action นี้")
    src, dst, who, text = FLOW[action]
    note = (b.fix_note or "").strip()
    if action == "record" and not note:
        raise HTTPException(422, "ระบุรายละเอียดการแก้ไข")
    with engine.begin() as c:
        r = c.execute(sa.select(issues).where(issues.c.id == issue_id)).first()
        if r is None:
            raise HTTPException(404, "ไม่พบรายการ")
        if r.status != src:
            raise HTTPException(409, "สถานะรายการเปลี่ยนไปแล้ว กรุณารีเฟรช")
        log = json.loads(r.log)
        log.append({"ts": now(), "who": who, "text": text.format(note=note)})
        vals = {"status": dst, "log": json.dumps(log, ensure_ascii=False)}
        if action == "record":
            vals["fix_note"] = note
        c.execute(issues.update().where(issues.c.id == issue_id).values(**vals))
    return {"ok": True, "status": dst}


# ต้องอยู่ท้ายสุด เพื่อไม่บัง /api
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
