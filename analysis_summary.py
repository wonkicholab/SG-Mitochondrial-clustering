#!/usr/bin/env python3
"""
aggregate_selected_columns_from_csv.py

- INPUT_DIR 안의 CSV 파일들을 모두 순회(패턴 매칭)
- 각 CSV에서 SELECT_COLS에 명시한 컬럼만 추출
  (파일마다 요약 컬럼이 모든 행에 반복되어 있다면 drop_duplicates로 1행만 유지)
- 파일명(확장자 제외)을 'filename' 컬럼으로 붙여 식별
- OUTPUT_DIR에 하나의 통합 CSV (및 선택적으로 XLSX) 저장

사용: 기본값만 수정하고 바로 실행 (인자 불필요)
"""

from pathlib import Path
import pandas as pd

# ======= 여기만 고치면 됩니다 =======
INPUT_DIR   = Path(r"G:\TBK1\sample\xml_files")  # CSV들이 있는 폴더
OUTPUT_DIR  = Path(r"G:\TBK1\sample\xml_files")  # 집계 결과를 저장할 폴더
FILE_PATTERN = "*_analysis.csv"                  # 예: "*_analysis.csv" 또는 "*.csv"

# CSV에서 뽑을 컬럼(없으면 NaN으로 채워집니다)
SELECT_COLS = [
    "total_tracks",
    "total_merges",
    "avg_speed_all",
    "avg_speed_merging",
    "avg_speed_nonmerge",
]

# 출력 파일명
OUT_CSV_NAME  = "tracking_summary.csv"
MAKE_XLSX     = False
OUT_XLSX_NAME = "tracking_summary.xlsx"
# ====================================

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def summarize_csv_one(csv_path: Path) -> dict:
    """하나의 CSV에서 SELECT_COLS만 추출해 dict로 반환. (중복행 제거 후 첫 행 사용)"""
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[WARN] 읽기 실패: {csv_path} -> {e}")
        return {}

    # 누락 컬럼은 NaN으로 채움
    for col in SELECT_COLS:
        if col not in df.columns:
            df[col] = pd.NA

    # 지정 컬럼만 남기고 중복 제거
    sub = df[SELECT_COLS].drop_duplicates()

    if sub.empty:
        # 완전히 비어 있으면 NaN 채운 1행 만들기
        row = {col: pd.NA for col in SELECT_COLS}
    else:
        row = sub.iloc[0].to_dict()

    # 파일 식별용
    row["filename"] = csv_path.stem
    return row

def main():
    if not INPUT_DIR.is_dir():
        raise NotADirectoryError(f"INPUT_DIR이 폴더가 아닙니다: {INPUT_DIR}")

    ensure_dir(OUTPUT_DIR)

    files = sorted(INPUT_DIR.glob(FILE_PATTERN))
    if not files:
        print(f"[INFO] 대상 CSV가 없습니다. 경로={INPUT_DIR} / 패턴={FILE_PATTERN}")
        return

    print(f"[INFO] CSV {len(files)}개 처리 시작.")
    records = []
    for i, f in enumerate(files, 1):
        print(f"  - ({i}/{len(files)}) {f.name}")
        rec = summarize_csv_one(f)
        if rec:
            records.append(rec)

    if not records:
        print("[INFO] 수집된 요약이 없습니다. 종료.")
        return

    # filename 먼저, 그 다음 SELECT_COLS 순서로 정렬
    cols_out = ["filename"] + SELECT_COLS
    df_all = pd.DataFrame(records)
    # 누락된 컬럼이 있더라도 항상 동일한 컬럼 순서로 출력
    for c in cols_out:
        if c not in df_all.columns:
            df_all[c] = pd.NA
    df_all = df_all[cols_out].sort_values("filename").reset_index(drop=True)

    out_csv = OUTPUT_DIR / OUT_CSV_NAME
    df_all.to_csv(out_csv, index=False)
    print(f"[OK] CSV 저장: {out_csv}")

    if MAKE_XLSX:
        out_xlsx = OUTPUT_DIR / OUT_XLSX_NAME
        df_all.to_excel(out_xlsx, index=False)
        print(f"[OK] XLSX 저장: {out_xlsx}")

if __name__ == "__main__":
    main()
