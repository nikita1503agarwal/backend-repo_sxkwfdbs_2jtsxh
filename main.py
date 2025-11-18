import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Category, Product

app = FastAPI(title="Ecommerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateCategory(BaseModel):
    name: str
    slug: str
    image: Optional[str] = None


class CreateProduct(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None
    in_stock: bool = True


@app.get("/")
def root():
    return {"message": "Ecommerce API running"}


@app.get("/schema")
def get_schema():
    # Basic schema discovery for the viewer
    return {
        "category": Category.model_json_schema(),
        "product": Product.model_json_schema(),
    }


@app.get("/api/categories")
def list_categories(limit: int = Query(50, ge=1, le=200)):
    try:
        items = get_documents("category", {}, limit)
        for it in items:
            it["_id"] = str(it["_id"])  # make JSON serializable
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/categories", status_code=201)
def create_category(payload: CreateCategory):
    try:
        # Basic uniqueness on slug
        exists = db["category"].find_one({"slug": payload.slug}) if db else None
        if exists:
            raise HTTPException(status_code=400, detail="Slug already exists")
        new_id = create_document("category", payload.model_dump())
        doc = db["category"].find_one({"_id": ObjectId(new_id)}) if db else None
        if doc:
            doc["_id"] = str(doc["_id"])
        return {"item": doc}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
def list_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    try:
        filt = {}
        if category:
            filt["category"] = category
        if q:
            filt["title"] = {"$regex": q, "$options": "i"}
        items = get_documents("product", filt, limit)
        for it in items:
            it["_id"] = str(it["_id"])  # make JSON serializable
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", status_code=201)
def create_product(payload: CreateProduct):
    try:
        # Validate category exists
        cat = db["category"].find_one({"slug": payload.category}) if db else None
        if not cat:
            raise HTTPException(status_code=400, detail="Category does not exist")
        new_id = create_document("product", payload.model_dump())
        doc = db["product"].find_one({"_id": ObjectId(new_id)}) if db else None
        if doc:
            doc["_id"] = str(doc["_id"])
        return {"item": doc}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        from database import db as _db

        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
