from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from jose import jwt
from pydantic import BaseModel
from typing import List
from datetime import date, datetime, timedelta
import os

# ======================================================
# CONFIGURATION
# ======================================================

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}"
    f"/{os.environ['DB_NAME']}?sslmode=require"
)

SECRET_KEY = "CHANGE_ME_SECRET_KEY"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

# Login simple (projet)
FAKE_USER = {
    "username": "admin",
    "password": "admin123"
}

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
security = HTTPBearer()

# ======================================================
# MODELE SQLALCHEMY (BDD)
# ======================================================

class MouvementLogistique(Base):
    __tablename__ = "mouvement_logistique"

    id_mouvement = Column(BigInteger, primary_key=True, index=True)
    id_produit = Column(Integer)
    id_entrepot = Column(Integer)
    id_transporteur = Column(Integer)
    id_date = Column(Date)

    quantite = Column(Integer)
    poids_total = Column(Numeric)
    volume_total = Column(Numeric)
    cout_transport = Column(Numeric)
    statut_logistique = Column(String)
    delai_livraison = Column(Integer)
    retard = Column(Integer)

# ======================================================
# MODELES PYDANTIC (API)
# ======================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MouvementLogistiqueIn(BaseModel):
    id_produit: int
    id_entrepot: int
    id_transporteur: int
    id_date: date
    quantite: int
    poids_total: float
    volume_total: float
    cout_transport: float
    statut_logistique: str
    delai_livraison: int
    retard: int

class MouvementLogistiqueOut(MouvementLogistiqueIn):
    id_mouvement: int

    class Config:
        from_attributes = True  # Pydantic v2

# ======================================================
# DEPENDANCES
# ======================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(username: str):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré"
        )

# ======================================================
# APPLICATION
# ======================================================

app = FastAPI(
    title="API Logistique",
    version="1.0.0",
    description="API REST Logistique sécurisée (FastAPI + PostgreSQL + JWT)"
)

# ======================================================
# HEALTH CHECK (OBLIGATOIRE POUR RENDER)
# ======================================================

@app.get("/")
def health():
    return {"status": "API running"}

# ======================================================
# AUTHENTIFICATION
# ======================================================

@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: LoginRequest):
    if (
        data.username != FAKE_USER["username"]
        or data.password != FAKE_USER["password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides"
        )

    token = create_token(data.username)
    return {"access_token": token}

# ======================================================
# ENDPOINTS METIER
# ======================================================

@app.get(
    "/api/mouvements",
    response_model=List[MouvementLogistiqueOut],
    dependencies=[Depends(verify_token)]
)
def get_all_mouvements(db: Session = Depends(get_db)):
    return db.query(MouvementLogistique).all()

@app.post(
    "/api/mouvements",
    response_model=MouvementLogistiqueOut,
    dependencies=[Depends(verify_token)]
)
def create_mouvement(mvt: MouvementLogistiqueIn, db: Session = Depends(get_db)):
    obj = MouvementLogistique(**mvt.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj