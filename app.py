import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
import psycopg2
from psycopg2 import extras
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống Yêu cầu Bảo trì v2.0", layout="wide")

# Link sau khi bạn Deploy lên Streamlit Cloud (Cần cập nhật sau khi có link chính thức)
WEB_URL = "https://your-app-url.streamlit.app" 

# Cấu hình Email gửi đi (Office 365 / Outlook công ty)
SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587
SENDER_EMAIL = "Mary.Nguyen@esquel.com" 
SENDER_PASSWORD = "nqfbwzfvqqmcxcbh" # App Password 16 ký tự từ Microsoft

# Email các bên nhận thông báo
LEADER_EMAIL = "Mary.Nguyen@esquel.com"
MAINTENANCE_EMAIL = "Mary.Nguyen@esquel.com"

# Cấu hình Database (Lấy từ Supabase -> Project Settings -> Database)
DB_CONFIG = {
    "host": "db.fucrufqdvsmkdevaguqy.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "y8JktKAHgnI5ycmf",
    "port": "5432"
}

# --- 2. DANH SÁCH MẬT KHẨU CỐ ĐỊNH (TỪ CODE GỐC CỦA BẠN) ---
USER_CREDENTIALS = {
    "Line 1": "TDV254", "Line 2": "TDV144", "Line 3": "TDV582", "Line 4": "TDV916", "Line 5": "TDV625",
    "Line 6": "TDV691", "Line 7": "TDV293", "Line 8": "TDV972", "Line 9": "TDV938", "Line 10": "TDV230",
    "Line 11": "TDV353", "Line 12": "TDV323", "Line 13": "TDV615", "Line 14": "TDV769", "Line 15": "TDV813",
    "Line 16": "TDV291", "Line 17": "TDV703", "Line 18": "TDV230", "Line 19": "TDV982", "Line 20": "TDV408",
    "Line 21": "TDV117", "Line 22": "TDV532", "Line 23": "TDV364", "Line 24": "TDV522", "Line 25": "TDV314",
    "Line 26": "TDV591", "Line 27": "TDV154", "Line 28": "TDV414", "Line 29": "TDV403", "Line 30": "TDV500"
}

# --- 3. CÁC HÀM XỬ LÝ DATABASE & EMAIL ---

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """Khởi tạo bảng trên PostgreSQL nếu chưa có"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_requests (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                line_name TEXT,
                item_name TEXT,
                quantity INTEGER,
                note TEXT,
                status TEXT
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Lỗi kết nối Cơ sở dữ liệu: {e}")

def send_mail(to_email, subject, html_content, image_data=None):
    """Gửi email thông báo kèm hình ảnh phụ kiện hỏng"""
    try:
        msg = MIMEMultipart('related')
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))
        
        if image_data:
            img = MIMEImage(image_data)
            img.add_header('Content-ID', '<item_photo>')
            msg.attach(img)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Lỗi gửi email: {e}")
        return False

# --- 4. XỬ LÝ PHÊ DUYỆT TỰ ĐỘNG ---

def handle_url_actions():
    """Xử lý các hành động Duyệt/Từ chối/Hoàn tất khi nhấn link từ Email"""
    params = st.query_params
    if "id" in params and "action" in params:
        req_id = params["id"]
        action = params["action"]
        
        new_status = None
        next_mail_to = None
        next_subject = ""
        next_body = ""

        if action == "approve":
            new_status = "Đã duyệt ✅"
            next_mail_to = MAINTENANCE_EMAIL
            finish_link = f"{WEB_URL}/?id={req_id}&action=complete"
            next_subject = f"[CẤP PHÁT] Yêu cầu {req_id} đã được duyệt"
            next_body = f"""
            <h3>Yêu cầu {req_id} đã được phê duyệt</h3>
            <p>Phòng bảo trì vui lòng tiến hành cấp phát linh kiện cho chuyền.</p>
            <br>
            <a href='{finish_link}' style='background-color:#0078D4; color:white; padding:12px; text-decoration:none; border-radius:5px;'>XÁC NHẬN ĐÃ THAY THẾ XONG</a>
            """
        
        elif action == "reject":
            new_status = "Từ chối ❌"
            
        elif action == "complete":
            new_status = "Hoàn tất 🏁"
            next_mail_to = LEADER_EMAIL
            next_subject = f"[HOÀN TẤT] Linh kiện {req_id} đã được thay xong"
            next_body = f"<h3>Thông báo</h3><p>Yêu cầu {req_id} đã được bộ phận Bảo trì xử lý hoàn tất tại hiện trường.</p>"

        if new_status:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE maintenance_requests SET status = %s WHERE id = %s", (new_status, req_id))
                conn.commit()
                cur.close()
                conn.close()
                
                if next_mail_to:
                    send_mail(next_mail_to, next_subject, next_body)
                
                st.success(f"Hệ thống đã ghi nhận trạng thái: {new_status}")
                st.info("Bạn có thể đóng trang web này.")
                st.stop()
            except Exception as e:
                st.error(f"Lỗi cập nhật: {e}")

# --- 5. GIAO DIỆN CHÍNH ---

def login_ui():
    st.title("🛡️ Hệ thống Quản lý Yêu cầu Bảo trì")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.selectbox("Chọn Chuyền/Line", list(USER_CREDENTIALS.keys()))
            pw = st.text_input("Mật khẩu (TDV...)", type="password")
            if st.form_submit_button("Đăng nhập Hệ thống"):
                if USER_CREDENTIALS.get(user) == pw.strip().upper():
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Mật khẩu không chính xác. Vui lòng thử lại!")

def main_app():
    # Sidebar
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption("Phiên bản Cloud v2.0 - PostgreSQL")

    # Form Yêu cầu
    st.header(f"📋 Form Yêu cầu Linh kiện - {st.session_state.user}")
    
    with st.form("request_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Ngày/Date", value=datetime.now().strftime("%d/%m/%Y %H:%M"), disabled=True)
            item = st.text_input("Tên linh kiện/phụ tùng (Items Description)")
        with c2:
            qty = st.number_input("Số lượng yêu cầu (Quantity)", min_value=1, value=1)
            note = st.text_area("Ghi chú/Lý do hỏng (Remark)")
        
        photo = st.camera_input("Chụp ảnh linh kiện hỏng")
        
        if st.form_submit_button("Gửi Yêu cầu & Chờ Phê duyệt"):
            if not item or not photo:
                st.warning("Vui lòng nhập tên linh kiện và chụp ảnh minh họa!")
            else:
                req_id = f"REQ{datetime.now().strftime('%y%m%d%H%M%S')}"
                try:
                    # 1. Lưu vào Database Cloud
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO maintenance_requests (id, line_name, item_name, quantity, note, status) VALUES (%s, %s, %s, %s, %s, %s)",
                        (req_id, st.session_state.user, item, qty, note, "Đang chờ duyệt ⏳")
                    )
                    conn.commit()
                    cur.close()
                    conn.close()

                    # 2. Tạo nội dung Email cho Leader
                    approve_link = f"{WEB_URL}/?id={req_id}&action=approve"
                    reject_link = f"{WEB_URL}/?id={req_id}&action=reject"
                    
                    email_body = f"""
                    <div style="font-family: Arial; border: 1px solid #ddd; padding: 20px;">
                        <h2 style="color:#0078D4;">YÊU CẦU PHÊ DUYỆT MỚI</h2>
                        <p><b>Mã yêu cầu:</b> {req_id}</p>
                        <p><b>Từ:</b> {st.session_state.user}</p>
                        <p><b>Linh kiện:</b> {item} (Số lượng: {qty})</p>
                        <p><b>Ghi chú:</b> {note}</p>
                        <hr>
                        <div style="margin-top:20px;">
                            <a href='{approve_link}' style='background-color:#28a745; color:white; padding:12px 25px; text-decoration:none; border-radius:5px; margin-right:10px;'>ĐỒNG Ý (APPROVE)</a>
                            <a href='{reject_link}' style='background-color:#dc3545; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;'>TỪ CHỐI (REJECT)</a>
                        </div>
                        <p style="margin-top:20px;"><b>Hình ảnh thực tế:</b></p>
                        <img src="cid:item_photo" style="max-width:100%; border: 1px solid #ccc;">
                    </div>
                    """
                    
                    if send_mail(LEADER_EMAIL, f"[PHÊ DUYỆT] {req_id} - {st.session_state.user}", email_body, photo.getvalue()):
                        st.success(f"Gửi yêu cầu {req_id} thành công! Vui lòng chờ Leader phê duyệt qua email.")
                        st.balloons()
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")

    # Lịch sử yêu cầu
    st.divider()
    st.subheader("📜 Lịch sử yêu cầu của chuyền")
    try:
        conn = get_db_connection()
        query = "SELECT id as Mã, created_at as Ngày, item_name as Linh_kiện, quantity as SL, status as Trạng_thái FROM maintenance_requests WHERE line_name = %s ORDER BY created_at DESC LIMIT 15"
        df = pd.read_sql(query, conn, params=(st.session_state.user,))
        conn.close()
        if not df.empty:
            df['Ngày'] = pd.to_datetime(df['Ngày']).dt.strftime('%H:%M %d/%m/%Y')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu yêu cầu nào.")
    except:
        st.write("Đang khởi tạo dữ liệu...")

# --- 6. KHỞI CHẠY ---

if __name__ == "__main__":
    init_db()
    handle_url_actions()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_ui()
    else:
        main_app()
