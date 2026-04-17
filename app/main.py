from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, dashboard, banks, imports, contracts, exchange_rates, admin, billing_simulator, about

app = FastAPI(title="SaaS Monthly Revenue", docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(banks.router)
app.include_router(imports.router)
app.include_router(contracts.router)
app.include_router(exchange_rates.router)
app.include_router(admin.router)
app.include_router(billing_simulator.router)
app.include_router(about.router)


@app.exception_handler(302)
async def redirect_handler(request: Request, exc):
    return RedirectResponse(url=exc.headers["Location"])


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})
