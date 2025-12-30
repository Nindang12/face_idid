from app.database import SessionLocal, Customer, RecognitionLog

db = SessionLocal()

print("🧹 Cleaning up invalid logs...")
logs = db.query(RecognitionLog).filter(RecognitionLog.customer_id.isnot(None)).all()
count = 0
for log in logs:
    customer = db.query(Customer).filter(Customer.id == log.customer_id).first()
    if not customer:
        print(f"❌ Found orphaned log {log.id} pointing to missing Customer {log.customer_id}. Deleting...")
        db.delete(log)
        count += 1

db.commit()
print(f"✅ Deleted {count} orphaned logs.")
db.close()
