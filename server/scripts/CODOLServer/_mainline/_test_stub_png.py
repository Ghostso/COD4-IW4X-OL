from PIL import Image
import io

path = r"COD OL\IIPS\TPFUI\IIPSRes\back\SystemSetting\button.png"
blob = open(path, "rb").read()
try:
    img = Image.open(io.BytesIO(blob))
    img.load()
    print("PIL OK mode=%s size=%s format=%s" % (
        img.mode, img.size, img.format))
except Exception as exc:
    print("PIL FAIL %s" % exc)
