from fastapi import FastAPI
from db import (
    get_all_user_interactions, 
    get_all_products, 
    get_all_recipes
)
from recommender import RecommenderEngine
import uvicorn
from bson import ObjectId # Đảm bảo đã import ObjectId

app = FastAPI()
engine = RecommenderEngine()

# Hàm helper để xử lý tất cả ObjectId lồng nhau
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
        
        # 2. Engine tính toán
        recommend_ids = engine.suggest_all_in_one(history, all_products, all_recipes)
        
        # 3. Map dữ liệu
        product_map = {str(p['_id']): p for p in all_products}
        
        recommended_full_objects = []
        for rid in recommend_ids:
            if rid in product_map:
                # Ép kiểu toàn bộ object (bao gồm cả các ID lồng bên trong)
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)