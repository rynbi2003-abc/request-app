import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
import psycopg2
import pytz
from psycopg2 import extras
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ thống Yêu cầu Bảo trì v2.0", layout="wide")

# Thiết lập múi giờ Hà Nội
local_tz = pytz.timezone("Asia/Ho_Chi_Minh")

def get_now():
    """Lấy thời gian hiện tại theo múi giờ Hà Nội"""
    return datetime.now(local_tz)

# Link sau khi bạn Deploy lên Streamlit Cloud
WEB_URL = "https://rynbi2003-abc-request-app-app-iimreh.streamlit.app/" 

# Cấu hình Email gửi đi
SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587
SENDER_EMAIL = "Mary.Nguyen@esquel.com" 
SENDER_PASSWORD = "nqfbwzfvqqmcxcbh" # App Password 16 ký tự

# Email các bên nhận thông báo
LEADER_EMAIL = "Mary.Nguyen@esquel.com"
MAINTENANCE_EMAIL = "Mary.Nguyen@esquel.com"

# Cấu hình Database Pooler
DB_CONFIG = {
    "host": "aws-1-ap-south-1.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.fucrufqdvsmkdevaguqy",
    "password": "y8JktKAHgnI5ycmf",
    "port": "6543"
}

# --- 2. DANH SÁCH MẬT KHẨU CỐ ĐỊNH ---
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
    return psycopg2.connect(**DB_CONFIG, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_requests (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
        st.error(f"Lỗi khởi tạo Cơ sở dữ liệu: {e}")

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
        st.error(f"Lỗi gửi email: {e}")
        return False

# --- 4. XỬ LÝ PHÊ DUYỆT QUA LINK ---

def handle_url_actions():
    params = st.query_params
    if "id" in params and "action" in params:
        req_id = params["id"]
        action = params["action"]
        
        line_name = "Unknown"
        item_name = "Linh kiện"
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT line_name, item_name FROM maintenance_requests WHERE id = %s", (req_id,))
            res = cur.fetchone()
            if res: 
                line_name = res[0]
                item_name = res[1]
            cur.close()
            conn.close()
        except: pass

        new_status = None
        next_mail_to = None
        next_subject = ""
        next_body = ""

        if action == "approve":
            new_status = "Đã duyệt ✅"
            next_mail_to = MAINTENANCE_EMAIL
            finish_link = f"{WEB_URL}/?id={req_id}&action=complete"
            next_subject = f"[CẤP PHÁT] Yêu cầu cấp linh kiện - {req_id} - {line_name}"
            next_body = f"""
            <h3>Thông báo cấp phát linh kiện</h3>
            <p>Leader đã duyệt yêu cầu <b>{req_id}</b> cho <b>{line_name}</b>.</p>
            <p><b>Linh kiện:</b> {item_name}</p>
            <p>Phòng bảo trì vui lòng chuẩn bị linh kiện và thực hiện thay thế.</p>
            <br>
            <a href='{finish_link}' style='background-color:#0078D4; color:white; padding:12px; text-decoration:none; border-radius:5px;'>XÁC NHẬN ĐÃ THAY XONG</a>
            """
        
        elif action == "reject":
            new_status = "Từ chối ❌"
            
        elif action == "complete":
            new_status = "Hoàn tất 🏁"
            next_mail_to = LEADER_EMAIL
            next_subject = f"[HOÀN TẤT] Yêu cầu cấp linh kiện - {req_id} - {line_name}"
            next_body = f"""
            <h3>Thông báo xử lý hoàn tất</h3>
            <p>Yêu cầu cấp linh kiện <b>{req_id}</b> cho <b>{line_name}</b> đã được bộ phận Bảo trì lắp đặt/thay thế hoàn tất.</p>
            """

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
                
                st.success(f"Trạng thái hiện tại: {new_status}")
                st.info("Bạn có thể đóng trang này.")
                st.stop()
            except Exception as e:
                st.error(f"Lỗi: {e}")

# --- 5. GIAO DIỆN CHÍNH ---

def login_ui():
    st.title("🛡️ Hệ thống Quản lý Yêu cầu Bảo trì")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.selectbox("Chọn Chuyền/Line", list(USER_CREDENTIALS.keys()))
            pw = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập"):
                if USER_CREDENTIALS.get(user) == pw.strip().upper():
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else: st.error("Mật khẩu không đúng!")

def main_app():
    st.sidebar.title(f"👤 {st.session_state.user}")
    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption("Phiên bản v2.3 (Hanoi Time)")

    st.header(f"📋 Form Yêu cầu - {st.session_state.user}")
    
    now = get_now()
    
    with st.form("request_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Ngày/Date", value=now.strftime("%d/%m/%Y %H:%M"), disabled=True)
            item = st.text_input("Tên linh kiện")
        with c2:
            qty = st.number_input("Số lượng", min_value=1, value=1)
            note = st.text_area("Ghi chú hỏng hóc")
        
        photo = st.camera_input("Chụp ảnh linh kiện thực tế")
        
        if st.form_submit_button("Gửi Yêu cầu & Thông báo Leader"):
            if not item or not photo:
                st.warning("Vui lòng nhập tên linh kiện và chụp ảnh!")
            else:
                # Tạo mã REQ dựa trên giờ Hà Nội
                req_id = f"REQ{now.strftime('%y%m%d%H%M%S')}"
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO maintenance_requests (id, line_name, item_name, quantity, note, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (req_id, st.session_state.user, item, qty, note, "Đang chờ duyệt ⏳", now)
                    )
                    conn.commit()
                    cur.close()
                    conn.close()

                    approve_link = f"{WEB_URL}/?id={req_id}&action=approve"
                    reject_link = f"{WEB_URL}/?id={req_id}&action=reject"
                    
                    mail_subject = f"[PHÊ DUYỆT] Yêu cầu cấp linh kiện - {req_id} - {st.session_state.user}"
                    
                    email_html = f"""
                    <div style="font-family: Arial; border: 1px solid #ddd; padding: 20px;">
                        <h2 style="color:#0078D4;">YÊU CẦU PHÊ DUYỆT LINH KIỆN</h2>
                        <p><b>Thời gian gửi:</b> {now.strftime('%H:%M %d/%m/%Y')}</p>
                        <p><b>Mã yêu cầu:</b> {req_id}</p>
                        <p><b>Từ Chuyền:</b> {st.session_state.user}</p>
                        <p><b>Linh kiện:</b> {item} (Số lượng: {qty})</p>
                        <p><b>Ghi chú:</b> {note}</p>
                        <hr>
                        <div style="margin-top:20px;">
                            <a href='{approve_link}' style='background-color:#28a745; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;'>ĐỒNG Ý (APPROVE)</a>
                            &nbsp;
                            <a href='{reject_link}' style='background-color:#dc3545; color:white; padding:12px 25px; text-decoration:none; border-radius:5px;'>TỪ CHỐI (REJECT)</a>
                        </div>
                        <p style="margin-top:20px;"><b>Hình ảnh thực tế:</b></p>
                        <img src="cid:item_photo" style="max-width:100%; border: 1px solid #ccc;">
                    </div>
                    """
                    
                    if send_mail(LEADER_EMAIL, mail_subject, email_html, photo.getvalue()):
                        st.success(f"Đã gửi yêu cầu {req_id} thành công (Giờ Hà Nội)!")
                        st.balloons()
                        st.cache_data.clear()
                except Exception as e:
                    st.error(f"Lỗi database: {e}")

    # Hiển thị lịch sử
    st.divider()
    st.subheader("📜 Lịch sử yêu cầu")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.DictCursor)
        cur.execute(
            "SELECT id, created_at, item_name, quantity, status FROM maintenance_requests WHERE line_name = %s ORDER BY created_at DESC LIMIT 15",
            (st.session_state.user,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            df = pd.DataFrame(rows, columns=['Mã', 'Ngày tạo', 'Linh kiện', 'SL', 'Trạng thái'])
            # Chuyển đổi thời gian từ DB sang múi giờ Hà Nội để hiển thị chính xác
            df['Ngày tạo'] = pd.to_datetime(df['Ngày tạo']).dt.tz_convert(local_tz).dt.strftime('%H:%M %d/%m/%Y')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu yêu cầu.")
    except Exception as e:
        st.error(f"Không thể tải lịch sử: {e}")

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
