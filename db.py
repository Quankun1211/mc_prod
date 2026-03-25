import motor.motor_asyncio
import os
from dotenv import load_dotenv
from bson import ObjectId
import pandas as pd
import io
load_dotenv()

MONGO_URI = os.getenv("MONGO_DB_URL")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

db = client["MenuApp"] 

async def get_all_user_interactions(user_id: str):
    try:
        if not ObjectId.is_valid(user_id):
            print(f"[AI Warning] Invalid user_id format: {user_id}")
            return []
            
        uid = ObjectId(user_id)
        cursor = db.userbehaviors.find({"userId": uid}).sort("createdAt", -1).limit(50)
        behaviors = await cursor.to_list(length=50)
        
        all_interactions = []

        for b in behaviors:
            action = b.get("action")
            target_id = b.get("targetId")
            target_type = b.get("targetType", "Product")

            # Trường hợp 1: Hành vi đặt hàng
            if action == "order" or target_type == "Order":
                try:
                    o_id = ObjectId(target_id) if ObjectId.is_valid(target_id) else target_id
                    item_cursor = db.orderitems.find({"orderId": o_id})
                    items = await item_cursor.to_list(length=100)
                    
                    if items:
                        for item in items:
                            all_interactions.append({
                                "targetId": str(item.get("productId")),
                                "targetType": "Product",
                                "action": "order" 
                            })
                        continue 
                except Exception:
                    pass 

            # Trường hợp 2: Xem Menu
            elif target_type == "Menu" and action == "view":
                try:
                    menu = await db.menus.find_one({"_id": ObjectId(target_id)})
                    if menu and "products" in menu:
                        for p_id in menu["products"]:
                            all_interactions.append({
                                "targetId": str(p_id), 
                                "targetType": "Product", 
                                "action": "view_menu"
                            })
                    continue
                except Exception:
                    pass

            # Trường hợp 3: Các hành vi trực tiếp
            if target_id:
                all_interactions.append({
                    "targetId": str(target_id),
                    "targetType": target_type,
                    "action": action
                })
        
        print(f"[AI System] Thu thập thành công {len(all_interactions)} tương tác từ User {user_id}")
        return all_interactions

    except Exception as e:
        print(f"[AI Critical Error] get_all_user_interactions: {e}")
        return []

async def get_all_products():
    try:
        cursor = db.products.find({}) 
        products = await cursor.to_list(length=1000)
        print(f"DEBUG DB: Đã lấy được {len(products)} sản phẩm.")
        return products
    except Exception as e:
        print(f"DEBUG DB ERROR: {e}")
        return []

async def get_all_recipes():
    try:
        cursor = db.recipes.find({}) 
        recipes = await cursor.to_list(length=1000)
        print(f"DEBUG DB: Đã lấy được {len(recipes)} CÔNG THỨC.")
        return recipes
    except Exception as e:
        print(f"DEBUG DB ERROR: {e}")
        return []
    
async def generate_user_excel_report():
    query_filter = {"role": {"$regex": "^user\s*$", "$options": "i"}}
    projection = {"_id": 1, "name": 1, "username": 1, "email": 1, "createdAt": 1, "role": 1}
    
    users_data = await db.users.find(query_filter, projection).to_list(length=5000)
    
    if not users_data:
        sample = await db.users.find_one({})
        return None, f"'{sample.get('role')}'" if sample else "DB Rỗng"

    df = pd.json_normalize(users_data)
    column_mapping = {"_id": "Mã Người Dùng", "name": "Họ và Tên", "username": "Tên Đăng Nhập", "email": "Email", "createdAt": "Ngày Tham Gia", "role": "Vai Trò"}
    df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)

    if "Ngày Tham Gia" in df.columns:
        df["Ngày Tham Gia"] = pd.to_datetime(df["Ngày Tham Gia"]).dt.strftime('%d/%m/%Y %H:%M')

    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if x is not None else "")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')
    output.seek(0)
    return output, None