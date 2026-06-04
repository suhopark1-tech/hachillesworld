import os

from PIL import Image

SS_DIR = r"C:\Users\suhop\ebook\Agentic World Modeling 2027\HAchillesWorld\screenshots"
OUT_PDF = r"C:\Users\suhop\ebook\Agentic World Modeling 2027\HAchillesWorld\HAchillesWorld_사이트_스크린샷.pdf"  # noqa: E501

files = sorted([f for f in os.listdir(SS_DIR) if f.endswith(".png")])

A4_W = 2480  # A4 300dpi width (px)

images = []
for fname in files:
    path = os.path.join(SS_DIR, fname)
    img = Image.open(path).convert("RGB")

    # A4 폭에 맞게 비율 유지 리사이즈
    orig_w, orig_h = img.size
    ratio = A4_W / orig_w
    new_h = int(orig_h * ratio)
    resized = img.resize((A4_W, new_h), Image.LANCZOS)
    images.append(resized)
    print(f"  {fname}  {orig_w}x{orig_h} → {A4_W}x{new_h}")

# 첫 장을 기준으로 나머지를 append
images[0].save(
    OUT_PDF,
    save_all=True,
    append_images=images[1:],
    resolution=300,
)

size_mb = os.path.getsize(OUT_PDF) / (1024 * 1024)
print(f"\n저장 완료: {OUT_PDF}")
print(f"파일 크기: {size_mb:.1f} MB  |  총 {len(images)}페이지")
