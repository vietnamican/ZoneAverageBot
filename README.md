# Bot Quản Lý Phân bổ vốn Crypto

Bot Telegram giúp bạn quản lý danh mục đầu tư crypto một cách hiệu quả.

## Tính năng

- **Ghi nhận giao dịch mua/bán**: Lưu trữ chi tiết các lệnh mua và bán
- **Tính break-even price**: Tự động tính giá hoà vốn cho từng đồng coin
- **Stop-loss tracking**: Cài đặt mức lỗ tối đa để bảo vệ vốn
- **Phát hiện "free coin"**: Tự động phát hiện khi đã thu hồi đủ vốn (Moonbag)

## Điều kiện tiên quyết

- Python 3.8 trở lên
- Tài khoản Telegram

## Cài đặt

```bash
git clone <repo_url>
cd Telegram
pip install -r requirements.txt
```

## Cấu hình môi trường (.env)

### 4.1. Lấy Telegram Bot Token

1. Chat với [@BotFather](https://t.me/BotFather) trên Telegram
2. Gửi `/newbot` và làm theo hướng dẫn
3. Copy token nhận được
4. Thông tin token này là trường TELEGRAM_TOKEN trong file .env

### 4.2. Lấy User ID

1. Chat với [@userinfobot](https://t.me/userinfobot)
2. Bot sẽ trả về User ID của bạn
3. Thông tin User này là trường ALLOWED_USER_IDS trong file .env

### 4.3. Cấu hình nhiều user

Phân cách các User ID bằng dấu phẩy:
```
ALLOWED_USER_IDS=123456789,987654321
```

### 4.4. Tạo file .env

```bash
cp .env_example .env
# Chỉnh sửa file .env với thông tin của bạn
```

## Khởi chạy

```bash
python bot_crypto.py
```

## Danh sách lệnh

| Lệnh | Lệnh ngắn | Cú pháp | Mô tả |
|------|-----------|---------|-------|
| `/start` | - | `/start` | Xem trợ giúp |
| `/buy` | `/b` | `/buy <TOKEN> <USDT> <GIÁ>` | Ghi nhận mua |
| `/sell` | `/s` | `/sell <TOKEN> <USDT> <GIÁ>` | Ghi nhận bán |
| `/list` | `/ls` | `/list` | Xem báo cáo dòng tiền |
| `/sl` | - | `/sl <TOKEN> <USDT_LỖ_TỐI_ĐA>` | Cài stop-loss |
| `/reset` | `/rs` | `/reset` | Xóa toàn bộ dữ liệu |

### Ví dụ sử dụng

- `/buy BTC 1000 65000` - Mua $1000 BTC giá $65,000
- `/sell BTC 500 70000` - Bán $500 BTC giá $70,000
- `/sell BTC 999999 70000` - Bán tất cả BTC (dùng số lớn)
- `/sl BTC 100` - Chấp nhận lỗ tối đa $100

Một số ví dụ về kịch bản sử dụng chi tiết trình bày trong thư mục `docs`
## License

MIT
