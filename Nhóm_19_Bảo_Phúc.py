import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import hashlib
import requests
from datetime import datetime
import threading
import random
import string
import re

class DataManager:
    """Class quản lý dữ liệu JSON"""
    
    @staticmethod
    def load_json(filename):
        """Đọc dữ liệu từ file JSON"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as file:
                    return json.load(file)
            return []
        except Exception as e:
            print(f"Lỗi đọc file {filename}: {e}")
            return []
    
    @staticmethod
    def save_json(filename, data):
        """Ghi dữ liệu vào file JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Lỗi ghi file {filename}: {e}")
            return False

class UserManager:
    """Class quản lý người dùng và phân quyền"""
    
    def __init__(self):
        self.users_file = "users.json"
        self.users = self.load_users()
        self.current_user = None
        
        # Tạo admin mặc định nếu chưa có
        if not self.users:
            self.create_default_admin()
    
    def load_users(self):
        """Tải danh sách người dùng"""
        return DataManager.load_json(self.users_file)
    
    def save_users(self):
        """Lưu danh sách người dùng"""
        return DataManager.save_json(self.users_file, self.users)
    
    def hash_password(self, password):
        """Mã hóa mật khẩu"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_random_password(self, length=8):
        """Tạo mật khẩu ngẫu nhiên"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def create_default_admin(self):
        """Tạo tài khoản admin mặc định"""
        admin_user = {
            "id": 1,
            "username": "admin",
            "password": self.hash_password("admin123"),
            "role": "admin",
            "email": "admin@example.com",
            "security_question": "Tên thú cưng đầu tiên của bạn?",
            "security_answer": self.hash_password("admin"),
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.users.append(admin_user)
        self.save_users()
    
    def login(self, username, password):
        """Đăng nhập"""
        hashed_password = self.hash_password(password)
        for user in self.users:
            if user["username"] == username and user["password"] == hashed_password:
                self.current_user = user
                return True
        return False
    
    def register(self, username, password, email, security_question, security_answer, role="user"):
        """Đăng ký tài khoản mới"""
        for user in self.users:
            if user["username"] == username:
                return False, "Tên đăng nhập đã tồn tại"
        
        for user in self.users:
            if user.get("email") == email:
                return False, "Email đã được sử dụng"
        
        new_user = {
            "id": len(self.users) + 1,
            "username": username,
            "password": self.hash_password(password),
            "role": role,
            "email": email,
            "security_question": security_question,
            "security_answer": self.hash_password(security_answer.lower()),
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.users.append(new_user)
        if self.save_users():
            return True, "Đăng ký thành công"
        return False, "Lỗi lưu dữ liệu"
    
    def change_password(self, current_password, new_password):
        """Đổi mật khẩu cho user hiện tại"""
        if not self.current_user:
            return False, "Chưa đăng nhập"
        
        # Kiểm tra mật khẩu hiện tại
        current_hashed = self.hash_password(current_password)
        if self.current_user["password"] != current_hashed:
            return False, "Mật khẩu hiện tại không đúng"
        
        # Kiểm tra độ dài mật khẩu mới
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự"
        
        # Cập nhật mật khẩu mới
        new_hashed = self.hash_password(new_password)
        for user in self.users:
            if user["id"] == self.current_user["id"]:
                user["password"] = new_hashed
                user["password_changed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.current_user = user  # Cập nhật current_user
                break
        
        if self.save_users():
            return True, "Đổi mật khẩu thành công"
        return False, "Lỗi lưu dữ liệu"
    
    def reset_password(self, username, security_answer):
        """Đặt lại mật khẩu"""
        hashed_answer = self.hash_password(security_answer.lower())
        for user in self.users:
            if user["username"] == username and user.get("security_answer") == hashed_answer:
                new_password = self.generate_random_password()
                user["password"] = self.hash_password(new_password)
                user["password_reset_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.save_users():
                    return True, new_password
                return False, "Lỗi lưu dữ liệu"
        return False, "Thông tin không chính xác"
    
    def get_user_by_username(self, username):
        """Lấy thông tin user theo username"""
        for user in self.users:
            if user["username"] == username:
                return user
        return None
    
    def is_admin(self):
        """Kiểm tra quyền admin"""
        return self.current_user and self.current_user["role"] == "admin"
    
    def can_edit_customers(self):
        """Kiểm tra quyền sửa khách hàng - chỉ admin mới được sửa"""
        return self.is_admin()
    
    def can_add_customers(self):
        """Kiểm tra quyền thêm khách hàng - cả admin và user đều được thêm"""
        return self.current_user is not None
    
    def logout(self):
        """Đăng xuất"""
        self.current_user = None

class APIService:
    """Class tích hợp API để lấy dữ liệu mẫu"""
    
    @staticmethod
    def fetch_sample_customers():
        """Lấy dữ liệu khách hàng mẫu từ API"""
        try:
            response = requests.get("https://jsonplaceholder.typicode.com/users", timeout=10)
            if response.status_code == 200:
                users_data = response.json()
                customers = []
                
                customer_types = ["Khách hàng thường", "Khách hàng VIP"]
                
                for user in users_data:
                    customer = {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user["email"],
                        "phone": user["phone"],
                        "address": f"{user['address']['street']}, {user['address']['city']}",
                        "customer_type": random.choice(customer_types),
                        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    customers.append(customer)
                
                return customers
            return []
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu từ API: {e}")
            return []

class CustomerManager:
    """Class quản lý khách hàng"""
    
    def __init__(self):
        self.customers_file = "customers.json"
        self.customers = self.load_customers()
        self.sort_column = None
        self.sort_reverse = False
        # Định nghĩa các loại khách hàng
        self.customer_types = ["Khách hàng thường", "Khách hàng VIP"]
    
    def load_customers(self):
        """Tải danh sách khách hàng"""
        return DataManager.load_json(self.customers_file)
    
    def save_customers(self):
        """Lưu danh sách khách hàng"""
        return DataManager.save_json(self.customers_file, self.customers)
    
    def check_duplicate_name(self, name, exclude_id=None):
        """Kiểm tra trùng tên khách hàng (không phân biệt hoa thường)"""
        name_lower = name.lower().strip()
        for customer in self.customers:
            if customer["id"] != exclude_id and customer["name"].lower().strip() == name_lower:
                return True
        return False
    
    def add_customer(self, name, email, phone, address, customer_type="Khách hàng thường"):
        """Thêm khách hàng mới"""
        if self.check_duplicate_name(name):
            return False, "Tên khách hàng đã tồn tại!"
        
        # Kiểm tra loại khách hàng hợp lệ
        if customer_type not in self.customer_types:
            customer_type = "Khách hàng thường"
        
        new_id = max([c["id"] for c in self.customers], default=0) + 1
        new_customer = {
            "id": new_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "customer_type": customer_type,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.customers.append(new_customer)
        return self.save_customers(), "Thêm khách hàng thành công!"
    
    def update_customer(self, customer_id, name, email, phone, address, customer_type="Khách hàng thường"):
        """Cập nhật thông tin khách hàng"""
        if self.check_duplicate_name(name, exclude_id=customer_id):
            return False, "Tên khách hàng đã tồn tại!"
        
        # Kiểm tra loại khách hàng hợp lệ
        if customer_type not in self.customer_types:
            customer_type = "Khách hàng thường"
        
        for customer in self.customers:
            if customer["id"] == customer_id:
                customer["name"] = name
                customer["email"] = email
                customer["phone"] = phone
                customer["address"] = address
                customer["customer_type"] = customer_type
                customer["updated_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return self.save_customers(), "Cập nhật khách hàng thành công!"
        return False, "Không tìm thấy khách hàng!"
    
    def delete_customer(self, customer_id):
        """Xóa khách hàng"""
        self.customers = [c for c in self.customers if c["id"] != customer_id]
        return self.save_customers()
    
    def search_customers(self, keyword):
        """Tìm kiếm khách hàng"""
        keyword = keyword.lower()
        results = []
        for customer in self.customers:
            if (keyword in customer["name"].lower() or 
                keyword in customer["email"].lower() or 
                keyword in customer["phone"].lower() or 
                keyword in customer["address"].lower() or
                keyword in customer.get("customer_type", "").lower()):
                results.append(customer)
        return results
    
    def sort_customers(self, column, reverse=False):
        """Sắp xếp khách hàng theo cột"""
        self.sort_column = column
        self.sort_reverse = reverse
        
        if column == "name":
            self.customers.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        elif column == "email":
            self.customers.sort(key=lambda x: x["email"].lower(), reverse=reverse)
        elif column == "phone":
            self.customers.sort(key=lambda x: x["phone"], reverse=reverse)
        elif column == "customer_type":
            self.customers.sort(key=lambda x: x.get("customer_type", "").lower(), reverse=reverse)
        elif column == "created_date":
            self.customers.sort(key=lambda x: x.get("created_date", ""), reverse=reverse)
        elif column == "id":
            self.customers.sort(key=lambda x: x["id"], reverse=reverse)
        
        return self.customers
    
    def import_sample_data(self):
        """Import dữ liệu mẫu từ API"""
        sample_customers = APIService.fetch_sample_customers()
        if sample_customers:
            self.customers = sample_customers
            return self.save_customers()
        return False

class ChangePasswordWindow:
    """Cửa sổ đổi mật khẩu với giao diện được cải thiện"""
    
    def __init__(self, user_manager, parent_window):
        self.user_manager = user_manager
        self.parent_window = parent_window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Đổi Mật Khẩu")
        self.window.geometry("600x500")  # Tăng kích thước cửa sổ để chứa nút to
        self.window.resizable(False, False)
        self.window.configure(bg="#f0f4f8")
        
        self.center_window()
        self.window.transient(parent_window)
        self.window.grab_set()
        
        self.create_widgets()
    
    def center_window(self):
        """Căn giữa cửa sổ"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.window.winfo_screenheight() // 2) - (500 // 2)
        self.window.geometry(f"600x500+{x}+{y}")
    
    def create_widgets(self):
        """Tạo giao diện đổi mật khẩu với layout được cải thiện"""
        # Style configuration
        style = ttk.Style()
        style.configure("Main.TFrame", background="#f0f4f8")
        style.configure("Title.TLabel", font=("Helvetica", 20, "bold"), foreground="#2c3e50")
        style.configure("Info.TLabel", font=("Helvetica", 12, "italic"), foreground="#34495e")
        style.configure("Field.TLabel", font=("Helvetica", 11), foreground="#2c3e50")
        style.configure("TButton", font=("Helvetica", 11), padding=(15, 8))
        style.configure("TEntry", padding=8, font=("Helvetica", 11))
        
        # Main container
        main_container = ttk.Frame(self.window, style="Main.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Title
        title_label = ttk.Label(main_container, text="ĐỔI MẬT KHẨU", style="Title.TLabel")
        title_label.pack(pady=(0, 15))
        
        # User info
        user_info = f"Tài khoản: {self.user_manager.current_user['username']}"
        info_label = ttk.Label(main_container, text=user_info, style="Info.TLabel")
        info_label.pack(pady=(0, 30))
        
        # Form container với grid layout được cải thiện
        form_container = ttk.Frame(main_container)
        form_container.pack(fill=tk.X, pady=(0, 30))
        
        # Configure grid weights để căn đều
        form_container.grid_columnconfigure(0, weight=1, minsize=180)
        form_container.grid_columnconfigure(1, weight=2, minsize=250)
        
        # Current password
        current_label = ttk.Label(form_container, text="Mật khẩu hiện tại:", style="Field.TLabel")
        current_label.grid(row=0, column=0, sticky="e", padx=(0, 15), pady=12)
        
        self.current_password_entry = ttk.Entry(form_container, show="*", style="TEntry", width=30)
        self.current_password_entry.grid(row=0, column=1, sticky="ew", pady=12)
        
        # New password
        new_label = ttk.Label(form_container, text="Mật khẩu mới:", style="Field.TLabel")
        new_label.grid(row=1, column=0, sticky="e", padx=(0, 15), pady=12)
        
        self.new_password_entry = ttk.Entry(form_container, show="*", style="TEntry", width=30)
        self.new_password_entry.grid(row=1, column=1, sticky="ew", pady=12)
        
        # Confirm new password
        confirm_label = ttk.Label(form_container, text="Xác nhận mật khẩu mới:", style="Field.TLabel")
        confirm_label.grid(row=2, column=0, sticky="e", padx=(0, 15), pady=12)
        
        self.confirm_password_entry = ttk.Entry(form_container, show="*", style="TEntry", width=30)
        self.confirm_password_entry.grid(row=2, column=1, sticky="ew", pady=12)
        
        # Buttons container
        button_container = ttk.Frame(main_container)
        button_container.pack(pady=(30, 0))
        
        # TẠO CÁC NÚT THẬT TO VÀ BỰ!
        confirm_btn = tk.Button(
            button_container, 
            text="Xác nhận", 
            command=self.change_password,
            font=("Arial", 15, "bold"),  # Font to hơn
            width=15,                    # Rộng hơn nhiều
            height=1,                    # Cao hơn nhiều
            bg="#2E7D32",               # Xanh đậm hơn
            fg="white",
            relief="raised",
            bd=4,                       # Border dày hơn
            cursor="hand2",
            activebackground="#1B5E20", # Màu khi nhấn
            activeforeground="white"
        )
        confirm_btn.pack(side=tk.LEFT, padx=20)
        
        cancel_btn = tk.Button(
            button_container, 
            text="Hủy bỏ", 
            command=self.window.destroy,
            font=("Arial", 15, "bold"),  # Font to hơn
            width=15,                    # Rộng hơn nhiều
            height=1,                    # Cao hơn nhiều
            bg="#C62828",               # Đỏ đậm hơn
            fg="white",
            relief="raised",
            bd=4,                       # Border dày hơn
            cursor="hand2",
            activebackground="#8E0000", # Màu khi nhấn
            activeforeground="white"
        )
        cancel_btn.pack(side=tk.LEFT, padx=20)
        
        # Bind Enter key to confirm action
        self.window.bind('<Return>', lambda event: self.change_password())
        
        # Focus on first entry
        self.current_password_entry.focus()
    
    def change_password(self):
        """Xử lý đổi mật khẩu với validation được cải thiện"""
        current_password = self.current_password_entry.get().strip()
        new_password = self.new_password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        
        # Validation với thông báo cụ thể
        if not current_password:
            messagebox.showerror("Lỗi", "Vui lòng nhập mật khẩu hiện tại!")
            self.current_password_entry.focus()
            return
        
        if not new_password:
            messagebox.showerror("Lỗi", "Vui lòng nhập mật khẩu mới!")
            self.new_password_entry.focus()
            return
        
        if not confirm_password:
            messagebox.showerror("Lỗi", "Vui lòng xác nhận mật khẩu mới!")
            self.confirm_password_entry.focus()
            return
        
        if new_password != confirm_password:
            messagebox.showerror("Lỗi", "Mật khẩu mới và xác nhận mật khẩu không khớp!")
            self.confirm_password_entry.delete(0, tk.END)
            self.confirm_password_entry.focus()
            return
        
        if current_password == new_password:
            messagebox.showerror("Lỗi", "Mật khẩu mới phải khác mật khẩu hiện tại!")
            self.new_password_entry.delete(0, tk.END)
            self.confirm_password_entry.delete(0, tk.END)
            self.new_password_entry.focus()
            return
        
        # Attempt to change password
        success, message = self.user_manager.change_password(current_password, new_password)
        
        if success:
            messagebox.showinfo("Thành công", 
                              f"{message}\n\nMật khẩu của bạn đã được cập nhật thành công!\nVui lòng ghi nhớ mật khẩu mới.")
            self.window.destroy()
        else:
            messagebox.showerror("Lỗi", message)
            if "hiện tại không đúng" in message:
                self.current_password_entry.delete(0, tk.END)
                self.current_password_entry.focus()
            elif "ít nhất 6 ký tự" in message:
                self.new_password_entry.delete(0, tk.END)
                self.confirm_password_entry.delete(0, tk.END)
                self.new_password_entry.focus()

class ForgotPasswordWindow:
    """Cửa sổ quên mật khẩu - Đã sửa để có thể cuộn"""
    
    def __init__(self, user_manager, parent_window):
        self.user_manager = user_manager
        self.parent_window = parent_window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Quên Mật Khẩu")
        self.window.geometry("500x600")
        self.window.resizable(True, True)
        self.window.configure(bg="#f0f4f8")
        
        self.center_window()
        self.window.transient(parent_window)
        self.window.grab_set()
        
        self.create_widgets()
    
    def center_window(self):
        """Căn giữa cửa sổ"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"500x600+{x}+{y}")
    
    def create_widgets(self):
        """Tạo giao diện quên mật khẩu với khả năng cuộn"""
        # Tạo Canvas và Scrollbar để có thể cuộn
        canvas = tk.Canvas(self.window, bg="#f0f4f8")
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Main frame with padding
        main_frame = ttk.Frame(scrollable_frame, padding="20", style="Main.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure style
        style = ttk.Style()
        style.configure("Main.TFrame", background="#f0f4f8")
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"), foreground="#2c3e50")
        style.configure("Subtitle.TLabel", font=("Helvetica", 12, "bold"), foreground="#34495e")
        style.configure("TButton", font=("Helvetica", 10), padding=10)
        style.configure("TEntry", padding=5)
        
        # Title
        ttk.Label(main_frame, text="KHÔI PHỤC MẬT KHẨU", style="Title.TLabel").pack(pady=(0, 20))
        
        # Step 1: Username
        step1_frame = ttk.Frame(main_frame)
        step1_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(step1_frame, text="Bước 1: Nhập tên đăng nhập", style="Subtitle.TLabel").pack(anchor=tk.W)
        ttk.Label(step1_frame, text="Tên đăng nhập:", font=("Helvetica", 10)).pack(anchor=tk.W, pady=(10, 0))
        self.username_entry = ttk.Entry(step1_frame, font=("Helvetica", 12), width=30)
        self.username_entry.pack(anchor=tk.W, pady=(5, 10))
        
        ttk.Button(step1_frame, text="Kiểm tra", command=self.check_username, style="TButton").pack(anchor=tk.W)
        
        # Step 2: Security question
        self.step2_frame = ttk.Frame(main_frame)
        
        ttk.Label(self.step2_frame, text="Bước 2: Trả lời câu hỏi bảo mật", style="Subtitle.TLabel").pack(anchor=tk.W)
        
        # Tạo frame cho câu hỏi với khả năng wrap text
        question_frame = ttk.Frame(self.step2_frame)
        question_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(question_frame, text="Câu hỏi bảo mật:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        # Sử dụng Text widget thay vì Label để hiển thị câu hỏi dài
        self.question_text = tk.Text(question_frame, height=3, width=50, wrap=tk.WORD, 
                                   font=("Helvetica", 10), bg="#f8f9fa", state=tk.DISABLED)
        self.question_text.pack(anchor=tk.W, pady=(5, 10))
        
        ttk.Label(self.step2_frame, text="Câu trả lời:", font=("Helvetica", 10)).pack(anchor=tk.W, pady=(10, 0))
        self.answer_entry = ttk.Entry(self.step2_frame, font=("Helvetica", 12), width=40)
        self.answer_entry.pack(anchor=tk.W, pady=(5, 10))
        
        ttk.Button(self.step2_frame, text="Đặt lại mật khẩu", command=self.reset_password, style="TButton").pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Đóng", command=self.window.destroy, style="TButton").pack()
        
        # Pack canvas và scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel để cuộn
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.username_entry.focus()
    
    def check_username(self):
        """Kiểm tra tên đăng nhập và hiển thị câu hỏi bảo mật"""
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên đăng nhập!")
            return
        
        user = self.user_manager.get_user_by_username(username)
        if user and user.get("security_question"):
            # Hiển thị câu hỏi trong Text widget
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(1.0, user["security_question"])
            self.question_text.config(state=tk.DISABLED)
            
            self.step2_frame.pack(pady=10, fill=tk.X)
            self.answer_entry.focus()
        else:
            messagebox.showerror("Lỗi", "Tên đăng nhập không tồn tại hoặc chưa thiết lập câu hỏi bảo mật!")
    
    def reset_password(self):
        """Đặt lại mật khẩu"""
        username = self.username_entry.get().strip()
        answer = self.answer_entry.get().strip()
        
        if not answer:
            messagebox.showerror("Lỗi", "Vui lòng nhập câu trả lời!")
            return
        
        success, result = self.user_manager.reset_password(username, answer)
        if success:
            messagebox.showinfo("Thành công", 
                               f"Mật khẩu mới của bạn là: {result}\n\n"
                               "Vui lòng ghi nhớ và đổi mật khẩu sau khi đăng nhập!")
            self.window.destroy()
        else:
            messagebox.showerror("Lỗi", "Câu trả lời không chính xác!")

class RegisterWindow:
    """Cửa sổ đăng ký"""
    
    def __init__(self, user_manager, parent_window):
        self.user_manager = user_manager
        self.parent_window = parent_window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Đăng Ký Tài Khoản")
        self.window.geometry("500x500")
        self.window.resizable(False, False)
        
        self.center_window()
        self.window.transient(parent_window)
        self.window.grab_set()
        
        self.create_widgets()
    
    def center_window(self):
        """Căn giữa cửa sổ"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (500 // 2)
        self.window.geometry(f"500x500+{x}+{y}")
    
    def create_widgets(self):
        """Tạo giao diện đăng ký"""
        # Main frame
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"), foreground="#2c3e50")
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10), padding=10)
        style.configure("TEntry", padding=5)
        
        # Title
        ttk.Label(main_frame, text="ĐĂNG KÝ TÀI KHOẢN", style="Title.TLabel").pack(pady=(0, 20))
        
        # Form frame
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X)
        
        fields = [
            ("Tên đăng nhập:", "username"),
            ("Mật khẩu:", "password"),
            ("Xác nhận mật khẩu:", "confirm_password"),
            ("Email:", "email"),
        ]
        
        self.entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(form_frame, text=label_text, style="TLabel").grid(
                row=i, column=0, sticky="e", padx=10, pady=8)
            
            entry = ttk.Entry(form_frame, font=("Helvetica", 12), width=25, 
                             show="*" if "password" in field_name else "")
            entry.grid(row=i, column=1, padx=10, pady=8)
            self.entries[field_name] = entry
        
        # Security question
        ttk.Label(form_frame, text="Câu hỏi bảo mật:", style="TLabel").grid(
            row=len(fields), column=0, sticky="e", padx=10, pady=8)
        
        self.security_question_var = tk.StringVar()
        security_questions = [
            "Tên thú cưng đầu tiên của bạn?",
            "Tên trường tiểu học của bạn?",
            "Tên thành phố nơi bạn sinh ra?",
            "Tên của người bạn thân nhất?",
            "Món ăn yêu thích của bạn?"
        ]
        
        question_combo = ttk.Combobox(form_frame, textvariable=self.security_question_var,
                                     values=security_questions, font=("Helvetica", 10), width=35, state="readonly")
        question_combo.grid(row=len(fields), column=1, padx=10, pady=8)
        question_combo.set(security_questions[0])
        
        # Security answer
        ttk.Label(form_frame, text="Câu trả lời:", style="TLabel").grid(
            row=len(fields)+1, column=0, sticky="e", padx=10, pady=8)
        
        self.security_answer_entry = ttk.Entry(form_frame, font=("Helvetica", 12), width=25)
        self.security_answer_entry.grid(row=len(fields)+1, column=1, padx=10, pady=8)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Đăng Ký", command=self.register, style="TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Hủy", command=self.window.destroy, style="TButton").pack(side=tk.LEFT, padx=10)
        
        self.entries["username"].focus()
    
    def register(self):
        """Xử lý đăng ký"""
        username = self.entries["username"].get().strip()
        password = self.entries["password"].get().strip()
        confirm_password = self.entries["confirm_password"].get().strip()
        email = self.entries["email"].get().strip()
        security_question = self.security_question_var.get()
        security_answer = self.security_answer_entry.get().strip()
        
        if not all([username, password, confirm_password, email, security_question, security_answer]):
            messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
        
        if password != confirm_password:
            messagebox.showerror("Lỗi", "Mật khẩu xác nhận không khớp!")
            return
        
        if len(password) < 6:
            messagebox.showerror("Lỗi", "Mật khẩu phải có ít nhất 6 ký tự!")
            return
        
        if "@" not in email:
            messagebox.showerror("Lỗi", "Email không hợp lệ!")
            return
        
        success, message = self.user_manager.register(username, password, email, 
                                                     security_question, security_answer)
        if success:
            messagebox.showinfo("Thành công", message)
            self.window.destroy()
        else:
            messagebox.showerror("Lỗi", message)

class LoginWindow:
    """Cửa sổ đăng nhập"""
    
    def __init__(self, user_manager, on_login_success):
        self.user_manager = user_manager
        self.on_login_success = on_login_success
        self.window = tk.Tk()
        self.window.title("Đăng Nhập - Hệ Thống Quản Lý Khách Hàng")
        self.window.geometry("450x400")
        self.window.resizable(False, False)
        self.window.configure(bg="#f0f4f8")
        
        self.center_window()
        self.create_widgets()
    
    def center_window(self):
        """Căn giữa cửa sổ"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.window.winfo_screenheight() // 2) - (400 // 2)
        self.window.geometry(f"450x400+{x}+{y}")
    
    def create_widgets(self):
        """Tạo giao diện đăng nhập"""
        # Style configuration
        style = ttk.Style()
        style.configure("Main.TFrame", background="#f0f4f8")
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"), foreground="#2c3e50")
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10), padding=10)
        style.configure("TEntry", padding=5)
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding="20", style="Main.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="HỆ THỐNG QUẢN LÝ KHÁCH HÀNG", style="Title.TLabel").pack(pady=(0, 20))
        
        # Login frame
        login_frame = ttk.Frame(main_frame)
        login_frame.pack(fill=tk.X, pady=10)
        
        # Username
        ttk.Label(login_frame, text="Tên đăng nhập:", style="TLabel").grid(row=0, column=0, sticky="e", padx=10, pady=10)
        self.username_entry = ttk.Entry(login_frame, font=("Helvetica", 12), width=25)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # Password
        ttk.Label(login_frame, text="Mật khẩu:", style="TLabel").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        self.password_entry = ttk.Entry(login_frame, font=("Helvetica", 12), width=25, show="*")
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Đăng Nhập", command=self.login, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Đăng Ký", command=self.register, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Quên Mật Khẩu?", command=self.forgot_password, style="TButton").pack(side=tk.LEFT, padx=5)
        
        self.window.bind('<Return>', lambda event: self.login())
        self.username_entry.focus()
    
    def login(self):
        """Xử lý đăng nhập"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
        
        if self.user_manager.login(username, password):
            self.window.destroy()
            self.on_login_success()
        else:
            messagebox.showerror("Lỗi", "Tên đăng nhập hoặc mật khẩu không đúng!")
            self.password_entry.delete(0, tk.END)
    
    def register(self):
        """Mở cửa sổ đăng ký"""
        RegisterWindow(self.user_manager, self.window)
    
    def forgot_password(self):
        """Mở cửa sổ quên mật khẩu"""
        ForgotPasswordWindow(self.user_manager, self.window)
    
    def run(self):
        """Chạy cửa sổ đăng nhập"""
        self.window.mainloop()

class CustomerManagementApp:
    """Ứng dụng chính quản lý khách hàng"""
    
    def __init__(self):
        self.user_manager = UserManager()
        self.customer_manager = CustomerManager()
        self.window = None
        self.tree = None
        self.search_var = None
        self.sort_var = None
        
    def start(self):
        """Khởi động ứng dụng"""
        login_window = LoginWindow(self.user_manager, self.show_main_window)
        login_window.run()
    
    def show_main_window(self):
        """Hiển thị cửa sổ chính"""
        self.window = tk.Tk()
        self.window.title("Hệ Thống Quản Lý Khách Hàng")
        self.window.geometry("1300x750")
        
        self.center_window()
        self.create_main_interface()
        self.load_customer_data()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def center_window(self):
        """Căn giữa cửa sổ"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (1300 // 2)
        y = (self.window.winfo_screenheight() // 2) - (750 // 2)
        self.window.geometry(f"1300x750+{x}+{y}")
    
    def create_main_interface(self):
        """Tạo giao diện chính"""
        header_frame = tk.Frame(self.window, bg="lightblue", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="HỆ THỐNG QUẢN LÝ KHÁCH HÀNG", 
                              font=("Arial", 18, "bold"), bg="lightblue")
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        user_info = f"Xin chào: {self.user_manager.current_user['username']} ({self.user_manager.current_user['role']})"
        user_label = tk.Label(header_frame, text=user_info, font=("Arial", 12), bg="lightblue")
        user_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
        toolbar_frame = tk.Frame(self.window, bg="lightgray", height=80)
        toolbar_frame.pack(fill=tk.X)
        toolbar_frame.pack_propagate(False)
        
        first_row = tk.Frame(toolbar_frame, bg="lightgray")
        first_row.pack(fill=tk.X, pady=5)
        
        tk.Label(first_row, text="Tìm kiếm:", bg="lightgray", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(first_row, textvariable=self.search_var, font=("Arial", 10), width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind('<KeyRelease>', self.on_search)
        
        tk.Label(first_row, text="Sắp xếp theo:", bg="lightgray", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        self.sort_var = tk.StringVar()
        sort_options = [
            ("ID (Tăng dần)", "id_asc"),
            ("ID (Giảm dần)", "id_desc"),
            ("Tên (A-Z)", "name_asc"),
            ("Tên (Z-A)", "name_desc"),
            ("Email (A-Z)", "email_asc"),
            ("Email (Z-A)", "email_desc"),
            ("Ngày tạo (Cũ nhất)", "date_asc"),
            ("Ngày tạo (Mới nhất)", "date_desc"),
            ("Loại KH (A-Z)", "customer_type_asc"),
            ("Loại KH (Z-A)", "customer_type_desc")
        ]
        
        sort_combo = ttk.Combobox(first_row, textvariable=self.sort_var, 
                                 values=[option[0] for option in sort_options],
                                 font=("Arial", 10), width=20, state="readonly")
        sort_combo.pack(side=tk.LEFT, padx=5)
        sort_combo.bind('<<ComboboxSelected>>', self.on_sort)
        
        self.stats_label = tk.Label(first_row, text="", bg="lightgray", font=("Arial", 10), fg="blue")
        self.stats_label.pack(side=tk.RIGHT, padx=20)
        
        second_row = tk.Frame(toolbar_frame, bg="lightgray")
        second_row.pack(fill=tk.X, pady=5)
        
        btn_frame = tk.Frame(second_row, bg="lightgray")
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        # Cả admin và user đều có thể thêm khách hàng
        if self.user_manager.can_add_customers():
            tk.Button(btn_frame, text="Thêm KH", command=self.add_customer, 
                     bg="green", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        # Chỉ admin mới có nút sửa khách hàng
        if self.user_manager.can_edit_customers():
            tk.Button(btn_frame, text="Sửa KH", command=self.edit_customer, 
                     bg="orange", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        else:
            # User chỉ có thể xem thông tin
            tk.Button(btn_frame, text="Xem KH", command=self.view_customer, 
                     bg="blue", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        # Chỉ admin mới có nút xóa
        if self.user_manager.is_admin():
            tk.Button(btn_frame, text="Xóa KH", command=self.delete_customer, 
                     bg="red", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        if self.user_manager.is_admin():
            tk.Button(btn_frame, text="Import API", command=self.import_sample_data, 
                     bg="blue", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="Làm mới", command=self.refresh_data, 
                 bg="gray", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        # Thêm nút đổi mật khẩu
        tk.Button(btn_frame, text="Đổi MK", command=self.change_password, 
                 bg="darkgreen", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="Đăng xuất", command=self.logout, 
                 bg="purple", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        self.create_customer_tree()
    
    def create_customer_tree(self):
        """Tạo bảng danh sách khách hàng"""
        tree_frame = tk.Frame(self.window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("ID", "Tên", "Email", "Điện thoại", "Địa chỉ", "Loại KH", "Ngày tạo")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        column_widths = {"ID": 60, "Tên": 150, "Email": 200, "Điện thoại": 120, 
                        "Địa chỉ": 200, "Loại KH": 150, "Ngày tạo": 150}
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 150), anchor=tk.CENTER)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind double click - admin có thể edit, user chỉ xem
        if self.user_manager.can_edit_customers():
            self.tree.bind("<Double-1>", lambda event: self.edit_customer())
        else:
            self.tree.bind("<Double-1>", lambda event: self.view_customer())
    
    def load_customer_data(self, customers=None):
        """Tải dữ liệu khách hàng vào bảng"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if customers is None:
            customers = self.customer_manager.customers
        
        for customer in customers:
            self.tree.insert("", tk.END, values=(
                customer["id"],
                customer["name"],
                customer["email"],
                customer["phone"],
                customer["address"],
                customer.get("customer_type", "Khách hàng thường"),
                customer.get("created_date", "")
            ))
        
        self.update_statistics(len(customers))
    
    def update_statistics(self, count):
        """Cập nhật thống kê"""
        total = len(self.customer_manager.customers)
        if count == total:
            self.stats_label.config(text=f"Tổng số khách hàng: {total}")
        else:
            self.stats_label.config(text=f"Hiển thị: {count}/{total} khách hàng")
    
    def on_search(self, event=None):
        """Xử lý tìm kiếm"""
        keyword = self.search_var.get().strip()
        
        if keyword:
            customers = self.customer_manager.search_customers(keyword)
        else:
            customers = self.customer_manager.customers
        
        self.load_customer_data(customers)
    
    def on_sort(self, event=None):
        """Xử lý sắp xếp"""
        sort_option = self.sort_var.get()
        if not sort_option:
            return
        
        sort_mapping = {
            "ID (Tăng dần)": ("id", False),
            "ID (Giảm dần)": ("id", True),
            "Tên (A-Z)": ("name", False),
            "Tên (Z-A)": ("name", True),
            "Email (A-Z)": ("email", False),
            "Email (Z-A)": ("email", True),
            "Ngày tạo (Cũ nhất)": ("created_date", False),
            "Ngày tạo (Mới nhất)": ("created_date", True),
            "Loại KH (A-Z)": ("customer_type", False),
            "Loại KH (Z-A)": ("customer_type", True)
        }
        
        if sort_option in sort_mapping:
            column, reverse = sort_mapping[sort_option]
            sorted_customers = self.customer_manager.sort_customers(column, reverse)
            
            keyword = self.search_var.get().strip()
            if keyword:
                sorted_customers = [c for c in sorted_customers 
                                  if keyword.lower() in c["name"].lower() or 
                                     keyword.lower() in c["email"].lower() or 
                                     keyword.lower() in c["phone"].lower() or 
                                     keyword.lower() in c["address"].lower() or
                                     keyword.lower() in c.get("customer_type", "").lower()]
            
            self.load_customer_data(sorted_customers)
    
    def add_customer(self):
        """Thêm khách hàng mới - cả admin và user đều có quyền"""
        if not self.user_manager.can_add_customers():
            messagebox.showerror("Lỗi", "Bạn không có quyền thêm khách hàng!")
            return
        self.show_customer_form()
    
    def edit_customer(self):
        """Sửa thông tin khách hàng - chỉ admin"""
        if not self.user_manager.can_edit_customers():
            messagebox.showerror("Lỗi", "Bạn không có quyền sửa thông tin khách hàng!")
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn khách hàng cần sửa!")
            return
        
        item = self.tree.item(selected[0])
        customer_id = item["values"][0]
        
        customer = None
        for c in self.customer_manager.customers:
            if c["id"] == customer_id:
                customer = c
                break
        
        if customer:
            self.show_customer_form(customer)
    
    def view_customer(self):
        """Xem thông tin khách hàng - cho user"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn khách hàng cần xem!")
            return
        
        item = self.tree.item(selected[0])
        customer_id = item["values"][0]
        
        customer = None
        for c in self.customer_manager.customers:
            if c["id"] == customer_id:
                customer = c
                break
        
        if customer:
            self.show_customer_form(customer, view_only=True)
    
    def delete_customer(self):
        """Xóa khách hàng - chỉ admin"""
        if not self.user_manager.is_admin():
            messagebox.showerror("Lỗi", "Chỉ admin mới có quyền xóa khách hàng!")
            return
        
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn khách hàng cần xóa!")
            return
        
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa khách hàng này?"):
            item = self.tree.item(selected[0])
            customer_id = item["values"][0]
            
            if self.customer_manager.delete_customer(customer_id):
                messagebox.showinfo("Thành công", "Xóa khách hàng thành công!")
                self.refresh_data()
            else:
                messagebox.showerror("Lỗi", "Không thể xóa khách hàng!")
    
    def change_password(self):
        """Mở cửa sổ đổi mật khẩu"""
        ChangePasswordWindow(self.user_manager, self.window)
    
    def show_customer_form(self, customer=None, view_only=False):
        """Hiển thị form thêm/sửa/xem khách hàng"""
        if view_only:
            title = "Xem thông tin khách hàng"
        else:
            title = "Thêm khách hàng" if customer is None else "Sửa khách hàng"
            
        form_window = tk.Toplevel(self.window)
        form_window.title(title)
        form_window.geometry("500x450")
        form_window.resizable(False, False)
        
        form_window.transient(self.window)
        form_window.grab_set()
        
        fields = [
            ("Tên khách hàng:", "name"),
            ("Email:", "email"),
            ("Điện thoại:", "phone"),
            ("Địa chỉ:", "address"),
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            tk.Label(form_window, text=label_text, font=("Arial", 12)).grid(row=i, column=0, sticky="e", padx=10, pady=10)
            
            if field_name == "address":
                entry = tk.Text(form_window, font=("Arial", 12), width=30, height=3)
                entry.grid(row=i, column=1, padx=10, pady=10)
                if customer:
                    entry.insert("1.0", customer.get(field_name, ""))
                if view_only:
                    entry.config(state=tk.DISABLED)
            else:
                entry = tk.Entry(form_window, font=("Arial", 12), width=30)
                entry.grid(row=i, column=1, padx=10, pady=10)
                if customer:
                    entry.insert(0, customer.get(field_name, ""))
                if view_only:
                    entry.config(state="readonly")
            
            entries[field_name] = entry
        
        # Thêm dropdown cho loại khách hàng
        tk.Label(form_window, text="Loại khách hàng:", font=("Arial", 12)).grid(row=len(fields), column=0, sticky="e", padx=10, pady=10)
        
        customer_type_var = tk.StringVar()
        customer_type_combo = ttk.Combobox(form_window, textvariable=customer_type_var,
                                         values=self.customer_manager.customer_types,
                                         font=("Arial", 12), width=27, state="readonly")
        customer_type_combo.grid(row=len(fields), column=1, padx=10, pady=10)
        
        # Set giá trị mặc định
        if customer:
            current_type = customer.get("customer_type", "Khách hàng thường")
            if current_type in self.customer_manager.customer_types:
                customer_type_var.set(current_type)
            else:
                customer_type_var.set("Khách hàng thường")
        else:
            customer_type_var.set("Khách hàng thường")
        
        if view_only:
            customer_type_combo.config(state="disabled")
        
        button_frame = tk.Frame(form_window)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        def validate_email(email):
            """Kiểm tra định dạng email"""
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, email))
        
        def validate_phone(phone):
            """Kiểm tra định dạng số điện thoại"""
            phone_pattern = r'^(?:\+84|0)(?:\d{9}|\d{8})$|^(?:\+?\d{1,3})?\d{8,12}$'
            return bool(re.match(phone_pattern, phone))
        
        def save_customer():
            name = entries["name"].get().strip()
            email = entries["email"].get().strip()
            phone = entries["phone"].get().strip()
            address = entries["address"].get("1.0", tk.END).strip()
            customer_type = customer_type_var.get()
            
            if not name or not email or not phone:
                messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ thông tin bắt buộc!")
                return
            
            if not validate_email(email):
                messagebox.showerror("Lỗi", "Email không hợp lệ! Vui lòng nhập đúng định dạng (VD: ten@domain.com)")
                return
            
            if not validate_phone(phone):
                messagebox.showerror("Lỗi", "Số điện thoại không hợp lệ! Vui lòng nhập số hợp lệ (VD: +84912345678 hoặc 0912345678)")
                return
            
            if customer is None:
                success, message = self.customer_manager.add_customer(name, email, phone, address, customer_type)
                if success:
                    messagebox.showinfo("Thành công", message)
                    form_window.destroy()
                    self.refresh_data()
                else:
                    messagebox.showerror("Lỗi", message)
            else:
                success, message = self.customer_manager.update_customer(customer["id"], name, email, phone, address, customer_type)
                if success:
                    messagebox.showinfo("Thành công", message)
                    form_window.destroy()
                    self.refresh_data()
                else:
                    messagebox.showerror("Lỗi", message)
        
        if not view_only:
            tk.Button(button_frame, text="Lưu", command=save_customer, 
                     bg="green", fg="white", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Đóng" if view_only else "Hủy", command=form_window.destroy, 
                 bg="gray", fg="white", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        
        if not view_only:
            entries["name"].focus()
    
    def import_sample_data(self):
        """Import dữ liệu mẫu từ API - chỉ admin"""
        if not self.user_manager.is_admin():
            messagebox.showerror("Lỗi", "Chỉ admin mới có quyền import dữ liệu!")
            return
        
        if messagebox.askyesno("Xác nhận", "Import dữ liệu sẽ thay thế toàn bộ dữ liệu hiện tại. Bạn có chắc?"):
            loading_window = tk.Toplevel(self.window)
            loading_window.title("Đang tải...")
            loading_window.geometry("300x100")
            loading_window.resizable(False, False)
            loading_window.transient(self.window)
            loading_window.grab_set()
            
            tk.Label(loading_window, text="Đang tải dữ liệu từ API...", 
                    font=("Arial", 12)).pack(pady=30)
            
            def import_data():
                success = self.customer_manager.import_sample_data()
                loading_window.destroy()
                
                if success:
                    messagebox.showinfo("Thành công", "Import dữ liệu thành công!")
                    self.refresh_data()
                else:
                    messagebox.showerror("Lỗi", "Không thể import dữ liệu từ API!")
            
            threading.Thread(target=import_data, daemon=True).start()
    
    def refresh_data(self):
        """Làm mới dữ liệu"""
        self.customer_manager.customers = self.customer_manager.load_customers()
        self.load_customer_data()
        self.search_var.set("")
        self.sort_var.set("")
        messagebox.showinfo("Thành công", "Đã làm mới dữ liệu!")
    
    def logout(self):
        """Đăng xuất"""
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn đăng xuất?"):
            self.user_manager.logout()
            self.window.destroy()
            self.start()
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn thoát ứng dụng?"):
            self.window.destroy()

if __name__ == "__main__":
    print("Khởi động Hệ Thống Quản Lý Khách Hàng...")
    print("Tài khoản mặc định: admin / admin123")
    print("Câu hỏi bảo mật mặc định: Tên thú cưng đầu tiên của bạn?")
    print("Câu trả lời mặc định: admin")
    print("\nPhân quyền:")
    print("- Admin: Có thể thêm, sửa, xóa khách hàng và import dữ liệu")
    print("- User: Có thể thêm và xem thông tin khách hàng (không thể sửa/xóa)")
    print("\nLoại khách hàng:")
    print("- Khách hàng thường")
    print("- Khách hàng VIP")
    print("\nTính năng mới:")
    print("- Đổi mật khẩu!")
    
    app = CustomerManagementApp()
    app.start()