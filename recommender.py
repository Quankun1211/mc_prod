import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RecommenderEngine:
    def __init__(self):
        # Loại bỏ các từ chung chung xuất hiện ở cả thực phẩm và tinh dầu
        stop_words_list = [
            'và', 'với', 'cho', 'món', 'của', 'nấu', 'làm', 'cách', 'trong', 'tại', 
            'sapa', 'bộ', 'thực', 'đơn', 'tự_nhiên', 'sạch', 'nguyên_chất', 'thơm', 
            'tác_dụng', 'đặc_sản', 'tây_bắc', 'hương_vị', 'tốt_cho'
        ]
        self.tfidf = TfidfVectorizer(stop_words=stop_words_list)
        self.weights = {
            'order': 5, 'favourite': 4, 'add_to_cart': 4,
            'search': 3, 'view_recipe': 3, 'view_menu': 2,
            'view_category': 2, 'view': 1
        }

    def suggest_all_in_one(self, history, all_products, all_recipes):
        if not all_products:
            return []

        df_prod = pd.DataFrame(all_products)
        df_prod['_id'] = df_prod['_id'].apply(lambda x: str(x))
        df_prod['content'] = (df_prod['name'].fillna('') + " " + df_prod['description'].fillna('')).str.lower()

        df_rec = pd.DataFrame(all_recipes)
        if not df_rec.empty:
            df_rec['_id'] = df_rec['_id'].apply(lambda x: str(x))
            df_rec['content'] = (df_rec['name'].fillna('') + " " + df_rec['description'].fillna('')).str.lower()

        user_interests = []
        interacted_categories = []
        interacted_ids = set()

        for action in history:
            target_id = str(action.get('targetId'))
            target_type = action.get('targetType', 'Product')
            action_name = action.get('action', 'view')
            weight = self.weights.get(action_name, 1)
            interacted_ids.add(target_id)

            found_content = ""
            if (target_type == 'Recipe' or target_type == 'Menu') and not df_rec.empty:
                row = df_rec[df_rec['_id'] == target_id]
                if not row.empty:
                    recipe_data = row.iloc[0]
                    embedded_ids = [str(p) for p in recipe_data.get('products', [])]
                    prod_in_rec = df_prod[df_prod['_id'].isin(embedded_ids)]
                    prod_names = " ".join(prod_in_rec['name'].tolist())
                    
                    # Thu thập category từ các sản phẩm trong recipe
                    for c_id in prod_in_rec['categoryId'].dropna():
                        interacted_categories.append(str(c_id))
                        
                    found_content = f"{recipe_data['content']} {prod_names}"
            else:
                row = df_prod[df_prod['_id'] == target_id]
                if not row.empty:
                    found_content = row.iloc[0]['content']
                    cat_id = row.iloc[0].get('categoryId')
                    if cat_id:
                        interacted_categories.append(str(cat_id))

            if found_content.strip():
                weighted_text = " ".join([found_content.lower()] * weight)
                user_interests.append(weighted_text)

        if not user_interests:
            return df_prod['_id'].tail(15).tolist()

        try:
            user_profile_text = " ".join(user_interests)
            texts = [user_profile_text] + df_prod['content'].tolist()
            
            tfidf_matrix = self.tfidf.fit_transform(texts)
            sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # --- LOGIC BOOSTING CATEGORY ---
            final_scores = sim_scores.copy()
            if interacted_categories:
                cat_counts = pd.Series(interacted_categories).value_counts()
                for i, row in df_prod.iterrows():
                    c_id = str(row.get('categoryId'))
                    if c_id in cat_counts:
                        # Thưởng điểm dựa trên tần suất danh mục trong lịch sử
                        final_scores[i] += 0.2
            
            results = pd.DataFrame({'id': df_prod['_id'], 'score': final_scores})
            recommendations = results[~results['id'].isin(interacted_ids)]
            
            top_ids = recommendations.sort_values(by='score', ascending=False)['id'].head(20).tolist()

            print(f"--- DEBUG AI CHANGE ---")
            print(f"User Profile Keywords (Top 10): {user_profile_text[:200]}...") # Xem từ khóa chính là gì
            print(f"Số lượng sản phẩm bị loại bỏ (đã tương tác): {len(interacted_ids)}")
            print(f"Top 5 IDs mới nhất: {top_ids[:5]}")
            return top_ids
            
        except Exception as e:
            print(f"Error: {e}")
            return df_prod['_id'].head(15).tolist()