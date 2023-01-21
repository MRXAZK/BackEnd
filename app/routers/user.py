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
    return JSONResponse(content={"username": username, "total_data": data_count, "date_upload": date_upload})
