from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


# =========================================================
# LOGGER
# =========================================================
#
# Logger dùng để hiển thị thông tin trong quá trình Load.
#
# Ví dụ:
#   đang lưu bảng customers
#   lưu thành công 99,441 dòng
#
# Sau này khi chạy bằng Airflow, các logger này cũng sẽ
# xuất hiện trong log của từng task.
#

logger = logging.getLogger(__name__)


# =========================================================
# XÁC ĐỊNH ĐƯỜNG DẪN PROJECT
# =========================================================
#
# File hiện tại nằm ở:
#
#   project/
#       etl/
#           load.py
#
# Path(__file__)              -> etl/load.py
# .resolve()                  -> đường dẫn tuyệt đối
# .parents[0]                 -> etl/
# .parents[1]                 -> thư mục gốc project
#
# Ví dụ:
#
# D:/doan/olist-ecommerce-etl-dwh
#

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# =========================================================
# KHAI BÁO THƯ MỤC STAGING
# =========================================================
#
# Sau khi Transform + Validate Clean PASS,
# dữ liệu sẽ được lưu vào:
#
#   data/staging/
#
# Riêng bảng được tạo ra từ dữ liệu khác như
# geolocation_lookup sẽ được lưu vào:
#
#   data/staging/derived/
#

STAGING_DIR = (
    PROJECT_ROOT
    / "data"
    / "staging"
)

DERIVED_DIR = (
    STAGING_DIR
    / "derived"
)


# =========================================================
# DANH SÁCH 9 BẢNG DỮ LIỆU NGUỒN
# =========================================================
#
# Đây là 9 bảng xuất phát từ 9 file CSV Olist.
#
# Sau Transform, tên các DataFrame tương ứng nằm
# trong dictionary clean_data.
#

SOURCE_TABLES = [
    "customers",
    "geolocation",
    "order_items",
    "payments",
    "reviews",
    "orders",
    "products",
    "sellers",
    "category_translation",
]


# =========================================================
# DANH SÁCH BẢNG DERIVED
# =========================================================
#
# geolocation_lookup KHÔNG phải bảng CSV nguồn.
#
# Nó được tạo trong transform.py từ bảng geolocation:
#
#   geolocation
#       ↓
# group theo ZIP
#       ↓
# 1 dòng / ZIP
#       ↓
# geolocation_lookup
#
# Vì vậy ta lưu riêng trong staging/derived/.
#

DERIVED_TABLES = [
    "geolocation_lookup",
]


# =========================================================
# HÀM TẠO CÁC THƯ MỤC STAGING
# =========================================================
#
# Nếu thư mục chưa tồn tại thì Python sẽ tự tạo:
#
#   data/staging/
#   data/staging/derived/
#
# parents=True:
#   cho phép tạo cả thư mục cha nếu cần.
#
# exist_ok=True:
#   nếu thư mục đã tồn tại thì không báo lỗi.
#

def create_staging_directories() -> None:

    STAGING_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    DERIVED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    logger.info(
        "Đã kiểm tra/tạo thư mục Staging."
    )


# =========================================================
# HÀM LƯU MỘT DATAFRAME THÀNH PARQUET
# =========================================================
#
# Hàm này nhận:
#
#   df          -> DataFrame cần lưu
#   output_path -> đường dẫn file cần tạo
#
# Ví dụ:
#
# customers DataFrame
#       ↓
# data/staging/customers.parquet
#
# index=False:
#   không ghi index 0,1,2,3... của Pandas vào file.
#

def save_dataframe_to_parquet(
    df: pd.DataFrame,
    output_path: Path
) -> None:

    df.to_parquet(
        output_path,
        index=False,
        engine="pyarrow"
    )


# =========================================================
# HÀM KIỂM TRA CLEAN_DATA CÓ ĐỦ BẢNG KHÔNG
# =========================================================
#
# Trước khi ghi xuống Staging, ta kiểm tra xem clean_data
# có đủ 9 bảng nguồn hay không.
#
# Ví dụ nếu transform.py vì lý do nào đó không trả về
# bảng customers thì Load phải dừng chứ không được
# tạo một Staging bị thiếu bảng.
#

def validate_staging_input(
    clean_data: dict[str, pd.DataFrame]
) -> None:

    missing_tables = []

    for table_name in SOURCE_TABLES:

        if table_name not in clean_data:

            missing_tables.append(
                table_name
            )

    if missing_tables:

        raise ValueError(
            "Không thể Load Staging. "
            "clean_data đang thiếu bảng: "
            + ", ".join(missing_tables)
        )

    logger.info(
        "STAGING INPUT CHECK - "
        "clean_data có đủ 9 bảng nguồn."
    )


# =========================================================
# HÀM LOAD 9 BẢNG CHÍNH VÀO STAGING
# =========================================================
#
# Hàm này sẽ duyệt lần lượt:
#
# customers
# geolocation
# order_items
# ...
#
# Mỗi DataFrame được lưu thành:
#
# data/staging/<table_name>.parquet
#

def load_source_tables(
    clean_data: dict[str, pd.DataFrame]
) -> None:

    logger.info(
        "Bắt đầu lưu 9 bảng nguồn vào Staging."
    )

    # -----------------------------------------------------
    # Duyệt từng bảng nguồn
    # -----------------------------------------------------

    for table_name in SOURCE_TABLES:

        # -------------------------------------------------
        # Lấy DataFrame tương ứng từ clean_data
        # -------------------------------------------------

        df = clean_data[
            table_name
        ]

        # -------------------------------------------------
        # Xây dựng tên file Parquet
        #
        # Ví dụ:
        #
        # customers
        #     ↓
        # data/staging/customers.parquet
        # -------------------------------------------------

        output_path = (
            STAGING_DIR
            / f"{table_name}.parquet"
        )

        # -------------------------------------------------
        # Ghi DataFrame xuống file Parquet
        # -------------------------------------------------

        save_dataframe_to_parquet(
            df=df,
            output_path=output_path
        )

        # -------------------------------------------------
        # Ghi log kết quả
        # -------------------------------------------------

        logger.info(
            "STAGING - %-25s %12s dòng -> %s",
            table_name,
            f"{len(df):,}",
            output_path
        )


# =========================================================
# HÀM LOAD BẢNG DERIVED
# =========================================================
#
# Hiện tại project chỉ có:
#
#   geolocation_lookup
#
# Đây là bảng Transform sinh thêm,
# không phải CSV nguồn.
#
# Nó sẽ được lưu:
#
# data/staging/derived/geolocation_lookup.parquet
#

def load_derived_tables(
    clean_data: dict[str, pd.DataFrame]
) -> None:

    logger.info(
        "Bắt đầu lưu các bảng Derived."
    )

    # -----------------------------------------------------
    # Duyệt danh sách các bảng Derived
    # -----------------------------------------------------

    for table_name in DERIVED_TABLES:

        # -------------------------------------------------
        # Nếu bảng không tồn tại thì báo lỗi.
        #
        # Với project hiện tại,
        # geolocation_lookup phải được transform.py tạo ra.
        # -------------------------------------------------

        if table_name not in clean_data:

            raise ValueError(
                f"Không tìm thấy bảng Derived "
                f"'{table_name}' trong clean_data."
            )

        # -------------------------------------------------
        # Lấy DataFrame Derived
        # -------------------------------------------------

        df = clean_data[
            table_name
        ]

        # -------------------------------------------------
        # Xây dựng đường dẫn output
        # -------------------------------------------------

        output_path = (
            DERIVED_DIR
            / f"{table_name}.parquet"
        )

        # -------------------------------------------------
        # Lưu thành Parquet
        # -------------------------------------------------

        save_dataframe_to_parquet(
            df=df,
            output_path=output_path
        )

        # -------------------------------------------------
        # Ghi log kết quả
        # -------------------------------------------------

        logger.info(
            "STAGING DERIVED - %-17s "
            "%12s dòng -> %s",
            table_name,
            f"{len(df):,}",
            output_path
        )


# =========================================================
# HÀM KIỂM TRA FILE SAU KHI GHI
# =========================================================
#
# Chúng ta không chỉ gọi to_parquet() rồi coi như xong.
#
# Sau khi ghi, kiểm tra:
#
#   - file có thật sự tồn tại không;
#   - có đọc lại được không;
#   - số dòng có bằng DataFrame trong clean_data không.
#
# Đây là một kiểm tra đơn giản giúp tránh trường hợp
# Load báo chạy xong nhưng file lưu bị thiếu/sai.
#

def verify_staging_files(
    clean_data: dict[str, pd.DataFrame]
) -> None:

    logger.info(
        "Bắt đầu kiểm tra các file Staging."
    )

    # -----------------------------------------------------
    # Kiểm tra 9 bảng chính
    # -----------------------------------------------------

    for table_name in SOURCE_TABLES:

        file_path = (
            STAGING_DIR
            / f"{table_name}.parquet"
        )

        # -------------------------------------------------
        # Kiểm tra file có tồn tại hay không
        # -------------------------------------------------

        if not file_path.exists():

            raise FileNotFoundError(
                f"Không tìm thấy file Staging: "
                f"{file_path}"
            )

        # -------------------------------------------------
        # Đọc lại file Parquet
        # -------------------------------------------------

        staging_df = pd.read_parquet(
            file_path
        )

        # -------------------------------------------------
        # So sánh số dòng:
        #
        # clean_data
        #     VS
        # file vừa ghi xuống ổ cứng
        # -------------------------------------------------

        expected_rows = len(
            clean_data[table_name]
        )

        actual_rows = len(
            staging_df
        )

        if expected_rows != actual_rows:

            raise ValueError(
                f"{table_name}: số dòng Staging "
                f"không khớp. "
                f"Kỳ vọng={expected_rows:,}, "
                f"thực tế={actual_rows:,}."
            )

        logger.info(
            "VERIFY - %-25s PASS (%s dòng)",
            table_name,
            f"{actual_rows:,}"
        )

    # -----------------------------------------------------
    # Kiểm tra các bảng Derived
    # -----------------------------------------------------

    for table_name in DERIVED_TABLES:

        file_path = (
            DERIVED_DIR
            / f"{table_name}.parquet"
        )

        # -------------------------------------------------
        # Kiểm tra file Derived có tồn tại không
        # -------------------------------------------------

        if not file_path.exists():

            raise FileNotFoundError(
                f"Không tìm thấy file Derived: "
                f"{file_path}"
            )

        # Đọc lại file


        staging_df = pd.read_parquet(
            file_path
        )

        # So sánh số dòng


        expected_rows = len(
            clean_data[table_name]
        )

        actual_rows = len(
            staging_df
        )

        if expected_rows != actual_rows:

            raise ValueError(
                f"{table_name}: số dòng Staging "
                f"không khớp. "
                f"Kỳ vọng={expected_rows:,}, "
                f"thực tế={actual_rows:,}."
            )

        logger.info(
            "VERIFY DERIVED - %-17s PASS (%s dòng)",
            table_name,
            f"{actual_rows:,}"
        )



# HÀM LOAD STAGING TỔNG


def load_staging(
    clean_data: dict[str, pd.DataFrame]
) -> bool:

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU LOAD STAGING")
    logger.info("=" * 70)


    # Kiểm tra clean_data


    validate_staging_input(
        clean_data
    )

    #  Tạo các thư mục cần thiết
    create_staging_directories()


    # Lưu 9 bảng nguồn
    load_source_tables(
        clean_data
    )


    #  Lưu bảng Derived

    load_derived_tables(
        clean_data
    )


    #  Verify dữ liệu vừa lưu

    verify_staging_files(
        clean_data
    )

    logger.info("=" * 70)
    logger.info("LOAD STAGING: SUCCESS")
    logger.info(
        "Dữ liệu Staging đã sẵn sàng "
        "cho bước Load BigQuery."
    )
    logger.info("=" * 70)

    return True


if __name__ == "__main__":

    from extract import extract_all

    from transform import transform_all

    from validate import (
        validate_all_raw,
        validate_all_clean,
    )

    # Cấu hình logger để hiển thị thông tin trên Terminal


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
    validate_all_raw(
        raw_data
    )

    clean_data = transform_all(
        raw_data
    )
    validate_all_clean(
        raw_data,
        clean_data
    )

    load_staging(
        clean_data
    )