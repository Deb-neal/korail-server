from fastapi import FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from korail2 import Korail, ReserveOption, TrainType, AdultPassenger, ChildPassenger, SeniorPassenger
from korail2.korail2 import NoResultsError
from fastapi.middleware.cors import CORSMiddleware
from sms_service import send_sms
import os
from dotenv import load_dotenv
from typing import Optional

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
    train_no: Optional[str] = None
    seat_no: Optional[str] = None
    car_no: Optional[str] = None
    dep_time: Optional[str] = None
    arr_time: Optional[str] = None
    message: Optional[str] = None

@app.post("/reserve", 
    response_model=TicketResponse,
    summary="기차표 예매 API",
    description="출발역, 도착역, 날짜, 시간, 인원수를 받아 KTX 기차표를 예매합니다.",
    tags=["tickets"],
    responses={
        200: {"description": "예매 성공"},
        400: {"description": "예매 실패"},
        404: {"description": "예약 가능한 열차 없음"},
        500: {"description": "서버 오류"},
    }
)
def reserve_ticket(data: ReserveRequest):
    korail_id = os.getenv("KORAIL_USERNAME")
    korail_pw = os.getenv("KORAIL_PASSWORD")
    
    if not korail_id or not korail_pw:
        raise HTTPException(status_code=500, detail="KORAIL 계정 정보가 설정되지 않았습니다.")

    korail = Korail(korail_id, korail_pw)
    psgrs = [AdultPassenger(data.passengers)]

    try:
        trains = korail.search_train(
            dep=data.dep,
            arr=data.arr,
            date=data.date,
            time=data.time,
            train_type=TrainType.KTX,
            passengers=psgrs,
            include_no_seats=False
        )
    except NoResultsError:
        raise HTTPException(status_code=404, detail="예약 가능한 열차가 없습니다.")

    if not trains:
        raise HTTPException(status_code=404, detail="예약 가능한 열차가 없습니다.")

    seat = korail.reserve(trains[0], psgrs, option=ReserveOption.GENERAL_ONLY)

    # 문자 발송
    message = f"[코레일 예매 완료]\n{data.dep} → {data.arr}\n열차 {seat.train_no}, 좌석 {seat.seat_no or '-'}, {seat.dep_time} 출발"
    send_sms(os.getenv("NOTIFICATION_PHONE"), message)

    return TicketResponse(
        status="success",
        train_no=seat.train_no or "",
        seat_no=seat.seat_no or "",
        car_no=seat.car_no or "",
        dep_time=seat.dep_time or "",
        arr_time=seat.arr_time or "",
        message="예매가 성공적으로 완료되었습니다."
    )