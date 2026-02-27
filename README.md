# SentezCopycenter - Online Sipariş (V4)

Bu sürüm **otomatik baskı yapmaz**.
Site:
- dosya yükleme + hesaplama + sepet
- kargo alt limit kuralı
- “Fatura istiyorum” seçeneği (TC / Vergi no)
- siparişi kaydeder
- sipariş oluşturunca WhatsApp’a dekont mesajı açar

## Kurulum
1) `.env.example` kopyala → `.env`
2) `pip install -r requirements.txt`
3) `python app.py`
4) Aç: http://127.0.0.1:5500

## Ayarlar (.env)
- PRICE_BW / PRICE_COLOR / PAGES_PER_SHEET
- SHIPPING_ENABLED / FREE_SHIPPING_LIMIT / SHIPPING_FEE
- WHATSAPP_NUMBER / BANK_RECIPIENT_NAME / BANK_IBAN

## Admin
- http://127.0.0.1:5500/admin
- Durum güncelle: Dekont Bekleniyor → Baskıya Hazır → Basıldı → Kargolandı → Tamamlandı
- Kargo firması + takip no gir (manuel)
