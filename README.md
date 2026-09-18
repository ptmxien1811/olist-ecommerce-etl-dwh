
# HƯỚNG DẪN CHẠY HỆ THỐNG OLIST E-COMMERCE ETL & DWH

## 1. Mục đích
Tài liệu này hướng dẫn cách khởi động và chạy hệ thống ETL Olist đã được triển khai bằng Docker, Apache Airflow, Google BigQuery và Power BI.

## 2. Thư mục dự án
Mở terminal tại thư mục dự án:

```powershell
cd D:\doan\olist-ecommerce-etl-dwh
```

## 3. Khởi động Docker Desktop
Trước khi chạy Airflow, cần mở **Docker Desktop** và chờ Docker khởi động hoàn tất.

Có thể kiểm tra Docker bằng lệnh:

```powershell
docker version
```

Nếu xuất hiện lỗi dạng:

```text
failed to connect to the docker API ... dockerDesktopLinuxEngine
```

thì Docker Desktop chưa chạy hoặc Docker Engine chưa sẵn sàng. Hãy mở Docker Desktop, chờ trạng thái Running rồi chạy lại lệnh.

## 4. Khởi động Apache Airflow
Tại thư mục gốc của dự án, chạy:

```powershell
docker compose up -d
```

Sau đó kiểm tra container:

```powershell
docker compose ps
```

Khi hệ thống hoạt động bình thường sẽ thấy container tương tự:

```text
NAME           SERVICE   STATUS
olist-airflow  airflow   Up
```

và cổng Airflow được ánh xạ qua:

```text
0.0.0.0:8080->8080/tcp
```

## 5. Mở giao diện Apache Airflow
Mở trình duyệt và truy cập:

```text
http://localhost:8080
```

Đăng nhập bằng tài khoản Airflow đã cấu hình cho project.
admin : xEQuYa3C5tmcETar

## 6. Chạy pipeline ETL
Trong giao diện Airflow:

1. Tìm DAG **olist_etl_pipeline**.
2. Bật DAG nếu đang ở trạng thái Pause.
3. Chọn **Trigger DAG** để chạy thủ công.
4. Theo dõi trạng thái các task.

DAG hiện gồm ba task chính:

```text
check_source_files
        ↓
run_etl_pipeline
        ↓
verify_dwh
```

Trong đó `run_etl_pipeline` thực hiện toàn bộ quy trình:

```text
Extract
→ Validate Raw
→ Transform
→ Validate Clean
→ Load Local Staging
→ Load BigQuery Staging
→ Load Dimension
→ Load Fact
→ DWH Reconciliation
```

Khi cả ba task chuyển sang trạng thái **Success** thì pipeline đã chạy thành công.

## 7. Kiểm tra log khi cần
Có thể xem log container bằng lệnh:

```powershell
docker compose logs -f airflow
```

Nhấn `Ctrl + C` để thoát chế độ xem log.

Trong Airflow UI cũng có thể bấm vào từng task và chọn **Logs** để kiểm tra chi tiết.

## 8. Kiểm tra dữ liệu trên BigQuery
Sau khi pipeline hoàn thành, kiểm tra các dataset chính trên Google BigQuery:

```text
olist_staging
olist_dwh
olist_error
```

Các bảng Data Warehouse chính gồm:

```text
dim_customers
dim_products
dim_sellers
dim_date
fact_orders
fact_order_items
fact_payments
fact_reviews
```

Kết quả Reconciliation cần hiển thị trạng thái **PASS** đối với các tiêu chí đã kiểm tra.

## 9. Mở Power BI
Mở file Power BI đã lưu của dự án, ví dụ:

```text
D:\doan\olist-ecommerce-etl-dwh\reports\olist_ecommerce_dashboard.pbix
```

Sau đó chọn **Refresh** nếu cần cập nhật dữ liệu từ BigQuery.

Lưu ý: chạy lại DAG không làm mất file Power BI. File `.pbix` vẫn được giữ nguyên; chỉ cần Refresh khi muốn lấy dữ liệu mới từ Data Warehouse.

## 10. Dừng hệ thống
Khi không sử dụng Airflow, có thể dừng container bằng:

```powershell
docker compose down
```

Nếu chỉ muốn tạm dừng:

```powershell
docker compose stop
```

Khởi động lại sau khi đã stop:

```powershell
docker compose start
```

## 11. Quy trình demo nhanh
Khi cần demo với giảng viên, thực hiện theo thứ tự:

```text
1. Mở Docker Desktop
2. Mở terminal tại D:\doan\olist-ecommerce-etl-dwh
3. Chạy: docker compose up -d
4. Chạy: docker compose ps
5. Mở http://localhost:8080
6. Trigger DAG olist_etl_pipeline
7. Theo dõi 3 task chuyển sang Success
8. Kiểm tra dữ liệu trên BigQuery nếu cần
9. Mở Power BI và Refresh để trình bày dashboard
```

## 12. Lưu ý
- Máy tính và Docker Desktop phải đang chạy thì Airflow local mới hoạt động.
- Không chạy trực tiếp file DAG bằng Python/PyCharm local để thay cho Airflow.
- Nếu `docker compose ps` báo lỗi kết nối Docker API, hãy kiểm tra Docker Desktop trước.
- DAG được cấu hình chạy định kỳ; khi demo có thể dùng **Trigger DAG** để chạy thủ công ngay lập tức.
