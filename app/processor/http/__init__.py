import fastapi


def register_routers(app: fastapi.FastAPI):
    from . import account, google, public, stadium, city

    app.include_router(public.router)
    app.include_router(account.router)
    app.include_router(google.router)
    app.include_router(stadium.router)
    app.include_router(city.router)
