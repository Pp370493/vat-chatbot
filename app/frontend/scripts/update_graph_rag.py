"""
นำหน้า Graph RAG ที่สร้างจากฝั่งข้อมูลประกาศ (branch chunking-import) มาไว้ให้หน้าแชทเปิดได้

    # บน branch chunking-import
    python chunking/scripts/build_graph_data.py --out graph_data.json --html chunking/reports/graph_view.html
    # แล้วที่ app/frontend
    python scripts/update_graph_rag.py <path ถึง graph_view.html>

ไฟล์ต้นทางเป็นเนื้อหาหน้า (ไม่มี <html>/<head>) — สคริปต์ห่อเป็นหน้า HTML เต็มที่ public/graph-rag.html
"""
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
head, sep, body = src.partition("</style>")
if not sep:
    raise SystemExit("ไม่พบ </style> ในไฟล์ต้นทาง")
page = (
    '<!doctype html>\n<html lang="th">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    "<style>body{margin:0}[hidden]{display:none!important}</style>\n"
    f"{head}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
)
out = Path(__file__).resolve().parent.parent / "public" / "graph-rag.html"
out.write_text(page, encoding="utf-8")
print(f"เขียน {out} ({len(page) // 1024} KB)")
