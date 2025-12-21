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
    print(TEXT["error"]["token_missing"])
    print(TEXT["error"]["env_instruction"])
    sys.exit(1)  # Dừng chương trình ngay lập tức

if not ALLOWED_USER_IDS:
    print(
        TEXT["error"]["allowed_id_warning"]
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- LOCALIZATION ---
def load_locales(lang='vi'):
    path = os.path.join(os.path.dirname(__file__), 'locales', f'{lang}.json')
    if not os.path.exists(path):
        logging.warning(f"Locale file not found: {path}, using default dict")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load locale: {e}")
        return {}

TEXT = load_locales('vi')


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
        logging.warning(TEXT["auth"]["unauthorized_log"].format(user_id=user_id))
        await update.message.reply_text(TEXT["auth"]["unauthorized_msg"])
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
def get_status_text(total_spent, total_received, quantity, stop_loss_limit=0):
    """
    Tính toán trạng thái vốn và điểm hoà vốn
    """
    net_cost = total_spent - total_received  # Số tiền thực tế đang nằm trong coin

    if quantity <= 0:
        # Đã bán hết
        pnl = -net_cost  # (Thu - Chi)
        emoji = TEXT["status"]["profit"] if pnl >= 0 else TEXT["status"]["loss"]
        return TEXT["status"]["sold_all"].format(emoji=emoji, pnl=pnl)

    # Vẫn còn coin
    if net_cost <= 0:
        # Đã thu hồi đủ vốn, số coin còn lại là miễn phí (Moonbag)
        profit_taken = -net_cost
        return TEXT["status"]["free_coin"].format(profit_taken=profit_taken)
    else:
        # Vẫn còn vốn kẹt, tính giá hoà vốn
        be_price = net_cost / quantity
        base_text = TEXT["status"]["break_even"].format(be_price=be_price)
        
        # Tính điểm dừng lỗ nếu có cài đặt
        if stop_loss_limit > 0:
            if net_cost > stop_loss_limit:
                sl_price = (net_cost - stop_loss_limit) / quantity
            else:
                sl_price = 0.0
            base_text += TEXT["status"]["stop_loss"].format(sl_price=sl_price, stop_loss_limit=stop_loss_limit)
            
        return base_text


# --- CÁC HÀM XỬ LÝ LỆNH ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền sở hữu ngay đầu hàm
    if not await check_authorization(update):
        return

    msg = TEXT["commands"]["start"]
    await update.message.reply_text(msg, parse_mode="Markdown")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(TEXT["commands"]["buy"]["usage"])
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
        sl_limit = data.get("stop_loss_limit", 0)
        status = get_status_text(
            data["total_spent"], data["total_received"], data["quantity"], sl_limit
        )

        msg = TEXT["commands"]["buy"]["success"].format(
                token=token,
                quantity=quantity,
                price=price,
                usdt_amount=usdt_amount,
                total_spent=data['total_spent'],
                total_received=data['total_received'],
                quantity_hold=data['quantity'],
                status=status
            )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text(TEXT["error"]["value_error"])


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                TEXT["commands"]["sell"]["usage"]
            )
            return

        token = args[0].upper()
        input_usdt_value = float(args[1])
        sell_price = float(args[2])

        portfolio = load_portfolio(user_id)

        if token not in portfolio or portfolio[token]["quantity"] <= 0:
            await update.message.reply_text(TEXT["commands"]["sell"]["not_hold"].format(token=token))
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

        sl_limit = data.get("stop_loss_limit", 0)
        status = get_status_text(
            data["total_spent"], data["total_received"], data["quantity"], sl_limit
        )

        msg = TEXT["commands"]["sell"]["success"].format(
                token=token,
                qty_sold=qty_sold,
                sell_price=sell_price,
                usdt_received=usdt_received,
                total_spent=data['total_spent'],
                total_received=data['total_received'],
                quantity_hold=data['quantity'],
                status=status
            )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text(TEXT["error"]["value_error"])


async def list_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    portfolio = load_portfolio(user_id)

    if not portfolio:
        await update.message.reply_text(TEXT["commands"]["list"]["empty"])
        return

    message_lines = [TEXT["commands"]["list"]["header"], ""]

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
            emoji = TEXT["status"]["profit"] if pnl >= 0 else TEXT["status"]["loss"]
            status_line = TEXT["commands"]["list"]["item_sold"].format(emoji=emoji, pnl=pnl)
        elif net_cost <= 0:
            status_line = TEXT["commands"]["list"]["item_free"].format(profit_taken=-net_cost)
        else:
            be = net_cost / qty
            status_line = TEXT["commands"]["list"]["item_hold"].format(be=be)
            
            # Check Stop Loss
            sl_limit = data.get("stop_loss_limit", 0)
            if sl_limit > 0:
                if net_cost > sl_limit:
                    sl_price = (net_cost - sl_limit) / qty
                else:
                    sl_price = 0.0
                status_line += TEXT["status"]["stop_loss_line"].format(sl_price=sl_price)

        message_lines.append(
            TEXT["commands"]["list"]["item_full_line1"].format(token=token, qty=qty) +
            TEXT["commands"]["list"]["item_full_line2"].format(spent=spent, received=received) +
            status_line
        )
        message_lines.append("\n")
    message_lines.pop()

    net_pnl_all = grand_total_received - grand_total_spent

    message_lines.append(TEXT["commands"]["list"]["footer_line1"])
    message_lines.append(TEXT["commands"]["list"]["footer_line2"].format(grand_total_spent=grand_total_spent))
    message_lines.append(TEXT["commands"]["list"]["footer_line3"].format(grand_total_received=grand_total_received))
    message_lines.append(TEXT["commands"]["list"]["footer_line4"].format(net_pnl_all=net_pnl_all))

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
            TEXT["commands"]["reset"]["success"]
        )
    except Exception as e:
        await update.message.reply_text(TEXT["error"]["reset_error"].format(error=e))


async def set_stop_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Kiểm tra quyền
    if not await check_authorization(update):
        return

    user_id = str(update.effective_user.id)
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(TEXT["commands"]["sl"]["usage"])
            return

        token = args[0].upper()
        stop_loss_amount = float(args[1])

        if stop_loss_amount < 0:
            await update.message.reply_text(TEXT["commands"]["sl"]["invalid_amount"])
            return
            
        portfolio = load_portfolio(user_id)
        if token not in portfolio:
             await update.message.reply_text(TEXT["commands"]["sl"]["not_found"].format(token=token))
             return

        # Lưu thông tin dừng lỗ
        portfolio[token]["stop_loss_limit"] = stop_loss_amount
        save_portfolio(user_id, portfolio)

        # Tính toán giá stop loss để hiển thị ngay
        data = portfolio[token]
        qty = data["quantity"]
        net_cost = data["total_spent"] - data["total_received"]
        
        confirmation = TEXT["commands"]["sl"]["success"].format(token=token, amount=stop_loss_amount)
        
        if qty > 0 and net_cost > stop_loss_amount:
            sl_price = (net_cost - stop_loss_amount) / qty
            confirmation += TEXT["commands"]["sl"]["trigger_at"].format(price=sl_price)
        elif qty > 0 and net_cost <= 0:
             confirmation += TEXT["commands"]["sl"]["profit_ignore"]
        elif qty <= 0:
             confirmation += TEXT["commands"]["sl"]["no_hold_ignore"]
             
        await update.message.reply_text(confirmation, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text(TEXT["error"]["value_error"])


# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Commnand Handler đầy đủ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("list", list_portfolio))
    app.add_handler(CommandHandler("sl", set_stop_loss))
    app.add_handler(CommandHandler("reset", reset_portfolio))

    # Command Handler ngắn gọn
    app.add_handler(CommandHandler("b", buy))
    app.add_handler(CommandHandler("s", sell))
    app.add_handler(CommandHandler("ls", list_portfolio))
    app.add_handler(CommandHandler("rs", reset_portfolio))

    print(f"Bot đang chạy với {len(ALLOWED_USER_IDS)} user(s) được cấp quyền...")
    app.run_polling()
