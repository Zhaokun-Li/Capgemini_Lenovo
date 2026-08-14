from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = (
    BASE_DIR
    / "Data"
    / "Raw"
    / "data_03.csv"
)

UTF8_CSV_FILE = (
    BASE_DIR
    / "Data"
    / "Processed"
    / "data_03_utf8.csv"
)


def main() -> None:
    print(f"准备读取：{CSV_FILE}")
    print(f"文件是否存在：{CSV_FILE.exists()}")

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"找不到 CSV 文件：{CSV_FILE}"
        )

    data = pd.read_csv(
        CSV_FILE,
        encoding="gb18030",
    )

    print("\n读取成功，前 5 行：")
    print(data.head())

    print("\n数据大小：")
    print(f"{data.shape[0]} 行，{data.shape[1]} 列")

    print("\n字段名称：")
    print(data.columns.tolist())

    UTF8_CSV_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data.to_csv(
        UTF8_CSV_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nUTF-8 CSV 已生成：{UTF8_CSV_FILE}")


if __name__ == "__main__":
    main()