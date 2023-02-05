from fastapi import APIRouter, Depends
from app.database import User
from .. import schemas, oauth2
from bson.objectid import ObjectId
from app.serializers.userSerializers import userResponseEntity

router = APIRouter()


@router.get('/me', response_model=schemas.UserResponse)
def get_me(user_id: str = Depends(oauth2.require_user)):
    user = userResponseEntity(User.find_one({'_id': ObjectId(str(user_id))}))
    return {"status": "success", "user": user}
