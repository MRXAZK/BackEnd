from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from bson.objectid import ObjectId
from fastapi.responses import JSONResponse
from app.database import OCR, User
from .. import oauth2

router = APIRouter()


@router.get("/")
async def dashboard(user_id: int = Depends(oauth2.require_user)):
    data = list(OCR.find({"data.user_id": user_id}))
    if not data:
        return JSONResponse(content={"message": "No data found"})
    date_upload = []
    for doc in data:
        for item in doc["data"]:
            date_obj = datetime.strptime(
                item["timestamp"], "%Y-%m-%d %H:%M:%S")
            date_upload.append(date_obj.strftime("%Y-%m-%d %H:%M:%S"))
    data_count = len(date_upload)
    return JSONResponse(content={"status": "success",  "total_data": data_count, "date_upload": date_upload})


@router.get("/{period}")
async def dashboard(period: str, user_id: int = Depends(oauth2.require_user)):
    data = list(OCR.find({"data.user_id": user_id}))
    if not data:
        return JSONResponse(content={"message": "No data found"})
    date_upload = []
    for doc in data:
        for item in doc["data"]:
            date_obj = datetime.strptime(
                item["timestamp"], "%Y-%m-%d %H:%M:%S")
            date_upload.append(date_obj.strftime("%Y-%m-%d %H:%M:%S"))
    data_count = len(date_upload)

    # filter data based on specified period
    if period == "day":
        today = datetime.now().strftime("%Y-%m-%d")
        filtered_data = [x for x in date_upload if x.startswith(today)]
        hours_of_day = [f"{i}" for i in range(24)]
        data_by_hour = [0] * 24
        for hour in filtered_data:
            data_by_hour[datetime.strptime(
                hour, "%Y-%m-%d %H:%M:%S").hour] += 1
        return JSONResponse(content={
            "status": "success",  "period": period,
            "period_data": hours_of_day, "data": data_by_hour
        })

    elif period == "week":
        week_ago = datetime.now() - timedelta(days=7)
        filtered_data = [x for x in date_upload if datetime.strptime(
            x, "%Y-%m-%d %H:%M:%S") > week_ago]
        days_of_week = ['Monday', 'Tuesday', 'Wednesday',
                        'Thursday', 'Friday', 'Saturday', 'Sunday']
        data_by_day = [0] * 7
        for day in filtered_data:
            data_by_day[datetime.strptime(
                day, "%Y-%m-%d %H:%M:%S").weekday()] += 1
        return JSONResponse(content={
            "status": "success",  "period": period,
            "period_data": days_of_week, "data": data_by_day
        })
    elif period == "month":
        month_ago = datetime.now() - timedelta(days=30)
        filtered_data = [x for x in date_upload if datetime.strptime(
            x, "%Y-%m-%d %H:%M:%S") > month_ago]
        days_of_month = [f"Day {i}" for i in range(1, 31)]
        data_by_day = [0] * 30
        for day in filtered_data:
            data_by_day[datetime.strptime(
                day, "%Y-%m-%d %H:%M:%S").day - 1] += 1
        return JSONResponse(content={
            "status": "success",  "period": period,
            "period_data": days_of_month, "data": data_by_day
        })
    elif period == "year":
        year_ago = datetime.now() - timedelta(days=365)
        filtered_data = [x for x in date_upload if datetime.strptime(
            x, "%Y-%m-%d %H:%M:%S") > year_ago]
        months_of_year = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
        data_by_month = [0] * 12
        for day in filtered_data:
            data_by_month[datetime.strptime(
                day, "%Y-%m-%d %H:%M:%S").month - 1] += 1
        return JSONResponse(content={
            "status": "success",  "period": period,
            "period_data": months_of_year, "data": data_by_month
        })

    else:
        return JSONResponse(content={"status": "error", "message": "Invalid period specified"})
