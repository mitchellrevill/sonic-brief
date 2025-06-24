from fastapi import APIRouter, Response, status

router = APIRouter()

@router.post("/logout", tags=["auth"])
async def logout():
    # Optionally, invalidate the token server-side if using JWT blacklisting or sessions
    return {
        "status": 200,
        "message": "Logged out",
        "force_frontend_logout": True
    }
