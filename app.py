from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, StudentDetail, MenuItem, Order, OrderDetail
# werkzeug.security.check_password_hash is not used directly because
# password checking is handled by User.check_password(); remove unused import
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import google.generativeai as genai
import os
import requests
import io
from flask import Response, send_file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-canteen-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Nạp biến môi trường từ file .env
load_dotenv()

# Lấy API key từ .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Khởi tạo model Gemini - ĐÃ SỬA THÀNH MODEL MỚI
    model = genai.GenerativeModel("gemini-2.5-pro")
else:
    print("⚠️  Không tìm thấy GEMINI_API_KEY trong file .env")
    model = None

db.init_app(app)


@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    total_qty = sum(item.get('quantity', 0) for item in cart.values())
    return dict(cart_quantity=total_qty)

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Tạo dữ liệu mẫu
def create_sample_data():
    # Tạo admin
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # Tạo sinh viên mẫu
    if User.query.filter_by(role='student').count() == 0:
        students_data = [
            {'username': 'sv001', 'ma_sv': 'B20DCCN001', 'ho_ten': 'Nguyễn Văn A', 
             'nganh_hoc': 'Công nghệ thông tin', 'email': 'sv001@student.edu.vn', 'sdt': '0123456789'},
            {'username': 'sv002', 'ma_sv': 'B20DCCN002', 'ho_ten': 'Trần Thị B', 
             'nganh_hoc': 'Kỹ thuật phần mềm', 'email': 'sv002@student.edu.vn', 'sdt': '0123456790'},
        ]
        
        for data in students_data:
            user = User(username=data['username'], role='student')
            user.set_password(data['username'])
            db.session.add(user)
            db.session.flush()
            
            student = StudentDetail(
                user_id=user.id,
                ma_sv=data['ma_sv'],
                ho_ten=data['ho_ten'],
                nganh_hoc=data['nganh_hoc'],
                email=data['email'],
                sdt=data['sdt']
            )
            db.session.add(student)
        
        db.session.commit()

    # Tạo menu mẫu
    if MenuItem.query.count() == 0:
        menu_items = [
            {'ten_mon': 'Cơm gà xối mỡ', 'gia': 35000, 'loai': 'Món chính'},
            {'ten_mon': 'Phở bò', 'gia': 40000, 'loai': 'Món chính'},
            {'ten_mon': 'Bún chả', 'gia': 30000, 'loai': 'Món chính'},
            {'ten_mon': 'Bánh mì pate', 'gia': 15000, 'loai': 'Đồ ăn nhanh'},
            {'ten_mon': 'Xôi gà', 'gia': 25000, 'loai': 'Đồ ăn sáng'},
            {'ten_mon': 'Cafe sữa', 'gia': 15000, 'loai': 'Đồ uống'},
        ]
        
        for item in menu_items:
            menu_item = MenuItem(**item)
            db.session.add(menu_item)
        
        db.session.commit()

# ========== ROUTES CƠ BẢN ==========

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('menu'))
    # Unauthenticated users see the public landing page
    return redirect(url_for('landing'))


@app.route('/landing')
def landing():
    # Public homepage / landing
    return render_template('home.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Simple validation
        if not name or not email or not message:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return redirect(url_for('contact'))

        # For now, we just flash a success message. Integrate email later if needed.
        flash('Cảm ơn bạn! Chúng tôi đã nhận được phản hồi.', 'success')
        return redirect(url_for('landing'))

    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('menu'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất!', 'success')
    return redirect(url_for('login'))

# ========== STUDENT ROUTES ==========

@app.route('/menu')
@login_required
def menu():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    # Load available menu items
    menu_items = MenuItem.query.order_by(MenuItem.loai, MenuItem.ten_mon).all()

    # Enhance items with image and description for better UI without changing DB schema
    sample_descriptions = {
        'Cơm gà xối mỡ': 'Cơm gà vàng ruộm, thấm vị, ăn kèm dưa leo và nước sốt đặc trưng.',
        'Phở bò': 'Phở thơm, nước dùng đậm đà, thịt bò mềm và bánh phở tươi.',
        'Bún chả': 'Bún tươi kèm chả nướng, nước mắm chua ngọt và rau sống.',
        'Bánh mì pate': 'Bánh mì giòn rụm, pate thơm béo, thêm dưa chuột và hành chua.',
        'Xôi gà': 'Xôi dẻo, gà xé thấm gia vị, rắc ruốc và hành phi.' ,
        'Cafe sữa': 'Cà phê phin thơm nồng, hòa quyện sữa đặc ngọt dịu.'
    }

    # Map display names to slug keys used by the server-side proxy
    name_to_key = {
        'Phở bò': 'pho_bo',
        'Cơm gà xối mỡ': 'com_ga_xoi_mo',
        'Bún chả': 'bun_cha',
        'Bánh mì pate': 'banh_mi_pate',
        'Xôi gà': 'xoi_ga',
        'Cafe sữa': 'cafe_sua'
    }

    for idx, item in enumerate(menu_items):
        # assign rotating placeholder images (static SVGs added earlier)
        # choose an illustrative image from Unsplash using query keywords (no external download needed)
        # Map known dish names to queries for better matches, otherwise fallback to category
        # First prefer explicit image URLs provided for known dishes (these come from the user)
        # Use a server-side proxy for the specific images to avoid hotlink/CORS issues
        # We expose them via the route '/remote_image/<key>' below.
        # Provide a simple emoji icon for each dish to use as a fallback or preferred display
        icon_map = {
            'Phở bò': '🍜',
            'Cơm gà xối mỡ': '🍗',
            'Bún chả': '🍖',
            'Bánh mì pate': '🥖',
            'Xôi gà': '🍚',
            'Cafe sữa': '☕'
        }

        if item.ten_mon in name_to_key:
            key = name_to_key[item.ten_mon]
            item.image = url_for('remote_image', name=key)
        else:
            # Fallback to Unsplash if no explicit mapping exists
            queries = {
                'Cơm gà xối mỡ': 'chicken rice vietnamese',
                'Phở bò': 'vietnamese pho beef soup',
                'Bún chả': 'bun cha vietnamese grill pork',
                'Bánh mì pate': 'banh mi sandwich',
                'Xôi gà': 'sticky rice chicken',
                'Cafe sữa': 'vietnamese coffee'
            }
            q = queries.get(item.ten_mon, item.loai or 'food')
            item.image = f'https://source.unsplash.com/800x480/?{q.replace(" ", ",")}'

        item.icon_emoji = icon_map.get(item.ten_mon, '🍽️')

        # description: use sample if available else generic based on category
        item.description = sample_descriptions.get(item.ten_mon,
                                                   f"{item.ten_mon} — một lựa chọn ngon thuộc hạng {item.loai}.")

    return render_template('menu.html', menu_items=menu_items)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    if current_user.role == 'admin':
        flash('Admin không thể đặt hàng!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Normalize item id and quantity
    form_item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))

    # Ensure we query with an int id and always store keys as strings in session
    menu_item = MenuItem.query.get(int(form_item_id))
    if not menu_item:
        flash('Món ăn không tồn tại!', 'error')
        return redirect(url_for('menu'))
    item_id = str(menu_item.id)

    cart = session.get('cart', {})
    if item_id in cart:
        cart[item_id]['quantity'] += quantity
    else:
        cart[item_id] = {
            'id': menu_item.id,
            'name': menu_item.ten_mon,
            'price': menu_item.gia,
            'quantity': quantity,
            'loai': menu_item.loai
        }
    
    session['cart'] = cart
    flash(f'Đã thêm {menu_item.ten_mon} vào giỏ hàng!', 'success')
    return redirect(url_for('menu'))

@app.route('/cart')
@login_required
def cart():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total)

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    if current_user.role == 'admin':
        flash('Admin không thể đặt hàng!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    cart = session.get('cart', {})
    if not cart:
        flash('Giỏ hàng trống!', 'error')
        return redirect(url_for('cart'))
    
    # Tạo đơn hàng
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
    order = Order(user_id=current_user.id, total_amount=total_amount, status='pending')
    db.session.add(order)
    db.session.commit()
    
    # Tạo chi tiết đơn hàng
    for item_id, item_data in cart.items():
        # item_id stored as string in session; convert to int for DB foreign key
        order_detail = OrderDetail(
            order_id=order.id,
            menu_item_id=int(item_id),
            quantity=item_data['quantity'],
            price=item_data['price']
        )
        db.session.add(order_detail)
    
    db.session.commit()
    session['cart'] = {}
    
    flash('Đặt hàng thành công! Đơn hàng đang được xử lý.', 'success')
    return redirect(url_for('orders'))

@app.route('/orders')
@login_required
def orders():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    student = StudentDetail.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        student.ho_ten = request.form['ho_ten']
        student.email = request.form['email']
        student.sdt = request.form['sdt']
        db.session.commit()
        flash('Cập nhật thông tin thành công!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', student=student)

# ========== QUẢN LÝ GIỎ HÀNG NÂNG CAO ==========

@app.route('/update_cart_quantity', methods=['POST'])
@login_required
def update_cart_quantity():
    """Cập nhật số lượng trong giỏ hàng"""
    if current_user.role == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    # Ensure item_id is a string to match session keys
    item_id = str(request.json.get('item_id'))
    action = request.json.get('action')  # 'increase' or 'decrease'
    
    cart = session.get('cart', {})
    
    if item_id in cart:
        if action == 'increase':
            cart[item_id]['quantity'] += 1
        elif action == 'decrease':
            if cart[item_id]['quantity'] > 1:
                cart[item_id]['quantity'] -= 1
            else:
                # Nếu số lượng = 1 mà giảm thì xóa luôn
                return remove_from_cart()
        
        session['cart'] = cart
        return jsonify({
            'success': True, 
            'new_quantity': cart[item_id]['quantity'],
            'item_total': cart[item_id]['price'] * cart[item_id]['quantity']
        })
    
    return jsonify({'success': False, 'message': 'Item not found'})

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    """Xóa món khỏi giỏ hàng"""
    if current_user.role == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    item_id = str(request.json.get('item_id'))

    cart = session.get('cart', {})
    
    if item_id in cart:
        removed_item = cart.pop(item_id)
        session['cart'] = cart
        
        return jsonify({
            'success': True, 
            'message': f'Đã xóa {removed_item["name"]} khỏi giỏ hàng',
            'cart_count': len(cart),
            'total_amount': sum(item['price'] * item['quantity'] for item in cart.values())
        })
    
    return jsonify({'success': False, 'message': 'Item not found'})

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    """Xóa toàn bộ giỏ hàng"""
    if current_user.role == 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    session['cart'] = {}
    return jsonify({'success': True, 'message': 'Đã xóa toàn bộ giỏ hàng'})

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Hủy đơn hàng (chỉ hủy được khi đang pending)"""
    if current_user.role == 'admin':
        flash('Admin không thể hủy đơn hàng!', 'error')
        return redirect(url_for('admin_orders'))
    
    order = Order.query.get_or_404(order_id)
    
    # Chỉ cho phép hủy đơn hàng của chính user và đang ở trạng thái pending
    if order.user_id != current_user.id:
        flash('Bạn không có quyền hủy đơn hàng này!', 'error')
        return redirect(url_for('orders'))
    
    if order.status != 'pending':
        flash('Chỉ có thể hủy đơn hàng đang chờ xác nhận!', 'error')
        return redirect(url_for('orders'))
    
    order.status = 'cancelled'
    db.session.commit()
    
    flash('Đã hủy đơn hàng thành công!', 'success')
    return redirect(url_for('orders'))

@app.route('/order_details/<int:order_id>')
@login_required
def order_details(order_id):
    """Chi tiết đơn hàng"""
    order = Order.query.get_or_404(order_id)
    
    # Kiểm tra quyền xem đơn hàng
    if current_user.role == 'student' and order.user_id != current_user.id:
        flash('Bạn không có quyền xem đơn hàng này!', 'error')
        return redirect(url_for('orders'))
    
    return render_template('order_details.html', order=order)

# ========== ADMIN ROUTES CƠ BẢN ==========

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))
    
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_students = User.query.filter_by(role='student').count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_students=total_students,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/update_order_status/<int:order_id>')
@login_required
def update_order_status(order_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'error')
        return redirect(url_for('menu'))
    
    order = Order.query.get_or_404(order_id)
    
    if order.status == 'pending':
        order.status = 'confirmed'
    elif order.status == 'confirmed':
        order.status = 'completed'
    
    db.session.commit()
    flash('Đã cập nhật trạng thái đơn hàng!', 'success')
    return redirect(url_for('admin_orders'))

# ========== ADMIN QUẢN LÝ MENU ==========

@app.route('/admin/menu')
@login_required
def admin_menu():
    """Quản lý menu cho admin"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))
    
    menu_items = MenuItem.query.order_by(MenuItem.loai, MenuItem.ten_mon).all()
    return render_template('admin_menu.html', menu_items=menu_items)

@app.route('/admin/add_menu_item', methods=['POST'])
@login_required
def add_menu_item():
    """Thêm món mới vào menu"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'error')
        return redirect(url_for('admin_menu'))
    
    try:
        ten_mon = request.form['ten_mon']
        gia = int(request.form['gia'])
        loai = request.form['loai']
        
        menu_item = MenuItem(ten_mon=ten_mon, gia=gia, loai=loai)
        db.session.add(menu_item)
        db.session.commit()
        
        flash('Thêm món ăn thành công!', 'success')
        return redirect(url_for('admin_menu'))
    
    except Exception as e:
        flash('Có lỗi xảy ra khi thêm món ăn!', 'error')
        return redirect(url_for('admin_menu'))

@app.route('/admin/toggle_menu_item/<int:item_id>')
@login_required
def toggle_menu_item(item_id):
    """Bật/tắt trạng thái món ăn"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'error')
        return redirect(url_for('menu'))
    
    menu_item = MenuItem.query.get_or_404(item_id)
    menu_item.is_available = not menu_item.is_available
    db.session.commit()
    
    status = "có sẵn" if menu_item.is_available else "tạm ngừng"
    flash(f'Đã cập nhật trạng thái món {menu_item.ten_mon} thành {status}', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/delete_menu_item/<int:item_id>', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    """Xóa món ăn khỏi menu"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Kiểm tra xem món ăn có trong đơn hàng nào không
    order_details = OrderDetail.query.filter_by(menu_item_id=item_id).first()
    if order_details:
        return jsonify({'success': False, 'message': 'Không thể xóa món ăn đã có trong đơn hàng!'})
    
    db.session.delete(menu_item)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã xóa món ăn thành công!'})

@app.route('/admin/edit_menu_item', methods=['POST'])
@login_required
def edit_menu_item():
    """Chỉnh sửa thông tin món ăn"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        item_id = request.form['item_id']
        ten_mon = request.form['ten_mon']
        gia = int(request.form['gia'])
        loai = request.form['loai']
        
        menu_item = MenuItem.query.get_or_404(item_id)
        menu_item.ten_mon = ten_mon
        menu_item.gia = gia
        menu_item.loai = loai
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Cập nhật món ăn thành công!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra khi cập nhật món ăn!'})

# ========== ADMIN QUẢN LÝ SINH VIÊN ==========

@app.route('/admin/students')
@login_required
def admin_students():
    """Quản lý sinh viên cho admin"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))
    
    students = StudentDetail.query.all()
    
    # Thống kê
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    ngành_học_count = db.session.query(StudentDetail.nganh_hoc).distinct().count()
    
    return render_template('admin_students.html',
                         students=students,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         ngành_học_count=ngành_học_count)


@app.route('/admin/student/<int:user_id>')
@login_required
def admin_student_detail(user_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))

    user = User.query.get_or_404(user_id)
    student = StudentDetail.query.filter_by(user_id=user_id).first()
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()

    return render_template('admin_student_detail.html', user=user, student=student, orders=orders)


@app.route('/admin/student_data/<int:user_id>')
@login_required
def admin_student_data(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    student = StudentDetail.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'success': False, 'message': 'Not found'}), 404

    data = {
        'user_id': student.user_id,
        'ma_sv': student.ma_sv,
        'ho_ten': student.ho_ten,
        'nganh_hoc': student.nganh_hoc,
        'email': student.email,
        'sdt': student.sdt,
        'username': student.user.username if student.user else ''
    }
    return jsonify({'success': True, 'student': data})


@app.route('/admin/edit_student', methods=['POST'])
@login_required
def admin_edit_student():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})

    try:
        user_id = int(request.form.get('user_id'))
        username = request.form.get('username')
        ma_sv = request.form.get('ma_sv')
        ho_ten = request.form.get('ho_ten')
        nganh_hoc = request.form.get('nganh_hoc')
        email = request.form.get('email')
        sdt = request.form.get('sdt')

        user = User.query.get_or_404(user_id)

        # check username conflict
        if username and username != user.username and User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại!'})

        # check student id conflict
        student = StudentDetail.query.filter_by(user_id=user_id).first()
        if ma_sv and student and ma_sv != student.ma_sv and StudentDetail.query.filter_by(ma_sv=ma_sv).first():
            return jsonify({'success': False, 'message': 'Mã sinh viên đã tồn tại!'})

        # update user
        if username:
            user.username = username

        # update student detail
        if student:
            student.ma_sv = ma_sv or student.ma_sv
            student.ho_ten = ho_ten or student.ho_ten
            student.nganh_hoc = nganh_hoc or student.nganh_hoc
            student.email = email or student.email
            student.sdt = sdt or student.sdt

        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật sinh viên thành công!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Có lỗi: {str(e)}'})


@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_detail(order_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))

    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)

@app.route('/admin/add_student', methods=['POST'])
@login_required
def add_student():
    """Thêm sinh viên mới"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'error')
        return redirect(url_for('admin_students'))
    
    try:
        username = request.form['username']
        password = request.form['password']
        ma_sv = request.form['ma_sv']
        ho_ten = request.form['ho_ten']
        nganh_hoc = request.form['nganh_hoc']
        email = request.form['email']
        sdt = request.form['sdt']
        
        # Kiểm tra username đã tồn tại
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'error')
            return redirect(url_for('admin_students'))
        
        # Kiểm tra mã sinh viên đã tồn tại
        if StudentDetail.query.filter_by(ma_sv=ma_sv).first():
            flash('Mã sinh viên đã tồn tại!', 'error')
            return redirect(url_for('admin_students'))
        
        # Tạo user
        user = User(username=username, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Tạo student detail
        student = StudentDetail(
            user_id=user.id,
            ma_sv=ma_sv,
            ho_ten=ho_ten,
            nganh_hoc=nganh_hoc,
            email=email,
            sdt=sdt
        )
        db.session.add(student)
        db.session.commit()
        
        flash('Thêm sinh viên thành công!', 'success')
        return redirect(url_for('admin_students'))
    
    except Exception as e:
        flash('Có lỗi xảy ra khi thêm sinh viên!', 'error')
        return redirect(url_for('admin_students'))

@app.route('/admin/delete_student/<int:user_id>', methods=['POST'])
@login_required
def delete_student(user_id):
    """Xóa sinh viên"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Kiểm tra nếu sinh viên có đơn hàng
        if user.orders:
            return jsonify({'success': False, 'message': 'Không thể xóa sinh viên đã có đơn hàng!'})
        
        # Xóa student detail trước
        student_detail = StudentDetail.query.filter_by(user_id=user_id).first()
        if student_detail:
            db.session.delete(student_detail)
        
        # Xóa user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đã xóa sinh viên thành công!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra khi xóa sinh viên!'})

# ========== ADMIN BÁO CÁO THỐNG KÊ ==========

@app.route('/admin/reports')
@login_required
def admin_reports():
    """Báo cáo thống kê"""
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'error')
        return redirect(url_for('menu'))
    
    # Thống kê tổng quan
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_students = User.query.filter_by(role='student').count()
    total_menu_items = MenuItem.query.count()
    
    # Tính giá trị đơn hàng trung bình
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Tỷ lệ hoàn thành đơn hàng
    completed_orders = Order.query.filter_by(status='completed').count()
    completion_rate = round((completed_orders / total_orders * 100), 1) if total_orders > 0 else 0
    
    stats = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_students': total_students,
        'total_menu_items': total_menu_items,
        'avg_order_value': round(avg_order_value),
        'completion_rate': completion_rate
    }
    
    # Thống kê trạng thái đơn hàng
    order_stats = {
        'pending': Order.query.filter_by(status='pending').count(),
        'confirmed': Order.query.filter_by(status='confirmed').count(),
        'completed': Order.query.filter_by(status='completed').count()
    }
    
    # Top món ăn bán chạy
    top_items = MenuItem.query.all()
    for item in top_items:
        item.total_sold = sum(detail.quantity for detail in item.order_details)
    
    top_items = sorted(top_items, key=lambda x: x.total_sold, reverse=True)[:5]
    
    # Thống kê doanh thu 7 ngày gần nhất (dummy data)
    revenue_data = [1500000, 1800000, 2200000, 1900000, 2100000, 2400000, 2300000]
    revenue_labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
    
    # Thống kê theo ngành học
    major_stats = []
    majors = db.session.query(StudentDetail.nganh_hoc).distinct().all()
    for major in majors:
        if major[0]:  # Kiểm tra nếu không phải None
            student_count = StudentDetail.query.filter_by(nganh_hoc=major[0]).count()
            total_spent = db.session.query(db.func.sum(Order.total_amount))\
                .join(User)\
                .join(StudentDetail)\
                .filter(StudentDetail.nganh_hoc == major[0])\
                .scalar() or 0
            major_stats.append({
                'nganh_hoc': major[0],
                'student_count': student_count,
                'total_spent': total_spent
            })
    
    # Thống kê giờ đặt hàng (dummy data)
    hour_stats = {f"{i:02d}": i * 2 + 5 for i in range(7, 22)}
    max_hour_orders = max(hour_stats.values()) if hour_stats else 1
    
    return render_template('admin_reports.html',
                         stats=stats,
                         order_stats=order_stats,
                         top_items=top_items,
                         revenue_data=revenue_data,
                         revenue_labels=revenue_labels,
                         major_stats=major_stats,
                         hour_stats=hour_stats,
                         max_hour_orders=max_hour_orders,
                         total_students=total_students)


# ----- Server-side image proxy for specific menu photos -----
CUSTOM_IMAGES = {
    'pho_bo': 'https://cdn.tgdd.vn/Files/2022/01/25/1412805/cach-nau-pho-bo-nam-dinh-chuan-vi-thom-ngon-nhu-hang-quan-202201250313281452.jpg',
    'com_ga_xoi_mo': 'https://cdn.tgdd.vn/2021/01/CookRecipe/GalleryStep/thanh-pham-362.jpg',
    'bun_cha': 'https://cdn2.fptshop.com.vn/unsafe/1920x0/filters:format(webp):quality(75)/2024_1_12_638406880045931692_cach-lam-bun-cha-ha-noi-0.jpg',
    'cafe_sua': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQII59mLCfEEqo3k-V98qEIxZDa1PF57ChUZQ&s',
    'banh_mi_pate': 'https://cdn2.fptshop.com.vn/unsafe/Uploads/images/tin-tuc/173733/Originals/banh-mi-pate-12.JPG',
    'xoi_ga': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRnAQXPgNjuFaExxPDZtR7xM7EcBrRV0_UnoA&s'
}


@app.route('/remote_image/<name>')
def remote_image(name):
    """Fetch a predefined remote image server-side and return it so the browser sees it as a local URL.

    This avoids hotlink/CORS problems from some image hosts. Only predefined keys are allowed.
    """
    # Only allow predefined names
    if name not in CUSTOM_IMAGES:
        return send_file(os.path.join(app.root_path, 'static', 'images', 'food1.svg'))

    # Ensure static images directory exists
    images_dir = os.path.join(app.root_path, 'static', 'images')
    os.makedirs(images_dir, exist_ok=True)

    # Cached filename pattern: remote_<name>.<ext>
    # Check for existing cached files with common extensions
    for ext in ('.jpg', '.jpeg', '.png', '.webp', '.svg'):
        cached_path = os.path.join(images_dir, f'remote_{name}{ext}')
        if os.path.exists(cached_path):
            return send_file(cached_path)

    # If no cached file, fetch remote image and cache it
    url = CUSTOM_IMAGES[name]
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        content_type = resp.headers.get('Content-Type', '')
        # Determine extension from content-type
        if 'svg' in content_type:
            ext = '.svg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'webp' in content_type:
            ext = '.webp'
        else:
            # default to jpg for other image types
            ext = '.jpg'

        cached_path = os.path.join(images_dir, f'remote_{name}{ext}')

        # Write bytes to file
        with open(cached_path, 'wb') as f:
            f.write(resp.content)

        return send_file(cached_path, mimetype=content_type or 'image/jpeg')

    except Exception:
        # On any failure, fall back to local placeholder image
        return send_file(os.path.join(app.root_path, 'static', 'images', 'food1.svg'))

# ====================== ROUTE CHATBOT GỢI Ý MÓN ĂN ======================
@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user_message = ""
    bot_reply = ""
    
    if request.method == "POST":
        user_message = request.form.get("message", "")
        
        if not user_message.strip():
            bot_reply = "Xin hãy nhập nội dung nào đó 👀"
        else:
            try:
                if model is None:
                    bot_reply = "Chatbot tạm thời không khả dụng. Vui lòng kiểm tra cấu hình API key."
                else:
                    # Lấy menu hiện tại từ database - ĐÃ THÊM TÍNH NĂNG NÀY
                    menu_items = MenuItem.query.filter_by(is_available=True).all()
                    menu_info = ""
                    for item in menu_items:
                        menu_info += f"- {item.ten_mon}: {item.gia:,}đ ({item.loai})\n"
                    
                    # Gửi prompt cho Gemini AI với thông tin menu thực tế - ĐÃ SỬA
                    prompt = f"""
                    Bạn là chatbot hỗ trợ căng tin trường học. Dưới đây là menu hiện có:

                    {menu_info}

                    Hãy sử dụng thông tin menu trên để:
                    - Gợi ý món ăn phù hợp với yêu cầu
                    - Tư vấn về giá cả
                    - Phân loại món theo bữa ăn (sáng, trưa, tối)
                    - Hỗ trợ chọn món theo ngân sách

                    Câu hỏi của người dùng: {user_message}

                    Lưu ý: 
                    - Chỉ gợi ý các món có trong menu trên
                    - Đề cập đến giá cả cụ thể
                    - Trả lời thân thiện, hữu ích
                    - Nếu không có thông tin, hãy nói rõ
                    """
                    response = model.generate_content(prompt)
                    bot_reply = response.text
            except Exception as e:
                bot_reply = f"Xin lỗi, tôi gặp sự cố kỹ thuật. Vui lòng thử lại sau. Lỗi: {str(e)}"

        return render_template("chat.html", bot_reply=bot_reply, user_message=user_message)

    return render_template("chat.html", user_message=user_message, bot_reply=bot_reply)
# =======================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True)