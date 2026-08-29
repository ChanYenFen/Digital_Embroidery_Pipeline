#!/bin/bash
# 把瀏覽器下載資料夾裡的 *_processed.svg 搬到 data/svg/processed/，
# 每個檔案都先驗證過才放行進入 pipeline。
#
# 由專案根目錄的 move-processed-svg.command 啟動。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
DEST_DIR="$REPO_ROOT/data/svg/processed"
DOWNLOADS="$HOME/Downloads"

if [ ! -d "$DOWNLOADS" ]; then
  echo "Downloads folder not found: $DOWNLOADS"
  exit 1
fi
mkdir -p "$DEST_DIR"

echo "From: $DOWNLOADS"
echo "To  : $DEST_DIR"
echo

shopt -s nullglob
candidates=("$DOWNLOADS"/*_processed.svg)
shopt -u nullglob

if [ ${#candidates[@]} -eq 0 ]; then
  echo "Nothing to move: no *_processed.svg in Downloads."
  exit 0
fi

# --- 驗證：這真的是編輯器匯出的檔案嗎？---
validate_svg() {
  python3 - "$1" <<'PYEOF'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
try:
    tree = ET.parse(path)
except ET.ParseError as e:
    print(f"not valid XML ({e})")
    sys.exit(1)

root = tree.getroot()
tag = root.tag.split('}')[-1]
if tag != 'svg':
    print(f"root element is <{tag}>, not <svg>")
    sys.exit(1)

paths = [el for el in root.iter() if el.tag.split('}')[-1] == 'path']
if not paths:
    print("contains no <path> elements")
    sys.exit(1)

# 圖層參數存在每個 path 的 id 裡：以底線分隔的 7 個欄位。
named = [p for p in paths if len(p.get('id', '').split('_')) >= 7]
if not named:
    print("no <path> carries a 7-field layer name in its id")
    sys.exit(1)

if len(named) < len(paths):
    print(f"note: {len(paths) - len(named)} of {len(paths)} paths have no layer name")

sys.exit(0)
PYEOF
}

moved=0; skipped=0; rejected=0

for file in "${candidates[@]}"; do
  name="$(basename "$file")"
  base="${name%.svg}"
  echo "- $name"

  # 還在下載中？Chrome/Edge/Firefox/Safari 會在旁邊留一個未完成的暫存檔。
  partial=0
  for ext in crdownload part tmp download; do
    if compgen -G "$DOWNLOADS/${base}"*".${ext}" > /dev/null; then
      partial=1
      break
    fi
  done
  if [ "$partial" -eq 1 ]; then
    echo "  skipped: download still in progress"
    skipped=$((skipped+1)); continue
  fi

  # 被其他程式鎖住（還在寫入）？
  if command -v lsof >/dev/null 2>&1 && lsof -- "$file" >/dev/null 2>&1; then
    echo "  skipped: file is locked by another process"
    skipped=$((skipped+1)); continue
  fi

  problem="$(validate_svg "$file" 2>&1)"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "  REJECTED: $problem"
    echo "  left in Downloads, nothing was moved"
    rejected=$((rejected+1)); continue
  fi
  if [ -n "$problem" ]; then
    echo "  $problem"
  fi

  target="$DEST_DIR/$name"

  if [ -e "$target" ]; then
    src_hash="$(shasum -a 256 "$file" | awk '{print $1}')"
    dst_hash="$(shasum -a 256 "$target" | awk '{print $1}')"

    if [ "$src_hash" = "$dst_hash" ]; then
      rm -f "$file"
      echo "  already in processed/ with identical content; removed the duplicate download"
      skipped=$((skipped+1)); continue
    fi

    # 同名但內容不同：兩個都留著，絕不覆蓋。
    stamp="$(date +%Y%m%d-%H%M%S)"
    target="$DEST_DIR/${base}_${stamp}.svg"
    echo "  name clash with different content -> saving as $(basename "$target")"
  fi

  src_hash="$(shasum -a 256 "$file" | awk '{print $1}')"
  mv "$file" "$target"
  dst_hash="$(shasum -a 256 "$target" | awk '{print $1}')"

  if [ "$src_hash" != "$dst_hash" ]; then
    echo "  ERROR: hash mismatch after move, file may be corrupt"
    rejected=$((rejected+1)); continue
  fi

  echo "  moved -> $(basename "$target")"
  moved=$((moved+1))
done

echo
echo "Done. moved: $moved  skipped: $skipped  rejected: $rejected"
