#!/usr/bin/env python3
"""
track_summary_simple_per_file.py

TrackMate “simple” XML들을 읽어 트랙별 정보(spot 개수, merge 개수, 평균/최대 속도)를 추출하고,
파일(샘플)별 요약치(총 트랙 수, 총 merge 수, 전체/merge/비merge 평균 속도)를
각 행에 반복 기입한 DataFrame을 **XML마다 개별 CSV**로 저장합니다.

- 결과 파일명: <원본이름>_analysis.csv  (기본 접미사 '_analysis')
- CSV에는 source_dir / source_file / source_stem 컬럼을 저장하지 않습니다.
"""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Optional
import pandas as pd

# ===== 기본값(원하면 하드코딩해서 인자 없이 실행) =====
DEFAULT_INPUT       = r"G:\TBK1\sample\xml_files"   # 폴더 또는 단일 XML
DEFAULT_OUTPUT      = r"G:\TBK1\sample\xml_files"   # None이면 각 XML 폴더에 저장
DEFAULT_GLOB        = "*.xml"
DEFAULT_RECURSIVE   = False
DEFAULT_NAME_SUFFIX = "_analysis"                   # sample.xml -> sample_analysis.csv
# =====================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="TrackMate simple-XML → per-file CSV summary (각 XML → 원본이름_analysis.csv)"
    )
    p.add_argument("-i", "--input",  help="XML 파일 또는 XML들이 있는 폴더 경로 (미지정 시 DEFAULT_INPUT 사용)")
    p.add_argument("-o", "--output", help="출력 폴더 (미지정 시 DEFAULT_OUTPUT 또는 각 XML 폴더)")
    p.add_argument("--recursive", action="store_true", help="폴더 입력 시 하위 폴더까지 재귀 탐색")
    p.add_argument("--suffix", default=DEFAULT_NAME_SUFFIX, help="출력 파일명 접미사 (기본: _analysis)")
    return p.parse_args()

def collect_xml_paths(in_path: Path, pattern: str, recursive: bool) -> List[Path]:
    if in_path.is_file():
        return [in_path]
    return list(in_path.rglob(pattern) if recursive else in_path.glob(pattern))

def parse_single_xml(xml_path: Path) -> pd.DataFrame:
    """하나의 simple XML에서 per-track 레코드 + 파일 요약치(반복기입) DataFrame 반환."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
    except Exception as e:
        print(f"[WARN] XML 파싱 실패: {xml_path} -> {e}")
        return pd.DataFrame()

    records = []
    for tr in root.findall(".//Track"):
        try:
            n_merges = int(tr.get("NUMBER_MERGES", 0))
            records.append({
                "track_id":         int(tr.get("TRACK_ID", -1)),
                "n_spots":          int(tr.get("NUMBER_SPOTS", 0)),
                "n_merges":         n_merges,
                "has_merging":      n_merges > 0,
                "mean_speed":       float(tr.get("TRACK_MEAN_SPEED", 0.0)),
                "max_speed":        float(tr.get("TRACK_MAX_SPEED", 0.0)),
            })
        except Exception as e:
            print(f"[WARN] 트랙 파싱 실패({xml_path.name}): {e}")

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 파일(샘플) 단위 요약
    total_tracks = len(df)
    total_merges = int(df["n_merges"].sum())
    avg_all      = df["mean_speed"].mean()
    avg_merg     = df.loc[df["has_merging"], "mean_speed"].mean()  if df["has_merging"].any() else 0.0
    avg_non      = df.loc[~df["has_merging"], "mean_speed"].mean() if (~df["has_merging"]).any() else 0.0

    # 반복 기입 (출처 컬럼은 생성하지 않음)
    df["total_tracks"]       = total_tracks
    df["total_merges"]       = total_merges
    df["avg_speed_all"]      = avg_all
    df["avg_speed_merging"]  = avg_merg
    df["avg_speed_nonmerge"] = avg_non

    return df

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def out_path_for(xml_path: Path, out_dir: Optional[Path], suffix: str) -> Path:
    # out_dir가 None이면 XML이 있는 폴더에 저장
    target_dir = out_dir if out_dir is not None else xml_path.parent
    ensure_dir(target_dir)
    return target_dir / f"{xml_path.stem}{suffix}.csv"

def main():
    args = parse_args()

    # 입력 경로 결정
    in_path = Path(args.input) if args.input else Path(DEFAULT_INPUT)
    if not in_path.exists():
        raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {in_path}")

    # 출력 폴더 결정
    if args.output:
        out_dir = Path(args.output)
    elif DEFAULT_OUTPUT:
        out_dir = Path(DEFAULT_OUTPUT)
    else:
        out_dir = None

    if out_dir is not None:
        if out_dir.suffix.lower() == ".csv":
            print(f"[INFO] --output은 폴더 경로여야 합니다. 파일명이 감지되어 상위 폴더로 저장합니다: {out_dir.parent}")
            out_dir = out_dir.parent
        ensure_dir(out_dir)

    # 재귀 여부
    recursive = args.recursive if (args.input or args.output) else DEFAULT_RECURSIVE

    # XML 수집
    xml_list = collect_xml_paths(in_path, DEFAULT_GLOB, recursive)
    if not xml_list:
        print(f"[INFO] XML을 찾지 못했습니다. 경로: {in_path} / 패턴: {DEFAULT_GLOB} / recursive={recursive}")
        return

    print(f"[INFO] XML 파일 {len(xml_list)}개 처리 시작.")
    done, skipped = 0, 0

    # 개별 저장 루프
    for i, xp in enumerate(sorted(xml_list)):
        print(f"  - ({i+1}/{len(xml_list)}) {xp}")
        df_one = parse_single_xml(xp)
        if df_one.empty:
            print("    -> 건너뜀(레코드 없음 또는 파싱 실패)")
            skipped += 1
            continue

        # 안전장치: 혹시 이전 버전 컬럼이 남아 있다면 제거
        df_one = df_one.drop(columns=["source_dir", "source_file", "source_stem"], errors="ignore")

        out_csv = out_path_for(xp, out_dir, args.suffix)
        try:
            df_one.to_csv(out_csv, index=False)
            print(f"    -> 저장 완료: {out_csv}")
            done += 1
        except Exception as e:
            print(f"    [ERROR] 저장 실패: {out_csv} -> {e}")
            skipped += 1

    print(f"[OK] 완료. 저장 {done}개, 건너뜀 {skipped}개.")

if __name__ == "__main__":
    main()
