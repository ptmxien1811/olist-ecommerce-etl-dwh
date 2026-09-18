from pathlib import Path
import logging

import pandas as pd



# CẤU HÌNH ĐƯỜNG DẪN



PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"



# LOGGER


logger = logging.getLogger(__name__)



# DANH SÁCH FILE NGUỒN OLIST


DATASET_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}



# ĐỌC MỘT FILE CSV


def read_csv_file(file_name: str) -> pd.DataFrame:

    file_path = RAW_DATA_DIR / file_name


    # 1. Kiểm tra file tồn tại


    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file nguồn: {file_path}"
        )


    # 2. Đọc CSV


    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8",
            low_memory=False
        )

    except Exception as error:
        raise RuntimeError(
            f"Lỗi khi đọc file {file_name}: {error}"
        ) from error


    # 3. Kiểm tra file rỗng


    if df.empty:
        raise ValueError(
            f"File {file_name} không chứa dữ liệu."
        )


    # 4. Ghi log


    logger.info(
        "Đã Extract %-45s | %10s dòng x %2s cột",
        file_name,
        f"{df.shape[0]:,}",
        df.shape[1]
    )

    return df



# EXTRACT TOÀN BỘ DATASET


def extract_all() -> dict[str, pd.DataFrame]:

    extracted_data: dict[str, pd.DataFrame] = {}

    logger.info(
        "Bắt đầu Extract dữ liệu từ: %s",
        RAW_DATA_DIR
    )

    for table_name, file_name in DATASET_FILES.items():

        extracted_data[table_name] = read_csv_file(
            file_name
        )

    logger.info(
        "Hoàn tất Extract %s/%s bảng Olist.",
        len(extracted_data),
        len(DATASET_FILES)
    )

    return extracted_data



# CHẠY TEST RIÊNG FILE extract.py


if __name__ == "__main__":

    # Cấu hình logging khi chạy file trực tiếp
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    raw_data = extract_all()

    print("\n" + "=" * 65)
    print("KẾT QUẢ EXTRACT")
    print("=" * 65)

    for table_name, df in raw_data.items():

        print(
            f"{table_name:<25}"
            f"{df.shape[0]:>12,} dòng   "
            f"{df.shape[1]:>2} cột"
        )

    print("=" * 65)
    print(
        f"Tổng số bảng đã Extract: {len(raw_data)}"
    )