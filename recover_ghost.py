import os
from app.database import SessionLocal, Customer, RecognitionLog
from app.minio_service import minio_service
from app.config import settings

db = SessionLocal()

def recover_ghost_customer(ghost_id):
    print(f"👻 Checking for Ghost Customer ID: {ghost_id}...")
    
    # 1. Check if ID exists in DB
    existing = db.query(Customer).filter(Customer.id == ghost_id).first()
    if existing:
        print(f"✅ Customer {ghost_id} already exists in DB.")
        return

    # 2. Check MinIO for encoding
    pkl_path = f"encodings/{ghost_id}.pkl"
    image_path = f"images/customer_{ghost_id}.jpg" # Guessing ext
    
    try:
        # Check if encoding exists (by trying to get stats or list)
        # MinIO client stat_object
        try:
            minio_service.client.stat_object(settings.MINIO_BUCKET_NAME, pkl_path)
            print(f"✅ Found orphaned encoding in MinIO: {pkl_path}")
            
            # 3. Resurrect Customer
            print(f"✨ Resurrecting Customer {ghost_id}...")
            new_customer = Customer(
                id=ghost_id, # Force ID
                name="Guest", # Default name
                face_encoding_path=image_path,
                phone=None,
                email=None
            )
            db.add(new_customer)
            db.commit()
            print(f"🎉 Successfully recovered Customer {ghost_id}!")
            
        except Exception as e:
            print(f"❌ MinIO object not found or error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

# Find ghost IDs from Logs
print("🔍 Scanning logs for missing customers...")
distinct_ids = db.query(RecognitionLog.customer_id).distinct().all()
for r in distinct_ids:
    cid = r[0]
    if cid:
        cust = db.query(Customer).filter(Customer.id == cid).first()
        if not cust:
            print(f"⚠️ Found Log with missing Customer ID: {cid}")
            recover_ghost_customer(cid)

db.close()
