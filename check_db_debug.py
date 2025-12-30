from app.database import SessionLocal, Customer, RecognitionLog
db = SessionLocal()

print("--- Checking Customer 13 ---")
c = db.query(Customer).filter(Customer.id == 13).first()
if c:
    print(f"✅ Found Customer 13: ID={c.id}, Name={c.name}, Created={c.created_at}")
else:
    print("❌ Customer 13 NOT FOUND")

print("\n--- Checking Latest Recognition Logs ---")
logs = db.query(RecognitionLog).order_by(RecognitionLog.created_at.desc()).limit(5).all()
for l in logs:
    print(f"Log ID={l.id}, Task={l.image_path}, CustomerID={l.customer_id}, Recognized={l.recognized}, Created={l.created_at}")

db.close()
