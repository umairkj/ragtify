from fastapi import APIRouter
from fastapi_utils.cbv import cbv

router = APIRouter()


@cbv(router)
class RootAPI:
    @router.get("/")
    async def root(self):
        return {"status": "ok"}