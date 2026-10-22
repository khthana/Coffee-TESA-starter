# Starter Agent — ตลาดเมล็ดกาแฟโรบัสตา

agent ตั้งต้นที่ **รันได้ทันทีและแข่งจนจบเกมได้** — ทีมแก้ให้เก่งขึ้นจากตรงนี้

## เริ่มใช้ (5 นาที)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Mac/Linux: .venv/bin/pip
cp .env.example .env                                # แล้วใส่ MARKET_URL, TEAM_KEY, LLM_*
.venv/Scripts/python main.py                        # เล่นจนตลาดปิด
.venv/Scripts/python main.py --forever              # sandbox: เล่นต่อเกมใหม่ไปเรื่อยๆ
```

- `TEAM_KEY` ใช้ key ของทีม (sandbox กับวันแข่งเป็นคนละ key)
- LLM: ช่วงงานใช้ **LLM gateway** ของผู้จัด (`LLM_BASE_URL`, `LLM_API_KEY` ตามที่แจก) — ถ้าจะลองบนโน้ตบุ๊กตัวเองใช้ Ollama: `ollama pull qwen3.5:4b` แล้วตั้ง `LLM_BASE_URL=http://localhost:11434/v1`
- `USE_LLM=0` = ใช้แต่ rule ไม่เรียก LLM เลย

## agent ทำอะไรบ้าง

```
ทุก ~5 วิ: GET /v1/state
  ├─ ช่วง APPRAISAL → คำนวณ TV จากผลวัด Sample ด้วยสูตรที่ตลาดประกาศ → POST /v1/appraisals (ครั้งเดียว)
  └─ รอบเปิดใหม่    → จำผลรอบก่อน → strategy.decide() → POST /v1/offers:batch
                       └─ ถ้า batch ถูกปฏิเสธ ส่งทีละ offer แล้วข้ามตัวที่ผิด
```

`strategy.decide()` ในแต่ละรอบ:

1. **candidates** — ทุกคู่ (ล็อต × RFQ) ที่ผลวัด Sample ผ่านสเปก สุ่มลำดับ (ถ้า 40 ทีมเรียงเหมือนกันจะรุม RFQ เดียวจน OUTBID)
2. **LLM เลือก** offer: candidate ไหน กี่กระสอบ markup เท่าไร (ราคา = markup × TV ที่ประเมิน) ตอบเป็น JSON ตาม schema
3. **rule เติม** ปริมาณที่ LLM เสนอไม่ครบ (LLM ตัวเล็กมักเสนอน้อยเกินไป ของเหลือขายได้แค่ 0.80 × TV)
4. **guard** ตรวจทุก offer ก่อนส่ง: ล็อต/RFQ มีจริง, สเปกผ่าน, kg ทวีคูณ 60 ไม่เกินคงเหลือ/ที่ RFQ ต้องการ/**Round Capacity** (`capacity_left_kg`), markup อยู่ใน 0.85–1.30
5. ถ้า LLM ล่ม ตอบผิดรูปแบบ หรือช้าจนจะหมดเวลารอบ → ใช้ **rule ล้วน** (markup คงที่ 1.00)

## ไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| `main.py` | loop หลัก, log, ส่ง offer |
| **`strategy.py`** | **จุดหลักที่ควรแก้**: prompt, markup, การกระจายขายแต่ละรอบ, guard |
| `appraisal.py` | สูตร TV และ Appraisal |
| `memory.py` | จำผลรอบก่อนๆ (`logs/memory-*.json`) สรุปให้ LLM |
| `llm.py` | เรียก LLM แบบ OpenAI-compatible, JSON schema, ไม่ throw (คืน `None` เมื่อพลาด) |
| `market.py` | client ของตลาด: retry, รอเมื่อเจอ 429, แปลง error |
| `logs/decisions.jsonl` | ทุกการตัดสินใจ: offer ที่ส่ง, มาจาก LLM หรือ rule, เหตุผลของ LLM, error |
| `คู่มือ-API.md` | คู่มือ API ตลาดและ LLM gateway ภาษาไทย พร้อมตาราง error code |

## สื่ออบรม (`notebooks/`)

| ไฟล์ | ใช้วันไหน |
|---|---|
| `ใบประเมินมูลค่า.xlsx` | วันที่ 1: ฝึกคำนวณมูลค่าจริงจากผลวัดตัวอย่าง |
| `เรียกตลาดด้วย-Python.ipynb` | วันที่ 1 ช่วงบ่าย: เติมช่องว่างเพื่อเรียก API ของตลาด |
| `สร้าง-agent.ipynb` | วันที่ 2: agent แบบกฎ → ให้ LLM ตอบ JSON → ใส่ LLM ในลูป |

## ความเก่งของ starter (ยังไม่แก้อะไร)

จำลอง 30 เกม 40 ทีม (ไม่ใช้ LLM): PR ~0.90 อันดับเฉลี่ย ~19/40 — ชนะบอตสุ่ม/บอตตัดราคา แต่แพ้บอตที่ปรับราคาตามผล (~0.94)
ใน sandbox กับ qwen3.5:9b ได้ PR 0.92 (อันดับ 8/20) — ผลต่อเกมแกว่งพอสมควร ลองหลายเกมก่อนสรุป

## ทำให้เก่งขึ้น (`# TODO` ในโค้ด)

- **markup ต่อ Buyer Type และปรับตามผลรอบก่อน** (`strategy.py` `MARKUP`) — ผู้ซื้อแต่ละประเภทยอมจ่ายไม่เท่ากัน
- **noise ของ Sample** — ล็อตที่ค่าใกล้ขอบเกรด/สเปก (`appraisal.py`, `spec_ok`)
- **Market Calendar** — ขายมากขึ้นช่วงเทศกาล น้อยลงช่วงซบเซา (`sell_budget`)
- **นิสัยของผู้ซื้อแต่ละราย** — สรุปจาก `market_summary` หลายรอบ (`memory.py`)
- **thinking mode** (`LLM_THINKING=1`) ฉลาดขึ้นแต่ช้ามาก และอาจคิดจน token หมดโดยไม่ตอบ — ถ้าเปิดต้องดูเวลา

## กติกาที่ต้องระวัง

- ห้ามส่งคำสั่งด้วยมือระหว่างแข่ง — agent ต้องทำเอง (ตรวจ log 5 อันดับแรก)
- อ่านเวลาจาก `/v1/state` เสมอ อย่า hardcode เวลารอบ (sandbox รอบสั้นกว่าวันแข่ง)
- เรียก API ได้ไม่เกิน 5 ครั้ง/วินาที
