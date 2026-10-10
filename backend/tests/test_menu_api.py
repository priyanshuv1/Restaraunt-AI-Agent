import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.menu import MenuItem  # noqa: F401
engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,autoflush=False,autocommit=False)
@pytest.fixture
def client():
 Base.metadata.create_all(bind=engine)
 def override_db():
  db=TestingSession()
  try: yield db
  finally: db.close()
 app.dependency_overrides[get_db]=override_db
 with TestClient(app) as c: yield c
 app.dependency_overrides.clear(); Base.metadata.drop_all(bind=engine)
def test_create_and_filter_menu(client):
 r=client.post("/api/menu",json={"name":"Cappuccino","category":"Coffee","price":"150.00","dietary_tags":["vegetarian"]})
 assert r.status_code==201 and r.json()["name"]=="Cappuccino"
 assert client.get("/api/menu?category=Coffee").json()[0]["dietary_tags"]==["vegetarian"]
def test_reject_zero_price(client):
 r=client.post("/api/menu",json={"name":"Mocha","category":"Coffee","price":"0"})
 assert r.status_code==422
def test_search_and_availability(client):
 created=client.post("/api/menu",json={"name":"Veg Club Sandwich","category":"Sandwiches","price":"159"}).json()
 assert client.get("/api/menu?search=club").json()[0]["name"]=="Veg Club Sandwich"
 changed=client.patch(f"/api/menu/{created['id']}",json={"is_available":False})
 assert changed.status_code==200 and changed.json()["is_available"] is False
 assert client.get("/api/menu?available_only=true").json()==[]
def test_delete_item(client):
 item=client.post("/api/menu",json={"name":"Brownie","category":"Desserts","price":"129"}).json()
 assert client.delete(f"/api/menu/{item['id']}").status_code==204
 assert client.get(f"/api/menu/{item['id']}").status_code==404
