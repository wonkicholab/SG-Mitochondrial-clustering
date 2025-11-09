#!/usr/bin/env python3
"""
track_summary_simple_all_rows.py

TrackMate “simple” XML (Spots → Edges → Tracks) 파일에서
트랙별 정보(spot 개수, merge 개수, 평균/최대 속도)를 읽고,
총 트랙 수, 총 merge 횟수, 전체/merge/비merge 평균 속도를
모든 행에 반복해서 채워 넣은 뒤 CSV로 저장하는 스크립트입니다.

Usage:
    python track_summary_simple_all_rows.py \
      -i path/to/your_simple_model.xml \
      -o path/to/track_summary.csv
"""

import xml.etree.ElementTree as ET
import pandas as pd
import argparse

def parse_args():
    p = argparse.ArgumentParser(
        description="Per-track info + repeated summary columns from simple TrackMate XML"
    )
    p.add_argument("-i","--input",  required=True, help="Input simple XML file")
    p.add_argument("-o","--output", required=True, help="Output CSV file")
    return p.parse_args()

def main(xml_path, out_csv):
    # 1) XML 파싱 및 개별 트랙 정보 수집
    tree = ET.parse(xml_path)
    root = tree.getroot()
    records = []
    for tr in root.findall(".//Track"):
        records.append({
            "track_id":    int(tr.get("TRACK_ID",   -1)),
            "n_spots":     int(tr.get("NUMBER_SPOTS",   0)),
            "n_merges":    int(tr.get("NUMBER_MERGES",   0)),
            "has_merging": int(tr.get("NUMBER_MERGES",   0)) > 0,
            "mean_speed":  float(tr.get("TRACK_MEAN_SPEED", 0.0)),
            "max_speed":   float(tr.get("TRACK_MAX_SPEED",  0.0)),
        })
    df = pd.DataFrame(records)

    # 2) 전체 통계 계산
    total_tracks = len(df)
    total_merges = int(df["n_merges"].sum())
    avg_all      = df["mean_speed"].mean()
    avg_merg     = df.loc[df["has_merging"], "mean_speed"].mean()  if df["has_merging"].any() else 0.0
    avg_non      = df.loc[~df["has_merging"], "mean_speed"].mean() if (~df["has_merging"]).any() else 0.0

    # 3) 모든 행에 summary 컬럼 반복 채우기
    df["total_tracks"]     = total_tracks
    df["total_merges"]     = total_merges
    df["avg_speed_all"]    = avg_all
    df["avg_speed_merging"]= avg_merg
    df["avg_speed_nonmerge"]= avg_non

    # 4) CSV 저장
    df.to_csv(out_csv, index=False)
    print(f"▶ Saved full summary to {out_csv}")

if __name__ == "__main__":
    args = parse_args()
    main(args.input, args.output)
