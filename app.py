from fastapi import FastAPI
from pydantic import BaseModel
from korail2 import Korail, ReserveOption, TrainType, AdultPassenger, ChildPassenger, SeniorPassenger
from fastapi.middleware.cors import CORSMiddleware
from sms_service import send_sms
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),  # 또는 ["http://localhost:3000"]로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ JSON 요청 본문 구조 정의
class ReserveRequest(BaseModel):
    dep: str
    arr: str
    date: str  # ex. 20250520
    time: str  # ex. 090000
    passengers: int = 1  # React의 key에 맞춰 이름 변경

@app.post("/reserve")
def reserve_ticket(data: ReserveRequest):
    korail = Korail(
        os.getenv("KORAIL_USERNAME"), 
        os.getenv("KORAIL_PASSWORD")
    )
    psgrs = [AdultPassenger(data.passengers)]

    print(f"예약 시도 인원 수: {psgrs}명")

    trains = korail.search_train(
        dep=data.dep,
        arr=data.arr,
        date=data.date,
        time=data.time,
        train_type=TrainType.KTX,
        passengers=psgrs,
        include_no_seats=False
    )

    if not trains:
        return { "status": "fail", "message": "예약 가능한 열차가 없습니다." }

    seat = korail.reserve(trains[0], psgrs, option=ReserveOption.GENERAL_ONLY)

    # ✅ 문자 발송
    message = f"[코레일 예매 완료]\n{data.dep} → {data.arr}\n열차 {seat.train_no}, 좌석 {seat.seat_no}, {seat.dep_time} 출발"
    send_sms(os.getenv("NOTIFICATION_PHONE"), message)

    return {
        "status": "success",
        "train_no": seat.train_no,
        "seat_no": seat.seat_no,
        "car_no": seat.car_no,
        "dep_time": seat.dep_time,
        "arr_time": seat.arr_time,
    }