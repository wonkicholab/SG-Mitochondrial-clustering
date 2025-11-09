#!/usr/bin/env python3
"""
batch_track_summary.py

지정된 폴더 내의 모든 simple TrackMate XML 파일을 순회하여
  1) 해당 폴더에 파일별 *_summary.csv 생성
  2) 생성된 *_summary.csv 파일들을 읽어
     aggregated_summary.xlsx 생성

Usage:
    python batch_track_summary.py \
      -d path/to/folder
"""

import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
import argparse

def process_xml(xml_path, out_csv):
    # XML 파싱 및 per-track DataFrame 생성
    tree = ET.parse(xml_path)
    root = tree.getroot()
    records = []
    for tr in root.findall(".//Track"):
        n_merges = int(tr.get("NUMBER_MERGES", 0))
        records.append({
            "track_id":    int(tr.get("TRACK_ID",   -1)),
            "n_spots":     int(tr.get("NUMBER_SPOTS", 0)),
            "n_merges":    n_merges,
            "has_merging": n_merges > 0,
            "mean_speed":  float(tr.get("TRACK_MEAN_SPEED", 0.0)),
            "max_speed":   float(tr.get("TRACK_MAX_SPEED",  0.0)),
        })
    df = pd.DataFrame(records)

    # 전체 통계 계산
    total_tracks = len(df)
    total_merges = int(df["n_merges"].sum())
    avg_all      = df["mean_speed"].mean() if total_tracks > 0 else 0.0
    avg_merg     = df.loc[df["has_merging"], "mean_speed"].mean() if df["has_merging"].any() else 0.0
    avg_non      = df.loc[~df["has_merging"], "mean_speed"].mean() if (~df["has_merging"]).any() else 0.0

    # summary 컬럼을 모든 행에 추가
    df["total_tracks"]       = total_tracks
    df["total_merges"]       = total_merges
    df["avg_speed_all"]      = avg_all
    df["avg_speed_merging"]  = avg_merg
    df["avg_speed_nonmerge"] = avg_non

    # 개별 CSV로 저장
    df.to_csv(out_csv, index=False)
    return out_csv

def aggregate_summaries(folder, excel_path):
    # *_summary.csv 파일 모아서 핵심 지표만 추출하여 엑셀로 통합
    pattern = os.path.join(folder, '*_summary.csv')
    files = glob.glob(pattern)
    if not files:
        print("No summary CSV files found in", folder)
        return

    records = []
    for csv_path in files:
        df = pd.read_csv(csv_path)
        base = os.path.splitext(os.path.basename(csv_path))[0].replace('_summary','')
        vals = df.iloc[0][[
            'total_tracks',
            'total_merges',
            'avg_speed_all',
            'avg_speed_merging',
            'avg_speed_nonmerge'
        ]].to_dict()
        vals['filename'] = base
        records.append(vals)

    df_agg = pd.DataFrame(records, columns=[
        'filename',
        'total_tracks',
        'total_merges',
        'avg_speed_all',
        'avg_speed_merging',
        'avg_speed_nonmerge'
    ])
    df_agg.to_excel(excel_path, index=False)
    print(f"▶ Aggregated summary saved to: {excel_path}")

def main(folder):
    # 입력 폴더 검증
    if not os.path.isdir(folder):
        print("Error: 지정된 경로가 폴더가 아닙니다:", folder)
        return

    # XML 파일 목록 수집
    xml_files = glob.glob(os.path.join(folder, '*.xml'))
    if not xml_files:
        print("No XML files found in", folder)
        return

    # 각 XML 파일 처리 및 *_summary.csv 생성
    for xml_path in xml_files:
        base = os.path.splitext(os.path.basename(xml_path))[0]
        out_csv = os.path.join(folder, base + '_summary.csv')
        try:
            process_xml(xml_path, out_csv)
            print(f"✔ {base}.xml -> {base}_summary.csv 생성 완료")
        except Exception as e:
            print(f"✖ Error processing {xml_path}: {e}")

    # 모든 summary 파일을 모아 aggregated_summary.xlsx 생성
    excel_path = os.path.join(folder, 'aggregated_summary.xlsx')
    aggregate_summaries(folder, excel_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="단일 폴더 내 XML 파일을 분석하고 요약 엑셀 생성"
    )
    parser.add_argument(
        "-d", "--folder", required=True,
        help="분석할 XML 파일들이 들어 있는 폴더"
    )
    args = parser.parse_args()
    main(args.folder)
