import re
import csv
import argparse
from pathlib import Path
from tqdm import tqdm

def split_time_and_offset(timestamp):
    parts = timestamp.strip().split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1]}", parts[2]
    return timestamp.strip(), ""

def parse_stat_block(block, split_path=True, utc_offset='+0000'):
    data = {
        "FilePath": "",
        "FileName": "",
        "Symbolic Target": "",
        "Size": "",
        "Blocks": "",
        "IO Block": "",
        "Type": "",
        "Device": "",
        "Inode": "",
        "Links": "",
        "Access": "",
        "Uid": "",
        "Gid": "",
        "UTC Offset": utc_offset,
        "Access Time": "",
        "Modify Time": "",
        "Change Time": ""
    }

    lines = block.strip().splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("File:"):
            symlink_match = re.match(r"File:\s+[`'\"](.+?)\s*->\s*(.+?)['\"]?$", line)
            normal_match = re.match(r"File:\s+[`'\"]?(.+?)['\"]?$", line)
            if symlink_match:
                fullpath, target = symlink_match.groups()
                data["Symbolic Target"] = target.strip()
            elif normal_match:
                fullpath = normal_match.group(1).strip()
            else:
                continue
            path = Path(fullpath)
            if split_path:
                data["FilePath"] = str(path.parent).replace("\\", "/") if str(path.parent) != '.' else '/'
                data["FileName"] = path.name
            else:
                data["FilePath"] = str(path).replace("\\", "/")

        elif "Size:" in line and "Blocks:" in line and "IO Block:" in line:
            match = re.search(r"Size:\s*(\d+)\s+Blocks:\s*(\d+)\s+IO Block:\s*(\d+)\s+(.+)", line)
            if match:
                data["Size"] = match.group(1)
                data["Blocks"] = match.group(2)
                data["IO Block"] = match.group(3)
                data["Type"] = match.group(4).strip()

        elif "Device:" in line and "Inode:" in line and "Links:" in line:
            parts = re.findall(r"([^\s]+):\s*([^\s]+)", line)
            for key, val in parts:
                if key == "Device":
                    data["Device"] = val
                elif key == "Inode":
                    data["Inode"] = val
                elif key == "Links":
                    data["Links"] = val

        elif "Access:" in line and "Uid:" in line and "Gid:" in line:
            match = re.search(
                r"Access:\s+\(([^)]+)\)\s+Uid:\s+\(\s*(\d+)\s*/\s*([^)]+)\)\s+Gid:\s+\(\s*(\d+)\s*/\s*([^)]+)\)",
                line
            )
            if match:
                data["Access"] = match.group(1).strip()
                data["Uid"] = f"{match.group(2)}/{match.group(3).strip()}"
                data["Gid"] = f"{match.group(4)}/{match.group(5).strip()}"

        elif line.startswith("Access:") and re.search(r"\d{4}-\d{2}-\d{2}", line):
            date_time, offset = split_time_and_offset(line[len("Access:"):].strip())
            data["Access Time"] = date_time
            if offset:
                data["UTC Offset"] = offset

        elif line.startswith("Modify:"):
            date_time, _ = split_time_and_offset(line[len("Modify:"):].strip())
            data["Modify Time"] = date_time

        elif line.startswith("Change:"):
            date_time, _ = split_time_and_offset(line[len("Change:"):].strip())
            data["Change Time"] = date_time

    return data

def main():
    parser = argparse.ArgumentParser(description="stat.txt 파일을 CSV로 변환")
    parser.add_argument("input", help="입력 파일 (stat.txt)")
    parser.add_argument("-o", "--output", default="stat_output.csv", help="출력 파일명")
    parser.add_argument("-d", "--directory", action="store_true", help="FilePath / FileName 분리 여부")
    parser.add_argument("-U", "--utc", default="+0000", help="UTC 오프셋 예: +0900")
    parser.add_argument("-p", "--progress", action="store_true", help="진행률 표시")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        print(f"[오류] 파일 읽기 실패: {e}")
        return

    blocks = re.split(r'\n(?=\s*File:)', content.strip())
    parse_iter = tqdm(blocks, desc="Parsing...") if args.progress else blocks
    results = [parse_stat_block(block, split_path=args.directory, utc_offset=args.utc)
               for block in parse_iter if block.strip()]

    headers = [
        "FilePath", "FileName", "Symbolic Target", "Size", "Blocks", "IO Block", "Type",
        "Device", "Inode", "Links", "Access", "Uid", "Gid", "UTC Offset",
        "Access Time", "Modify Time", "Change Time"
    ]

    try:
        with open(args.output, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)
        print(f"[완료] CSV 저장됨 → {args.output}")
    except Exception as e:
        print(f"[오류] CSV 저장 실패: {e}")

if __name__ == "__main__":
    main()
