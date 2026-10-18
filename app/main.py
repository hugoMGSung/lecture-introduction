from contextlib import asynccontextmanager
from datetime import date
import json
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, settings
from .models import Course, CourseOverview, ScheduleModule, TrainingDay, TrainingPeriod

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
SCHEDULE_DATA = json.loads((BASE_DIR / "data" / "training_schedule.json").read_text(encoding="utf-8"))

COURSES = [
    {"title": "AI IoT 스마트 항만물류 SW개발자", "description": "AI와 IoT를 활용해 스마트 항만물류의 서비스를 설계하고 구현하는 실무형 개발자 과정입니다.", "category": "대표 과정", "duration": "960시간", "featured": True},
    {"title": "재직자_MySQL성능최적화", "description": "실행 계획과 인덱스 분석을 바탕으로 MySQL 쿼리와 데이터베이스 성능을 개선합니다.", "category": "재직자 과정", "duration": "세부 일정 준비 중", "featured": False},
    {"title": "재직자_바이브코딩", "description": "생성형 AI와 함께 아이디어를 빠르게 구현하고 실제 동작하는 소프트웨어로 발전시킵니다.", "category": "재직자 과정", "duration": "세부 일정 준비 중", "featured": False},
    {"title": "재직자_생성형 AI기반 제조품질 개선 실무", "description": "생성형 AI를 활용해 제조 현장의 품질 데이터를 살펴보고 개선 기회를 찾습니다.", "category": "재직자 과정", "duration": "세부 일정 준비 중", "featured": False},
]

SCHEDULE = [(module["title"], module["hours"]) for module in SCHEDULE_DATA["modules"]]
DATE_SPECIFIC_TESTS = {
    "2027-03-08": (5, 6, 7, 8),
    "2027-03-22": (5, 6, 7, 8),
    "2027-03-29": (5, 6, 7, 8),
    "2027-04-05": (5, 6, 7, 8),
    "2027-04-12": (5, 6, 7, 8),
    "2027-05-06": (5, 6, 7, 8),
    "2027-05-14": (5, 6, 7, 8),
    "2027-05-21": (5, 6, 7, 8),
    "2027-06-03": (5, 6, 7, 8),
}
DATE_SPECIFIC_PRESENTATIONS = {
    "2027-04-20": ("프로젝트 발표", (5, 6, 7, 8)),
    "2027-06-14": ("프로젝트 발표", (5, 6, 7, 8)),
    "2027-08-06": ("최종 프로젝트 발표", (5, 6, 7, 8)),
}


def add_coding_assessments(schedule_data: dict) -> set[int]:
    """Mark assessment hours inside the existing module hours; indices are 0-based."""
    periods = [period for day in schedule_data["days"] for period in day["periods"]]
    expected_hours = sum(module["hours"] for module in schedule_data["modules"])
    if len(periods) != expected_hours:
        raise ValueError(f"Schedule has {len(periods)} periods but modules total {expected_hours} hours")

    schedule_override_indices: set[int] = set()
    offset = 0
    for module in schedule_data["modules"]:
        hours = module["hours"]
        assessments: list[int] = []
        if hours == 40:
            assessments.append(hours - 4)
        elif hours == 80:
            assessments.append(36)
        elif hours == 96:
            assessments.extend([36, hours - 4])

        for local_start in assessments:
            for local_hour in range(local_start, local_start + 4):
                index = offset + local_hour
                period = periods[index]
                period["subject"] = "코딩 테스트"
                period["content"] = f"코딩 테스트 (과목 내 {local_hour + 1}/{hours}시간차)"
                schedule_override_indices.add(index)
        offset += hours

    day_by_date = {day["date"]: day for day in schedule_data["days"]}
    flattened_start = 0
    for day in schedule_data["days"]:
        scheduled_numbers = DATE_SPECIFIC_TESTS.get(day["date"], ())
        for scheduled_number in scheduled_numbers:
            period = next((p for p in day["periods"] if p["number"] == scheduled_number), None)
            if period is None:
                raise ValueError(f"Missing period {scheduled_number} on {day['date']}")
            period["subject"] = "코딩 테스트"
            period["content"] = "코딩 테스트"
            schedule_override_indices.add(flattened_start + scheduled_number - 1)
        flattened_start += len(day["periods"])
    missing_dates = set(DATE_SPECIFIC_TESTS) - set(day_by_date)
    if missing_dates:
        raise ValueError(f"Schedule is missing assessment dates: {sorted(missing_dates)}")

    missing_presentation_dates = set(DATE_SPECIFIC_PRESENTATIONS) - set(day_by_date)
    if missing_presentation_dates:
        raise ValueError(f"Schedule is missing presentation dates: {sorted(missing_presentation_dates)}")
    flattened_start = 0
    for day in schedule_data["days"]:
        presentation = DATE_SPECIFIC_PRESENTATIONS.get(day["date"])
        if presentation:
            title, period_numbers = presentation
            for period_number in period_numbers:
                period = next((p for p in day["periods"] if p["number"] == period_number), None)
                if period is None:
                    raise ValueError(f"Missing period {period_number} on {day['date']}")
                period["subject"] = title
                period["content"] = title
                schedule_override_indices.add(flattened_start + period_number - 1)
        flattened_start += len(day["periods"])
    return schedule_override_indices


SCHEDULE_OVERRIDE_INDICES = add_coding_assessments(SCHEDULE_DATA)

INDUSTRY_PAGES = {
    "smart_ship": {
        "template": "smart_ship.html",
        "title": "스마트쉽",
        "english_title": "SMART SHIP",
        "description": "선박의 센서와 운항 데이터가 안전하고 효율적인 바다를 만드는 스마트쉽 영역입니다.",
        "icon": "♧",
    },
    "smart_logistic": {
        "template": "smart_logistic.html",
        "title": "스마트 항만",
        "english_title": "SMART PORT & LOGISTICS",
        "description": "항만의 장비와 물류 흐름을 연결해 하역과 운영을 최적화하는 스마트 항만 영역입니다.",
        "icon": "⚓",
    },
    "smart_factory": {
        "template": "smart_factory.html",
        "title": "스마트 팩토리",
        "english_title": "SMART FACTORY",
        "description": "생산 데이터와 자동화 시스템을 통해 품질과 생산성을 높이는 스마트 팩토리 영역입니다.",
        "icon": "▦",
    },
}

COURSE_OVERVIEW = {
    "concept": "선박, 컨테이너, 차량, 크레인, 게이트, 장치장 등 실제 항만의 물리적 객체와 운영시스템을 가상공간에 동일하게 구현하고, IoT 센서와 정보통신망을 통해 수집되는 실시간 데이터를 연계하여 항만의 현재 상태와 운영 흐름을 분석·예측·최적화하는 기술",
    "applications": "스마트항만, 항만물류, 선박 입출항 관리, 컨테이너 반입·반출 및 위치추적, 게이트 자동화, 장치장 운영, 하역장비 상태관리, 항만 안전관리, 해양환경 모니터링 등에 적용하며, 항만 운영효율 향상, 장비 고장 예측, 물류 지연 최소화, 안전사고 예방 및 의사결정 지원에 활용",
    "data_linkage": "TOS, AIS, GPS, RFID, OCR 및 IoT 센서에서 수집되는 선박·컨테이너·차량·하역장비 데이터를 고유 식별정보로 연계하여 실제 항만과 디지털트윈 모델을 동기화하는 체계",
    "practical_value": "IoT 센서, AIS, GPS, RFID, OCR 및 영상장비를 활용하여 선박·컨테이너·항만장비 데이터를 실시간으로 수집하고 분석·시각화하는 전 과정을 경험할 수 있으므로 스마트항만 정보통신 구축에 효과적",
    "technologies": "MQTT, TCP/IP, Modbus, OPC UA 등의 통신기술과 C#/.NET, ASP.NET Core, WPF, Python, OpenCV, 데이터베이스 및 AI 기술을 연계하여 항만정보 수집, 관제, 분석, 예측 및 디지털트윈 시스템을 구현",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        if not db.scalar(select(Course.id).limit(1)):
            db.add_all(Course(**course) for course in COURSES)
        existing_schedule = db.scalars(select(ScheduleModule).order_by(ScheduleModule.order)).all()
        expected_schedule = [(title, hours) for title, hours in SCHEDULE]
        actual_schedule = [(module.title, module.hours) for module in existing_schedule]
        if actual_schedule != expected_schedule:
            db.execute(delete(ScheduleModule))
            db.add_all(
                ScheduleModule(order=index, title=title, description="", hours=hours, phase="")
                for index, (title, hours) in enumerate(SCHEDULE, start=1)
            )
        if not db.scalar(select(TrainingDay.id).limit(1)):
            imported_days = []
            for item in SCHEDULE_DATA["days"]:
                training_day = TrainingDay(
                    day_number=item["day_number"],
                    training_date=date.fromisoformat(item["date"]),
                    weekday=item["weekday"],
                    daily_hours=item["daily_hours"],
                    cumulative_hours=item["cumulative_hours"],
                )
                db.add(training_day)
                imported_days.append((training_day, item["periods"]))
            db.flush()
            db.add_all(
                TrainingPeriod(
                    training_day_id=training_day.id,
                    number=period["number"],
                    label=period["label"],
                    start_time=period["start_time"],
                    end_time=period["end_time"],
                    subject=period["subject"],
                    content=period["content"],
                    instructor=period["instructor"],
                    location=period["location"],
                )
                for training_day, periods in imported_days
                for period in periods
            )
        else:
            # Apply assessment labels to existing Excel-imported records as well as fresh databases.
            stored_periods = db.scalars(
                select(TrainingPeriod).order_by(TrainingPeriod.training_day_id, TrainingPeriod.number)
            ).all()
            expected_periods = [
                period for day in SCHEDULE_DATA["days"] for period in day["periods"]
            ]
            if len(stored_periods) != len(expected_periods):
                raise ValueError("Stored training period count does not match the configured schedule")
            for index in SCHEDULE_OVERRIDE_INDICES:
                stored_periods[index].subject = expected_periods[index]["subject"]
                stored_periods[index].content = expected_periods[index]["content"]
        featured_course = db.scalar(select(Course).where(Course.featured.is_(True)))
        if featured_course:
            overview = db.scalar(select(CourseOverview).where(CourseOverview.course_id == featured_course.id))
            if overview is None:
                db.add(CourseOverview(course_id=featured_course.id, **COURSE_OVERVIEW))
            else:
                for field, value in COURSE_OVERVIEW.items():
                    setattr(overview, field, value)
        db.commit()
    yield


app = FastAPI(title=settings.app_title, description="ICT 교육 과정 소개 웹서비스", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    courses = db.scalars(select(Course).order_by(Course.featured.desc(), Course.id)).all()
    modules = db.scalars(select(ScheduleModule).order_by(ScheduleModule.order)).all()
    overview = db.scalar(select(CourseOverview))
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"courses": courses, "modules": modules, "overview": overview, "total_hours": sum(m.hours for m in modules), "title": settings.app_title},
    )


def render_industry_page(request: Request, page_key: str):
    industry = INDUSTRY_PAGES[page_key]
    return templates.TemplateResponse(
        request=request,
        name=industry["template"],
        context={"industry": industry, "title": settings.app_title},
    )


@app.get("/smart_ship.html", response_class=HTMLResponse, name="smart_ship")
def smart_ship(request: Request):
    return render_industry_page(request, "smart_ship")


@app.get("/smart_logistic.html", response_class=HTMLResponse, name="smart_logistic")
def smart_logistic(request: Request):
    return render_industry_page(request, "smart_logistic")


@app.get("/smart_factory.html", response_class=HTMLResponse, name="smart_factory")
def smart_factory(request: Request):
    return render_industry_page(request, "smart_factory")


@app.get("/detail.html", response_class=HTMLResponse)
@app.get("/detail", response_class=HTMLResponse, include_in_schema=False)
def course_detail(request: Request, db: Session = Depends(get_db)):
    course = db.scalar(select(Course).where(Course.featured.is_(True)))
    modules = db.scalars(select(ScheduleModule).order_by(ScheduleModule.order)).all()
    overview = db.scalar(select(CourseOverview))
    day_models = db.scalars(select(TrainingDay).order_by(TrainingDay.day_number)).all()
    period_models = db.scalars(
        select(TrainingPeriod).order_by(TrainingPeriod.training_day_id, TrainingPeriod.number)
    ).all()
    periods_by_day = {day.id: [] for day in day_models}
    for period in period_models:
        periods_by_day[period.training_day_id].append(period)

    month_groups = []
    for day in day_models:
        month_key = day.training_date.strftime("%Y-%m")
        if not month_groups or month_groups[-1]["key"] != month_key:
            month_groups.append(
                {
                    "key": month_key,
                    "label": f"{day.training_date.year}년 {day.training_date.month}월",
                    "days": [],
                    "hours": 0,
                }
            )
        month_groups[-1]["days"].append(
            {"day": day, "periods": periods_by_day[day.id]}
        )
        month_groups[-1]["hours"] += day.daily_hours

    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={
            "course": course,
            "modules": modules,
            "overview": overview,
            "modules": modules,
            "month_groups": month_groups,
            "total_hours": sum(day.daily_hours for day in day_models),
            "total_days": len(day_models),
            "training_start": day_models[0].training_date if day_models else None,
            "training_end": day_models[-1].training_date if day_models else None,
            "title": settings.app_title,
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/courses")
def list_courses(db: Session = Depends(get_db)):
    return db.scalars(select(Course).order_by(Course.featured.desc(), Course.id)).all()


@app.get("/api/schedule")
def list_schedule(db: Session = Depends(get_db)):
    modules = db.scalars(select(ScheduleModule).order_by(ScheduleModule.order)).all()
    return {"total_hours": sum(module.hours for module in modules), "modules": modules}
