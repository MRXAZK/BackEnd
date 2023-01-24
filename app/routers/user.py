from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from bson.objectid import ObjectId
from app.serializers.userSerializers import userResponseEntity
from fastapi.responses import JSONResponse


from app.database import OCR, User
from .. import schemas, oauth2

router = APIRouter()


@router.get('/me', response_model=schemas.UserResponse)
def get_me(user_id: str = Depends(oauth2.require_user)):
    user = userResponseEntity(User.find_one({'_id': ObjectId(str(user_id))}))
    return {"status": "success", "user": user}

@router.get("/dashboard")
async def dashboard(user_id: int = Depends(oauth2.require_user)):
    user = User.find_one({'_id': ObjectId(str(user_id))})
    username = user["username"]
    data = list(OCR.find({"data.user_id": user_id}))
    if not data:
        return JSONResponse(content={"username": username, "message": "No data found"})
    date_upload = []
    for doc in data:
        for item in doc["data"]:
            date_upload.append(item["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
    data_count = len(date_upload)
    return JSONResponse(content={"status": "success", "username": username, "total_data": data_count, "date_upload": date_upload})


@router.get("/dashboard/{period}")
async def dashboard(period: str, user_id: int = Depends(oauth2.require_user)):
    user = User.find_one({'_id': ObjectId(str(user_id))})
    username = user["username"]
    data = list(OCR.find({"data.user_id": user_id}))
    if not data:
        return JSONResponse(content={"username": username, "message": "No data found"})
    date_upload = []
    for doc in data:
        for item in doc["data"]:
            date_upload.append(item["timestamp"])
    data_count = len(date_upload)

    # filter data based on specified period
    if period == "week":
        week_ago = datetime.now() - timedelta(days=7)
        filtered_data = [x for x in date_upload if x > week_ago]
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        data_by_day = [0] * 7
        for day in filtered_data:
            data_by_day[day.weekday()] += 1
        return JSONResponse(content={
            "status": "success", "username": username, "period": period,
            "period_data": days_of_week, "data": data_by_day
        })
    elif period == "month":
        month_ago = datetime.now() - timedelta(days=30)
        filtered_data = [x for x in date_upload if x > month_ago]
        days_of_month = [f"Day {i}" for i in range(1,31)]
        data_by_day = [0] * 30
        for day in filtered_data:
            data_by_day[day.day - 1] += 1
        return JSONResponse(content={
            "status": "success", "username": username, "period": period,
            "period_data": days_of_month, "data": data_by_day
        })
    elif period == "year":
        year_ago = datetime.now() - timedelta(days=365)
        filtered_data = [x for x in date_upload if x > year_ago]
        months_of_year = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        data_by_month = [0] * 12
        for day in filtered_data:
            data_by_month[day.month - 1] += 1
        return JSONResponse(content={
            "status": "success", "username": username, "period": period,
            "period_data": months_of_year, "data": data_by_month
        })
    else:
        return JSONResponse(content={"status": "error", "message": "Invalid period specified"})