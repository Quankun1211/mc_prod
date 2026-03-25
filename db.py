import motor.motor_asyncio
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()

async def get_all_user_interactions(user_id: str):
    try:
        uid = ObjectId(user_id)
        # Lấy 50 hành vi gần nhất của người dùng
        cursor = db.userbehaviors.find({"userId": uid}).sort("createdAt", -1).limit(50)
        behaviors = await cursor.to_list(length=50)
        
        all_interactions = []

        for b in behaviors:
            action = b.get("action")
            target_id = b.get("targetId")
            target_type = b.get("targetType", "Product")

            # Trường hợp 1: Hành vi đặt hàng (Cần bóc tách các sản phẩm trong đơn)
            if action == "order" or target_type == "Order":
                try:
                    o_id = ObjectId(target_id) if ObjectId.is_valid(target_id) else target_id
                    
                    # Truy vấn tất cả sản phẩm thuộc đơn hàng này
                    item_cursor = db.orderitems.find({"orderId": o_id})
                    items = await item_cursor.to_list(length=100)
                    
                    if items:
                        for item in items:
                            all_interactions.append({
                                "targetId": str(item.get("productId")),
                                "targetType": "Product",
                                "action": "order" 
                            })
                        continue # Đã xử lý xong Order, chuyển sang behavior tiếp theo
                except Exception:
                    pass # Bỏ qua lỗi bóc tách đơn lẻ để không dừng hệ thống

            # Trường hợp 2: Xem Menu (Bóc tách các sản phẩm trong menu đó)
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

            # Trường hợp 3: Các hành vi trực tiếp (view sản phẩm, view công thức, add to cart)
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