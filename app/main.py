from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import uuid
import os
import shutil
import json
import logging
from pathlib import Path

from app.database import init_db, get_db, Branch, Customer, Order, RecognitionLog
from app.face_recognition_service import face_service
from app.kafka_producer import producer
from app.config import settings
from app.minio_service import minio_service

app = FastAPI(title="Coffee Shop Face Recognition System", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Không cần mount static files nữa vì dùng MinIO
# upload_dir chỉ dùng cho temp files
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(exist_ok=True)

# Tạo endpoint để serve images từ MinIO
@app.get("/uploads/{image_path:path}")
async def get_image_from_minio(image_path: str):
    """Serve image từ MinIO"""
    try:
        # Lấy object path từ MinIO
        object_path = f"images/{image_path}"
        image_data = minio_service.download_file(object_path)
        
        if image_data is None:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Xác định content type
        content_type = "image/jpeg"
        if image_path.lower().endswith('.png'):
            content_type = "image/png"
        elif image_path.lower().endswith('.gif'):
            content_type = "image/gif"
        
        from fastapi.responses import Response
        return Response(content=image_data, media_type=content_type)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error serving image from MinIO: {e}")
        raise HTTPException(status_code=500, detail="Error loading image")

def get_image_url(face_encoding_path: Optional[str]) -> Optional[str]:
    """Convert MinIO object path to public URL"""
    if not face_encoding_path:
        return None

    # Nếu là path cũ (local), chuyển sang MinIO path
    path = str(face_encoding_path)
    
    # Loại bỏ các prefix cũ
    path = (
        path.replace('/code/app/uploads/', '')
            .replace('/app/uploads/', '')
            .replace('/uploads/', '')
            .replace('uploads/', '')
            .replace(f'{settings.UPLOAD_DIR}/', '')
    )

    if path.startswith('/'):
        path = path[1:]
    
    # Nếu đã là MinIO path (images/...), giữ nguyên
    if path.startswith('images/'):
        object_path = path
    else:
        # Chuyển sang MinIO path format
        object_path = f"images/{path}"
    
    # Trả về URL endpoint để serve từ MinIO
    return f"/uploads/{path}" if path else None

# Initialize database
init_db()

@app.on_event("startup")
async def startup_event():
    print("Coffee Shop Face Recognition System started!")
    print(f"Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Spark: {settings.SPARK_MASTER}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Trang chủ với giao diện web"""
    from fastapi.responses import Response
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})


@app.get("/camera", response_class=HTMLResponse)
async def camera_page():
    """
    Trang web đơn giản để dùng camera trên từng máy (worker hoặc server)
    và gửi ảnh liên tục lên API nhận diện.
    - Người dùng chọn chi nhánh (branch)
    - Trang sẽ chụp frame từ camera và POST tới:
      /api/branches/{branch_id}/recognize
    """
    try:
        with open("app/templates/camera.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="camera.html not found")

# ========== BRANCH APIs ==========

@app.post("/api/branches/")
async def create_branch(
    name: str = Form(...), 
    location: str = Form(None), 
    description: str = Form(None), 
    db: Session = Depends(get_db)
):
    """Tạo chi nhánh mới"""
    db_branch = Branch(name=name, location=location, description=description)
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    return {
        "id": db_branch.id, 
        "name": db_branch.name, 
        "location": db_branch.location,
        "description": db_branch.description
    }

@app.get("/api/branches/")
async def get_branches(db: Session = Depends(get_db)):
    """Lấy danh sách tất cả chi nhánh"""
    branches = db.query(Branch).filter(Branch.is_active == True).all()
    return [{
        "id": b.id, 
        "name": b.name, 
        "location": b.location,
        "description": b.description
    } for b in branches]

@app.get("/api/branches/{branch_id}")
async def get_branch(branch_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin chi nhánh"""
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_active == True).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return {
        "id": branch.id, 
        "name": branch.name, 
        "location": branch.location,
        "description": branch.description
    }

@app.delete("/api/branches/{branch_id}")
async def delete_branch(branch_id: int, db: Session = Depends(get_db)):
    """
    Xóa chi nhánh (hard delete) và toàn bộ dữ liệu liên quan trong database:
    - Xóa tất cả orders thuộc chi nhánh
    - Xóa tất cả recognition logs thuộc chi nhánh
    - Sau đó xóa chính bản ghi chi nhánh
    """
    try:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")

        # Xóa tất cả orders của chi nhánh này
        orders = db.query(Order).filter(Order.branch_id == branch_id).all()
        for order in orders:
            db.delete(order)
        logging.getLogger(__name__).info(f"Deleted {len(orders)} orders for branch {branch_id}")

        # Xóa tất cả recognition logs của chi nhánh này
        logs = db.query(RecognitionLog).filter(RecognitionLog.branch_id == branch_id).all()
        for log in logs:
            db.delete(log)
        logging.getLogger(__name__).info(f"Deleted {len(logs)} recognition logs for branch {branch_id}")

        # Xóa chi nhánh
        db.delete(branch)
        db.commit()

        return {"message": "Branch deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error deleting branch {branch_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting branch: {str(e)}")

# ========== CUSTOMER APIs ==========

@app.post("/api/customers/")
async def register_customer(
    name: str = Form(...),
    image: UploadFile = File(...),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Đăng ký khách hàng mới với ảnh khuôn mặt"""
    # Đọc ảnh vào memory
    image_data = await image.read()
    file_extension = Path(image.filename).suffix or ".jpg"
    
    # Lưu tạm vào local để encode face (face_recognition cần file path)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(image_data)
        temp_image_path = temp_file.name
    
    try:
        # Kiểm tra xem có thể encode face không
        encoding = face_service.encode_face(temp_image_path)
        if encoding is None:
            raise HTTPException(status_code=400, detail="Không thể nhận diện khuôn mặt trong ảnh")
        
        # Lưu vào database để lấy ID thực tế
        db_customer = Customer(
            name=name,
            face_encoding_path="",  # Sẽ cập nhật sau
            phone=phone,
            email=email
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        
        # Upload ảnh lên MinIO với ID thực tế
        minio_object_path = f"images/customer_{db_customer.id}{file_extension}"
        content_type = f"image/{file_extension[1:]}" if file_extension else "image/jpeg"
        
        if not minio_service.upload_file(minio_object_path, image_data, content_type):
            raise HTTPException(status_code=500, detail="Không thể lưu ảnh lên MinIO")
        
        # Lưu face encoding với customer_id thực tế (sử dụng temp file)
        face_service.save_face_encoding(str(db_customer.id), name, temp_image_path)
        
        # Cập nhật path trong database (lưu MinIO object path)
        db_customer.face_encoding_path = minio_object_path
        db.commit()
        
        return {
            "id": db_customer.id,
            "name": db_customer.name,
            "phone": db_customer.phone,
            "email": db_customer.email,
            "face_encoding_path": get_image_url(minio_object_path),
            "message": "Customer registered successfully"
        }
    finally:
        # Xóa file tạm
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

@app.get("/api/customers/")
async def get_customers(db: Session = Depends(get_db)):
    """Lấy danh sách khách hàng"""
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    return [{
        "id": c.id, 
        "name": c.name, 
        "phone": c.phone,
        "email": c.email,
        "face_encoding_path": get_image_url(c.face_encoding_path)
    } for c in customers]

@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin khách hàng"""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "face_encoding_path": get_image_url(customer.face_encoding_path)
    }

@app.put("/api/customers/{customer_id}")
async def update_customer(
    customer_id: int,
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin khách hàng"""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Cập nhật thông tin cơ bản
    if name is not None:
        customer.name = name
    if phone is not None:
        customer.phone = phone
    if email is not None:
        customer.email = email
    
    # Cập nhật ảnh nếu có
    if image:
        # Xóa ảnh cũ từ MinIO nếu có
        if customer.face_encoding_path:
            # Nếu là MinIO path (images/...), xóa từ MinIO
            if customer.face_encoding_path.startswith('images/'):
                minio_service.delete_file(customer.face_encoding_path)
            # Nếu là path cũ (local), cũng thử xóa từ MinIO
            else:
                old_path = customer.face_encoding_path.replace('/app/uploads/', '').replace('/uploads/', '').replace('uploads/', '').replace(f'{settings.UPLOAD_DIR}/', '')
                minio_object_path = f"images/{old_path}"
                minio_service.delete_file(minio_object_path)
        
        # Đọc ảnh mới
        image_data = await image.read()
        file_extension = Path(image.filename).suffix or ".jpg"
        
        # Lưu tạm để encode face
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(image_data)
            temp_image_path = temp_file.name
        
        try:
            # Kiểm tra và encode face
            encoding = face_service.encode_face(temp_image_path)
            if encoding is None:
                raise HTTPException(status_code=400, detail="Không thể nhận diện khuôn mặt trong ảnh")
            
            # Upload ảnh mới lên MinIO
            minio_object_path = f"images/customer_{customer_id}{file_extension}"
            content_type = f"image/{file_extension[1:]}" if file_extension else "image/jpeg"
            
            if not minio_service.upload_file(minio_object_path, image_data, content_type):
                raise HTTPException(status_code=500, detail="Không thể lưu ảnh lên MinIO")
            
            # Lưu face encoding mới
            face_service.save_face_encoding(str(customer_id), customer.name, temp_image_path)
            
            # Cập nhật path trong database (lưu MinIO object path)
            customer.face_encoding_path = minio_object_path
        finally:
            # Xóa file tạm
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
    
    db.commit()
    db.refresh(customer)
    
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "face_encoding_path": get_image_url(customer.face_encoding_path),
        "message": "Customer updated successfully"
    }

@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Xóa khách hàng (hard delete - xóa thật sự khỏi database)"""
    try:
        # Không filter is_active để có thể xóa cả những khách đã bị soft delete trước đó
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Xóa tất cả orders liên quan trước (để tránh foreign key constraint violation)
        orders = db.query(Order).filter(Order.customer_id == customer_id).all()
        for order in orders:
            db.delete(order)
        logging.getLogger(__name__).info(f"Deleted {len(orders)} orders for customer {customer_id}")
        
        # Xóa tất cả recognition logs liên quan
        logs = db.query(RecognitionLog).filter(RecognitionLog.customer_id == customer_id).all()
        for log in logs:
            db.delete(log)
        logging.getLogger(__name__).info(f"Deleted {len(logs)} recognition logs for customer {customer_id}")
        
        # Xóa file ảnh từ MinIO nếu có
        if customer.face_encoding_path:
            try:
                # Nếu là MinIO path (images/...), xóa trực tiếp
                if customer.face_encoding_path.startswith('images/'):
                    minio_service.delete_file(customer.face_encoding_path)
                    logging.getLogger(__name__).info(f"Deleted image from MinIO: {customer.face_encoding_path}")
                else:
                    # Nếu là path cũ (local), thử chuyển sang MinIO path và xóa
                    image_path_str = customer.face_encoding_path.replace('/code/app/uploads/', '').replace('/app/uploads/', '').replace('/uploads/', '').replace('uploads/', '').replace(f'{settings.UPLOAD_DIR}/', '')
                    if image_path_str.startswith('/'):
                        image_path_str = image_path_str[1:]
                    minio_object_path = f"images/{image_path_str}"
                    minio_service.delete_file(minio_object_path)
                    logging.getLogger(__name__).info(f"Deleted image from MinIO: {minio_object_path}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Could not delete image from MinIO: {e}")
        
        # Xóa face encoding từ MinIO nếu có
        try:
            encoding_object_path = f"encodings/{customer_id}.pkl"
            if minio_service.file_exists(encoding_object_path):
                minio_service.delete_file(encoding_object_path)
                logging.getLogger(__name__).info(f"Deleted face encoding from MinIO: {encoding_object_path}")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not delete face encoding from MinIO: {e}")
        
        # Xóa khỏi memory cache của face_service
        try:
            if str(customer_id) in face_service.known_encodings:
                del face_service.known_encodings[str(customer_id)]
            if str(customer_id) in face_service.known_names:
                del face_service.known_names[str(customer_id)]
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not delete face encoding from cache: {e}")
        
        # Hard delete: xóa thật sự khỏi database
        db.delete(customer)
        db.commit()
        
        return {"message": "Customer deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error deleting customer {customer_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting customer: {str(e)}")

# ========== ORDER APIs ==========

@app.post("/api/orders/")
async def create_order(
    customer_id: int = Form(...),
    branch_id: int = Form(...),
    items: str = Form(...),  # JSON string
    total_amount: float = Form(...),
    db: Session = Depends(get_db)
):
    """Tạo đơn hàng mới"""
    # Validate customer và branch
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_active == True).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Parse items JSON
    try:
        items_data = json.loads(items)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid items JSON format")
    
    db_order = Order(
        customer_id=customer_id,
        branch_id=branch_id,
        items=items,
        total_amount=total_amount,
        status="completed"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return {
        "id": db_order.id,
        "customer_id": db_order.customer_id,
        "branch_id": db_order.branch_id,
        "items": items_data,
        "total_amount": db_order.total_amount,
        "status": db_order.status,
        "created_at": db_order.created_at.isoformat()
    }

@app.get("/api/customers/{customer_id}/orders")
async def get_customer_orders(customer_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Lấy danh sách đơn hàng của khách hàng"""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    orders = db.query(Order).filter(
        Order.customer_id == customer_id
    ).order_by(desc(Order.created_at)).limit(limit).all()
    
    return [{
        "id": o.id,
        "branch_id": o.branch_id,
        "items": json.loads(o.items) if o.items else [],
        "total_amount": o.total_amount,
        "status": o.status,
        "created_at": o.created_at.isoformat()
    } for o in orders]

@app.get("/api/customers/{customer_id}/orders/latest")
async def get_customer_latest_order(customer_id: int, db: Session = Depends(get_db)):
    """Lấy đơn hàng gần nhất của khách hàng"""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    order = db.query(Order).filter(
        Order.customer_id == customer_id
    ).order_by(desc(Order.created_at)).first()
    
    if not order:
        return None
    
    return {
        "id": order.id,
        "branch_id": order.branch_id,
        "items": json.loads(order.items) if order.items else [],
        "total_amount": order.total_amount,
        "status": order.status,
        "created_at": order.created_at.isoformat()
    }

@app.get("/api/customers/{customer_id}/details")
async def get_customer_details(customer_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết của khách hàng: branches visited, items per branch, visit timeline, frequent combos"""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(desc(Order.created_at)).all()
    
    if not orders:
        return {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "total_items_all_branches": 0,
            "branches_visited": [],
            "items_by_branch": {},
            "visit_timeline": [],
            "frequent_combos": []
        }
    
    from collections import defaultdict, Counter
    from datetime import datetime
    
    # Tính toán thống kê
    total_items_all = 0
    branches_data = {}  # {branch_id: {name, items_count, items_list, orders_count, total_amount}}
    visit_timeline = []  # [{date, branch_name, items, total_amount}]
    all_item_combos = []  # Danh sách các combo (set of items) trong mỗi order
    
    for order in orders:
        branch = db.query(Branch).filter(Branch.id == order.branch_id).first()
        branch_name = branch.name if branch else f"Chi nhánh {order.branch_id}"
        
        items = json.loads(order.items) if order.items else []
        items_list = []
        items_count = 0
        order_item_names = []
        
        for item in items:
            name = item.get("name") if isinstance(item, dict) else str(item)
            qty = item.get("quantity", 1) if isinstance(item, dict) else 1
            price = item.get("price", 0) if isinstance(item, dict) else 0
            items_count += qty
            total_items_all += qty
            items_list.append({
                "name": name,
                "quantity": qty,
                "price": price
            })
            order_item_names.extend([name] * qty)  # Thêm tên món theo số lượng
        
        # Cập nhật thông tin branch
        if order.branch_id not in branches_data:
            branches_data[order.branch_id] = {
                "branch_id": order.branch_id,
                "branch_name": branch_name,
                "items_count": 0,
                "items_list": [],
                "orders_count": 0,
                "total_amount": 0.0
            }
        
        branches_data[order.branch_id]["items_count"] += items_count
        branches_data[order.branch_id]["orders_count"] += 1
        branches_data[order.branch_id]["total_amount"] += order.total_amount or 0.0
        
        # Thêm items vào danh sách (gộp các món trùng lặp)
        for item in items_list:
            existing = next((x for x in branches_data[order.branch_id]["items_list"] if x["name"] == item["name"]), None)
            if existing:
                existing["quantity"] += item["quantity"]
            else:
                branches_data[order.branch_id]["items_list"].append(item)
        
        # Thêm vào timeline
        visit_timeline.append({
            "date": order.created_at.isoformat(),
            "branch_id": order.branch_id,
            "branch_name": branch_name,
            "items": items_list,
            "total_amount": order.total_amount or 0.0,
            "order_id": order.id
        })
        
        # Lưu combo (set các món trong order này)
        if order_item_names:
            combo_set = tuple(sorted(set(order_item_names)))  # Sorted tuple để so sánh
            all_item_combos.append(combo_set)
    
    # Tìm các combo thường mua (combo xuất hiện >= 2 lần)
    combo_counter = Counter(all_item_combos)
    frequent_combos = []
    for combo, count in combo_counter.items():
        if count >= 2:  # Combo xuất hiện ít nhất 2 lần
            frequent_combos.append({
                "items": list(combo),
                "frequency": count
            })
    
    # Sắp xếp combo theo frequency
    frequent_combos.sort(key=lambda x: x["frequency"], reverse=True)
    
    # Chuyển branches_data thành list
    branches_visited = list(branches_data.values())
    
    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "total_items_all_branches": total_items_all,
        "branches_visited": branches_visited,
        "items_by_branch": {str(bid): branches_data[bid] for bid in branches_data.keys()},
        "visit_timeline": visit_timeline,
        "frequent_combos": frequent_combos
    }

# ========== FACE RECOGNITION HELPERS ==========

def _build_customer_stats(db: Session, customer_id: int, current_branch_id: Optional[int] = None):
    """Tính toán thống kê cho khách: số lần đến, món đã mua, theo từng chi nhánh."""
    orders = db.query(Order).filter(Order.customer_id == customer_id).all()
    if not orders:
        return {
            "total_orders": 0,
            "total_items": 0,
            "branches": [],
            "by_branch": {},
            "favorite_items": [],
            "current_branch_menu": [],
        }

    from collections import defaultdict

    total_orders = len(orders)
    total_items = 0
    by_branch = defaultdict(lambda: {"orders": 0, "items": 0, "total_amount": 0.0})
    item_counter = defaultdict(int)
    branch_menu = defaultdict(set)

    for o in orders:
        by_branch[o.branch_id]["orders"] += 1
        by_branch[o.branch_id]["total_amount"] += o.total_amount or 0.0
        items = json.loads(o.items) if o.items else []
        for it in items:
            name = it.get("name") if isinstance(it, dict) else str(it)
            qty = it.get("quantity", 1) if isinstance(it, dict) else 1
            total_items += qty
            by_branch[o.branch_id]["items"] += qty
            item_counter[name] += qty
            branch_menu[o.branch_id].add(name)

    branches = list(by_branch.keys())
    favorite_items = sorted(
        [{"name": n, "count": c} for n, c in item_counter.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    current_menu = sorted(branch_menu.get(current_branch_id, [])) if current_branch_id else []

    return {
        "total_orders": total_orders,
        "total_items": total_items,
        "branches": branches,
        "by_branch": by_branch,
        "favorite_items": favorite_items,
        "current_branch_menu": current_menu,
    }


def _auto_register_customer_from_image(
    db: Session,
    image_path: Path,
    file_extension: str,
) -> Optional[Customer]:
    """
    Tự động đăng ký khách hàng mới dựa trên khuôn mặt từ ảnh:
    - Tạo Customer mới với tên mặc định.
    - Lưu encoding khuôn mặt để lần sau nhận diện lại.
    """
    customer = Customer(
        name="Guest",
        face_encoding_path="",  # Sẽ cập nhật sau
        phone=None,
        email=None,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    try:
        # Đọc ảnh từ file tạm
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Upload ảnh lên MinIO
        minio_object_path = f"images/customer_{customer.id}{file_extension}"
        content_type = f"image/{file_extension[1:]}" if file_extension else "image/jpeg"
        
        if not minio_service.upload_file(minio_object_path, image_data, content_type):
            logging.getLogger(__name__).warning(f"Could not upload image to MinIO for customer {customer.id}")
        
        # Cố gắng lưu face encoding, nếu thất bại vẫn giữ lại customer
        saved = face_service.save_face_encoding(str(customer.id), customer.name, str(image_path))
        if not saved:
            # Log cảnh báo nhưng KHÔNG xóa customer, để vẫn có thể dùng cho demo / order
            logging.getLogger(__name__).warning(
                f"Could not save face encoding for customer {customer.id} from image {image_path}"
            )

        # Lưu MinIO object path
        customer.face_encoding_path = minio_object_path
        db.commit()
        db.refresh(customer)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in _auto_register_customer_from_image: {e}", exc_info=True)
        # Vẫn trả về customer dù có lỗi
    
    return customer


# ========== FACE RECOGNITION APIs ==========

@app.post("/api/recognize/")
async def recognize_face(
    image: UploadFile = File(...),
    branch_id: Optional[int] = Form(None),
    use_spark: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Nhận diện khuôn mặt khách hàng (toàn hệ thống).
    - Nếu nhận diện được: trả về thông tin khách + thống kê + đơn hàng gần nhất.
    - Nếu KHÔNG nhận diện được: tự động đăng ký khách mới dựa trên khuôn mặt.
    """
    # Suy ra branch mặc định nếu không truyền
    if branch_id is None and getattr(settings, "DEFAULT_BRANCH_ID", 0):
        branch_id = settings.DEFAULT_BRANCH_ID or None
    
    # Lưu ảnh tạm
    file_extension = Path(image.filename).suffix or ".jpg"
    task_id = str(uuid.uuid4())
    image_path = upload_dir / f"temp_{task_id}{file_extension}"
    
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    if use_spark:
        # Gửi task vào Kafka để Spark xử lý
        producer.send_recognition_task(task_id, str(image_path), branch_id)
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Task sent to Spark for processing"
        }

    # Xử lý trực tiếp
    if branch_id:
        # Ưu tiên so sánh với khách đã từng đặt hàng tại branch này
        branch_orders = db.query(Order).filter(Order.branch_id == branch_id).all()
        branch_customer_ids = list({o.customer_id for o in branch_orders})
        if branch_customer_ids:
            result, confidence = face_service.recognize_face_in_branch(
                str(image_path), 
                [str(cid) for cid in branch_customer_ids]
            )
        else:
            result, confidence = face_service.recognize_face(str(image_path))
    else:
        result, confidence = face_service.recognize_face(str(image_path))
    
    customer: Optional[Customer] = None
    auto_registered = False

    if result and confidence > 0.6:
        customer_id = int(result["customer_id"])
        customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    else:
        # Không nhận diện được -> tự động đăng ký khách mới
        customer = _auto_register_customer_from_image(db, image_path, file_extension)
        auto_registered = customer is not None
        confidence = confidence or 0.0

    customer_id = customer.id if customer else None

    # Lưu log
    log = RecognitionLog(
        customer_id=customer_id,
        branch_id=branch_id,
        image_path=str(image_path),
        confidence=str(confidence),
        recognized=customer is not None
    )
    db.add(log)
    db.commit()
    
    if not customer:
        return {
            "task_id": task_id,
            "status": "error",
            "recognized": False,
            "message": "Không thể nhận diện hoặc đăng ký khách hàng từ ảnh này."
        }

    # Đơn hàng gần nhất
    latest_order = db.query(Order).filter(
        Order.customer_id == customer.id
    ).order_by(desc(Order.created_at)).first()
    
    order_data = None
    if latest_order:
        order_data = {
            "id": latest_order.id,
            "branch_id": latest_order.branch_id,
            "items": json.loads(latest_order.items) if latest_order.items else [],
            "total_amount": latest_order.total_amount,
            "status": latest_order.status,
            "created_at": latest_order.created_at.isoformat()
        }
    
    stats = _build_customer_stats(db, customer.id, current_branch_id=branch_id)
    
    return {
        "task_id": task_id,
        "status": "recognized" if not auto_registered else "auto_registered",
        "recognized": True,
        "auto_registered": auto_registered,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email
        },
        "latest_order": order_data,
        "confidence": confidence,
        "stats": stats,
        "message": (
            f"Khách hàng mới đã được tạo tự động với ID {customer.id}."
            if auto_registered
            else f"Khách hàng {customer.name} đã được nhận diện."
        )
    }

@app.post("/api/branches/{branch_id}/recognize")
async def recognize_at_branch(
    branch_id: int,
    image: UploadFile = File(...),
    use_spark: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    API cho từng chi nhánh (máy tại quán, mobile/web chi nhánh).
    Logic:
    - Nếu nhận diện được: trả về thông tin khách + thống kê + đơn hàng gần nhất.
    - Nếu KHÔNG nhận diện được: tự động đăng ký khách mới dựa trên khuôn mặt tại chi nhánh này.
    """
    
    # Kiểm tra branch tồn tại và đang active
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_active == True).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Lưu ảnh tạm
    file_extension = Path(image.filename).suffix
    task_id = str(uuid.uuid4())
    image_path = upload_dir / f"branch_{branch_id}_{task_id}{file_extension}"
    
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    if use_spark:
        # Gửi task vào Kafka
        producer.send_recognition_task(task_id, str(image_path), branch_id)
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Recognition task sent to Spark for processing"
        }

    # Xử lý trực tiếp
    # Trước tiên kiểm tra xem có face trong ảnh không
    test_encoding = face_service.encode_face(str(image_path))
    if test_encoding is None:
        # Không có face trong ảnh -> không tạo khách mới, chỉ trả về lỗi
        return {
            "status": "no_face",
            "recognized": False,
            "branch_id": branch_id,
            "branch_name": branch.name,
            "message": "Không phát hiện khuôn mặt trong ảnh. Vui lòng đưa mặt vào camera."
        }
    
    # Bước 1: So sánh nhanh với customers trong branch này trước
    branch_orders = db.query(Order).filter(Order.branch_id == branch_id).all()
    branch_customer_ids = list({o.customer_id for o in branch_orders})
    
    result = None
    confidence = 0.0
    
    if branch_customer_ids:
        result, confidence = face_service.recognize_face_in_branch(
            str(image_path), 
            [str(cid) for cid in branch_customer_ids],
            tolerance=0.6
        )
    
    customer: Optional[Customer] = None
    auto_registered = False

    if result and confidence > 0.6:
        # Nhận diện được trong branch -> trả về ngay
        customer_id = int(result["customer_id"])
        customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    else:
        # Không nhận diện được trong branch -> so sánh kỹ với TẤT CẢ customers trong hệ thống
        # với tolerance thấp hơn để chắc chắn không có customer tương tự
        all_customers = db.query(Customer).filter(Customer.is_active == True).all()
        all_customer_ids = [str(c.id) for c in all_customers]
        
        if all_customer_ids:
            # So sánh với tolerance thấp hơn (0.5) để chắc chắn hơn
            result_all, confidence_all = face_service.recognize_face_in_branch(
                str(image_path),
                all_customer_ids,
                tolerance=0.5  # Tolerance thấp hơn để chắc chắn hơn
            )
            
            if result_all and confidence_all > 0.5:
                # Tìm thấy customer tương tự trong hệ thống -> dùng customer đó
                customer_id = int(result_all["customer_id"])
                customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
                confidence = confidence_all
            else:
                # Chắc chắn không có customer tương tự -> tạo khách mới
                # Trả về status "processing_new_customer" để frontend pause streaming
                customer = _auto_register_customer_from_image(db, image_path, file_extension)
                auto_registered = customer is not None
                confidence = confidence_all if confidence_all else 0.0
        else:
            # Không có customer nào trong hệ thống -> tạo khách mới
            customer = _auto_register_customer_from_image(db, image_path, file_extension)
            auto_registered = customer is not None
            confidence = 0.0

    customer_id = customer.id if customer else None

    # Lưu log
    log = RecognitionLog(
        customer_id=customer_id,
        branch_id=branch_id,
        image_path=str(image_path),
        confidence=str(confidence),
        recognized=customer is not None
    )
    db.add(log)
    db.commit()
    
    if not customer:
        return {
            "status": "error",
            "recognized": False,
            "branch_id": branch_id,
            "branch_name": branch.name,
            "message": "Không thể nhận diện hoặc đăng ký khách hàng từ ảnh này."
        }

    # Lấy thông tin khách và đơn hàng gần nhất
    latest_order = db.query(Order).filter(
        Order.customer_id == customer.id
    ).order_by(desc(Order.created_at)).first()
    
    order_data = None
    if latest_order:
        order_data = {
            "id": latest_order.id,
            "branch_id": latest_order.branch_id,
            "items": json.loads(latest_order.items) if latest_order.items else [],
            "total_amount": latest_order.total_amount,
            "status": latest_order.status,
            "created_at": latest_order.created_at.isoformat()
        }

    stats = _build_customer_stats(db, customer.id, current_branch_id=branch_id)
    
    # Lấy frequent combos từ customer details (chỉ cho khách hàng đã có lịch sử)
    frequent_combos = []
    if not auto_registered:  # Chỉ lấy combos cho khách hàng đã có lịch sử
        try:
            orders = db.query(Order).filter(Order.customer_id == customer.id).order_by(desc(Order.created_at)).all()
            if orders:
                from collections import Counter
                all_item_combos = []
                for order in orders:
                    items = json.loads(order.items) if order.items else []
                    order_item_names = []
                    for item in items:
                        name = item.get("name") if isinstance(item, dict) else str(item)
                        qty = item.get("quantity", 1) if isinstance(item, dict) else 1
                        order_item_names.extend([name] * qty)
                    if order_item_names:
                        combo_set = tuple(sorted(set(order_item_names)))
                        all_item_combos.append(combo_set)
                
                combo_counter = Counter(all_item_combos)
                for combo, count in combo_counter.items():
                    if count >= 2:  # Combo xuất hiện ít nhất 2 lần
                        frequent_combos.append({
                            "items": list(combo),
                            "frequency": count
                        })
                frequent_combos.sort(key=lambda x: x["frequency"], reverse=True)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not load frequent combos for customer {customer.id}: {e}")
            frequent_combos = []
    
    # Nếu là khách mới được tạo tự động, trả về status "processing_new_customer" 
    # để frontend pause streaming và mở modal thanh toán
    status = "recognized"
    if auto_registered:
        status = "processing_new_customer"  # Frontend sẽ pause streaming khi nhận status này
    
    return {
        "status": status,
        "recognized": True,
        "auto_registered": auto_registered,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email
        },
        "latest_order": order_data,
        "confidence": confidence,
        "stats": stats,
        "frequent_combos": frequent_combos,
        "branch_id": branch_id,
        "branch_name": branch.name,
        "message": (
            f"Khách hàng mới đã được tạo tự động với ID {customer.id} tại chi nhánh {branch.name}. Vui lòng thanh toán."
            if auto_registered
            else f"Khách hàng {customer.name} đã được nhận diện tại chi nhánh {branch.name}."
        )
    }

@app.get("/api/logs/")
async def get_logs(branch_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db)):
    """Lấy logs nhận diện"""
    query = db.query(RecognitionLog)
    if branch_id:
        query = query.filter(RecognitionLog.branch_id == branch_id)
    logs = query.order_by(desc(RecognitionLog.created_at)).limit(limit).all()
    
    return [{
        "id": log.id,
        "customer_id": log.customer_id,
        "branch_id": log.branch_id,
        "recognized": log.recognized,
        "confidence": log.confidence,
        "created_at": log.created_at.isoformat()
    } for log in logs]

# ========== DATABASE VIEW APIs ==========

@app.get("/api/stats/")
async def get_stats(db: Session = Depends(get_db)):
    """Lấy thống kê tổng quan"""
    from sqlalchemy import func
    
    total_customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_branches = db.query(func.count(Branch.id)).filter(Branch.is_active == True).scalar()
    total_logs = db.query(func.count(RecognitionLog.id)).scalar()
    
    # Tỷ lệ nhận diện thành công
    successful_logs = db.query(func.count(RecognitionLog.id)).filter(RecognitionLog.recognized == True).scalar()
    success_rate = (successful_logs / total_logs * 100) if total_logs > 0 else 0
    
    # Tổng doanh thu
    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0
    
    return {
        "total_customers": total_customers,
        "total_orders": total_orders,
        "total_branches": total_branches,
        "total_logs": total_logs,
        "success_rate": round(success_rate, 2),
        "total_revenue": float(total_revenue)
    }

@app.get("/api/orders/")
async def get_orders(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Lấy danh sách đơn hàng với thông tin chi tiết"""
    orders = db.query(Order).order_by(desc(Order.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for o in orders:
        customer = db.query(Customer).filter(Customer.id == o.customer_id, Customer.is_active == True).first()
        branch = db.query(Branch).filter(Branch.id == o.branch_id, Branch.is_active == True).first()
        
        result.append({
            "id": o.id,
            "created_at": o.created_at.isoformat(),
            "customer_id": o.customer_id,
            "customer_name": customer.name if customer else "N/A",
            "branch_id": o.branch_id,
            "branch_name": branch.name if branch else "N/A",
            "items": json.loads(o.items) if o.items else [],
            "total_amount": o.total_amount,
            "status": o.status
        })
    
    return result

@app.get("/api/orders/stats/by-branch")
async def get_orders_stats_by_branch(db: Session = Depends(get_db)):
    """Thống kê đơn hàng theo chi nhánh"""
    from sqlalchemy import func
    
    stats = db.query(
        Branch.id,
        Branch.name,
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers')
    ).join(Order, Branch.id == Order.branch_id, isouter=True).group_by(Branch.id, Branch.name).all()
    
    return [{
        "branch_id": s.id,
        "branch_name": s.name,
        "total_orders": s.total_orders or 0,
        "total_revenue": float(s.total_revenue or 0),
        "unique_customers": s.unique_customers or 0
    } for s in stats]

@app.get("/api/orders/stats/by-customer")
async def get_orders_stats_by_customer(limit: int = 20, db: Session = Depends(get_db)):
    """Thống kê đơn hàng theo khách hàng"""
    from sqlalchemy import func
    
    stats = db.query(
        Customer.id,
        Customer.name,
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_spent'),
        func.avg(Order.total_amount).label('avg_order_value')
    ).filter(Customer.is_active == True).join(Order, Customer.id == Order.customer_id, isouter=True).group_by(Customer.id, Customer.name).order_by(func.sum(Order.total_amount).desc()).limit(limit).all()
    
    return [{
        "customer_id": s.id,
        "customer_name": s.name,
        "total_orders": s.total_orders or 0,
        "total_spent": float(s.total_spent or 0),
        "avg_order_value": float(s.avg_order_value or 0)
    } for s in stats]

@app.get("/api/recognition-logs/detailed")
async def get_detailed_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Lấy logs nhận diện với thông tin chi tiết"""
    logs = db.query(RecognitionLog).order_by(desc(RecognitionLog.created_at)).limit(limit).all()
    
    result = []
    for log in logs:
        customer = None
        branch = None
        if log.customer_id:
            customer = db.query(Customer).filter(Customer.id == log.customer_id, Customer.is_active == True).first()
        if log.branch_id:
            branch = db.query(Branch).filter(Branch.id == log.branch_id, Branch.is_active == True).first()
        
        result.append({
            "id": log.id,
            "created_at": log.created_at.isoformat(),
            "customer_id": log.customer_id,
            "customer_name": customer.name if customer else None,
            "branch_id": log.branch_id,
            "branch_name": branch.name if branch else None,
            "recognized": log.recognized,
            "confidence": log.confidence,
            "image_path": log.image_path
        })
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
