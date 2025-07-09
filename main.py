from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers import auth, profile, match, company, docgen, upload

app = FastAPI(
    title="Tendorix API", 
    version="1.0.0",
    description="AI-Powered Tender Matching Platform"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api", tags=["Profile"])
app.include_router(match.router, prefix="/api", tags=["Matching"])
app.include_router(company.router, prefix="/api", tags=["Company"])
app.include_router(docgen.router, prefix="/api/docgen", tags=["Document Generation"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload & File Management"])

@app.get("/")
def root():
    return {
        "message": "Tendorix API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}