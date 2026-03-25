from fastapi import FastAPI
from db import (
    get_all_user_interactions, 
    get_all_products, 
    get_all_recipes,
    generate_user_excel_report
)
from recommender import RecommenderEngine
import uvicorn
from bson import ObjectId 
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import StreamingResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)
engine = RecommenderEngine()

def clean_mongo_data(data):
    if isinstance(data, list):
        return [clean_mongo_data(item) for item in data]
    if isinstance(data, dict):
        return {k: clean_mongo_data(v) for k, v in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    return data

@app.get("/recommend/{id}")
async def get_recommendations(id: str):
    try:
        # 1. Lấy dữ liệu
        history = await get_all_user_interactions(id) 
        all_products = await get_all_products() 
        all_recipes = await get_all_recipes()
        
        recommend_ids = engine.suggest_all_in_one(history, all_products, all_recipes)
        
        product_map = {str(p['_id']): p for p in all_products}
        
        recommended_full_objects = []
        for rid in recommend_ids:
            if rid in product_map:
                clean_prod = clean_mongo_data(product_map[rid])
                recommended_full_objects.append(clean_prod)

        return {
            "status": "success",
            "userId": id,
            "data": recommended_full_objects 
        }
    except Exception as e:
        print(f"❌ Error in recommend route: {e}")
        return {"status": "error", "message": str(e), "data": []}

@app.get("/export/users")
async def export_users():
    output, error_msg = await generate_user_excel_report()
    
    if error_msg:
        return {"status": "error", "message": f"Không tìm thấy role 'user'. Role thực tế: {error_msg}"}

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="thong_ke_user.xlsx"'}
    )
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)