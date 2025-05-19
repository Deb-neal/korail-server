from fastapi import FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from korail2 import Korail, ReserveOption, TrainType, AdultPassenger, ChildPassenger, SeniorPassenger
from fastapi.middleware.cors import CORSMiddleware
from sms_service import send_sms
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Swagger documentation setup
app = FastAPI(
    title="Korail API",
    description="기차표 예매 자동화 API 서비스",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "tickets",
            "description": "KTX 기차표 예약 관련 API",
        },
        {
            "name": "general",
            "description": "일반 API 정보",
        },
    ],
)

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),  # 또는 ["http://localhost:3000"]로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 루트 경로
@app.get("/", 
    tags=["general"],
    summary="API 루트 경로",
    description="API의 루트 경로로, API 정보를 반환합니다."
)
def read_root():
    """
    API의 루트 경로로, API의 정보를 반환합니다.
    """
    return "hello world"

# ✅ JSON 요청 본문 구조 정의
class ReserveRequest(BaseModel):
    dep: str = "서울"
    arr: str = "부산"
    date: str = "20250520"  # ex. 20250520
    time: str = "090000"  # ex. 090000
    passengers: int = 1  # React의 key에 맞춰 이름 변경
    
    class Config:
        schema_extra = {
            "example": {
                "dep": "서울",
                "arr": "부산",
                "date": "20250520",
                "time": "090000",
                "passengers": 1
            }
        }

class TicketResponse(BaseModel):
    status: str
    train_no: str = None
    seat_no: str = None
    car_no: str = None
    dep_time: str = None
    arr_time: str = None
    message: str = None

@app.post("/reserve", 
    response_model=TicketResponse,
    summary="기차표 예매 API",
    description="출발역, 도착역, 날짜, 시간, 인원수를 받아 KTX 기차표를 예매합니다.",
    tags=["tickets"],
    responses={
        200: {
            "description": "예매 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "train_no": "123",
                        "seat_no": "5A",
                        "car_no": "8",
                        "dep_time": "09:00",
                        "arr_time": "11:30"
                    }
                }
            }
        },
        400: {
            "description": "예매 실패",
            "content": {
                "application/json": {
                    "example": {
                        "status": "fail", 
                        "message": "예약 가능한 열차가 없습니다."
                    }
                }
            }
        }
    }
)
def reserve_ticket(data: ReserveRequest):
    """
    KTX 기차표를 자동으로 예매하고 결과를 반환합니다.
    
    - **dep**: 출발역 (예: 서울, 부산)
    - **arr**: 도착역 (예: 부산, 서울)
    - **date**: 날짜 (예: 20250520)
    - **time**: 시간 (예: 090000)
    - **passengers**: 인원 수 (기본값: 1)
    """
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
        return TicketResponse(status="fail", message="예약 가능한 열차가 없습니다.")

    seat = korail.reserve(trains[0], psgrs, option=ReserveOption.GENERAL_ONLY)

    # ✅ 문자 발송
    message = f"[코레일 예매 완료]\n{data.dep} → {data.arr}\n열차 {seat.train_no}, 좌석 {seat.seat_no}, {seat.dep_time} 출발"
    send_sms(os.getenv("NOTIFICATION_PHONE"), message)

    return TicketResponse(
        status="success",
        train_no=seat.train_no,
        seat_no=seat.seat_no,
        car_no=seat.car_no,
        dep_time=seat.dep_time,
        arr_time=seat.arr_time
    )