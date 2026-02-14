# Kịch bản sử dụng

## Kịch bản 1: Mua và theo dõi danh mục

### Mua BTC
```
/buy BTC 1000 65000
```

Bot sẽ trả về:
- Số BTC mua được: 0.01538461 BTC
- Tổng chi: $1,000
- Holding: 0.01538461 BTC
- Break-even: $65,000

### Mua ETH
```
/buy ETH 500 3500
```

### Xem báo cáo
```
/list
```

Bot sẽ hiển thị danh sách tất cả các đồng coin đang nắm giữ cùng với:
- Số lượng đang hold
- Tổng chi, tổng thu
- Điểm hoà vốn

---

## Kịch bản 2: Bán một phần và tính break-even

### Bước 1: Mua BTC lần đầu
```
/buy BTC 1000 50000
```
- Mua: 0.02 BTC
- Chi: $1,000
- Break-even: $50,000

### Bước 2: Bán một phần với giá cao hơn
```
/sell BTC 500 60000
```
- Bán: 0.00833333 BTC (tương đương $500)
- Thu về: $500
- Còn lại: 0.01166667 BTC

### Bước 3: Kiểm tra break-even mới
```
/list
```

Bot sẽ hiển thị break-even mới được điều chỉnh:
- Tổng chi: $1,000
- Tổng thu: $500
- Net cost: $500
- Số coin còn: 0.01166667 BTC
- Break-even mới: $42,857.14

---

## Kịch bản 3: Free Coin (Moonbag)

### Bước 1: Mua BTC
```
/buy BTC 1000 50000
```

### Bước 2: Bán một phần với giá cao gấp đôi
```
/sell BTC 1000 100000
```
- Bán 0.01 BTC (tương đương $1,000)
- Thu về: $1,000

### Bước 3: Kiểm tra trạng thái
```
/list
```

Bot sẽ hiển thị:
- Tổng chi: $1,000
- Tổng thu: $1,000
- Net cost: $0
- Trạng thái: **"Đã lãi gốc - Free Coin"**

Toàn bộ số BTC còn lại trong danh mục là "miễn phí" vì bạn đã thu hồi đủ vốn ban đầu.

---

## Kịch bản 4: Sử dụng Stop-loss

### Bước 1: Mua coin
```
/buy BTC 1000 50000
```

### Bước 2: Cài đặt stop-loss
```
/sl BTC 100
```
Bot sẽ thông báo:
- Đã cài đặt dừng lỗ cho BTC là $100
- Dừng lỗ sẽ kích hoạt tại giá: $40,000

### Bước 3: Kiểm tra trong danh sách
```
/list
```

Bot sẽ hiển thị thêm thông tin stop-loss trong báo cáo:
- Break-even: $50,000
- Stop-loss: $40,000

### Cách tính Stop-loss

Nếu:
- Tổng chi: $1,000
- Tổng thu: $0
- Net cost: $1,000
- Số coin: 0.02 BTC
- Stop-loss limit: $100

Thì giá stop-loss = ($1,000 - $100) / 0.02 = $45,000

---

## Mẹo sử dụng

1. **Bán tất cả**: Sử dụng số USDT lớn hơn giá trị danh mục để bán hết
   ```
   /sell BTC 999999 70000
   ```

2. **Kiểm tra nhanh**: Dùng lệnh ngắn để tiết kiệm thời gian
   - `/b` thay cho `/buy`
   - `/s` thay cho `/sell`
   - `/ls` thay cho `/list`
   - `/rs` thay cho `/reset`

3. **Reset dữ liệu**: Khi muốn bắt đầu lại từ đầu
   ```
   /reset
   ```
