
<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
 SMART CANTEEN – HỆ THỐNG ĐẶT MÓN & QUẢN LÝ NHÀ ĂN THÔNG MINH
</h2>
<div align="center">
    <p align="center">
        <img src="docs/aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="docs/fitdnu_logo.png" alt="AIoTLab Logo" width="180"/>
        <img src="docs/dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>

</div>
1. 📖 Giới thiệu hệ thống

Smart Canteen là hệ thống web hỗ trợ đặt món & quản lý nhà ăn dành cho môi trường đại học.
Dự án giải quyết loạt vấn đề hay gặp ở căng tin truyền thống: xếp hàng dài, sai sót đơn hàng, khó quản lý và thiếu minh bạch.

Hệ thống được phát triển bằng Flask + SQLAlchemy + Bootstrap 5, nhắm tới trải nghiệm nhanh – ổn định – mượt cho sinh viên & nhân viên nhà ăn.

🎯 Mục tiêu chính

Giảm thời gian chờ đặt món

Tối ưu quy trình xử lý đơn hàng

Giao diện trực quan, dễ dùng

Quản trị menu, sinh viên, đơn hàng trong 1 dashboard

Tương thích đa thiết bị (mobile/PC)

✨ Chức năng nổi bật

Sinh viên (User):

👤 Đăng ký / Đăng nhập

🔍 Duyệt menu

🛒 Giỏ hàng thông minh

💵 Đặt món & theo dõi trạng thái

📜 Xem lịch sử đặt hàng

Quản trị viên (Admin):

🗂️ Quản lý món ăn

📦 Quản lý đơn hàng

👥 Quản lý sinh viên

📊 Dashboard thống kê real-time

2. 🛠️ Công nghệ sử dụng

🐍 Python 3.8+

⚙️ Flask 2.3.3 (MVC-based)

🗄️ SQLAlchemy ORM + SQLite

🎨 Bootstrap 5.3 + Jinja2

🌐 HTML/CSS/JavaScript ES6+

3. 🖼️ Hình ảnh giao diện
🔑 Login / Register

🍽️ Trang Menu & Giỏ hàng

🛠️ Admin Dashboard

4. 🧩 Kiến trúc & Mô hình hệ thống
Client (Browser)
     │
     ▼
Flask Controller (Routes)
     │
     ▼
Jinja2 Templates (View)
     │
     ▼
SQLAlchemy ORM (Model)
     │
     ▼
SQLite Database

5. ⚙️ Tính năng & Luồng hoạt động
Luồng đặt món của sinh viên

Đăng nhập

Duyệt menu

Thêm món vào giỏ

Xác nhận & thanh toán

Theo dõi trạng thái đơn

Các module chính

Menu Management

Cart Session

Order Processing

User Auth

Admin Management

6. 🔧 Cài đặt & Chạy dự án
Bước 1 — Clone repo
git clone https://github.com/username/smart-canteen.git
cd smart-canteen

Bước 2 — Cài đặt thư viện
pip install -r requirements.txt

Bước 3 — Khởi tạo DB
python init_db.py

Bước 4 — Chạy ứng dụng
python run.py

Bước 5 — Truy cập

Sinh viên: http://localhost:5000

Admin: http://localhost:5000/admin

Tài khoản demo

👨‍🎓 Student: student1 / password123

🛠️ Admin: admin / admin123

7. 📊 Kết quả thực nghiệm
Tiêu chí	Hệ thống cũ	Smart Canteen	Cải thiện
Thời gian đặt món	3–5 phút	30–60 giây	+80%
Sai sót đơn hàng	15%	2%	-87%
Đơn xử lý/giờ	20–30	60–80	+150%
Hài lòng người dùng	60%	92%	+53%
8. 🚀 Hướng phát triển tương lai

Thanh toán số (Momo, VNPay, ZaloPay)

App mobile Android/iOS

AI gợi ý món ăn theo lịch sử

Websocket realtime order tracking

Dashboard phân tích nâng cao

9. 👤 Liên hệ
Sinh viên thực hiện: Trịnh Hữu Hiệu
Khoa Công nghệ Thông tin – Đại học Đại Nam

Email: trinhhuuhieu19122003@gmail.com
Website: https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin
Fanpage: AIoTLab - FIT DNU
