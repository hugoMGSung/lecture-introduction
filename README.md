# 부경대학교 지역산업맞춤사업단 ICT 강의

FastAPI 한 서비스가 웹 페이지, 정적 파일, SQLite 데이터와 JSON API를 함께 제공하는 웹서비스입니다. 화면은 HTML 템플릿, CSS, 바닐라 JavaScript로 구성되어 별도의 프런트엔드 서버가 필요하지 않습니다.

## 로컬 실행

프로젝트 루트에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

웹사이트: `http://localhost:8000`  
API 문서: `http://localhost:8000/docs`  
상태 확인: `http://localhost:8000/api/health`

## 데이터 및 설정

`.env`에서 `DATABASE_URL`과 `APP_TITLE`을 설정합니다. 기본 SQLite 파일은 `data/lecture.db`입니다. 첫 실행 때 `app/data/training_schedule.json`을 바탕으로 2027년 훈련일 120일, 8교시 일정, 훈련내용·강사·장소가 DB에 등록됩니다. 상세 화면은 엑셀처럼 월별, 일자별로 일정을 확인하고 날짜별 상세를 펼쳐 볼 수 있습니다.

`.env`와 SQLite 파일은 Git에 포함하지 않습니다. 배포 환경에서는 SQLite 파일을 지속 보관할 저장 공간을 설정해야 합니다.

## Render 배포

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

SQLite 파일을 재배포 이후에도 보존하려면 Render 서비스에 영속 디스크를 연결하고 `DATABASE_URL`을 디스크 경로로 지정합니다.
