# คู่มือ API ตลาดเมล็ดกาแฟ (v1)

สำหรับเขียน agent · ทุกอย่างที่หน้าเว็บซื้อขายทำ เรียกผ่าน API นี้ได้ทั้งหมด

## พื้นฐาน

| เรื่อง | ค่า |
|---|---|
| ที่อยู่ | `http://<ที่อยู่ตลาด>:8000` ทีมงานแจ้ง (ตลาดฝึกกับวันแข่งเป็นคนละที่อยู่และคนละ key) |
| ยืนยันตัวตน | header `Authorization: Bearer <key ของทีม>` ทุกคำขอ |
| รูปแบบ | JSON ทั้งขาเข้าและขาออก (UTF-8) |
| หน่วย | น้ำหนักเป็น **กก.** ทวีคูณของ 60 (1 กระสอบ) · ราคาเป็น **บาท/กก.** |
| จำกัดความถี่ | ไม่เกิน **5 ครั้งต่อวินาที** ต่อทีม (กระชากได้ชั่วครู่ 10 ครั้ง) · อ่าน `GET /v1/state` ทุก ~1 วินาทีก็พอ |
| เวลา | อ่านจาก `seconds_left` หรือ `phase_ends_at` เสมอ อย่าเขียนเวลารอบตายตัว |

```python
import httpx
api = httpx.Client(base_url="http://<ที่อยู่ตลาด>:8000", headers={"Authorization": "Bearer sk-T00-..."}, timeout=10)
state = api.get("/v1/state").json()
```

## ช่วงของตลาด (`phase`)

| phase | ความหมาย | ทำอะไรได้ |
|---|---|---|
| `WAITING` | ยังไม่เริ่ม (รอบเก็บคะแนนแบบตลาดส่วนตัว: รอทีมกดเริ่ม) | อ่านอย่างเดียว |
| `SETUP` | เตรียมตัว เห็นล็อตแล้ว | อ่าน คำนวณ TV |
| `APPRAISAL` | ช่วงประเมินมูลค่า | `POST /v1/appraisals` ครั้งเดียว |
| `ROUND_OPEN` | รอบเปิดรับข้อเสนอ | ส่ง แก้ ยกเลิกข้อเสนอ |
| `ROUND_CLEARING` | ปิดรับ กำลังจับคู่ | รอผล |
| `CLOSED` | ปิดตลาด | อ่านผล |

รอบมี 2 แบบ (`round.kind`): `practice` รอบซ้อม ไม่นับคะแนน · `real` นับคะแนน (`round.counts_for_score`)

## Endpoint

| method | path | ใช้ทำอะไร |
|---|---|---|
| GET | `/v1/version` | รุ่นเซิร์ฟเวอร์ โหมด เวลาเซิร์ฟเวอร์ (ไม่ต้องใช้ key) |
| GET | `/v1/state` | **ทุกอย่างในครั้งเดียว**: ช่วง เวลา รอบ ล็อต RFQ ข้อเสนอที่เปิดอยู่ ผลรอบล่าสุด |
| GET | `/v1/calendar` | สูตร TV และตัวเลขกติกา (`rules`) ปฏิทินตลาด (`calendar`) |
| POST | `/v1/appraisals` | ส่งผลประเมินมูลค่า (ครั้งเดียว) |
| GET | `/v1/appraisals` | ดูผลประเมินที่ส่งไปแล้ว |
| POST | `/v1/offers` | ส่งข้อเสนอ 1 รายการ |
| POST | `/v1/offers:batch` | ส่งหลายรายการพร้อมกัน (แนะนำ) |
| GET | `/v1/offers` | ข้อเสนอของทีมในรอบนี้ |
| PUT | `/v1/offers/{offer_id}` | แก้ `kg` หรือ `price_per_kg` |
| DELETE | `/v1/offers/{offer_id}` | ยกเลิกข้อเสนอ |
| GET | `/v1/results` | ผลรอบล่าสุดที่จับคู่แล้ว · `?round=R3` ดูรอบที่ระบุ |
| GET | `/v1/standings` | ยอดขาย กก.ที่ขายได้/เหลือ ราคาเฉลี่ยของทีม |
| GET | `/v1/leaderboard` | อันดับ (ระหว่างแข่งมีแต่อันดับ ไม่มีตัวเลข) |
| GET | `/v1/lots` · `/v1/rfqs` | ส่วนย่อยของ `/v1/state` |
| POST | `/v1/sandbox/reset` | ตลาดฝึกเท่านั้น: เริ่มเกมใหม่ |
| GET | `/v1/sandbox/reveal` | ตลาดฝึกเท่านั้น หลังปิดตลาด: คุณภาพจริง TV จริง และคะแนน |

### `GET /v1/state`

```json
{
  "market": "sandbox", "team_id": "T05",
  "phase": "ROUND_OPEN", "paused": false, "seconds_left": 212.4, "phase_ends_at": 1792562391.4,
  "round": {"round_id": "R2", "kind": "real", "number": 2, "of": 8, "counts_for_score": true, "calendar": "ปกติ"},
  "lots": [
    {"lot_id": "LOT-T05-1", "kg_total": 300, "kg_remaining": 300, "kg_in_open_offers": 120, "kg_available": 180,
     "origin": "ชุมพร - ปะทิว", "process": "Washed",
     "sample": {"defect_pct": 5.56, "moisture_pct": 12.95, "screen": 13}}
  ],
  "rfqs": [
    {"rfq_id": "R2-03", "buyer": "สยามคอมเมิร์ซ", "buyer_type": "COMMERCIAL", "kg": 600, "bags": 10,
     "spec": {"max_defect_pct": 7.0, "max_moisture_pct": 12.5, "min_screen": null}}
  ],
  "my_open_offers": [],
  "round_capacity_kg": 360, "capacity_left_kg": 240,
  "appraisal_submitted": true,
  "last_results": {"round_id": "R1", "my_offers": [], "market_summary": []},
  "standings": {"revenue_thb": 0, "kg_sold": 0, "kg_remaining": 1560, "kg_total": 1560, "avg_price_per_kg": null},
  "salvage_ratio": 0.8
}
```

- `kg_available` = เหลือขาย ลบที่ติดอยู่ในข้อเสนอที่เปิดอยู่ · ใช้ค่านี้ตอนตัดสินใจ
- `spec` ล็อตต้องผ่าน **ทุกข้อ** (`min_screen: null` = ไม่กำหนด) · ผู้ซื้อตรวจกับ **คุณภาพจริง** ไม่ใช่ผลวัดตัวอย่าง
- `capacity_left_kg` = ทีมเสนอรวมได้อีกกี่ กก. ในรอบนี้ · `null` = ไม่จำกัด
- `last_results` = ผลรอบล่าสุด รูปแบบเดียวกับ `GET /v1/results`

### `GET /v1/calendar`

`rules` มีตัวเลขสูตร TV ครบ (`p0`, `defect_steps`, `moisture`, `screen_factors`), `bag_kg`, `salvage_ratio`, `scoring`, `timeline` · `calendar` บอกช่วงรอบและป้ายกำกับ (เช่น ปกติ เทศกาล) — **ใช้ค่าจากที่นี่ อย่าพิมพ์ตัวเลขเอง** เพราะวันแข่งอาจต่างจากตลาดฝึก

### `POST /v1/appraisals`

```json
{"items": [{"lot_id": "LOT-T05-1", "est_value_per_kg": 119.75, "grade": "GRADE_1"}]}
```
ส่งได้ครั้งเดียว เฉพาะช่วง `APPRAISAL` · `grade` ไม่บังคับ · คะแนนประเมินคิดจากความคลาดเฉลี่ยเทียบ TV จริง (คลาด 0% ได้เต็ม, 10% ขึ้นไปได้ 0) ไม่ส่งได้ 0

### `POST /v1/offers`

```json
{"rfq_id": "R2-03", "lot_id": "LOT-T05-1", "kg": 120, "price_per_kg": 121.5}
```
ตอบกลับ `201` พร้อมข้อเสนอ `{"offer_id": "O00042", "status": "OPEN", ...}`

เงื่อนไข: ส่งได้เฉพาะ `ROUND_OPEN` · `kg` ทวีคูณ 60 · ไม่เกิน `kg` ของ RFQ · ไม่เกิน `kg_available` ของล็อต · รวมทั้งทีมไม่เกิน `capacity_left_kg` · ราคามากกว่า 0 ไม่เกิน 1000 · ล็อตเดียวเสนอหลาย RFQ ได้ แต่ กก. ที่เสนอรวมต้องไม่เกินที่มี

### `POST /v1/offers:batch`

```json
{"offers": [{"rfq_id": "R2-03", "lot_id": "LOT-T05-1", "kg": 120, "price_per_kg": 121.5},
            {"rfq_id": "R2-05", "lot_id": "LOT-T05-3", "kg": 60, "price_per_kg": 98.0}],
 "replace_existing": true}
```
- **ทั้งหมดหรือไม่มีเลย**: ผิดแม้รายการเดียว ไม่บันทึกสักรายการ ได้ `BATCH_REJECTED` และ `allowed.errors` บอกว่ารายการที่เท่าไร (`index`) ผิดเพราะอะไร
- `replace_existing: true` = ยกเลิกข้อเสนอที่เปิดอยู่ของทีมในรอบนี้ก่อน แล้วใช้ชุดใหม่แทน (ส่งซ้ำได้ไม่ซ้อน)

### `GET /v1/results`

```json
{"round_id": "R2", "kind": "real",
 "my_offers": [{"offer_id": "O00042", "rfq_id": "R2-03", "lot_id": "LOT-T05-1", "kg": 120, "price_per_kg": 121.5,
                "status": "ACCEPTED", "filled_kg": 120}],
 "market_summary": [{"rfq_id": "R2-03", "buyer": "สยามคอมเมิร์ซ", "buyer_type": "COMMERCIAL", "wanted_kg": 600,
                     "bought_kg": 420, "offers": 5, "price_min": 103.86, "price_max": 124.22, "price_avg": 118.18}]}
```

| status | ความหมาย | ควรทำอะไรรอบหน้า |
|---|---|---|
| `ACCEPTED` | ขายได้ครบ | ลองขอแพงขึ้นเล็กน้อย |
| `PARTIAL` | ขายได้บางส่วน (คนอื่นคุ้มกว่า หรือ RFQ เต็ม) | ใกล้จุดพอดี |
| `OUTBID` | ข้อเสนออื่นคุ้มกว่า RFQ เต็มก่อน | ลดราคา หรือไป RFQ อื่น |
| `ABOVE_LIMIT` | แพงเกินเพดานลับของผู้ซื้อรายนั้น | ลดตัวคูณกับผู้ซื้อรายนั้น/ประเภทนั้น |
| `SPEC_MISMATCH` | คุณภาพจริงไม่ผ่านสเปก (ผลวัดตัวอย่างคลาดเคลื่อน) | ระวังล็อตที่ค่าใกล้ขอบสเปก |
| `CANCELLED` | ทีมยกเลิกเอง หรือถูกแทนด้วย `replace_existing` | — |

การจับคู่: ผู้ซื้อตัดข้อเสนอที่ไม่ผ่านสเปกและเกินเพดานออก → เรียง **ราคา ÷ TV จริง** จากต่ำไปสูง → รับจนครบ กก. ที่ต้องการ → จ่ายตามราคาที่เสนอ · ข้อเสนอที่คุ้มเท่ากันแบ่งกันทีละกระสอบ · ข้อเสนอหมดอายุเมื่อรอบปิด

## Error

ทุก error ใช้รูปแบบเดียวกัน อ่าน `code` ด้วยโปรแกรม แสดง `message` และทำตาม `hint`

```json
{"error": {"code": "EXCEEDS_REMAINING", "message": "LOT-T05-1 has 300 kg left; open offers already use 240 kg. You can offer at most 60 kg more.",
           "field": "kg", "hint": "Reduce kg to 60 or cancel another offer on LOT-T05-1.", "allowed": {"max_kg": 60}}}
```

| code | HTTP | เกิดเมื่อ | แก้อย่างไร |
|---|---|---|---|
| `UNAUTHORIZED` | 401 | ไม่มี key หรือ key ผิด | ตรวจ header `Authorization: Bearer ...` และใช้ key ให้ตรงตลาด (ฝึก/แข่ง) |
| `INVALID_FIELD` | 400 | ค่าผิดรูปแบบ เช่น ขาดช่อง ราคาไม่อยู่ใน 0–1000 เสนอเกิน กก. ของ RFQ | ดู `field` และ `allowed` |
| `NOT_MULTIPLE_OF_BAG` | 400 | `kg` ไม่ใช่ทวีคูณ 60 | ใช้ค่าใน `allowed.nearest` |
| `EXCEEDS_REMAINING` | 400 | เสนอเกินที่ล็อตเหลือ (รวมข้อเสนอที่เปิดอยู่) | ลด `kg` ถึง `allowed.max_kg` หรือยกเลิกข้อเสนออื่นของล็อตนั้น |
| `OVER_ROUND_CAPACITY` | 400 | ทีมเสนอรวมเกินที่จำกัดต่อรอบ | ลดถึง `allowed.max_kg` ดู `capacity_left_kg` ก่อนส่ง |
| `BATCH_REJECTED` | 400 | มีรายการผิดใน batch ไม่บันทึกเลย | แก้ตาม `allowed.errors[].index` แล้วส่งใหม่ทั้งชุด |
| `MANUAL_DISABLED` | 403 | ส่งคำสั่งจากหน้าเว็บในช่วงที่ห้ามส่งด้วยมือ | ให้ agent ส่ง |
| `UNKNOWN_LOT` | 404 | ไม่มีล็อตนี้ | ใช้ `lot_id` จาก `state.lots` |
| `NOT_YOUR_LOT` | 404 | ล็อตของทีมอื่น | ใช้ล็อตของทีมตัวเอง |
| `UNKNOWN_RFQ` | 404 | RFQ ไม่ได้เปิดในรอบนี้ (มักเป็น RFQ รอบก่อน) | ใช้ `rfq_id` จาก `state.rfqs` รอบปัจจุบัน |
| `UNKNOWN_OFFER` | 404 | ไม่มีข้อเสนอนี้ของทีม | ดู `GET /v1/offers` |
| `WRONG_PHASE` | 409 | ทำผิดช่วง เช่น ส่งข้อเสนอนอก `ROUND_OPEN` ประเมินนอก `APPRAISAL` | รอช่วงที่ถูก ดู `allowed` |
| `ROUND_CLOSED` | 409 | รอบปิดรับแล้ว หรือแก้ข้อเสนอที่หมดอายุ | รอรอบใหม่ แล้วส่งข้อเสนอใหม่ |
| `APPRAISAL_ALREADY_SUBMITTED` | 409 | ส่งผลประเมินซ้ำ | ไม่ต้องทำอะไร ส่งได้ครั้งเดียว |
| `NOT_AVAILABLE` | 409 | ยังไม่มีข้อมูล/ใช้ไม่ได้ในโหมดนี้ เช่น ผลรอบที่ยังไม่จับคู่ เฉลยก่อนปิดตลาด | ดู `hint` |
| `RATE_LIMITED` | 429 | เรียกเกิน 5 ครั้ง/วินาที | รอ `allowed.retry_after_s` วินาที แล้วเรียกให้ห่างลง |
| `UNKNOWN_ENDPOINT` | 404 | path ผิด | ทุก path ขึ้นต้นด้วย `/v1` |
| `METHOD_NOT_ALLOWED` | 405 | ใช้ method ผิด เช่น GET กับ path ที่ต้อง POST | ดูตาราง endpoint |

## LLM gateway (ของผู้จัด)

LLM ของงานพูด API แบบ OpenAI (`/v1/chat/completions`) ใช้ไลบรารี `openai` ได้เลย

| เรื่อง | ค่า |
|---|---|
| ที่อยู่ | `http://<ที่อยู่ gateway>:4000/v1` ทีมงานแจ้ง |
| key | key เดียวกับตลาด |
| model | `event-llm` |
| จำกัด | ทำงานพร้อมกันได้ **2 คำขอ** ต่อทีม · ไม่เกิน **20 คำขอต่อนาที** · `max_tokens` สูงสุด 2000 |
| thinking | ปิดเป็นค่าเริ่มต้น · เปิดด้วย `reasoning_effort="medium"` (ช้ากว่ามาก อาจคิดจน token หมด) |

```python
from openai import OpenAI
llm = OpenAI(base_url="http://<ที่อยู่ gateway>:4000/v1", api_key="sk-T00-...", timeout=60, max_retries=0)
r = llm.chat.completions.create(model="event-llm", max_tokens=300, reasoning_effort="none",
                                messages=[{"role": "user", "content": "..."}],
                                response_format={"type": "json_schema", "json_schema": {"name": "answer", "schema": SCHEMA}})
```

| error | HTTP | ความหมาย |
|---|---|---|
| `BAD_KEY` | 401 | key ผิด |
| `TOO_MANY_CONCURRENT` | 429 | ทีมมีคำขอค้างอยู่ 2 คำขอแล้ว รอให้เสร็จก่อน |
| `RATE_LIMIT` | 429 | เกิน 20 คำขอ/นาที รอตาม header `Retry-After` |

LLM ช้าหรือล่มได้เสมอ: ตั้ง timeout ให้จบก่อนรอบปิด และมีกฎสำรองเมื่อ LLM ไม่ตอบ (starter ทำไว้แล้วใน `llm.py` และ `strategy.py`)
