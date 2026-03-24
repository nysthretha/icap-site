# ICAP Nobet Cizelgesi

Hastane doktorlari icin aylik nobet planlama ve takip sistemi.

## Ozellikler

### Takvim Gorunumu
- Bir sonraki ayin takvimi otomatik olarak goruntulenir
- Is gunleri, hafta sonlari ve resmi tatiller farkli renklerle isaretlenir
- Her gun icin nobet suresi belirtilir: is gunleri **16 saat**, hafta sonu ve tatiller **24 saat**

### Turk Resmi Tatilleri
- Sabit resmi tatiller otomatik olarak hesaplanir (Cumhuriyet Bayrami, 23 Nisan, 19 Mayis, 1 Mayis, 15 Temmuz, 30 Agustos, Yilbasi)
- Dini bayramlar (Ramazan Bayrami ve Kurban Bayrami) Hicri takvim uzerinden otomatik hesaplanir
- Bayram arifeleri de tatil olarak islenir

### Nobet Secimi
- Doktorlar sisteme giris yaparak nobet gunlerini secerler
- Ayni uzmanliktaki iki doktor ayni gune nobet koyamaz (ornegin 2 Ortopedi doktoru farkli gunler secmelidir)
- Secimler anlik olarak takvim uzerinde goruntulenir
- Baska doktorlarin secimleri de takvimde gorunur

### Toplam Saat Takibi
- Her doktorun toplam nobet saati takvimin altinda canli olarak guncellenir
- Secim yapildikca veya kaldirilacak toplam saatler anlik degisir

### Onizleme ve Kesinlestirme
- Doktorlar secimlerini tablo formatinda onizleyebilir (tarihler satirlarda, uzmanliklar sutunlarda)
- Onizleme tablosunun altinda her uzmanlik icin toplam saat gosterilir
- Kesinlestirme sonrasi degisiklik yapilamaz

### Excel Ciktisi
- Nobet cizelgesi Excel dosyasi olarak indirilebilir
- Uzmanliklar sutunlarda, tarihler satirlarda gosterilir
- Is gunleri beyaz, tatil ve hafta sonlari acik gri arka plan ile isaretlenir
- Her uzmanlik icin toplam nobet saati dosyanin alt satirinda yer alir

## Kurulum

### Gereksinimler
- Python 3.10+
- Flask, hijridate, openpyxl, gunicorn

### Yerel Calistirma
```bash
pip install -r requirements.txt
python3 app.py
```
Tarayicida `http://127.0.0.1:5000` adresini acin.

### Railway Uzerinde Yayinlama
Proje Railway ile uyumludur. GitHub reposunu Railway'e baglayin, `SECRET_KEY` ortam degiskenini tanimlayin ve alan adi olusturun.

## Doktor Yonetimi

Doktor listesi `models.py` dosyasindaki `seed_doctors()` fonksiyonunda tanimlidir. Doktor eklemek veya cikarmak icin:

**Veritabanini sifirdan olusturmak icin:**
```bash
rm instance/oncall.db
python3 app.py
```

**Mevcut verileri koruyarak doktor eklemek icin:**
```bash
python3 -c "
from models import get_db
from werkzeug.security import generate_password_hash
conn = get_db()
conn.execute('INSERT INTO doctors (username, password_hash, full_name, specialty) VALUES (?, ?, ?, ?)',
    ('yenikullanici', generate_password_hash('sifre123'), 'Yeni Doktor', 'Uzmanlik'))
conn.commit()
conn.close()
"
```
