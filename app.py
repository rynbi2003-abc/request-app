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

# Link thật của bạn
WEB_URL = "https://rynbi2003-abc-request-app-app-iimreh.streamlit.app" 

# Cấu hình Email gửi đi
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SENDER_EMAIL = "Mary.Nguyen@esquel.com" 
SENDER_PASSWORD = "@Tessel!2#$%6" 

# Email nhận thông báo
LEADER_EMAIL = "Mary.Nguyen@esquel.com"
MAINTENANCE_EMAIL = "Mary.Nguyen@esquel.com"

# Cấu hình Database Pooler (Cổng 6543)
DB_CONFIG = {
    "host": "aws-0-ap-southeast-1.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.fucrufqdvsmkdevaguqy",
    "password": "y8JktKAHgnI5ycmf",
    "port": "6543"
}

# --- 2. DANH SÁCH MẬT KHẨU ---
USER_CREDENTIALS = {
    "Line 1": "TDV254", "Line 2": "TDV144", "Line 3": "TDV582", "Line 4": "TDV916", "Line 5": "TDV625",
    "Line 6": "TDV691", "Line 7": "TDV293", "Line 8": "TDV972", "Line 9": "TDV938", "Line 10": "TDV230",
    "Line 11": "TDV353", "Line 12": "TDV323", "Line 13": "TDV615", "Line 14": "TDV769", "Line 15": "TDV813",
    "Line 16": "TDV291", "Line 17": "TDV703", "Line 18": "TDV230", "Line 19": "TDV982", "Line 20": "TDV408",
    "Line 21": "TDV117", "Line 22": "TDV532", "Line 23": "TDV364", "Line 24": "TDV522", "Line 25": "TDV314",
    "Line 26": "TDV591", "Line 27": "TDV154", "Line 28": "TDV414", "Line 29": "TDV403", "Line 30": "TDV500"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, sslmode='require')

def init_db():
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
        st.error(f"Lỗi khởi tạo CSDL: {e}")

def send_mail(to_email, subject, html_content, image_data=None):
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
        st.error(f"Lỗi gửi mail: {e}")
        return False

def handle_url_actions():
    params = st.query_params
    if "id" in params and "action" in params:
        req_id = params["id"]
        action = params["action"]
        new_status = None
        if action == "approve":
            new_status = "Đã duyệt ✅"
            send_mail(MAINTENANCE_EMAIL, f"[CẤP PHÁT] {req_id} đã duyệt", f"Duyệt yêu cầu {req_id}. <br><a href='{WEB_URL}/?id={req_id}&action=complete'>Xác nhận hoàn tất</a>")
        elif action == "reject":
            new_status = "Từ chối ❌"
        elif action == "complete":
            new_status = "Hoàn tất 🏁"
            send_mail(LEADER_EMAIL, f"[XONG] {req_id} hoàn tất", f"Yêu cầu {req_id} đã xong.")
        
        if new_status:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE maintenance_requests SET status = %s WHERE id = %s", (new_status, req_id))
                conn.commit()
                conn.close()
                st.success(f"Cập nhật thành công: {new_status}")
                st.stop()
            except Exception as e:
                st.error(f"Lỗi cập nhật trạng thái: {e}")

def login_ui():
    st.title("🛡️ Hệ thống Quản lý Bảo trì")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.selectbox("Chọn Chuyền", list(USER_CREDENTIALS.keys()))
            pw = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập"):
                if USER_CREDENTIALS.get(user) == pw.strip().upper():
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else: st.error("Mật khẩu không đúng!")

def main_app():
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.header("📋 Gửi yêu cầu bảo trì")
    with st.form("request_form", clear_on_submit=True):
        item = st.text_input("Tên linh kiện")
        qty = st.number_input("Số lượng", min_value=1, value=1)
        note = st.text_area("Ghi chú")
        photo = st.camera_input("Chụp ảnh linh kiện hỏng")
        
        if st.form_submit_button("Gửi Yêu cầu & Thông báo Mail"):
            if item and photo:
                req_id = f"REQ{datetime.now().strftime('%y%m%d%H%M%S')}"
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO maintenance_requests (id, line_name, item_name, quantity, note, status) VALUES (%s,%s,%s,%s,%s,%s)", 
                        (req_id, st.session_state.user, item, qty, note, "Chờ duyệt ⏳")
                    )
                    conn.commit()
                    conn.close()
                    
                    body = f"""
                    <h3>Yêu cầu bảo trì mới từ {st.session_state.user}</h3>
                    <p><b>Linh kiện:</b> {item} - <b>Số lượng:</b> {qty}</p>
                    <p><b>Ghi chú:</b> {note}</p>
                    <br>
                    <a href='{WEB_URL}/?id={req_id}&action=approve' style='padding:10px; background:green; color:white; text-decoration:none;'>CHẤP NHẬN (APPROVE)</a>
                    &nbsp;
                    <a href='{WEB_URL}/?id={req_id}&action=reject' style='padding:10px; background:red; color:white; text-decoration:none;'>TỪ CHỐI (REJECT)</a>
                    <br><br>
                    <img src='cid:item_photo'>
                    """
                    if send_mail(LEADER_EMAIL, f"Yêu cầu {req_id} - {st.session_state.user}", body, photo.getvalue()):
                        st.success(f"Đã gửi yêu cầu {req_id} thành công!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Lỗi lưu dữ liệu: {e}")
            else: st.warning("Vui lòng điền tên linh kiện và chụp ảnh!")

    # --- PHẦN LỊCH SỬ ---
    st.divider()
    st.subheader("📜 Lịch sử yêu cầu của chuyền")
    try:
        conn = get_db_connection()
        # Truy vấn lấy 10 bản ghi mới nhất của chuyền hiện tại
        query = "SELECT created_at, item_name, quantity, status FROM maintenance_requests WHERE line_name = %s ORDER BY created_at DESC LIMIT 10"
        df = pd.read_sql(query, conn, params=(st.session_state.user,))
        conn.close()
        
        if not df.empty:
            df.columns = ['Thời gian', 'Linh kiện', 'SL', 'Trạng thái']
            # Định dạng lại cột thời gian để dễ nhìn
            df['Thời gian'] = pd.to_datetime(df['Thời gian']).dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có lịch sử yêu cầu nào cho chuyền này.")
    except Exception as e:
        st.error(f"Không thể tải lịch sử: {e}")

if __name__ == "__main__":
    init_db()
    handle_url_actions()
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in: login_ui()
    else: main_app()
