import json
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CẤU HÌNH HỆ THỐNG ---
# 1. Tải các biến từ file .env
load_dotenv()

# 2. Lấy Token từ biến môi trường
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Lấy danh sách ID và chuyển thành Set để tra cứu O(1)
ALLOWED_USER_IDS_RAW = os.getenv(
    "ALLOWED_USER_IDS", ""
)  # <--- Lấy ID chủ nhân từ file .env
ALLOWED_USER_IDS = set(
    uid.strip() for uid in ALLOWED_USER_IDS_RAW.split(",") if uid.strip()
)

# 3. Kiểm tra xem đã lấy được Token chưa
if not TOKEN:
    print("❌ LỖI: Không tìm thấy Token!")
    print("👉 Hãy tạo file '.env' và thêm dòng: TELEGRAM_TOKEN=your_token_here")
    sys.exit(1)  # Dừng chương trình ngay lập tức

if not ALLOWED_USER_IDS:
    print(
        "⚠️ CẢNH BÁO: Bạn chưa cài ALLOWED_USER_ID trong file .env. Bot đang công khai cho mọi người!"
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# --- SECURITY LAYER ---
async def check_authorization(update: Update) -> bool:
    """
    Middleware kiểm tra quyền truy cập.
    Trả về True nếu user nằm trong whitelist.
    """
    if not ALLOWED_USER_IDS:
        return True  # Mở cho tất cả nếu không có cấu hình

    user_id = str(update.effective_user.id)

    if user_id not in ALLOWED_USER_IDS:
        # Tùy chọn: Có thể log lại attempt truy cập trái phép
        logging.warning(f"Unauthorized access attempt from user ID: {user_id}")
        await update.message.reply_text("⛔ **BẠN KHÔNG CÓ QUYỀN TRUY CẬP BOT NÀY.**")
        return False

    return True


# --- XỬ LÝ DỮ LIỆU ---
def get_user_filename(user_id: str) -> str:
    """Tạo tên file riêng biệt cho từng user ID."""
    return f"portfolio_{user_id}.json"


def load_portfolio(user_id: str):
    filename = get_user_filename(user_id)
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_portfolio(user_id: str, data: dict):
    filename = get_user_filename(user_id)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Failed to save data for user {user_id}: {e}")


# --- HÀM TÍNH TOÁN HỖ TRỢ ---
def get_status_text(total_spent, total_received, quantity):
    """
    Tính toán trạng thái vốn và điểm hoà vốn
    """
    net_cost = total_spent - total_received  # Số tiền thực tế đang nằm trong coin

    if quantity <= 0:
        # Đã bán hết
        pnl = -net_cost  # (Thu - Chi)
        emoji = "🟢 LÃI RÒNG" if pnl >= 0 else "🔴 LỖ THỰC TẾ"
        return f"{emoji}: ${pnl:,.2f} (Đã tất toán)"

    # Vẫn còn coin
    if net_cost <= 0:
        # Đã thu hồi đủ vốn, số coin còn lại là miễn phí (Moonbag)
        profit_taken = -net_cost
        return f"♾️ **Đã lãi gốc ${profit_taken:,.2f}**. (Số coin còn lại là Free)"
    else:
        # Vẫn còn vốn kẹt, tính giá hoà vốn
        be_price = net_cost / quantity
        return f"⚖️ **Hoà vốn tại giá: ${be_price:,.2f}**"


# --- CÁC HÀM XỬ LÝ LỆNH ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền sở hữu ngay đầu hàm
    if not await check_authorization(update):
        return

    msg = (
        "📊 **Bot Quản Lý Dòng Tiền Crypto**\n\n"
        "Các lệnh đầy đủ (Command Handler đầy đủ):\n"
        "1️⃣ `/buy <Tên> <Số Tiền USDT> <Giá>`\n"
        "2️⃣ `/sell <Tên> <Số Tiền USDT> <Giá>`\n"
        "3️⃣ `/list` - Xem báo cáo dòng tiền\n"
        "4️⃣ `/reset` - ⚠️ Xoá toàn bộ dữ liệu làm lại từ đầu\n"
        "\n"
        "Các lệnh ngắn gọn (Command Handler ngắn gọn):\n"
        "5️⃣ `/b <Tên> <Số Tiền USDT> <Giá>`\n"
        "6️⃣ `/s <Tên> <Số Tiền USDT> <Giá>`\n"
        "7️⃣ `/ls` - Xem báo cáo dòng tiền\n"
        "8️⃣ `/rs` - ⚠️ Xoá toàn bộ dữ liệu làm lại từ đầu"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("⚠️ Dùng: /buy BTC 1000 65000")
            return

        token = args[0].upper()
        usdt_amount = float(args[1])
        price = float(args[2])

        if price <= 0 or usdt_amount <= 0:
            return

        quantity = usdt_amount / price

        # Load dữ liệu riêng của user
        portfolio = load_portfolio(user_id)

        if token not in portfolio:
            portfolio[token] = {
                "quantity": 0.0,
                "total_spent": 0.0,
                "total_received": 0.0,
                "transactions": [],
            }

        if "transactions" not in portfolio[token]:
            portfolio[token]["transactions"] = []

        portfolio[token]["quantity"] += quantity
        portfolio[token]["total_spent"] += usdt_amount
        
        # Record Transaction
        portfolio[token]["transactions"].append({
            "type": "buy",
            "quantity": quantity,
            "price": price,
            "usdt_amount": usdt_amount,
            "timestamp": datetime.now().isoformat()
        })

        # Lưu lại vào file riêng
        save_portfolio(user_id, portfolio)

        data = portfolio[token]
        status = get_status_text(
            data["total_spent"], data["total_received"], data["quantity"]
        )

        msg = (
            f"📥 **MUA THÊM {token}**\n"
            f"➕ Mua: `{quantity:.6f}` {token} (Giá ${price:,.2f})\n"
            f"💸 Chi lệnh này: `${usdt_amount:,.2f}`\n"
            f"--------------------------\n"
            f"📊 **Tổng kết {token}:**\n"
            f"🔴 Tổng CHI: `${data['total_spent']:,.2f}`\n"
            f"🟢 Tổng THU: `${data['total_received']:,.2f}`\n"
            f"📦 Holding: `{data['quantity']:.6f}`\n"
            f"{status}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("⚠️ Lỗi nhập số.")


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "⚠️ Dùng: /sell BTC 999999 70000 (để bán hết)"
            )
            return

        token = args[0].upper()
        input_usdt_value = float(args[1])
        sell_price = float(args[2])

        portfolio = load_portfolio(user_id)

        if token not in portfolio or portfolio[token]["quantity"] <= 0:
            await update.message.reply_text(f"⚠️ Bạn chưa có {token} để bán.")
            return

        data = portfolio[token]
        current_qty = data["quantity"]

        requested_qty = input_usdt_value / sell_price

        if requested_qty >= current_qty:
            qty_sold = current_qty
            usdt_received = current_qty * sell_price
            data["quantity"] = 0
        else:
            qty_sold = requested_qty
            usdt_received = input_usdt_value
            data["quantity"] -= qty_sold

        data["total_received"] += usdt_received

        if "transactions" not in data:
            data["transactions"] = []

        # Record Transaction
        data["transactions"].append({
            "type": "sell",
            "quantity": qty_sold,
            "price": sell_price,
            "usdt_received": usdt_received,
            "timestamp": datetime.now().isoformat()
        })

        save_portfolio(user_id, portfolio)

        status = get_status_text(
            data["total_spent"], data["total_received"], data["quantity"]
        )

        msg = (
            f"📤 **BÁN RA {token}**\n"
            f"➖ Bán: `{qty_sold:.6f}` {token} (Giá ${sell_price:,.2f})\n"
            f"💵 Thu về lệnh này: `${usdt_received:,.2f}`\n"
            f"--------------------------\n"
            f"📊 **Tổng kết {token}:**\n"
            f"🔴 Tổng CHI: `${data['total_spent']:,.2f}`\n"
            f"🟢 Tổng THU: `${data['total_received']:,.2f}`\n"
            f"📦 Holding: `{data['quantity']:.6f}`\n"
            f"{status}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("⚠️ Lỗi nhập số.")


async def list_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    portfolio = load_portfolio(user_id)

    if not portfolio:
        await update.message.reply_text("📂 Portfolio của bạn đang trống.")
        return

    message_lines = ["📑 **BÁO CÁO DÒNG TIỀN (CASH FLOW)**", ""]

    grand_total_spent = 0
    grand_total_received = 0

    for token, data in portfolio.items():
        qty = data.get("quantity", 0)
        spent = data.get("total_spent", 0)
        received = data.get("total_received", 0)

        if spent == 0 and received == 0:
            continue

        grand_total_spent += spent
        grand_total_received += received

        net_cost = spent - received
        status_line = ""

        if qty <= 0:
            pnl = received - spent
            emoji = "🟢" if pnl >= 0 else "🔴"
            status_line = f"   🏁 Đã tất toán. PnL: {emoji} ${pnl:,.2f}"
        elif net_cost <= 0:
            status_line = f"   ♾️ Đã lãi gốc: ${-net_cost:,.2f} (Free Coin)"
        else:
            be = net_cost / qty
            status_line = f"   ⚖️ Hoà vốn: ${be:,.2f}"

        message_lines.append(
            f"🔹 **{token}** (Hold: {qty:.4f})\n"
            f"   🔴 Chi: ${spent:,.2f} | 🟢 Thu: ${received:,.2f}\n"
            f"{status_line}"
            # f"-----------------------------"
        )
        message_lines.append("\n")
    message_lines.pop()

    net_pnl_all = grand_total_received - grand_total_spent

    message_lines.append("-----------------------------")
    message_lines.append(f"TOTAL CHI: `${grand_total_spent:,.2f}`")
    message_lines.append(f"TOTAL THU: `${grand_total_received:,.2f}`")
    message_lines.append(f"DÒNG TIỀN RÒNG: `${net_pnl_all:,.2f}`")

    await update.message.reply_text("\n".join(message_lines), parse_mode="Markdown")


async def reset_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        # Chỉ save file rỗng vào ID của người gọi lệnh
        save_portfolio(user_id, {})
        await update.message.reply_text(
            "🗑️ Đã xoá Portfolio của bạn.**\nBạn có thể bắt đầu lại từ đầu."
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Có lỗi khi reset: {e}")


# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Commnand Handler đầy đủ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("list", list_portfolio))
    app.add_handler(CommandHandler("reset", reset_portfolio))

    # Command Handler ngắn gọn
    app.add_handler(CommandHandler("b", buy))
    app.add_handler(CommandHandler("s", sell))
    app.add_handler(CommandHandler("ls", list_portfolio))
    app.add_handler(CommandHandler("rs", reset_portfolio))

    print(f"Bot đang chạy với {len(ALLOWED_USER_IDS)} user(s) được cấp quyền...")
    app.run_polling()
