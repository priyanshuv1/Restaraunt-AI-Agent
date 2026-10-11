from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.menu import MenuItem
ITEMS=[
("Espresso","Coffee","Short, rich espresso shot.",90,"vegetarian"),("Americano","Coffee","Espresso topped with hot water.",120,"vegan,vegetarian"),("Cappuccino","Coffee","Espresso with steamed milk and foam.",150,"vegetarian"),("Cafe Latte","Coffee","Espresso with smooth steamed milk.",160,"vegetarian"),("Cafe Mocha","Coffee","Espresso, chocolate and steamed milk.",180,"vegetarian"),("Cold Coffee","Beverages","Chilled blended coffee.",170,"vegetarian"),("Masala Chai","Beverages","Indian tea brewed with spices.",70,"vegetarian"),("Margherita Pizza","Pizza","Tomato, mozzarella and basil.",249,"vegetarian"),("Farmhouse Pizza","Pizza","Capsicum, onion, tomato and cheese.",329,"vegetarian"),("Chicken Tikka Pizza","Pizza","Chicken tikka, onion and cheese.",379,"non_vegetarian"),("Classic Veg Burger","Burgers","Veg patty, lettuce and house sauce.",149,"vegetarian"),("Crispy Chicken Burger","Burgers","Crispy chicken, lettuce and house sauce.",199,"non_vegetarian"),("Paneer Tikka Burger","Burgers","Grilled paneer tikka and fresh vegetables.",179,"vegetarian"),("Alfredo White Sauce Pasta","Pasta","Creamy white sauce pasta with herbs.",249,"vegetarian"),("Arrabbiata Pasta","Pasta","Pasta in spicy tomato sauce.",229,"vegan,vegetarian"),("Chicken Penne Pasta","Pasta","Penne pasta with chicken.",299,"non_vegetarian"),("Grilled Cheese Sandwich","Sandwiches","Toasted bread with melted cheese.",129,"vegetarian"),("Veg Club Sandwich","Sandwiches","Layered vegetable sandwich.",159,"vegetarian"),("Chicken Club Sandwich","Sandwiches","Chicken, lettuce and house dressing.",199,"non_vegetarian"),("French Fries","Snacks","Golden fries with seasoning.",99,"vegan,vegetarian"),("Garlic Bread","Snacks","Toasted garlic bread with herbs.",119,"vegetarian"),("Chocolate Brownie","Desserts","Rich chocolate brownie.",129,"vegetarian"),("Chocolate Lava Cake","Desserts","Warm chocolate cake with molten center.",149,"vegetarian")]
def main():
 with SessionLocal() as db:
  added=0
  for name,category,description,price,tags in ITEMS:
   if db.scalar(select(MenuItem).where(MenuItem.name==name)): continue
   db.add(MenuItem(name=name,category=category,description=description,price=price,dietary_tags=tags,is_available=True)); added+=1
  db.commit()
 print(f"Menu seed complete: {added} added; existing items kept.")
if __name__=="__main__": main()
